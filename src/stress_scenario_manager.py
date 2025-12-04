import asyncio
import random
import concurrent.futures
import time
import threading
import sys
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

        self.progress = {}
        self.lock = threading.Lock()

        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=30)

    def _print_progress(self):
        sys.stdout.write("\033[2J\033[H")  # clear screen
        print("======== Stress Test Progress ========")
        for ns, d in self.progress.items():
            pct = d["progress"]
            task = d["task"]
            bar = "█" * int(pct / 5) + "-" * (20 - int(pct / 5))
            print(f"{ns:<10} [{bar}] {pct:3d}% | {task} | Ops: {d['count']}")
        print("========================================")
        sys.stdout.flush()

    def _ui_loop(self, end_time):
        while time.time() < end_time:
            with self.lock:
                self._print_progress()
            time.sleep(0.5)
        with self.lock:
            self._print_progress()

    def _run_task_blocking(self, ns, task_func, end_time):
        count = 0
        while time.time() < end_time:
            task_func(ns)
            count += 1
            with self.lock:
                self.progress[ns]["count"] = count
                elapsed = self.progress[ns]["start"]
                pct = int(((time.time() - elapsed) / self.duration) * 100)
                self.progress[ns]["progress"] = min(pct, 100)
        return count

    def _dns_query(self, ns):
        run_cmd(
            f"sudo ip netns exec {ns} dig +time=1 google.com @{self.dns_server}",
            suppress_output=True,
        )

    def _tcp_connect(self, ns):
        cmd = (
            f"sudo ip netns exec {ns} "
            f"sh -c 'exec 3<>/dev/tcp/{self.router_ip}/80; exec 3<&-; exec 3>&-'"
        )
        run_cmd(cmd, suppress_output=True)

    def _http_router_hit(self, ns):
        run_cmd(
            f"sudo ip netns exec {ns} curl -m 2 -s -o /dev/null http://{self.router_ip}/"
        )

    async def _launch_namespace(self, ns, task, end_time):
        self.progress[ns] = {
            "task": task.__name__,
            "count": 0,
            "progress": 0,
            "start": time.time(),
        }
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            self.executor, self._run_task_blocking, ns, task, end_time
        )
        return {ns: result}

    async def start(self, namespaces):
        end_time = time.time() + self.duration
        results = {}

        tasks = [self._dns_query, self._tcp_connect, self._http_router_hit]

        assigned = {}

        for ns in namespaces:
            assigned[ns] = random.choice(tasks)
            logger.info(f"{ns}: Task → {assigned[ns].__name__}")

        ui_thread = threading.Thread(
            target=self._ui_loop, args=(end_time,), daemon=True
        )
        ui_thread.start()

        coros = [
            self._launch_namespace(ns, assigned[ns], end_time) for ns in namespaces
        ]
        r = await asyncio.gather(*coros)

        for obj in r:
            results.update(obj)

        logger.info("======= COMPLETE =======")
        return results
