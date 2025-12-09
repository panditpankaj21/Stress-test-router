import asyncio
from behave import given
from src.client_manager import NetworkManager
from utils.logger import logger


@given('I create "{count:d}" virtual clients using macvlan')
def step_create_clients(context, count):
    logger.info(f"--- GIVEN: Creating {count} Virtual Clients ---")

    context.net_mgr = NetworkManager(context.interface)
    asyncio.run(context.net_mgr.create_clients(count))
    logger.info(
        f"STATUS: {count} clients successfully created and assigned IP addresses."
    )
