import asyncio
import re
from prettytable import PrettyTable
from utils.logger import logger


async def run_cmd(cmd):
    """Execute shell command asynchronously"""
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    return {
        "returncode": proc.returncode,
        "stdout": stdout.decode().strip() if stdout else "",
        "stderr": stderr.decode().strip() if stderr else "",
    }


class RouteVerifier:
    """Verify network routing path for downloads"""

    def __init__(self, expected_router_ip=None, isIPV6=False):
        self.expected_router_ip = expected_router_ip
        logger.info(f"Expected Router is: {self.expected_router_ip} \n")
        self.isIPV6 = isIPV6
        self.route_cache = {}

    async def get_default_gateway(self, ns):
        """Get default gateway for namespace"""
        cmd = f"sudo ip netns exec {ns} ip route show default"
        result = await run_cmd(cmd)

        if result["returncode"] != 0:
            return None

        # Parse: default via 192.168.1.1 dev eth0
        match = re.search(r'default via ([\d.]+)', result["stdout"])
        if match:
            return match.group(1)
        return None

    async def get_route_to_destination(self, ns, destination):
        """Get route to specific destination"""

        if self.isIPV6:
            return {
                "gateway": self.expected_router_ip,
                "interface": None,
                "error": None,
            }

        cmd = f"sudo ip netns exec {ns} ip route get {destination}"
        result = await run_cmd(cmd)

        if result["returncode"] != 0:
            return {"gateway": None, "interface": None, "error": result["stderr"]}

        # Parse: 8.8.8.8 via 192.168.1.1 dev eth0 src 192.168.1.100
        gateway = None
        interface = None

        via_match = re.search(r'via ([\d.]+)', result["stdout"])
        if via_match:
            gateway = via_match.group(1)

        dev_match = re.search(r'dev (\S+)', result["stdout"])
        if dev_match:
            interface = dev_match.group(1)

        return {
            "gateway": gateway,
            "interface": interface,
            "raw": result["stdout"],
            "error": None,
        }

    async def traceroute_first_hops(self, ns, destination, max_hops=3):
        """Get first few hops via traceroute"""
        if self.isIPV6:
            cmd = (
                f"sudo ip netns exec {ns} "
                f"traceroute -6 -n -m {max_hops} -q 1 -w 2 {destination} 2>/dev/null"
            )
        else:
            cmd = (
                f"sudo ip netns exec {ns} "
                f"traceroute -4 -n -m {max_hops} -q 1 -w 2 {destination} 2>/dev/null"
            )

        result = await run_cmd(cmd)

        if result["returncode"] != 0:
            return []

        if self.isIPV6:
            hops = []
            for line in result["stdout"].split('\n'):
                # Parse: " 1  2001:db8::1  0.5 ms"
                match = re.search(r'^\s*(\d+)\s+([\da-f:]+|\*)', line)
                if match:
                    hop_num = int(match.group(1))
                    hop_ip = match.group(2) if match.group(2) != '*' else None
                    hops.append({"hop": hop_num, "ip": hop_ip})
            return hops
        else:
            hops = []
            for line in result["stdout"].split('\n'):
                # Parse: " 1  192.168.1.1  0.5 ms"
                match = re.search(r'^\s*(\d+)\s+([\d.]+|\*)', line)
                if match:
                    hop_num = int(match.group(1))
                    hop_ip = match.group(2) if match.group(2) != '*' else None
                    hops.append({"hop": hop_num, "ip": hop_ip})
            return hops

    async def verify_route(self, ns, destination="8.8.8.8"):
        """Complete route verification"""
        route_info = {
            "namespace": ns,
            "gateway": None,
            "first_hop": None,
            "via_router": False,
            "route_type": "unknown",
            "hops": [],
            "error": None,
        }

        try:
            # Get default gateway
            if not self.isIPV6:
                gateway = await self.get_default_gateway(ns)
                route_info["gateway"] = gateway
            else:
                gateway = self.expected_router_ip
                route_info["gateway"] = self.expected_router_ip

            # Get route to destination
            route = await self.get_route_to_destination(ns, destination)
            if route["error"]:
                route_info["error"] = route["error"]
                return route_info

            # Get first few hops
            hops = await self.traceroute_first_hops(ns, destination, max_hops=3)
            route_info["hops"] = hops

            if hops and hops[0]["ip"]:
                route_info["first_hop"] = hops[0]["ip"]

            # Determine if going through router
            if gateway and route_info["first_hop"]:
                route_info["via_router"] = gateway == route_info["first_hop"]

                if self.expected_router_ip:
                    if route_info["first_hop"] == self.expected_router_ip:
                        route_info["route_type"] = "via_expected_router"
                    elif route_info["via_router"]:
                        route_info["route_type"] = "via_different_router"
                    else:
                        route_info["route_type"] = "direct_or_unknown"
                else:
                    route_info["route_type"] = (
                        "via_router" if route_info["via_router"] else "direct"
                    )

            # Cache the result
            self.route_cache[ns] = route_info

        except Exception as e:
            route_info["error"] = str(e)

        return route_info

    def display_route_summary(self, route_results):
        """Display routing verification results"""
        table = PrettyTable()
        table.field_names = [
            "Namespace",
            "Gateway",
            "First Hop",
            "Via Router",
            "Route Type",
            "Status",
        ]

        table.align["Namespace"] = "l"
        table.align["Via Router"] = "c"
        table.align["Status"] = "c"

        via_router_count = 0
        direct_count = 0

        for result in route_results:
            via_router = "✓" if result["via_router"] else "✗"
            status = "OK" if not result["error"] else "ERROR"

            if result["via_router"]:
                via_router_count += 1
            else:
                direct_count += 1

            table.add_row(
                [
                    result["namespace"],
                    result["gateway"] or "N/A",
                    result["first_hop"] or "N/A",
                    via_router,
                    result["route_type"],
                    status,
                ]
            )

        logger.info(
            "\n"
            + "═" * 90
            + "\n"
            + f"ROUTE VERIFICATION | VIA ROUTER: {via_router_count} | DIRECT: {direct_count}"
            + "\n"
            + "═" * 90
        )
        logger.info(f"\n{table}\n" + "═" * 90 + "\n")
