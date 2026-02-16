import asyncio
import utils.config


async def get_router_health(stop_event):
    """
    Checks router health periodically without blocking the main event loop.
    """
    loop = asyncio.get_running_loop()

    while not stop_event.is_set():
        try:
            # IMPORTANT: We run the blocking SSH call in a separate thread
            # purely so it doesn't freeze the ping tasks.
            await loop.run_in_executor(None, utils.config.router_ssh.get_health)
        except Exception as e:
            print(f"Error checking router health: {e}")

        # Non-blocking sleep
        await asyncio.sleep(2)
