import asyncio
import time
import random
from prettytable import PrettyTable
from utils.logger import logger
from utils.pi_health_check import health_worker
from utils.router_health import get_router_health
from lib.route_verifier import RouteVerifier
import psutil  # To capture system stats like CPU/Memory usage
import utils.config


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
        max_concurrent=None,
        connect_timeout=10,
        max_retries=2,
        verify_routes=True,
        expected_router_ip=None,
    ):
        self.url = url
        self.worker_timeout = worker_timeout
        self.connect_timeout = connect_timeout
        self.max_retries = max_retries
        self.verify_routes = verify_routes
        self.semaphore = asyncio.Semaphore(max_concurrent) if max_concurrent else None
        self.failure_messages = {}
        self.route_verifier = (
            RouteVerifier(expected_router_ip) if verify_routes else None
        )

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
                await asyncio.sleep(1)
            else:
                logger.error(f"{ns}: All {self.max_retries} attempts failed")

        return result

    async def _execute_download(self, ns):
        """Execute single download attempt with optimized curl"""
        cmd = (
            f"sudo ip netns exec {ns} "
            f"curl -4 "
            f"--location "
            f"--silent "
            f"--show-error "
            f"--output /dev/null "
            f"--connect-timeout {self.connect_timeout} "
            f"--max-time {self.worker_timeout} "
            f"--retry 0 "
            f"--compressed "
            f"--tcp-nodelay "
            f"--write-out '%{{size_download}} %{{speed_download}} %{{time_total}} %{{time_starttransfer}} %{{http_code}}' "
            f"'{self.url}'"
        )

        start = time.time()
        result = await run_cmd(cmd)
        duration = time.time() - start

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
            if len(parts) != 5:
                raise ValueError(f"Expected 5 values, got {len(parts)}")

            size_bytes = float(parts[0])
            speed_bytes = float(parts[1])
            time_total = float(parts[2])
            time_start_transfer = float(parts[3])
            http_code = int(parts[4])

            speed_mbps = (speed_bytes * 8) / (1024 * 1024)
            size_mb = size_bytes / (1024 * 1024)

            return {
                "success": True,
                "duration": round(time_total, 2),
                "speed": round(speed_mbps, 2),
                "size": round(size_mb, 2),
                "http_code": http_code,
                "start_transfer_time": round(time_start_transfer, 2),
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

            result = await self.download_with_retry(ns)
            results[ns] = result

            if not result["success"]:
                self.failure_messages[ns] = result["error"]

        if self.semaphore:
            async with self.semaphore:
                await _work()
        else:
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
            "Start Transfer Time (s)",
            "Remarks",
        ]

        table.align["Namespace"] = "l"
        table.align["Status"] = "c"
        table.align["Remarks"] = "l"

        success_count = 0
        total_speed = 0
        total_time = 0
        total_start_transfer = 0

        for ns, data in sorted(results.items()):
            status = "✓ OK" if data["success"] else "✗ FAIL"
            if data["success"]:
                success_count += 1
                total_speed += data["speed"]
                total_time += data["duration"]
                total_start_transfer += data.get("start_transfer_time", 0)

            table.add_row(
                [
                    ns,
                    status,
                    data["duration"],
                    data["speed"],
                    data.get("size", 0),
                    data.get("http_code", 0) or "-",
                    data.get("start_transfer_time", "-"),
                    data["error"],
                ]
            )

        avg_speed = round(total_speed / success_count, 2) if success_count > 0 else 0
        avg_time = round(total_time / success_count, 2) if success_count > 0 else 0
        avg_start_transfer_time = round(
            total_start_transfer / success_count, 2
        ) if success_count > 0 else 0

        logger.info(
            "\n"
            + "═" * 90
            + "\n"
            + f"DOWNLOAD SUMMARY | SUCCESS: {success_count}/{len(results)} | "
            + f"AVG SPEED: {avg_speed} Mbps | AVG TIME: {avg_time}s | "
            + f"AVG START TRANSFER TIME: {avg_start_transfer_time}s"
            + "\n"
            + "═" * 90
        )
        logger.info(f"\n{table}\n" + "═" * 90 + "\n")

    async def start_parallel_download(self, namespaces, global_timeout=300):
        """Start parallel downloads for all namespaces with route verification"""
        logger.info(
            f"----- STARTING {'BATCHED' if self.semaphore else 'PARALLEL'} "
            f"DOWNLOAD FOR {len(namespaces)} CLIENTS -----"
        )

        # Step 1: Verify routes BEFORE downloading (if enabled)
        route_results = []
        if self.verify_routes and self.route_verifier:
            logger.info("----- VERIFYING NETWORK ROUTES -----")
            route_tasks = [self.route_verifier.verify_route(ns) for ns in namespaces]
            route_results = await asyncio.gather(*route_tasks, return_exceptions=True)

            # Filter out exceptions
            route_results = [r for r in route_results if isinstance(r, dict)]

            # Display route verification results
            if route_results:
                self.route_verifier.display_route_summary(route_results)

            # Check if all routes go through expected router (optional strict check)
            if self.route_verifier.expected_router_ip:
                non_compliant = [
                    r["namespace"]
                    for r in route_results
                    if r["route_type"] != "via_expected_router"
                ]
                if non_compliant:
                    logger.warning(
                        f"WARNING: {len(non_compliant)} namespace(s) not using "
                        f"expected router: {', '.join(non_compliant)}"
                    )

        # Step 2: Start downloads
        results = {}
        stop_event_pi = asyncio.Event()
        stop_event_router = asyncio.Event()

        pi_task = asyncio.create_task(health_worker(stop_event_pi))
        router_task = asyncio.create_task(get_router_health(stop_event_router))

        tasks = [asyncio.create_task(self.worker(ns, results)) for ns in namespaces]

        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=global_timeout
            )
        except asyncio.TimeoutError:
            logger.error("!!! GLOBAL TIMEOUT REACHED !!!")
            self.failure_messages["GLOBAL"] = "Global timeout reached"

            for task in tasks:
                if not task.done():
                    task.cancel()

            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Unexpected error during downloads: {e}")
            self.failure_messages["EXCEPTION"] = str(e)

        finally:
            stop_event_pi.set()
            stop_event_router.set()

            await asyncio.gather(pi_task, router_task, return_exceptions=True)

            self.display_results(results)

        if self.failure_messages:
            details = "; ".join(
                [f"{ns}: {msg}" for ns, msg in self.failure_messages.items()]
            )
            raise AssertionError(f"Download test failed. Details: {details}")
        
        utils.config.metrics = results

        return {"download_results": results, "route_results": route_results}
