import re
import os
import yaml
import asyncio
from utils.logger import logger
from behave import given, when, then
from lib.ping_manager import PingManager
from lib.client_manager import NetworkManager


def load_config():
    with open("config.yaml") as f:
        return yaml.safe_load(f)


def extract_ip(output):
    """Extract IPv4 address from ip addr show."""
    match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)/", output)
    return match.group(1) if match else None


# ---------------------GIVEN STEPS --------------------- #
@given("the router IP address is configured")
def step_router_ip_configured(context):
    router_IPV4 = context.config.get("ROUTER_IPV4")
    router_IPV6 = context.config.get("ROUTER_IPV6")

    if router_IPV4 and router_IPV6:
        is_configured = True
    else:
        is_configured = False

    assert is_configured, "Router IP address is not configured."

    context.router_IPV4 = router_IPV4
    context.router_IPV6 = router_IPV6


@given("the base network interface is available on the system")
def step_interface_available(context):
    interface = context.config.get("INTERFACE")

    assert interface is not None, "Interface is not specified in the configuration."

    result = os.system(f"ip link show {interface} > /dev/null 2>&1")

    assert result == 0, f"Network interface {interface} is not available on the system."

    context.interface = interface


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


# ---------------------WHEN STEPS --------------------- #


@when('all clients attempt to ping the router simultaneously')
def step_ping_parallel(context):
    logger.info("------ PARALLEL CLIENT PING STARTED -----")
    pm = PingManager(context.router_ip, context.config.get("ping_duration"))
    namespaces = context.net_mgr.client_namespaces
    context.results = asyncio.run(pm.run_test(namespaces))
    logger.info("----- STOPPED PING -----")


# ---------------------THEN STEPS --------------------- #


@then("no two clients should have the same IP address")
def step_no_duplicate_ips(context):
    context.clients = context.net_mgr.client_ips
    ips = list(context.clients.values())
    duplicates = set([x for x in ips if ips.count(x) > 1])
    assert len(duplicates) == 0, f"Duplicate IPs found: {duplicates}"
    logger.info("All clients received unique IPs.")


@then("all assigned IPs should be reachable")
def step_validate_ip_reachability(context):
    for ns, ip in context.clients.items():
        ip_only = ip.split("/")[0]
        success = context.net_mgr.ping_ip_from_ns(ns, ip_only)
        assert success, f"{ns} could not ping its own assigned IP ({ip_only})"
    logger.info("All assigned IPs are reachable.")
