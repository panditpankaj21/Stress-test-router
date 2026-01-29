import asyncio
from behave import given, when, then
from utils.logger import logger
from lib.ping_manager import PingManager
from lib.client_manager import NetworkManager


@given("I initialize the Network Manager")
def step_init_manager(context):
    assert hasattr(context, 'interface'), "Interface was not checked in previous steps!"
    context.net_mgr = NetworkManager(context.interface)


@when('I provision "{count:d}" virtual clients using macvlan')
def step_provision_clients(context, count):
    logger.info(f"----- Creating {count} Virtual Clients -----")

    asyncio.run(context.net_mgr.create_clients(count))
    logger.info(
        f"STATUS: {count} clients successfully created and assigned IP addresses."
    )


@when('all clients attempt to ping the router simultaneously using "{ip_version}"')
def step_ping_clients(context, ip_version):

    logger.info(f"----- PARALLEL CLIENT PING TO ROUTER STARTED ({ip_version}) -----")

    if ip_version == "IPV6":
        router_ip = context.router_IPV6
    elif ip_version == "IPV4":
        router_ip = context.router_IPV4
    else:
        raise Exception(f"Unknown IP version: {ip_version}")

    ping_duration = context.config.get("PING_DURATION")

    pm = PingManager(
        context.router_ssh,
        router_ip,
        ping_duration,
        "IPV4" if ip_version == "IPV4" else "IPV6",
    )

    context.results = asyncio.run(
        pm.run_test([ns for ns in context.net_mgr.client_namespaces])
    )
    logger.info("----- STOPPED PING -----")


@then("each client should successfully reach the router")
def step_validate_client_connectivity(context):
    failed = [ns for ns, success in context.results.items() if not success]
    assert len(failed) == 0, f"Clients failed to reach router: {', '.join(failed)}"
    logger.info("All clients successfully reached the router.")
