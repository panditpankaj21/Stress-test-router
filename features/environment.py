import os
import re
import yaml
import json
import asyncio
import logging
import subprocess
from dotenv import load_dotenv
import time
from datetime import datetime
from utils.logger import logger
from utils.command_runner import run_cmd
from utils.router_ssh import create_router_ssh
import utils.config

summary_logger = None

def shorten_ipv6_one_digit(addr):
    if "::" in addr:
        prefix, rest = addr.split("::", 1)
        if rest:  
            first_group = rest.split(":")[0]
            return prefix + "::" + first_group[0]
        else:
            return prefix + "::"
    return addr


def get_router_global_ipv6():
    try:
        output = subprocess.check_output(
            "ip -6 addr show scope global | awk '/inet6/ {print $2}' | cut -d/ -f1 | head -1",
            shell=True,
            text=True
        ).strip()

        if output.startswith(("2", "3")):
            return shorten_ipv6_one_digit(output)
        return None
    except Exception as e:
        raise AssertionError(f"Error: {e}")

def setup_summary_logger():
    """
    Sets up the summary logger.
    mode='w' ensures the file is cleared when this logger is initialized.
    """
    s_logger = logging.getLogger("scenario_summary")
    s_logger.setLevel(logging.INFO)
    s_logger.propagate = False

    if not s_logger.handlers:
        os.makedirs("results/logs", exist_ok=True)
        handler = logging.FileHandler("results/logs/summary.log", mode='w')
        formatter = logging.Formatter("%(asctime)s | %(message)s")
        handler.setFormatter(formatter)
        s_logger.addHandler(handler)

    return s_logger


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
    global summary_logger

    context.ROUTER_IPV6 = get_router_global_ipv6()

    summary_logger = setup_summary_logger()
    summary_logger.info("Test Run Started:")

    os.makedirs("results/json", exist_ok=True)
    with open("results/json/summary.json", "w") as f:
        json.dump([], f)

    logger.info("----- STARTING TEST -----")

    try:
        load_dotenv()
        logger.info(".env file loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load .env file: {e}")
        raise AssertionError(f"Failed to load .env file: {e}")

    logger.info("----- EXECUTING SSH LOGIN SCRIPT -----")
    # try:
    # logger.info(os.getenv('ROUTER_MAC'))
    cmd = f"./ssh-login.py -i {os.getenv('ROUTER_MAC')}"
    subprocess.run(
        cmd,
        shell=True,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # cmd = ["./ssh-login.py", "-i", "90d3cfcd0e75"]
    # subprocess.run(cmd, check=True)
    logger.info("SSH login script executed successfully.")
    # except subprocess.CalledProcessError as e:
    #     logger.error(f"SSH login script failed: {e}")
    #     raise AssertionError(f"SSH login script failed: {e}")

    context.ssid = os.getenv('WIFI_SSID')
    context.password = os.getenv('WIFI_PASSWORD')

    if not context.ssid or not context.password:
        raise ValueError("WIFI_SSID and WIFI_PASSWORD must be set in .env")

    logger.info("----- CLEANING UP BEFORE STARTING TEST -----")
    cleanup()
    logger.info("----- CLEANUP DONE SUCCESSFULLY -----")

    logger.info("----- INITIALIZING ROUTER SSH MANAGER -----")
    utils.config.router_ssh = create_router_ssh()
    try:
        utils.config.router_ssh.connect()
        logger.info("Router SSH Manager initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to router: {e}")
        raise AssertionError(f"Failed to Connect to router: {e}")
    
    # get all information about the Router here and run command
    try: 
        logger.info("----- Getting Router Info -----")
        context.router_info = utils.config.router_ssh.get_router_info()
        logger.info(context.router_info)
    except Exception as e:
        logger.info(f"Failed to get Riouter information: {e}")
        raise AssertionError(f"Failed to get Riouter information: {e}")


    logger.info("----- LOADING CONFIGURATION -----")
    try:
        with open("config.yaml") as file:
            context.config = yaml.safe_load(file)
        logger.info("Configuration loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise AssertionError(f"Failed to load configuration: {e}")


def before_scenario(context, scenario):
    logger.info("\n" + "----- BEFORE SCENARIO CLEANING PROCESS STARTS -----")
    cleanup()
    scenario.start_time = datetime.now().isoformat()
    logger.info("----- CLEANUP DONE SUCCESSFULLY -----")


def after_scenario(context, scenario):
    end_time = datetime.now().isoformat()
    steps_data = []
    failure_message = None

    for step in scenario.steps:
        step_info = {"name": step.name, "status": step.status.name}
        if step.status.name == "failed":
            step_info["failure_message"] = str(step.exception)
            failure_message = str(step.exception)
        elif step.status.name == "undefined":
            step_info["failure_message"] = "Step definition not found"
            failure_message = "Step definition not found"
        elif step.status.name == "skipped":
            step_info["failure_message"] = "Step skipped due to previous failure"
        steps_data.append(step_info)

    scenario_result = {
        "feature": scenario.feature.name,
        "scenario": scenario.name,
        "status": scenario.status.name,
        "steps": steps_data,
        "timestamps": {
            "start": getattr(scenario, 'start_time', datetime.now().isoformat()),
            "end": end_time,
        },
        "failure_message": failure_message,
    }

    json_file = "results/json/summary.json"
    try:
        with open(json_file, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []

    data.append(scenario_result)

    with open(json_file, "w") as f:
        json.dump(data, f, indent=2)

    if summary_logger:
        summary_logger.info(
            f"Feature: {scenario.feature.name} | Scenario: {scenario.name} | "
            f"Status: {scenario.status.name} | Failure: {failure_message or 'None'}"
        )

    logger.info(f"Scenario '{scenario.name}' finished. Result: {scenario.status.name}")


def after_all(context):
    logger.info("----- END CLEANING PROCESS STARTS -----")
    cleanup()
    logger.info("----- CLEANUP DONE SUCCESSFULLY -----")
    utils.config.router_ssh.disconnect()
