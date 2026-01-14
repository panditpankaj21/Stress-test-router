import asyncio
import time
from prettytable import PrettyTable
from utils.logger import logger
from utils.pi_health_check import health_worker
from utils.router_health import get_router_health


async def run_cmd(cmd):
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
        max_concurrent=10,
    ):
        self.url = url
        self.worker_timeout = worker_timeout
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.failure_messages = {}  # ns -> failure reason

    async def verify_connectivity(self, ns):
        cmd = f"sudo ip netns exec {ns} ping -4 -c 1 -W 2 8.8.8.8"
        result = await run_cmd(cmd)
        return result["returncode"] == 0

    async def worker(self, ns, results):
        async with self.semaphore:

            if not await self.verify_connectivity(ns):
                msg = "No Internet connectivity"
                results[ns] = {
                    "success": False,
                    "duration": 0,
                    "speed": 0,
                    "error": msg,
                }
                self.failure_messages[ns] = msg
                return

            cmd = (
                f"sudo ip netns exec {ns} "
                f"timeout {self.worker_timeout} "
                f"curl -4 -L -s -o /dev/null "
                f"-w '%{{speed_download}} %{{time_total}}' "
                f"'{self.url}'"
            )

            start = time.time()
            result = await run_cmd(cmd)
            duration = time.time() - start

            if result["returncode"] != 0 or not result["stdout"]:
                msg = "Timeout/Error during download"
                results[ns] = {
                    "success": False,
                    "duration": round(duration, 2),
                    "speed": 0,
                    "error": msg,
                }
                self.failure_messages[ns] = msg
                return

            try:
                speed_bytes, time_total = result["stdout"].split()
                speed_mbps = (float(speed_bytes) * 8) / (1024 * 1024)

                results[ns] = {
                    "success": True,
                    "duration": round(float(time_total), 2),
                    "speed": round(speed_mbps, 2),
                    "error": "",
                }
            except Exception as e:
                msg = f"Parsing error: {e}"
                results[ns] = {
                    "success": False,
                    "duration": round(duration, 2),
                    "speed": 0,
                    "error": msg,
                }
                self.failure_messages[ns] = msg

    def display_results(self, results):
        table = PrettyTable()
        table.field_names = [
            "Namespace",
            "Status",
            "Time (s)",
            "Speed (Mbps)",
            "Remarks",
        ]

        table.align["Namespace"] = "l"
        table.align["Status"] = "c"
        table.align["Remarks"] = "l"

        success_count = 0

        for ns, data in sorted(results.items()):
            status = "OK" if data["success"] else "FAIL"
            if data["success"]:
                success_count += 1

            table.add_row(
                [
                    ns,
                    status,
                    data["duration"],
                    data["speed"],
                    data["error"],
                ]
            )

        logger.info(
            "\n"
            + "═" * 70
            + "\n"
            + f"DOWNLOAD SUMMARY | SUCCESS: {success_count}/{len(results)}"
            + "\n"
            + "═" * 70
        )
        logger.info(f"\n {table}" + "\n" + "═" * 70 + "\n")

    async def start_parallel_download(self, namespaces, global_timeout=300):
        logger.info(f"----- STARTING DOWNLOAD FOR {len(namespaces)} CLIENTS -----")

        results = {}
        stop_event_pi = asyncio.Event()
        stop_event_router = asyncio.Event()

        pi_task = asyncio.create_task(health_worker(stop_event_pi))
        router_task = asyncio.create_task(get_router_health(stop_event_router))

        tasks = [self.worker(ns, results) for ns in namespaces]

        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=global_timeout)
        except asyncio.TimeoutError:
            logger.error("!!! GLOBAL TIMEOUT REACHED !!!")
            self.failure_messages["GLOBAL"] = "Global timeout reached"
        finally:
            stop_event_pi.set()
            stop_event_router.set()

            await pi_task
            await router_task
            self.display_results(results)

        if self.failure_messages:
            details = "; ".join(
                [f"{ns}: {msg}" for ns, msg in self.failure_messages.items()]
            )
            raise AssertionError(f"Download test failed. Details: {details}")

        return results
