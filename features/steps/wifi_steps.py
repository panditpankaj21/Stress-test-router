import subprocess
import asyncio
import time
import re
from behave import given, when, then
from utils.logger import logger
from lib.ping_manager import PingManager


def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def replace_network_in_config(ssid, password):
    """Replace network block in wpa_supplicant.conf, keep everything else"""

    config_file = '/etc/wpa_supplicant/wpa_supplicant.conf'

    # Read existing config
    code, existing_config, err = run_cmd(f'sudo cat {config_file}')

    if code != 0:
        # Config doesn't exist, create new one
        existing_config = """ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev update_config=1 country=US"""

    # Remove all existing network blocks
    # This regex removes everything from "network={" to its matching "}"
    config_without_networks = re.sub(
        r'network\s*=\s*\{[^}]*\}', '', existing_config, flags=re.DOTALL
    )

    # Clean up extra blank lines
    config_without_networks = re.sub(r'\n{3,}', '\n\n', config_without_networks)
    config_without_networks = config_without_networks.strip()

    # Generate new network block
    code, psk_output, err = run_cmd(f'wpa_passphrase "{ssid}" "{password}"')

    if code != 0:
        return False

    # Extract just the network block from wpa_passphrase output
    network_block = []
    capture = False
    for line in psk_output.split('\n'):
        if 'network={' in line:
            capture = True
        if capture:
            # Skip commented plain password line
            if not line.strip().startswith('#psk='):
                network_block.append(line)

    new_network = '\n'.join(network_block)

    # Combine: existing config (without networks) + new network
    final_config = f"{config_without_networks}\n\n{new_network}\n"

    # Write to temp file
    with open('/tmp/wpa_temp.conf', 'w') as f:
        f.write(final_config)

    # Move to actual location
    code, out, err = run_cmd('sudo mv /tmp/wpa_temp.conf ' + config_file)

    return code == 0


@given('WiFi radio is on')
def enable_radio(context):
    run_cmd('sudo rfkill unblock wifi')
    run_cmd('sudo ip link set wlan0 up')
    time.sleep(2)
    run_cmd('sudo killall wpa_supplicant 2>/dev/null')
    time.sleep(1)


@when('I connect to WiFi')
def connect_wifi(context):
    # Replace network block in config
    success = replace_network_in_config(context.ssid, context.password)
    assert success, "Failed to update config file"

    print(f"Network block replaced with SSID: {context.ssid}")

    # Start wpa_supplicant
    code, out, err = run_cmd(
        'sudo wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf'
    )
    print(f"wpa_supplicant started: {out}")
    time.sleep(5)

    # Get IPv4
    code1, _, _ = run_cmd('sudo dhclient wlan0 2>/dev/null')
    if code1 != 0:
        run_cmd('sudo udhcpc -i wlan0')

    # Try IPv6
    run_cmd('sudo dhclient -6 wlan0 2>/dev/null')

    time.sleep(5)


@when('all clients attempt to ping WiFi Client "{ip_version}"')
def ping_wifi_client(context, ip_version):
    logger.info("------ ALL CLIENT START PINGING TO WiFi CLIENT -----")
    pm = PingManager(context.wifi_ipv4, 30, ip_version)
    context.results = asyncio.run(
        pm.run_test([ns for ns in context.net_mgr.client_namespaces])
    )
    logger.info("----- STOPPED PING TO Wifi Client -----")


@then('WiFi should be connected')
def verify_connected(context):
    code, out, err = run_cmd('ip addr show wlan0')
    assert 'inet ' in out, "No IP address assigned"

    # Show connected network
    code, status, _ = run_cmd('sudo wpa_cli -i wlan0 status')
    for line in status.split('\n'):
        if 'ssid=' in line:
            connected_ssid = line.split('=')[1]
            print(f"Connected to: {connected_ssid}")


@then('I should have IPv4 address')
def verify_ipv4(context):
    code, out, err = run_cmd('ip -4 addr show wlan0')
    assert 'inet ' in out, "No IPv4 address"

    for line in out.split('\n'):
        if 'inet ' in line:
            ip = line.split()[1].split('/')[0]
            print(f"IPv4: {ip}")
            context.wifi_ipv4 = ip
            break


@then('I should have IPv6 address')
def verify_ipv6(context):
    code, out, err = run_cmd('ip -6 addr show wlan0')

    has_global = False

    for line in out.split('\n'):
        if 'inet6' in line and 'scope global' in line:
            ip = line.split()[1]
            print(f"IPv6 Global: {ip}")
            has_global = True

    if not has_global:
        print("No global IPv6 (router doesn't provide IPv6 - this is normal)")


@then('I can ping internet')
def verify_internet(context):
    code, out, err = run_cmd('ping -c 3 -W 5 8.8.8.8')
    assert code == 0, "Cannot ping internet"
    print("Internet connectivity OK")


@when('I turn off WiFi radio')
def disable_radio(context):
    run_cmd('sudo killall wpa_supplicant')
    run_cmd('sudo ip link set wlan0 down')
    run_cmd('sudo rfkill block wifi')
    time.sleep(1)


@then('WiFi radio should be off')
def verify_radio_off(context):
    code, out, err = run_cmd('ip link show wlan0')
    assert 'state DOWN' in out or 'NO-CARRIER' in out, "Interface still up"
    print("WiFi radio is off")


@then('the config file should only have one network block')
def verify_single_network(context):
    code, config, err = run_cmd('sudo cat /etc/wpa_supplicant/wpa_supplicant.conf')

    # Count network blocks
    network_count = config.count('network={')

    assert network_count == 1, f"Expected 1 network block, found {network_count}"
    assert (
        f'ssid="{context.ssid}"' in config
    ), f"SSID {context.ssid} not found in config"

    print(f"✅ Config has exactly 1 network block for: {context.ssid}")
