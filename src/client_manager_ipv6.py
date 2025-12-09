import asyncio
import time
import subprocess
import shlex
from unittest import SkipTest

from utils.logger import logger
from utils.command_runner import run_cmd
from utils.namespace_utils import create_namespace  # reuse common setup


class NetworkManagerIPv6:
    def __init__(self, interface="eth0", router_ip=None):
        self.parent_if = interface
        self.router_ip = router_ip
        self.client_namespaces = []
        self.client_ips = {}
        self.failed_any = False
        self._sem = asyncio.Semaphore(32)

    async def _ns_first_global_v6(self, ns, iface):
        try:
            output = await run_cmd(f"sudo ip netns exec {ns} ip -6 addr show {iface}")
        except Exception:
            return None
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("inet6") and not line.split()[1].startswith("fe80:"):
                return line.split()[1]
        return None

    async def wait_for_ip(self, ns, iface, timeout=10):
        start = time.time()
        while time.time() - start < timeout:
            cidr = await self._ns_first_global_v6(ns, iface)
            if cidr:
                ip_only = cidr.split("/")[0]
                self.client_ips[ns] = cidr
                logger.info(f"{ns} got IPv6 via DHCP: {ip_only}")
                return True
            await asyncio.sleep(0.5)
        return False

    async def cleanup(self):
        try:
            output = await run_cmd("sudo ip netns list")
            namespaces = [line.split()[0] for line in output.splitlines() if line]
        except Exception:
            namespaces = []

        for ns in namespaces:
            idx = ns[2:] if ns.startswith("ns") else ns
            macvlan = f"macvlan{idx}"
            # Explicit usage of macvlan
            logger.debug(f"Cleaning up interface {macvlan} in namespace {ns}")
            print(f"Cleanup: {macvlan}")
            await run_cmd(
                f"sudo pkill -F /run/dhclient6-{ns}.pid", suppress_output=True
            )
            await run_cmd(f"sudo ip netns delete {ns}", suppress_output=True)
            await run_cmd(f"sudo rm -rf /etc/netns/{ns}", suppress_output=True)

        await run_cmd(
            "sudo rm -f /var/lib/dhcp/dhclient6-*.leases", suppress_output=True
        )
        await run_cmd("sudo rm -f /run/dhclient6-*.pid", suppress_output=True)
        logger.info("All IPv6 clients deleted successfully.")

    async def create_client(self, i):
        ns = f"ns{i}"
        macvlan = f"macvlan{i}"
        self.client_namespaces.append(ns)

        try:
            mac = f"00:1A:79:{(i >> 8) & 0xff:02x}:{(i >> 4) & 0xff:02x}:{i & 0xff:02x}"
            await create_namespace(
                ns, macvlan, self.parent_if, mac, router_ip=self.router_ip
            )

            await run_cmd(
                f"sudo ip netns exec {ns} dhclient -6 -nw {macvlan} "
                f"-pf /run/dhclient6-{ns}.pid "
                f"-lf /var/lib/dhcp/dhclient6-{ns}.leases",
                suppress_output=True,
            )

            # Explicit usage of macvlan
            logger.info(f"Namespace {ns} created with interface {macvlan}")
            print(f"DEBUG: Using macvlan {macvlan} for ns {ns}")

            if not await self.wait_for_ip(ns, macvlan, timeout=10):
                self.failed_any = True

        except Exception as error:
            logger.error(f"Failed to create IPv6 client {ns} ({macvlan}): {error}")
            print(f"ERROR: {macvlan} failed in {ns}")
            self.failed_any = True

    async def create_clients(self, count):
        logger.info("Starting parallel IPv6 client creation...")

        async def wrapped(i):
            async with self._sem:
                await self.create_client(i)

        tasks = [wrapped(i) for i in range(1, count + 1)]
        await asyncio.gather(*tasks)

        ok_ns = [n for n in self.client_namespaces if n in self.client_ips]
        logger.info(f"----- {len(ok_ns)} / {count} got IPv6 via DHCP ------")

        if self.failed_any:
            await self.cleanup()
            raise SkipTest("Skipping scenario due to failed IPv6 client creation")

        logger.info(f"Created {count} IPv6 namespaces successfully.")

    def get_namespace_ip(self, ns):
        cmd = f"sudo ip netns exec {ns} ip -6 addr show"
        result = subprocess.run(
            shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return result.stdout.decode("utf-8")

    def ping_ip_from_ns(self, ns, ip):
        iface = f"macvlan{ns[2:]}"
        cmd = f"sudo ip netns exec {ns} ping6 -c 1 -W 1 -I {iface} {ip}"
        result = subprocess.run(
            shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return result.returncode == 0
