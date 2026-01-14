import asyncio
from behave import given, when
from utils.logger import logger
from lib.download_manager import DownloadManager


@given("the download target URL is configured")
def step_configure_file_url(context):

    context.download_url = context.config.get("DOWNLOAD_URL")

    assert context.download_url, "Download URL missing in config!"


@when("all clients start downloading the configured file simultaneously")
def step_start_parallel_download(context):
    logger.info("----- PARALLEL DOWNLOAD STARTED -----")
    dm = DownloadManager()
    context.download_results = asyncio.run(
        dm.start_parallel_download(context.net_mgr.client_namespaces)
    )
    logger.info("----- PARALLEL DOWNLOAD ENDED -----")
