import asyncio
import utils.config
import re
import time
from utils.logger import logger


def parse_cpu_usage(cpu_line: str) -> float:
    """
    Extracts idle percentage from router CPU line and returns usage = 100 - idle.
    Supports both old top format and new mpstat format.
    """
    # Try mpstat format first (more reliable)
    # Looking for: "[ROUTER ] CPU: 2% usr 2% sys 0% irq 0% sirq 94% idle"
    match = re.search(r'(\d+)%\s+idle', cpu_line)
    if match:
        idle = float(match.group(1))
        usage = 100 - idle
        return usage

    # Fallback: try to extract from raw mpstat output
    # Format: "all  2.66  0.00  2.34  0.00  0.17  0.67  0.00  0.00  94.15"
    parts = cpu_line.split()
    if 'all' in parts:
        try:
            # Last column is idle %
            idle = float(parts[-1])
            usage = 100 - idle
            return usage
        except (ValueError, IndexError):
            pass

    logger.warning(f"Could not parse CPU usage from: {cpu_line}")
    return 0


async def get_router_health(stop_event, type="test"):
    """
    Checks router health periodically without blocking the main event loop.
    """
    loop = asyncio.get_running_loop()

    cnt = 1
    router_cpu = 0

    while not stop_event.is_set():
        try:
            # IMPORTANT: We run the blocking SSH call in a separate thread
            # purely so it doesn't freeze the ping tasks.
            raw = await loop.run_in_executor(None, utils.config.router_ssh.get_health)
            cpu_usage = parse_cpu_usage(raw)
            if cpu_usage is not None and cpu_usage > 0:
                router_cpu += cpu_usage
                utils.config.cpu_percentage.append(cpu_usage)
                elapsed = time.time() - utils.config.start_time
                utils.config.cpu_timestamps.append(elapsed)
                cnt = cnt + 1
        except Exception as e:
            print(f"Error checking router health: {e}")
        await asyncio.sleep(2)

    if type == "creation":
        utils.config.router_cpu_creation = router_cpu / cnt
    else:
        utils.config.router_cpu_test = router_cpu / cnt
