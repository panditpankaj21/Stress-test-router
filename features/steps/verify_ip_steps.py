import re
from behave import then
from utils.logger import logger


def extract_ip(output):
    """Extract IPv4 address from ip addr show."""
    match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)/", output)
    return match.group(1) if match else None


@then("no two clients should receive the same IP address")
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
