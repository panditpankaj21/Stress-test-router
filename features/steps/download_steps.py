import asyncio
from behave import when
from utils.logger import logger
from src.download_manager import DownloadManager


@when("all clients start downloading the 20MB ZIP file simultaneously")
def step_start_parallel_download(context):
    logger.info("----- PARALLEL DOWNLOAD STARTED -----")
    dm = DownloadManager(
        url=context.download_url, timeout=context.config.get("DOWNLOAD_TIMEOUT")
    )
    context.download_results = asyncio.run(
        dm.start_parallel_download(context.net_mgr.client_namespaces)
    )
    logger.info("----- PARALLEL DOWNLOAD ENDED -----")
