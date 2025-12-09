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


class PingManager:
    def __init__(self, target_ip, ping_duration, ip_version):
        self.target_ip = target_ip
        self.duration = ping_duration
        self.ip_version = ip_version

    async def worker(self, ns, end_time, results):
        success = True
        while time.time() < end_time:
            ping_cmd = "-6" if self.ip_version == "IPV6" else "-4"
            result = await run_cmd(
                f"sudo ip netns exec {ns} ping {ping_cmd} -c 1 -W 1 {self.target_ip}"
            )
            if result["returncode"] != 0:
                success = False
                logger.error(f"[FAIL] {ns} cannot reach {self.target_ip}")
            await asyncio.sleep(random.random() * 0.05)
        results[ns] = success

    async def run_test(self, namespaces):
        end_time = time.time() + self.duration
        results = {}
        stop_event = asyncio.Event()
        ping_task = [self.worker(ns, end_time, results) for ns in namespaces]
        health_task = asyncio.create_task(health_worker(stop_event))
        await asyncio.gather(*ping_task)
        stop_event.set()
        await health_task
        return results
