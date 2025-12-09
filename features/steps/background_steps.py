from behave import given
import os


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


@given("a 20MB ZIP file URL is configured as the download source")
def step_configure_file_url(context):

    context.download_url = context.config.get("DOWNLOAD_URL")

    assert context.download_url, "Download URL missing in config!"
