import yaml
import asyncio
import subprocess
from utils.logger import logger
from utils.command_runner import run_cmd


async def cleanup_namespace(ns):
    macvlan = f"macvlan{ns[2:]}"
    try:
        await run_cmd(
            f"sudo ip netns exec {ns} dhclient -6 -r {macvlan} "
            f"-pf /run/dhclient6-{ns}.pid "
            f"-lf /var/lib/dhcp/dhclient6-{ns}.leases"
        )
        await run_cmd(
            f"sudo ip netns exec {ns} dhclient -r {macvlan} "
            f"-pf /run/dhclient-{ns}.pid "
            f"-lf /var/lib/dhcp/dhclient-{ns}.leases"
        )
        await run_cmd(f"sudo ip netns delete {ns}")
        await run_cmd(f"sudo rm -rf /etc/netns/{ns}")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to clean up {ns}: {e}")


async def async_cleanup():
    logger.info("----- ASYNC CLEANUP STARTED -----")
    try:
        output = await run_cmd("sudo ip netns list")
        namespaces = [line.split()[0] for line in output.splitlines() if line]
        tasks = [cleanup_namespace(ns) for ns in namespaces]
        await asyncio.gather(*tasks)
        logger.info("All clients deleted successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to list namespaces: {e}")


def cleanup():
    asyncio.run(async_cleanup())


def before_all(context):
    logger.info("----- STARTING NETWORK STRESS TEST -----")
    logger.info("Loading configuration from config.yaml")
    with open("config.yaml") as file:
        context.config = yaml.safe_load(file)
    logger.info("Configuration loaded successfully.")
    cleanup()


def before_scenario(context, scenario):
    logger.info("----- BEFORE SCENARIO CLEANING PROCESS STARTS -----")
    cleanup()
    logger.info("----- CLEANUP DONE SUCCESSFULLY -----")


def after_all(context):
    logger.info("----- END CLEANING PROCESS STARTS -----")
    cleanup()
    logger.info("----- CLEANUP DONE SUCCESSFULLY -----")
