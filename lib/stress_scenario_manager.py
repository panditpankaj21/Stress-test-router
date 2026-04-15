import asyncio
import time
import random
import struct
from utils.logger import logger
from utils.pi_health_check import health_worker
from utils.router_health import get_router_health


class StressScenarioManager:
    """
    Asyncio-based stress test - mirrors ping/download pattern
    Lightweight coroutines instead of heavy threads
    """

    def __init__(
        self, duration, router_ip="192.168.1.1", dns_server="8.8.8.8"
    ):
        self.duration = duration
        self.router_ip = router_ip
        self.dns_server = dns_server
        self.results = {}

    # ==================== ASYNCIO STRESS TASKS ====================

    async def _tcp_flood(self, ns, end_time):
        """
        Asyncio TCP flood using subprocess (like your ping code)
        """
        count = 0
        ports = [80, 443, 22, 23]
        
        while time.time() < end_time:
            try:
                # Use asyncio subprocess like your ping code
                for port in random.sample(ports, 3):
                    cmd = (
                        f"sudo ip netns exec {ns} "
                        f"timeout 0.3 bash -c "
                        f"'exec 3<>/dev/tcp/{self.router_ip}/{port} 2>/dev/null; "
                        f"exec 3<&-'"
                    )
                    
                    proc = await asyncio.create_subprocess_shell(
                        cmd,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL
                    )
                    await proc.communicate()
                    count += 1
                
                # Small delay to prevent machine overload
                await asyncio.sleep(0.001)
            except:
                await asyncio.sleep(0.001)
        
        return count

    async def _udp_flood(self, ns, end_time):
        """
        Asyncio UDP flood using netcat
        """
        count = 0
        
        while time.time() < end_time:
            try:
                # Send UDP packets using netcat (lighter than raw sockets)
                cmd = (
                    f"sudo ip netns exec {ns} timeout 0.2 bash -c '"
                    f"for i in {{1..50}}; do "
                    f"echo \"stress\" | nc -u -w0 {self.router_ip} 53 2>/dev/null; "
                    f"done'"
                )
                
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await proc.communicate()
                count += 50
                
                await asyncio.sleep(0.002)
            except:
                await asyncio.sleep(0.002)
        
        return count

    async def _http_download(self, ns, end_time):
        """
        Asyncio HTTP requests using curl (like your download code)
        """
        count = 0
        
        while time.time() < end_time:
            try:
                cmd = (
                    f"sudo ip netns exec {ns} "
                    f"curl -4 --silent --show-error --output /dev/null "
                    f"--max-time 1 --connect-timeout 0.5 "
                    f"http://{self.router_ip}/"
                )
                
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await proc.communicate()
                count += 1
                
                await asyncio.sleep(0.003)
            except:
                await asyncio.sleep(0.003)
        
        return count

    async def _dns_flood(self, ns, end_time):
        """
        Asyncio DNS flood using dig (like your ping uses ping command)
        """
        count = 0
        domains = [
            "google.com", "facebook.com", "amazon.com",
            "youtube.com", "twitter.com", "netflix.com"
        ]
        
        while time.time() < end_time:
            try:
                domain = random.choice(domains)
                cmd = (
                    f"sudo ip netns exec {ns} "
                    f"dig +time=1 +tries=1 +short {domain} @{self.dns_server}"
                )
                
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await proc.communicate()
                count += 1
                
                await asyncio.sleep(0.005)
            except:
                await asyncio.sleep(0.005)
        
        return count

    async def _icmp_flood(self, ns, end_time):
        """
        Asyncio ICMP flood using ping (exactly like your ping code)
        """
        count = 0
        
        while time.time() < end_time:
            try:
                cmd = (
                    f"sudo ip netns exec {ns} "
                    f"ping -c 5 -i 0.02 -W 1 {self.router_ip}"
                )
                
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await proc.communicate()
                count += 5
                
                await asyncio.sleep(0.01)
            except:
                await asyncio.sleep(0.01)
        
        return count

    # ==================== ASYNCIO WORKER (LIKE YOUR PING) ====================

    async def worker(self, ns, end_time):
        """
        Single worker that runs ALL stress tasks concurrently
        Uses asyncio.gather like your ping code
        """
        logger.info(f"{ns}: Starting asyncio hybrid stress")
        
        # Create tasks (like your ping code creates ping_tasks)
        tasks = [
            asyncio.create_task(self._tcp_flood(ns, end_time)),
            asyncio.create_task(self._udp_flood(ns, end_time)),
            asyncio.create_task(self._http_download(ns, end_time)),
            asyncio.create_task(self._dns_flood(ns, end_time)),
            asyncio.create_task(self._icmp_flood(ns, end_time)),
        ]
        
        # Wait for all tasks (like your ping code)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total = sum(r for r in results if isinstance(r, int))
        logger.info(f"{ns}: Completed {total:,} operations")
        return total

    async def _print_progress(self, start_time):
        """Progress monitor"""
        while time.time() - start_time < self.duration:
            elapsed = time.time() - start_time
            pct = min(int((elapsed / self.duration) * 100), 100)
            
            hrs = int(elapsed // 3600)
            mins = int((elapsed % 3600) // 60)
            secs = int(elapsed % 60)
            
            remain = max(self.duration - elapsed, 0)
            r_hrs = int(remain // 3600)
            r_mins = int((remain % 3600) // 60)
            r_secs = int(remain % 60)
            
            print(
                f"\rProgress: {pct:3d}% | "
                f"Elapsed: {hrs:02d}:{mins:02d}:{secs:02d} | "
                f"Remaining: {r_hrs:02d}:{r_mins:02d}:{r_secs:02d}",
                end="", flush=True
            )
            
            await asyncio.sleep(1)
        
        print("\rProgress: 100% | Complete!                                 ")

    # ==================== MAIN START (LIKE YOUR PING/DOWNLOAD) ====================

    async def start(self, namespaces):
        """
        Main entry - EXACTLY like your ping code structure
        """
        if not namespaces:
            raise AssertionError("No namespaces provided")

        logger.info("=" * 70)
        logger.info(f"ASYNCIO HYBRID STRESS TEST - {len(namespaces)} clients")
        logger.info(f"Duration: {self.duration}s ({self.duration/3600:.2f} hours)")
        logger.info(f"Pattern: Mirrors ping/download asyncio architecture")
        logger.info("=" * 70)

        start_time = time.time()
        end_time = start_time + self.duration

        # Health monitoring (like your ping code)
        stop_event_pi = asyncio.Event()
        stop_event_router = asyncio.Event()
        
        pi_task = asyncio.create_task(health_worker(stop_event_pi))
        router_task = asyncio.create_task(get_router_health(stop_event_router))
        # memory_router_task = asyncio.create_task(get_router_memory_health(stop_memory_router))

        # Create worker tasks (EXACTLY like your ping code)
        stress_tasks = [
            asyncio.create_task(self.worker(ns, end_time))
            for ns in namespaces
        ]

        # Progress monitor
        progress_task = asyncio.create_task(self._print_progress(start_time))

        try:
            # Wait for all workers (like your ping code)
            results = await asyncio.gather(*stress_tasks, return_exceptions=True)
            
            # Collect results
            for ns, count in zip(namespaces, results):
                if isinstance(count, int):
                    self.results[ns] = count
                else:
                    logger.error(f"{ns}: Task failed - {count}")
                    self.results[ns] = 0

        except Exception as e:
            logger.error(f"Critical error: {e}")
            raise

        finally:
            # Stop monitoring (like your ping code)
            stop_event_pi.set()
            stop_event_router.set()
            await asyncio.gather(
                pi_task, router_task, progress_task,
                return_exceptions=True
            )

        # Display results
        actual_duration = time.time() - start_time
        total_ops = sum(self.results.values())
        
        logger.info("\n" + "=" * 70)
        logger.info("STRESS TEST COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Total operations: {total_ops:,}")
        logger.info(f"Operations/second: {total_ops / actual_duration:.0f}")
        logger.info(f"Actual duration: {actual_duration:.2f}s")
        logger.info("=" * 70)

        # Validation (like your ping code)
        failed_ns = {ns: count for ns, count in self.results.items() if count == 0}
        if failed_ns:
            logger.warning(f"⚠ Zero operations for: {list(failed_ns.keys())}")

        return self.results