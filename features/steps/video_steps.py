import asyncio
from behave import when, then
from utils.logger import logger
from lib.video_manager import VideoManager


@when("all clients start streaming a video simultaneously")
def step_start_video_streaming(context):
    logger.info("----- PARALLEL VIDEO STREAMING (MPV) STARTED -----")
    vm = VideoManager(
        video_ids=context.config.get("video_ids"),
        duration=int(context.config.get("video_duration")),
    )
    context.video_results = asyncio.run(
        vm.start_parallel_streaming(context.net_mgr.client_namespaces)
    )
    logger.info("----- PARALLEL VIDEO STREAMING ENDED -----")


@then("each client should successfully stream for the given duration")
def step_validate_video_streaming(context):
    failed = [ns for ns, data in context.video_results.items() if not data["success"]]
    if failed:
        logger.error(f"Clients failed to stream: {', '.join(failed)}")
    assert len(failed) == 0, f"Some clients failed to stream video: {failed}"
    logger.info("All clients successfully streamed the video.")
