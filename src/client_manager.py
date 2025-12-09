import asyncio
import time
from utils.logger import logger
import subprocess
from unittest import SkipTest
from utils.command_runner import run_cmd
import shlex


class NetworkManager:
    def __init__(self, interface):
        self.parent_if = interface
        self.client_namespaces = []
        self.client_ips = {}
        self.isFailed = False
        self.count = 0

    async def wait_for_ip(self, namespace, interface, timeout=2):
        start = time.time()
        while time.time() - start < timeout:
            try:
                output_v4 = await run_cmd(
                    f"sudo ip netns exec {namespace} ip -4 addr show {interface}"
                )
                ip_v4 = None
                if "inet " in output_v4:
                    ip_v4 = output_v4.split("inet ")[1].split()[0]
                    ip_v4_only = ip_v4.split("/")[0]
                    self.client_ips[namespace] = ip_v4
                output_v6 = await run_cmd(
                    f"sudo ip netns exec {namespace} ip -6 addr show {interface}"
                )
                ip_v6_only = "none"
                if "inet6 " in output_v6:
                    ip_v6 = output_v6.split("inet6 ")[1].split()[0]
                    ip_v6_only = ip_v6.split("/")[0]
                if ip_v4:
                    logger.info(
                        f"{namespace} got IPv4: {ip_v4_only} and IPv6: {ip_v6_only}"
                    )
                    return True
            except subprocess.CalledProcessError:
                await asyncio.sleep(0.5)
        logger.warning(f"{namespace} did not get IP within {timeout}s.")
        return False

    async def cleanup(self):
        logger.info("----- IP is Not Alloated to some client, Aborting -----")
        try:
            output = await run_cmd("sudo ip netns list")
            namespaces = [line.split()[0] for line in output.splitlines() if line]
            for ns in namespaces:
                macvlan = f"macvlan{ns[2:]}"
                try:
                    output = await run_cmd(
                        f"sudo ip netns exec {ns} ip -4 addr show {macvlan}"
                    )
                    if "inet " in output:
                        await run_cmd(
                            f"sudo ip netns exec {ns} dhclient -r {macvlan} "
                            f"-pf /run/dhclient-{ns}.pid -lf /var/lib/dhcp/dhclient-{ns}.leases"
                        )
                        await run_cmd(
                            f"sudo ip netns exec {ns} dhclient -6 -r {macvlan} -pf "
                            f"/run/dhclient6-{ns}.pid -lf /var/lib/dhcp/dhclient6-{ns}.leases"
                        )
                    await run_cmd(f"sudo ip netns delete {ns}")
                    await run_cmd(f"sudo rm -rf /etc/netns/{ns}")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Failed to delete {ns}: {e}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list namespaces: {e}")
        logger.info("All client deleted Successfully that was created")

    async def create_client(self, i):
        ns = f"ns{i}"
        macvlan = f"macvlan{i}"
        mac = f"00:1A:80:{(i >> 8) & 0xff:02x}:{(i >> 4) & 0xff:02x}:{i & 0xff:02x}"
        self.client_namespaces.append(ns)
        try:
            await run_cmd(f"sudo ip netns add {ns}")
            await run_cmd(
                f"sudo ip link add link {self.parent_if} {macvlan} address {mac} type macvlan mode bridge"
            )
            await run_cmd(f"sudo ip link set {macvlan} netns {ns}")
            await run_cmd(f"sudo ip netns exec {ns} ip link set dev {macvlan} up")
            await run_cmd(f"sudo ip netns exec {ns} ip link set lo up")
            await run_cmd(
                f"sudo ip netns exec {ns} dhclient -v {macvlan} "
                f"-pf /run/dhclient-{ns}.pid -lf /var/lib/dhcp/dhclient-{ns}.leases &"
            )
            for attempt in range(4):
                if await self.wait_for_ip(ns, macvlan):
                    self.count += 1
                    await run_cmd(f"sudo mkdir -p /etc/netns/{ns}")
                    await run_cmd(
                        f"sudo ip netns exec {ns} dhclient -6 -v {macvlan} -pf "
                        f"/run/dhclient6-{ns}.pid -lf /var/lib/dhcp/dhclient6-{ns}.leases &"
                    )
                    await run_cmd(
                        f'echo "nameserver 8.8.8.8\nnameserver 1.1.1.1" | sudo tee /etc/netns/{ns}/resolv.conf'
                    )
                    return
                logger.warning(f"{ns} retrying IP acquisition ({attempt + 1}/4)...")
                await asyncio.sleep(1)
            self.isFailed = True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create {ns}: {e}")
            self.isFailed = True

    async def create_clients(self, count):
        tasks = [self.create_client(i) for i in range(1, count + 1)]
        await asyncio.gather(*tasks)
        logger.info(f"----- ONLY {self.count} / {count} got IP ------")
        self.count = 0
        if self.isFailed:
            self.isFailed = False
            raise SkipTest("Skipping scenario due to failed client creation")
        logger.info(f"Created {count} namespaces successfully.")

    def get_namespace_ip(self, ns):
        """Returns output of 'ip addr show' inside namespace."""
        cmd = f"sudo ip netns exec {ns} ip addr show"
        result = subprocess.run(
            shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return result.stdout.decode("utf-8")

    def ping_ip_from_ns(self, ns, ip):
        """Returns True/False based on ping output."""
        cmd = f"sudo ip netns exec {ns} ping -c 1 -W 1 {ip}"
        result = subprocess.run(
            shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return result.returncode == 0
