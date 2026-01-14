import asyncio
from utils.logger import logger
from utils.pi_health_check import health_worker
from utils.router_health import get_router_health


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


class VideoManager:
    def __init__(self, video_ids: list[str], duration: int):
        self.video_ids = video_ids
        self.duration = duration

    async def _stream_with_mpv(self, ns: str, video_id: str) -> dict:
        url = f"https://www.youtube.com/watch?v={video_id}"
        cmd = (
            f"sudo ip netns exec {ns} "
            f"timeout {self.duration}s "
            f"mpv --ytdl-format=bestvideo+bestaudio "
            f"--ao=null --vo=null --no-terminal --no-cache "
            f"{url}"
        )

        result = await run_cmd(cmd)

        is_success = result["returncode"] in [0, 124]

        if not is_success:
            logger.error(
                f"[ERROR] {ns} stream failed. Code: {result['returncode']} | Stderr: {result['stderr']}"
            )

        return {
            "success": is_success,
            "returncode": result["returncode"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
        }

    async def start_parallel_streaming(self, namespaces: list[str]) -> dict:
        stop_event_pi = asyncio.Event()
        stop_event_router = asyncio.Event()

        tasks = [
            self._stream_with_mpv(ns, self.video_ids[i % len(self.video_ids)])
            for i, ns in enumerate(namespaces)
        ]

        pi_task = asyncio.create_task(health_worker(stop_event_pi))
        router_task = asyncio.create_task(get_router_health(stop_event_router))

        results_list = await asyncio.gather(*tasks)

        stop_event_pi.set()
        stop_event_router.set()
        await pi_task
        await router_task

        return {ns: res for ns, res in zip(namespaces, results_list)}
