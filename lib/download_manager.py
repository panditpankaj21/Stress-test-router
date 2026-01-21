import asyncio
import time
from prettytable import PrettyTable
from utils.logger import logger
from utils.pi_health_check import health_worker
from utils.router_health import get_router_health


async def run_cmd(cmd):
    """Execute shell command asynchronously"""
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    return {
        "returncode": proc.returncode,
        "stdout": stdout.decode().strip() if stdout else "",
        "stderr": stderr.decode().strip() if stderr else "",
    }


class DownloadManager:
    def __init__(
        self,
        url="http://speedtest.tele2.net/10MB.zip",
        worker_timeout=60,
        max_concurrent=None,  # None = unlimited, or set a number for batching
        connect_timeout=10,
        max_retries=2,
    ):
        self.url = url
        self.worker_timeout = worker_timeout
        self.connect_timeout = connect_timeout
        self.max_retries = max_retries
        self.semaphore = asyncio.Semaphore(max_concurrent) if max_concurrent else None
        self.failure_messages = {}  # ns -> failure reason
        self.active_processes = {}  # ns -> process object for cleanup

    async def verify_connectivity(self, ns):
        """Check if namespace has internet connectivity"""
        cmd = f"sudo ip netns exec {ns} ping -4 -c 1 -W 2 8.8.8.8"
        result = await run_cmd(cmd)
        return result["returncode"] == 0

    async def download_with_retry(self, ns):
        """Download with retry logic"""
        for attempt in range(1, self.max_retries + 1):
            result = await self._execute_download(ns)
            
            if result["success"]:
                return result
            
            if attempt < self.max_retries:
                logger.warning(
                    f"{ns}: Attempt {attempt} failed, retrying... "
                    f"({result['error']})"
                )
                await asyncio.sleep(1)  # Small delay between retries
            else:
                logger.error(f"{ns}: All {self.max_retries} attempts failed")
                
        return result

    async def _execute_download(self, ns):
        """Execute single download attempt with optimized curl"""
        # Optimized curl command with proper timeouts and options
        cmd = (
            f"sudo ip netns exec {ns} "
            f"curl -4 "  # Force IPv4
            f"--location "  # Follow redirects
            f"--silent "  # Silent mode
            f"--show-error "  # Show errors even in silent mode
            f"--output /dev/null "  # Discard downloaded data
            f"--connect-timeout {self.connect_timeout} "  # Connection timeout
            f"--max-time {self.worker_timeout} "  # Total timeout
            f"--retry 0 "  # No curl internal retries (we handle it)
            f"--compressed "  # Accept compressed response
            f"--tcp-nodelay "  # Disable Nagle's algorithm for better speed
            f"--write-out '%{{size_download}} %{{speed_download}} %{{time_total}} %{{http_code}}' "
            f"'{self.url}'"
        )

        start = time.time()
        result = await run_cmd(cmd)
        duration = time.time() - start

        # Parse result
        if result["returncode"] != 0:
            error_msg = result["stderr"] or "Download failed"
            return {
                "success": False,
                "duration": round(duration, 2),
                "speed": 0,
                "size": 0,
                "http_code": 0,
                "error": f"curl error (code {result['returncode']}): {error_msg}",
            }

        if not result["stdout"]:
            return {
                "success": False,
                "duration": round(duration, 2),
                "speed": 0,
                "size": 0,
                "http_code": 0,
                "error": "Empty response from curl",
            }

        try:
            parts = result["stdout"].split()
            if len(parts) != 4:
                raise ValueError(f"Expected 4 values, got {len(parts)}")

            size_bytes = float(parts[0])
            speed_bytes = float(parts[1])
            time_total = float(parts[2])
            http_code = int(parts[3])

            # Convert speed to Mbps
            speed_mbps = (speed_bytes * 8) / (1024 * 1024)
            size_mb = size_bytes / (1024 * 1024)

            # Check HTTP status
            if http_code != 200:
                return {
                    "success": False,
                    "duration": round(time_total, 2),
                    "speed": round(speed_mbps, 2),
                    "size": round(size_mb, 2),
                    "http_code": http_code,
                    "error": f"HTTP {http_code}",
                }

            # Success
            return {
                "success": True,
                "duration": round(time_total, 2),
                "speed": round(speed_mbps, 2),
                "size": round(size_mb, 2),
                "http_code": http_code,
                "error": "",
            }

        except (ValueError, IndexError) as e:
            return {
                "success": False,
                "duration": round(duration, 2),
                "speed": 0,
                "size": 0,
                "http_code": 0,
                "error": f"Parse error: {str(e)} | Output: {result['stdout']}",
            }

    async def worker(self, ns, results):
        """Worker task for downloading in a namespace"""
        
        async def _work():
            # Verify connectivity first
            if not await self.verify_connectivity(ns):
                msg = "No Internet connectivity"
                results[ns] = {
                    "success": False,
                    "duration": 0,
                    "speed": 0,
                    "size": 0,
                    "http_code": 0,
                    "error": msg,
                }
                self.failure_messages[ns] = msg
                return

            # Download with retry
            result = await self.download_with_retry(ns)
            results[ns] = result
            
            if not result["success"]:
                self.failure_messages[ns] = result["error"]

        # Use semaphore if configured (for batching)
        if self.semaphore:
            async with self.semaphore:
                await _work()
        else:
            # Truly parallel - no throttling
            await _work()

    def display_results(self, results):
        """Display download results in a formatted table"""
        table = PrettyTable()
        table.field_names = [
            "Namespace",
            "Status",
            "Time (s)",
            "Speed (Mbps)",
            "Size (MB)",
            "HTTP",
            "Remarks",
        ]

        table.align["Namespace"] = "l"
        table.align["Status"] = "c"
        table.align["Remarks"] = "l"

        success_count = 0
        total_speed = 0
        total_time = 0

        for ns, data in sorted(results.items()):
            status = "✓ OK" if data["success"] else "✗ FAIL"
            if data["success"]:
                success_count += 1
                total_speed += data["speed"]
                total_time += data["duration"]

            table.add_row(
                [
                    ns,
                    status,
                    data["duration"],
                    data["speed"],
                    data.get("size", 0),
                    data.get("http_code", 0) or "-",
                    data["error"],
                ]
            )

        # Calculate averages
        avg_speed = round(total_speed / success_count, 2) if success_count > 0 else 0
        avg_time = round(total_time / success_count, 2) if success_count > 0 else 0

        logger.info(
            "\n"
            + "═" * 90
            + "\n"
            + f"DOWNLOAD SUMMARY | SUCCESS: {success_count}/{len(results)} | "
            + f"AVG SPEED: {avg_speed} Mbps | AVG TIME: {avg_time}s"
            + "\n"
            + "═" * 90
        )
        logger.info(f"\n{table}\n" + "═" * 90 + "\n")

    async def start_parallel_download(self, namespaces, global_timeout=300):
        """Start parallel downloads for all namespaces"""
        logger.info(
            f"----- STARTING {'BATCHED' if self.semaphore else 'PARALLEL'} "
            f"DOWNLOAD FOR {len(namespaces)} CLIENTS -----"
        )

        results = {}
        stop_event_pi = asyncio.Event()
        stop_event_router = asyncio.Event()

        # Start health monitoring tasks
        pi_task = asyncio.create_task(health_worker(stop_event_pi))
        router_task = asyncio.create_task(get_router_health(stop_event_router))

        # Create all worker tasks
        tasks = [asyncio.create_task(self.worker(ns, results)) for ns in namespaces]

        try:
            # Wait for all downloads to complete or timeout
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=global_timeout
            )
        except asyncio.TimeoutError:
            logger.error("!!! GLOBAL TIMEOUT REACHED !!!")
            self.failure_messages["GLOBAL"] = "Global timeout reached"
            
            # Cancel remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for cancellations to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Unexpected error during downloads: {e}")
            self.failure_messages["EXCEPTION"] = str(e)
            
        finally:
            # Stop health monitoring
            stop_event_pi.set()
            stop_event_router.set()

            # Wait for health tasks to finish
            await asyncio.gather(pi_task, router_task, return_exceptions=True)
            
            # Display results
            self.display_results(results)

        # Raise exception if there were failures
        if self.failure_messages:
            details = "; ".join(
                [f"{ns}: {msg}" for ns, msg in self.failure_messages.items()]
            )
            raise AssertionError(f"Download test failed. Details: {details}")

        return results