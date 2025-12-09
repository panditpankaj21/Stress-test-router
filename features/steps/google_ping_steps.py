import asyncio
from behave import when, then
from src.ping_manager import PingManager
from utils.logger import logger


@when('all clients attempt to ping Google DNS "{ip_version}"')
def step_ping_google(context, ip_version):
    logger.info("------ PARALLEL CLIENT PING TO GOOGLE DNS STARTED -----")

    if ip_version == "IPV6":
        google_dns_ip = "2001:4860:4860::8888"
    else:
        google_dns_ip = "8.8.8.8"

    ping_duration = context.config.get("PING_DURATION")

    pm = PingManager(google_dns_ip, ping_duration, ip_version)
    context.results = asyncio.run(
        pm.run_test([ns for ns in context.net_mgr.client_namespaces])
    )
    logger.info("----- STOPPED PING TO GOOGLE DNS -----")


@then("each client should successfully reach the internet")
def step_validate_ping(context):
    failed = [ns for ns, success in context.results.items() if not success]
    assert len(failed) == 0, f"Clients failed to reach Google DNS: {', '.join(failed)}"
    logger.info("All clients successfully reached Google DNS.")
