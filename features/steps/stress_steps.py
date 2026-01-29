import asyncio
from behave import when
from lib.stress_scenario_manager import StressScenarioManager


@when('I assign a random workload to each client for "{duration:d}" seconds')
def step_create_stress_manager(context, duration):
    download_url = context.config.get("DOWNLOAD_URL")
    context.sc_manager = StressScenarioManager(duration, download_url)
    ns_list = context.net_mgr.client_namespaces
    context.results = asyncio.run(context.sc_manager.start(ns_list))
