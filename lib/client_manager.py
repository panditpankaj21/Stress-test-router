import asyncio
import time
import subprocess
import shlex
from utils.logger import logger
from utils.command_runner import run_cmd
from prettytable import PrettyTable


class NetworkManager:
    def __init__(self, interface):
        self.parent_if = interface
        self.client_namespaces = []
        self.client_ips = {}
        self.client_info = (
            {}
        )  # ns -> {"mac": str, "ipv4": str, "ipv6": str, "status": str}
        self.count = 0
        self.failure_messages = {}  # ns -> failure reason

    async def wait_for_ip(self, namespace, interface, mac, timeout=20):
        start = time.time()
        ipv4_only, ipv6_only = None, None
        while time.time() - start < timeout:
            try:
                output_v4 = await run_cmd(
                    f"sudo ip netns exec {namespace} ip -4 addr show {interface}"
                )
                if "inet " in output_v4:
                    ip_v4 = output_v4.split("inet ")[1].split()[0]
                    ipv4_only = ip_v4.split("/")[0]
                    self.client_ips[namespace] = ip_v4

                output_v6 = await run_cmd(
                    f"sudo ip netns exec {namespace} ip -6 addr show {interface}"
                )
                if "inet6 " in output_v6:
                    ip_v6 = output_v6.split("inet6 ")[1].split()[0]
                    ipv6_only = ip_v6.split("/")[0]

                if ipv4_only:
                    logger.info(
                        f"{namespace} got IPv4: {ipv4_only} and IPv6: {ipv6_only or 'Not created'}"
                    )
                    self.client_info[namespace] = {
                        "mac": mac,
                        "ipv4": ipv4_only,
                        "ipv6": ipv6_only or "Not created",
                        "status": "Created",
                    }
                    return True
            except subprocess.CalledProcessError:
                await asyncio.sleep(0.5)

        # Timeout case
        msg = f"{namespace} did not get IP within {timeout}s."
        logger.warning(msg)
        self.client_info[namespace] = {
            "mac": mac,
            "ipv4": "Not created",
            "ipv6": "Not created",
            "status": "Not created",
        }
        self.failure_messages[namespace] = msg
        return False

    async def cleanup(self):
        logger.info("----- Cleaning up namespaces -----")
        try:
            output = await run_cmd("sudo ip netns list")
            namespaces = [line.split()[0] for line in output.splitlines() if line]
            for ns in namespaces:
                # macvlan = f"macvlan{ns[2:]}"
                try:
                    await run_cmd(f"sudo ip netns delete {ns}")
                    await run_cmd(f"sudo rm -rf /etc/netns/{ns}")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Failed to delete {ns}: {e}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list namespaces: {e}")
        logger.info("All clients deleted successfully.")

    async def create_client(self, i):
        ns = f"ns{i}"
        macvlan = f"macvlan{i}"
        mac = f"00:1A:80:{(i >> 8) & 0xff:02x}:{(i >> 4) & 0xff:02x}:{i & 0xff:02x}"
        self.client_namespaces.append(ns)
        self.client_info[ns] = {
            "mac": "Not created",
            "ipv4": "Not created",
            "ipv6": "Not created",
            "status": "Not created",
        }
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

            await run_cmd(
                f"sudo ip netns exec {ns} dhclient -6 -v {macvlan} -pf "
                f"/run/dhclient6-{ns}.pid -lf /var/lib/dhcp/dhclient6-{ns}.leases &"
            )

            for attempt in range(4):
                if await self.wait_for_ip(ns, macvlan, mac):
                    self.count += 1
                    await run_cmd(f"sudo mkdir -p /etc/netns/{ns}")

                    await run_cmd(
                        f'echo "nameserver 8.8.8.8\nnameserver 1.1.1.1" | sudo tee /etc/netns/{ns}/resolv.conf'
                    )
                    return
                logger.warning(f"{ns} retrying IP acquisition ({attempt + 1}/4)...")
                await asyncio.sleep(1)

            # Retries exhausted
            msg = f"{ns} failed to acquire IP after 4 attempts."
            logger.error(msg)
            self.failure_messages[ns] = msg

        except subprocess.CalledProcessError as e:
            msg = f"Failed to create {ns}: {e}"
            logger.error(msg)
            self.failure_messages[ns] = msg

    async def create_clients(self, count):
        tasks = [self.create_client(i) for i in range(1, count + 1)]
        await asyncio.gather(*tasks)
        logger.info(f"----- ONLY {self.count} / {count} got IP ------")
        self.count = 0

        self.display_client_table()

        if self.failure_messages:
            details = "; ".join(
                [f"{ns}: {msg}" for ns, msg in self.failure_messages.items()]
            )
            await self.cleanup()
            raise AssertionError(f"Client creation failed. Details: {details}")

        logger.info(f"Created {count} namespaces successfully.")

    def display_client_table(self):
        table = PrettyTable()
        table.field_names = ["Namespace", "MAC", "IPv4", "IPv6", "Status"]
        table.align["Namespace"] = "l"
        table.align["MAC"] = "l"
        table.align["IPv4"] = "l"
        table.align["IPv6"] = "l"
        table.align["Status"] = "c"

        created_count = 0
        for ns, info in sorted(self.client_info.items()):
            if info["status"] == "Created":
                created_count += 1
            table.add_row([ns, info["mac"], info["ipv4"], info["ipv6"], info["status"]])

        banner = "═" * 70
        logger.info(
            "\n"
            + banner
            + "\n"
            + f"CLIENT SUMMARY | Created: {created_count}/{len(self.client_info)}"
            + "\n"
            + banner
        )
        logger.info("\n" + str(table) + "\n" + banner + "\n")

    def get_namespace_ip(self, ns):
        cmd = f"sudo ip netns exec {ns} ip addr show"
        result = subprocess.run(
            shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return result.stdout.decode("utf-8")

    def ping_ip_from_ns(self, ns, ip):
        cmd = f"sudo ip netns exec {ns} ping -c 1 -W 1 {ip}"
        result = subprocess.run(
            shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return result.returncode == 0
