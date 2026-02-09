import asyncio
import time
import random
import re
from typing import List, Dict, Any
from prettytable import PrettyTable
from utils.logger import logger
from utils.pi_health_check import health_worker
from utils.router_health import get_router_health
from lib.route_verifier import RouteVerifier


async def run_exec(cmd_args: List[str]) -> Dict[str, Any]:
    """Execute a command securely without a shell (avoids injection risks)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        return {
            "returncode": proc.returncode,
            "stdout": stdout.decode().strip() if stdout else "",
            "stderr": stderr.decode().strip() if stderr else "",
        }
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e)}


class PingManager:
    def __init__(
        self,
        target_ip: str,
        duration: int = 10,
        ip_version: str = "IPV4",
        interval: float = 0.5,
        verify_routes=True,
        expected_router_ip=None,
    ):
        self.target_ip = target_ip
        self.duration = duration
        self.ip_version = ip_version
        self.interval = interval
        self.verify_routes = verify_routes
        logger.info(f"****the Second Update router ip is: {expected_router_ip}")
        self.route_verifier = (
            RouteVerifier(expected_router_ip, isIPV6=(ip_version == "IPV6"))
            if verify_routes
            else None
        )

        # Determine ping flag once
        self.ping_flag = "-6" if self.ip_version == "IPV6" else "-4"

        self.results: Dict[str, Any] = {}
        self.failure_messages: Dict[str, str] = {}

    async def _execute_single_ping(self, ns: str) -> Dict[str, Any]:
        """Runs a single ping and parses latency."""
        cmd = [
            "sudo",
            "ip",
            "netns",
            "exec",
            ns,
            "ping",
            self.ping_flag,
            "-c",
            "1",  # Send 1 packet
            "-W",
            "1",  # Wait max 1 second
            self.target_ip,
        ]

        result = await run_exec(cmd)

        if result["returncode"] != 0:
            return {"success": False, "latency": 0.0, "error": result["stderr"]}

        # Parse Latency (e.g., "time=14.2 ms")
        latency = 0.0
        try:
            # Regex to find time=X.X
            match = re.search(r"time=([\d.]+)", result["stdout"])
            if match:
                latency = float(match.group(1))
        except Exception:
            pass

        return {"success": True, "latency": latency, "error": ""}

    async def worker(self, ns: str):
        """Worker that runs pings for the specified duration and aggregates stats."""
        end_time = time.time() + self.duration

        stats = {
            "sent": 0,
            "received": 0,
            "total_latency": 0.0,
            "min_latency": 9999.0,
            "max_latency": 0.0,
            "errors": set(),
        }

        while time.time() < end_time:
            stats["sent"] += 1
            res = await self._execute_single_ping(ns)

            if res["success"]:
                stats["received"] += 1
                lat = res["latency"]
                stats["total_latency"] += lat
                stats["min_latency"] = min(stats["min_latency"], lat)
                stats["max_latency"] = max(stats["max_latency"], lat)
            else:
                # Capture unique errors
                clean_err = (
                    res["error"].replace(self.target_ip, "").strip() or "Timeout"
                )
                stats["errors"].add(clean_err)

                # Log only the first error to avoid flooding
                if len(stats["errors"]) == 1:
                    logger.debug(f"{ns}: Ping failed - {clean_err}")

            # Sleep with jitter to avoid packet bursts
            await asyncio.sleep(self.interval + random.uniform(0, 0.05))

        # Calculate final metrics for this namespace
        loss_pct = 0.0
        avg_lat = 0.0

        if stats["sent"] > 0:
            loss_pct = ((stats["sent"] - stats["received"]) / stats["sent"]) * 100

        if stats["received"] > 0:
            avg_lat = stats["total_latency"] / stats["received"]
        else:
            stats["min_latency"] = 0.0  # Reset if no packets received

        self.results[ns] = {
            "loss_pct": round(loss_pct, 1),
            "avg_latency": round(avg_lat, 2),
            "min_latency": round(stats["min_latency"], 2),
            "max_latency": round(stats["max_latency"], 2),
            "sent": stats["sent"],
            "received": stats["received"],
            "errors": list(stats["errors"]),
        }

        if loss_pct > 0:
            self.failure_messages[ns] = f"Loss {loss_pct}%"

    def display_results(self):
        """Display a PrettyTable summary similar to DownloadManager."""
        table = PrettyTable()
        table.field_names = [
            "Namespace",
            "Status",
            "Loss %",
            "Avg (ms)",
            "Min/Max (ms)",
            "Sent/Recv",
            "Remarks",
        ]
        table.align = "l"
        table.align["Loss %"] = "r"
        table.align["Avg (ms)"] = "r"
        table.align["Status"] = "c"

        total_sent = 0
        total_recv = 0
        namespaces_with_loss = 0

        for ns in sorted(self.results.keys()):
            data = self.results[ns]
            total_sent += data["sent"]
            total_recv += data["received"]

            # Determine Status
            if data["loss_pct"] == 0:
                status = "✓ OK"
            elif data["loss_pct"] < 100:
                status = "⚠ DEGRADED"
                namespaces_with_loss += 1
            else:
                status = "✗ FAIL"
                namespaces_with_loss += 1

            remarks = ", ".join(data["errors"]) if data["errors"] else ""

            table.add_row(
                [
                    ns,
                    status,
                    f"{data['loss_pct']}%",
                    f"{data['avg_latency']}",
                    f"{data['min_latency']}/{data['max_latency']}",
                    f"{data['sent']}/{data['received']}",
                    remarks,
                ]
            )

        # Global Stats
        global_loss = 0.0
        if total_sent > 0:
            global_loss = ((total_sent - total_recv) / total_sent) * 100

        logger.info(
            f"\n{'='*95}\n"
            f"PING SUMMARY | Target: {self.target_ip} | Duration: {self.duration}s\n"
            f"Total Pings: {total_sent} | Global Loss: {global_loss:.1f}%"
            f" | Affected Clients: {namespaces_with_loss}/{len(self.results)}\n"
            f"{'='*95}"
        )
        logger.info(f"\n{table}\n{'='*95}\n")

    async def run_test(self, namespaces: List[str]):

        logger.info("--- Before Ping Test Verifying the Route ---")

        route_results = []
        if self.verify_routes and self.route_verifier:
            logger.info("----- VERIFYING NETWORK ROUTES -----")
            route_tasks = [
                self.route_verifier.verify_route(ns, self.target_ip)
                for ns in namespaces
            ]
            route_results = await asyncio.gather(*route_tasks, return_exceptions=True)

            # Filter out exceptions
            route_results = [r for r in route_results if isinstance(r, dict)]

            # Display route verification results
            if route_results:
                self.route_verifier.display_route_summary(route_results)

            # Check if all routes go through expected router (optional strict check)
            if self.route_verifier.expected_router_ip:
                non_compliant = [
                    r["namespace"]
                    for r in route_results
                    if r["route_type"] != "via_expected_router"
                ]
                if non_compliant:
                    logger.warning(
                        f"WARNING: {len(non_compliant)} namespace(s) not using "
                        f"expected router: {', '.join(non_compliant)}"
                    )
        logger.info("----- ROUTE VERIFICATION COMPLETE -----")

        logger.info(
            f"--- STARTING PING TEST: {len(namespaces)} Clients -> {self.target_ip} ---"
        )

        self.results = {}
        self.failure_messages = {}

        stop_event_pi = asyncio.Event()
        stop_event_router = asyncio.Event()

        # Background Health Checks
        pi_task = asyncio.create_task(health_worker(stop_event_pi))
        router_task = asyncio.create_task(get_router_health(stop_event_router))

        # Create Worker Tasks
        ping_tasks = [asyncio.create_task(self.worker(ns)) for ns in namespaces]

        try:
            # Wait for all ping workers to finish (based on duration)
            await asyncio.gather(*ping_tasks)

        except Exception as e:
            logger.error(f"Critical error in ping manager: {e}")
            raise

        finally:
            # CLEANUP: Stop background monitors
            stop_event_pi.set()
            stop_event_router.set()
            await asyncio.gather(pi_task, router_task, return_exceptions=True)

            self.display_results()

        if self.failure_messages:
            # Create a summary string for the exception
            details = "; ".join(
                [f"{ns}: {msg}" for ns, msg in self.failure_messages.items()]
            )
            raise AssertionError(f"Ping test failed. Details: {details}")

        return self.results
