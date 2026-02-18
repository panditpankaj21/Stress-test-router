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
from lib.mongo_handler import TestDataHandler
from lib.report_generator import ReportGenerator
from lib.excel_report_generator import ExcelReportGenerator
from lib.excel_statistics_generator import ExcelStatisticsGenerator

summary_logger = None

MONGODB_CONNECTION_STRING = "mongodb+srv://pkp20022_db_user:Nfo60hcufd2tVwLW@cluster0.cxkwlpd.mongodb.net/"

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

    """Initialize MongoDB handler"""
    context.db_handler = TestDataHandler(MONGODB_CONNECTION_STRING)
    context.report_generator = ReportGenerator(output_dir="test_reports")
    context.stats_generator = ExcelStatisticsGenerator(
        excel_path="test_reports/test_statistics.xlsx"
    )

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
    
    
    # getting information about the Router
    logger.info("----- Getting Router Info -----")
    try: 
        router_info = utils.config.router_ssh.get_router_info()
        context.router_mac = router_info.get('router_mac')
        context.router_firmware = router_info.get('router_firmware')
        context.router_name = router_info.get('router_name')
        context.router_model = router_info.get('router_model')
        
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
     
    #getting information about the secenario and feature
    context.scenario_name = scenario.name
    context.feature_name = scenario.feature.name
    context.status = scenario.status.name
    context.linux_avg_cpu_creation = utils.config.linux_cpu_creation
    context.linux_avg_cpu_test = utils.config.linux_cpu_test
    context.time_taken = utils.config.time_taken
    context.router_avg_cpu_creation = utils.config.router_cpu_creation
    context.router_avg_cpu_test = utils.config.router_cpu_test
    context.test_time = datetime.now().isoformat()

    logger.info("----- displaying the information --------")

    logger.info(context.router_mac)
    logger.info(context.router_firmware)
    logger.info(context.router_name)
    logger.info(context.router_model)
    logger.info(context.scenario_name)
    logger.info(context.feature_name)
    logger.info(context.status)
    logger.info(context.number_of_clients)
    logger.info(context.linux_avg_cpu_creation)
    logger.info(context.linux_avg_cpu_test)
    logger.info(context.time_taken)
    logger.info(context.router_avg_cpu_creation)
    logger.info(context.router_avg_cpu_test)

    logger.info("----- end of the displaying the info -----")

    # Store the test result in MongoDB
    try:
        doc_id = context.db_handler.store_test_result(context)
        logger.info(f"\n✓ Test result stored in MongoDB with ID: {doc_id}")
    except Exception as e:
        logger.info(f"\n✗ Failed to store test result: {e}")
        return
    


    if hasattr(context, 'router_mac') and hasattr(context, 'feature_name') and hasattr(context, 'number_of_clients'):
        try:
            # Get historical data for comparison
            historical_data = context.db_handler.get_filtered_results(
                router_mac=context.router_mac,
                feature_name=context.feature_name,
                number_of_clients=context.number_of_clients,
                limit=50  # Last 50 tests
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
                    'linux_avg_cpu_creation': getattr(context, 'linux_avg_cpu_creation', 0),
                    'linux_avg_cpu_test': getattr(context, 'linux_avg_cpu_test', 0),
                    'router_avg_cpu_creation': getattr(context, 'router_avg_cpu_creation', 0),
                    'router_avg_cpu_test': getattr(context, 'router_avg_cpu_test', 0),
                    'number_of_clients': context.number_of_clients,
                    'time_taken': getattr(context, 'time_taken', 0),
                    'metrics': getattr(context, 'metrics', {}),
                    'test_time': getattr(context, 'test_time', None)
                }
                
                # Generate plots
                router_cpu_img = context.report_generator.generate_router_cpu_plot(
                    historical_data, current_test
                )
                # linux_cpu_img = context.report_generator.generate_linux_cpu_plot(
                #     historical_data, current_test
                # )
                time_taken_img = context.report_generator.generate_time_taken_plot(
                    historical_data, current_test
                )
                
                # Calculate metrics averages
                # metrics_data = context.report_generator.calculate_metrics_average(historical_data)
                
                # Generate HTML report
                # report_path = context.report_generator.generate_html_report(
                #     current_test=current_test,
                #     historical_data=historical_data,
                #     router_cpu_img=router_cpu_img,
                #     linux_cpu_img=linux_cpu_img,
                #     time_taken_img=time_taken_img,
                #     metrics_data=metrics_data
                # )
                
                # logger.info(f"\n✓ Report generated: {report_path}")
                # logger.info(f"  Open in browser: file://{os.path.abspath(report_path)}")
            else:
                logger.info("\n⚠ No historical data found for comparison")
                
        except Exception as e:
            logger.info(f"\n✗ Failed to generate report: {e}")
            import traceback
            traceback.print_exc()




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


def after_all(context):
    logger.info("----- END CLEANING PROCESS STARTS -----")
    cleanup()
    logger.info("----- CLEANUP DONE SUCCESSFULLY -----")
    utils.config.router_ssh.disconnect()

    
    # Ask if user wants Excel report
    # logger.info("\n" + "="*70)
    # logger.info(" TEST EXECUTION COMPLETED")
    # logger.info("\n"+"="*70)
    
    # response = input("\n Do you want to generate an Excel report of all tests? (yes/no): ").strip().lower()
    
    # if response in ['yes', 'y']:
    #     try:
    #         logger.info("\n⏳ Generating Excel report...")
            
    #         # Retrieve all test data from MongoDB
    #         all_tests = context.db_handler.get_all_test_results()
            
    #         if not all_tests:
    #             logger.info("  No test data found in database!")
    #         else:
    #             # Generate Excel report
    #             excel_generator = ExcelReportGenerator()
                
    #             timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    #             excel_filename = f"test_report_{timestamp}.xlsx"
    #             excel_path = os.path.join("test_reports", excel_filename)
                
    #             # Ensure output directory exists
    #             os.makedirs("test_reports", exist_ok=True)
                
    #             generated_path = excel_generator.generate_excel_report(all_tests, excel_path)
                
    #             logger.info(f"\n Excel report generated successfully!")
    #             logger.info(f" File location: {os.path.abspath(generated_path)}")
    #             logger.info(f" Total tests included: {len(all_tests)}")
    #             logger.info(f" Routers analyzed: {len(set(t.get('router_mac') for t in all_tests if t.get('router_mac')))}")
                
    #     except Exception as e:
    #         logger.info(f"\n Failed to generate Excel report: {e}")
    #         import traceback
    #         traceback.print_exc()
    # else:
    #     logger.info("\n Skipping Excel report generation.")
    
    # # Close MongoDB connection
    # if hasattr(context, 'db_handler'):
    #     context.db_handler.close()
    #     logger.info("\n✓ MongoDB connection closed")
    
    # logger.info("\n" + "="*70)
    # logger.info(" Thank you for using the test framework! \n")
    # logger.info("="*70 + "\n")



    # logger.info("\n" + "="*70)
    # logger.info("🔔 TEST EXECUTION COMPLETED")
    # logger.info("="*70)
    
    # logger.info(f"\n📊 Auto-updated statistics file: {os.path.abspath('test_reports/test_statistics.xlsx')}")
    
    # response = input("\n📈 Do you want to generate a comprehensive Excel analysis report? (yes/no): ").strip().lower()
    
    # if response in ['yes', 'y']:
    #     try:
    #         logger.info("\n⏳ Generating comprehensive Excel report...")
            
    #         # Retrieve all test data from MongoDB
    #         all_tests = context.db_handler.get_all_test_results()
            
    #         if not all_tests:
    #             logger.info("⚠️  No test data found in database!")
    #         else:
    #             # Generate comprehensive Excel report
    #             excel_generator = ExcelReportGenerator()
                
    #             timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    #             excel_filename = f"comprehensive_analysis_{timestamp}.xlsx"
    #             excel_path = os.path.join("test_reports", excel_filename)
                
    #             generated_path = excel_generator.generate_excel_report(all_tests, excel_path)
                
    #             logger.info(f"\n✅ Comprehensive Excel report generated successfully!")
    #             logger.info(f"📁 File location: {os.path.abspath(generated_path)}")
    #             logger.info(f"📊 Total tests included: {len(all_tests)}")
    #             logger.info(f"🔧 Routers analyzed: {len(set(t.get('router_mac') for t in all_tests if t.get('router_mac')))}")
                
    #     except Exception as e:
    #         logger.info(f"\n❌ Failed to generate comprehensive Excel report: {e}")
    #         import traceback
    #         traceback.print_exc()
    # else:
    #     logger.info("\n⏭️  Skipping comprehensive Excel report generation.")
    
    # # Close MongoDB connection
    # if hasattr(context, 'db_handler'):
    #     context.db_handler.close()
    #     logger.info("\n✓ MongoDB connection closed")
    
    # logger.info("\n" + "="*70)
    # logger.info("👋 Thank you for using the test framework!")
    # logger.info("="*70 + "\n")


    print("\n⏳ Updating Excel statistics...")
    all_tests = context.db_handler.get_all_test_results()  # Get all tests from MongoDB
    stats_path = context.stats_generator.update_statistics(all_tests)  # THIS LINE calls the method
    print(f"✓ Excel statistics updated: {os.path.abspath(stats_path)}")
