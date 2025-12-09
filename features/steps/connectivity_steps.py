import asyncio
from behave import when, then
from src.ping_manager import PingManager
from utils.logger import logger


@when('all clients attempt to ping the router simultaneously "{ip_version}"')
def step_ping_clients(context, ip_version):

    logger.info(ip_version)
    if ip_version == "IPV6":
        router_ip = context.router_IPV6
    else:
        router_ip = context.router_IPV4

    print(router_ip)

    logger.info("------ PARALLEL CLIENT PING STARTED -----")

    ping_duration = context.config.get("PING_DURATION")

    pm = PingManager(router_ip, ping_duration)

    context.results = asyncio.run(
        pm.run_test([ns for ns in context.net_mgr.client_namespaces])
    )
    logger.info("----- STOPPED PING -----")


@then("each client should successfully reach the router")
def step_validate_client_connectivity(context):
    failed = [ns for ns, success in context.results.items() if not success]
    assert len(failed) == 0, f"Clients failed to reach router: {', '.join(failed)}"
    logger.info("All clients successfully reached the router.")
