import asyncio
import random
import time
from utils.pi_health_check import health_worker
from utils.logger import logger


async def run_cmd(cmd, suppress_output=False):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=(
            asyncio.subprocess.DEVNULL if suppress_output else asyncio.subprocess.PIPE
        ),
        stderr=(
            asyncio.subprocess.DEVNULL if suppress_output else asyncio.subprocess.PIPE
        ),
    )
    stdout, stderr = await proc.communicate()
    return {
        "returncode": proc.returncode,
        "stdout": None if suppress_output else stdout.decode(),
        "stderr": None if suppress_output else stderr.decode(),
    }


async def get_router_health(router_ssh, host, username, password, stop_event):
    while not stop_event.is_set():
        router_ssh.get_health()
        await asyncio.sleep(5)


class PingManager:
    def __init__(self, router_ssh, target_ip, ping_duration, ip_version):
        self.router_ssh = router_ssh
        self.target_ip = target_ip
        self.duration = ping_duration
        self.ip_version = ip_version
        self.failure_messages = {}  # ns -> failure reason

    async def worker(self, ns, end_time, results):
        success = True
        while time.time() < end_time:
            ping_cmd = "-6" if self.ip_version == "IPV6" else "-4"
            result = await run_cmd(
                f"sudo ip netns exec {ns} ping {ping_cmd} -c 1 -W 1 {self.target_ip}"
            )
            if result["returncode"] != 0:
                success = False
                msg = f"{ns} cannot reach {self.target_ip}"
                logger.error(f"[FAIL] {msg}")
                self.failure_messages[ns] = msg
            await asyncio.sleep(random.random() * 0.05)
        results[ns] = success

    async def run_test(self, namespaces):
        end_time = time.time() + self.duration
        results = {}

        stop_event_pi = asyncio.Event()
        stop_event_router = asyncio.Event()

        ping_tasks = [self.worker(ns, end_time, results) for ns in namespaces]

        pi_task = asyncio.create_task(health_worker(stop_event_pi))
        router_task = asyncio.create_task(
            get_router_health(
                self.router_ssh,
                "192.168.1.1",
                "operator",
                "Charter123",
                stop_event_router,
            )
        )

        await asyncio.gather(*ping_tasks)

        stop_event_pi.set()
        stop_event_router.set()

        await pi_task
        await router_task

        # Raise assertion if any failures
        if self.failure_messages:
            details = "; ".join(
                [f"{ns}: {msg}" for ns, msg in self.failure_messages.items()]
            )
            raise AssertionError(f"Ping test failed. Details: {details}")

        return results
