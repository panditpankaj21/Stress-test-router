import logging
import os
from colorlog import ColoredFormatter

LOG_FILE = "results/realtime_log/report.log"
if os.path.exists(LOG_FILE):
    os.remove(LOG_FILE)

logger = logging.getLogger("network_test")
logger.setLevel(logging.INFO)
logger.handlers = []

console_handler = logging.StreamHandler()
console_formatter = ColoredFormatter(
    "%(log_color)s%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "white",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    },
)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)


file_handler = logging.FileHandler(LOG_FILE)
file_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)
