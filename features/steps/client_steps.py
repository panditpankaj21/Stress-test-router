from behave import given, when
from src.client_manager import NetworkManager
from src.ping_manager import PingManager
from utils.logger import logger
import asyncio
import yaml


def load_config():
    with open("config.yaml") as f:
        return yaml.safe_load(f)


@given('I launch 10 clients using the selected topology')
def step_launch_clients(context):
    config = load_config()
    topology = config.get("network", {}).get("topology", "wired")
    logger.info(f"--- GIVEN: Launching 10 {topology.upper()} Clients ---")

    async def create():
        if topology == "wired":
            context.net_mgr = NetworkManager(config["interface"])
            await context.net_mgr.create_clients(10)
        else:
            raise Exception(f"Unknown topology: {topology}")

    asyncio.run(create())
    logger.info("STATUS: Clients successfully created and assigned IP addresses.")


@when('all clients ping the router in parallel')
def step_ping_parallel(context):
    logger.info("------ PARALLEL CLIENT PING STARTED -----")
    pm = PingManager(context.router_ip, context.config.get("ping_duration"))
    namespaces = context.net_mgr.client_namespaces
    context.results = asyncio.run(pm.run_test(namespaces))
    logger.info("----- STOPPED PING -----")
