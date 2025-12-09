import asyncio
import time
import subprocess
from utils.logger import logger
from utils.pi_health_check import health_worker
from utils.command_runner import run_cmd


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
        start_ts = time.time()
        success = False
        try:
            await run_cmd(cmd, suppress_output=True)
            success = True
        except subprocess.CalledProcessError as e:
            if e.returncode in (124, 143):  # timeout exit codes
                success = True
            else:
                logger.error(f"[ERROR] {ns} mpv crashed with code {e.returncode}")
        except Exception as e:
            logger.error(f"[ERROR] {ns} mpv exception: {e}")
        elapsed = time.time() - start_ts
        if elapsed < (self.duration * 0.9):
            success = False
            logger.warning(f"{ns} stopped early ({elapsed:.2f}s / {self.duration}s)")
        result = {"success": success, "duration": elapsed}
        if success:
            logger.info(f"[OK] {ns} streamed {video_id} for {elapsed:.2f}s")
        else:
            logger.error(f"[FAIL] {ns} failed ({elapsed:.2f}s)")
        return result

    async def start_parallel_streaming(self, namespaces: list[str]) -> dict:
        stop_event = asyncio.Event()
        health_task = asyncio.create_task(health_worker(stop_event))
        tasks = [
            self._stream_with_mpv(ns, self.video_ids[i % len(self.video_ids)])
            for i, ns in enumerate(namespaces)
        ]
        results_list = await asyncio.gather(*tasks)
        stop_event.set()
        await health_task
        return {ns: res for ns, res in zip(namespaces, results_list)}
