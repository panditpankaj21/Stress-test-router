import asyncio
import random
import concurrent.futures
import time
import threading
from utils.logger import logger
from utils.command_runner import run_cmd


class StressScenarioManager:
    def __init__(
        self, duration, download_url, router_ip="192.168.1.1", dns_server="8.8.8.8"
    ):
        self.duration = duration
        self.download_url = download_url
        self.router_ip = router_ip
        self.dns_server = dns_server
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=20)

    def _run_task_blocking(self, ns, task_func, end_time, result_dict):
        count = 0
        while time.time() < end_time:
            task_func(ns)
            count += 1
        result_dict[ns] = count

    def _dns_query(self, ns):
        run_cmd(
            f"sudo ip netns exec {ns} dig +time=1 google.com @{self.dns_server}",
            suppress_output=True,
        )

    def _tcp_connect(self, ns):
        run_cmd(
            f"sudo ip netns exec {ns} "
            f"sh -c 'exec 3<>/dev/tcp/{self.router_ip}/80; exec 3<&-; exec 3>&-'",
            suppress_output=True,
        )

    def _http_router_hit(self, ns):
        run_cmd(
            f"sudo ip netns exec {ns} curl -m 2 -s -o /dev/null http://{self.router_ip}/",
            suppress_output=True,
        )

    def _print_global_progress(self, start_time):
        while time.time() - start_time < self.duration:
            elapsed = time.time() - start_time
            pct = min(int((elapsed / self.duration) * 100), 100)
            print(
                f"\rProgress: {pct:3d}% | Time left: {max(self.duration - int(elapsed),0):2d}s",
                end="",
                flush=True,
            )
            time.sleep(1)

        print("\rProgress: 100% | Done!                 ")

    async def start(self, namespaces):
        logger.info("======= STRESS TEST START =======")

        start_time = time.time()
        end_time = start_time + self.duration

        tasks = [self._dns_query, self._tcp_connect, self._http_router_hit]

        assigned = {}

        for ns in namespaces:
            assigned[ns] = random.choice(tasks)
            logger.info(f"{ns}: Task → {assigned[ns].__name__}")

        result_dict = {}
        loop = asyncio.get_running_loop()

        futures = [
            loop.run_in_executor(
                self.executor,
                self._run_task_blocking,
                ns,
                assigned[ns],
                end_time,
                result_dict,
            )
            for ns in namespaces
        ]

        progress_thread = threading.Thread(
            target=self._print_global_progress, args=(start_time,), daemon=True
        )
        progress_thread.start()

        await asyncio.gather(*futures)

        logger.info("\n======= COMPLETE =======")
        return result_dict
