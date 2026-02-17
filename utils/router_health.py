import asyncio
import utils.config
import re
import utils.config

def parse_cpu_usage(cpu_line: str) -> float:
    """
    Extracts idle percentage from router CPU line and returns usage = 100 - idle.
    """
    match = re.search(r'(\d+)% idle', cpu_line)
    if match:
        idle = float(match.group(1))
        usage = 100 - idle
        return usage
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
            router_cpu += cpu_usage
        except Exception as e:
            print(f"Error checking router health: {e}")

        cnt = cnt + 1
        await asyncio.sleep(2)

    if type=="creation":
        utils.config.router_cpu_creation = router_cpu / cnt
    else:
        utils.config.router_cpu_test = router_cpu / cnt

    
