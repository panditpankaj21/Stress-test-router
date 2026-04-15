import os
import yaml
import asyncio
import subprocess
import utils.config
from datetime import datetime
from dotenv import load_dotenv
from utils.logger import logger
from utils.command_runner import run_cmd
from lib.mongo_handler import TestDataHandler
from utils.router_ssh import create_router_ssh
from lib.report_generator import ReportGenerator
from lib.html_report_generator import HTMLReportGenerator


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
            text=True,
        ).strip()

        if output.startswith(("2", "3")):
            return shorten_ipv6_one_digit(output)
        return None
    except Exception as e:
        raise AssertionError(f"Error: {e}")


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
    logger.info("Cleaning up client namespaces...")
    try:
        output = await run_cmd("sudo ip netns list")
        namespaces = [line.split()[0] for line in output.splitlines() if line]
        tasks = [cleanup_namespace(ns) for ns in namespaces]
        await asyncio.gather(*tasks)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to list namespaces: {e}")


def cleanup():
    asyncio.run(async_cleanup())


async def async_cleanup_report_files():
    try:
        await run_cmd("sudo rm -rf test_reports/*")
        logger.info("Report files cleaned up successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to clean up report files: {e}")


def cleanup_report_files():
    asyncio.run(async_cleanup_report_files())


def before_all(context):
    logger.info("----- STARTING TEST -----")

    logger.info("----- CLEANING UP BEFORE STARTING TEST -----")
    cleanup()
    logger.info("----- CLEANUP DONE SUCCESSFULLY -----")

    context.ROUTER_IPV6 = get_router_global_ipv6()
    cleanup_report_files()


    logger.info("----- LOADING ENVIRONMENT VARIABLES -----")
    try:
        load_dotenv()
    except Exception as e:
        logger.error(f"Failed to load .env file: {e}")
        raise AssertionError(f"Failed to load .env file: {e}")

    
    logger.info("----- INITIALIZING DATABASE HANDLER -----")
    context.db_handler = TestDataHandler(os.getenv("MONGODB_CONNECTION_STRING"))
    context.report_generator = ReportGenerator(output_dir="test_reports")
    context.html_generator = HTMLReportGenerator(output_dir="test_reports")


    logger.info("----- EXECUTING SSH LOGIN SCRIPT -----")
    cmd = f"./ssh-login.py -i {os.getenv('ROUTER_MAC')}"
    subprocess.run(
        cmd,
        shell=True,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    context.ssid = os.getenv('WIFI_SSID')
    context.password = os.getenv('WIFI_PASSWORD')

    if not context.ssid or not context.password:
        raise ValueError("WIFI_SSID and WIFI_PASSWORD must be set in .env")

    logger.info("----- INITIALIZING ROUTER SSH MANAGER -----")
    utils.config.router_ssh = create_router_ssh()
    
    try:
        utils.config.router_ssh.connect()
    except Exception as e:
        logger.error(f"Failed to connect to router: {e}")
        raise AssertionError(f"Failed to Connect to router: {e}")

    
    logger.info("----- Getting Router Info -----")
    try:
        router_info = utils.config.router_ssh.get_router_info()
        context.router_mac = router_info.get('router_mac')
        context.router_firmware = router_info.get('router_firmware')
        context.router_name = router_info.get('router_name')
        context.router_model = router_info.get('router_model')

    except Exception as e:
        logger.info(f"Failed to get Router information: {e}")
        raise AssertionError(f"Failed to get Riouter information: {e}")
    

    logger.info("----- LOADING CONFIGURATION -----")
    try:
        with open("config.yaml") as file:
            context.config = yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise AssertionError(f"Failed to load configuration: {e}")


def before_scenario(context, scenario):
    scenario.start_time = datetime.now().isoformat()
    context.start_time = datetime.utcnow()


def after_scenario(context, scenario):

    logger.info(f"----- SCENARIO '{scenario.name}' ENDED -----")

    context.scenario_name = scenario.name
    context.feature_name = scenario.feature.name
    context.linux_avg_cpu_creation = utils.config.linux_cpu_creation
    context.linux_avg_cpu_test = utils.config.linux_cpu_test
    context.time_taken = utils.config.time_taken
    context.router_avg_cpu_creation = utils.config.router_cpu_creation
    context.router_avg_cpu_test = utils.config.router_cpu_test
    context.test_time = datetime.now().isoformat()
    context.end_time = datetime.utcnow()
    context.metrics = utils.config.metrics

    steps_data = []
    failure_message = None

    for step in scenario.steps:
        step_info = {
            "name": step.name,
            "status": step.status.name,
            "keyword": step.keyword,
        }

        if step.status.name == "failed":
            step_info["failure_message"] = str(step.exception)
            failure_message = str(step.exception)
        elif step.status.name == "undefined":
            step_info["failure_message"] = "Step definition not found"
            failure_message = "Step definition not found"
        elif step.status.name == "skipped":
            step_info["failure_message"] = "Step skipped due to previous failure"

        steps_data.append(step_info)

    # Store in context
    context.steps_data = steps_data

    
    if scenario.status.name == 'failed':
        context.status = 'failed'
        context.failure_reason = (
            failure_message if failure_message else 'Test failed - reason not captured'
        )
    else:
        context.status = 'passed'
        context.failure_reason = ''

    try:
        doc_id = context.db_handler.store_test_result(context)
        logger.info(f"Test result stored in MongoDB with ID: {doc_id}")
    except Exception as e:
        logger.info(f"✗ Failed to store test result: {e}")
        return

    if (
        hasattr(context, 'router_mac')
        and hasattr(context, 'feature_name')
        and hasattr(context, 'number_of_clients')
    ):
        try:
            # Get historical data for comparison
            historical_data = context.db_handler.get_filtered_results(
                router_mac=context.router_mac,
                feature_name=context.feature_name,
                number_of_clients=context.number_of_clients,
                limit=50,  # Last 50 tests
            )

            if historical_data:
                # Prepare current test data
                current_test = {
                    'router_mac': context.router_mac,
                    'router_firmware': getattr(context, 'router_firmware', 'Unknown'),
                    'router_name': getattr(context, 'router_name', 'Unknown'),
                    'router_model': getattr(context, 'router_model', 'Unknown'),
                    'status': getattr(context, 'status', 'Unknown'),
                    'scenario_name': context.scenario_name,
                    'feature_name': context.feature_name,
                    'linux_avg_cpu_creation': getattr(
                        context, 'linux_avg_cpu_creation', 0
                    ),
                    'linux_avg_cpu_test': getattr(context, 'linux_avg_cpu_test', 0),
                    'router_avg_cpu_creation': getattr(
                        context, 'router_avg_cpu_creation', 0
                    ),
                    'router_avg_cpu_test': getattr(context, 'router_avg_cpu_test', 0),
                    'number_of_clients': context.number_of_clients,
                    'time_taken': getattr(context, 'time_taken', 0),
                    'metrics': getattr(context, 'metrics', context.metrics),
                    'test_time': getattr(context, 'test_time', None),
                    'start_time': getattr(context, 'start_time'),
                    'end_time': getattr(context, 'end_time'),
                    "steps_data": getattr(context, 'steps_data', []),
                }

                context.report_generator.generate_router_cpu_plot(
                    historical_data, current_test
                )

                context.report_generator.generate_time_taken_plot(
                    historical_data, current_test
                )
                context.report_generator.generate_cpu_graph()

            else:
                logger.info("No historical data found for comparison")

        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            import traceback
            traceback.print_exc()



def after_all(context):
    logger.info("----- END CLEANING PROCESS STARTS -----")
    cleanup()
    logger.info("----- CLEANUP DONE SUCCESSFULLY -----")

    logger.info("----- DISCONNECTING SSH -----")
    utils.config.router_ssh.disconnect()

    logger.info("----- GENERATING HTML REPORT -----")
    try:
        all_tests = context.db_handler.get_all_test_results()
        context.html_generator.generate_html_report(all_tests)
        
        logger.info("----- UPDATING PERMISSIONS FOR REPORTS -----")
        give_permission_cmd()

    except Exception as e:
        logger.error(f"Failed to generate HTML report: {e}")
        import traceback
        traceback.print_exc()

    context.db_handler.close()

    logger.info(
        "\n" + "=" * 70 + "\nThank you for using the test framework!\n" + "=" * 70
    )


def give_permission_cmd():
    asyncio.run(async_give_permission_cmd())


async def async_give_permission_cmd():
    try:
        await run_cmd("sudo chown -R blueplanet:blueplanet test_reports")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to update permissions for test_reports directory: {e}")
