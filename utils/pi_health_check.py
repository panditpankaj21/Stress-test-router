import psutil
import os
import asyncio
from utils.logger import logger
import utils.config


async def get_pi_health():
    cpu_usage = psutil.cpu_percent(interval=0.1)
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            temp_c = int(f.read()) / 1000.0
    except (FileNotFoundError, OSError, ValueError):
        temp_c = None
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    load1, _, _ = os.getloadavg()
    return {
        "cpu": cpu_usage,
        "temp": temp_c,
        "ram": mem,
        "disk": disk,
        "load": load1,
    }


async def health_worker(stop_event, type="test"):
    cnt = 1
    pi_cpu = 0
    while not stop_event.is_set():
        data = await get_pi_health()
        temp_str = f"{data['temp']:.1f}C" if data["temp"] is not None else "N/A"
        logger.info(
            f"[PI     ] CPU={data['cpu']}%  Temp={temp_str}  "
            f"RAM={data['ram']}%  Disk={data['disk']}%  Load={data['load']}"
        )
        pi_cpu = 100 - data['cpu']
        cnt = cnt + 1
        await asyncio.sleep(2)

    if type == "creation":
        utils.config.linux_cpu_creation = pi_cpu / cnt
    else:
        utils.config.linux_cpu_test = pi_cpu / cnt
