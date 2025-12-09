import logging
import os

LOG_FILE = "network_stress_report.log"
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("network_test")
logger.handlers = []
if os.path.exists(LOG_FILE):
    os.remove(LOG_FILE)
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(file_handler)
