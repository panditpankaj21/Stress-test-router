import asyncio
from behave import when
from lib.stress_scenario_manager import StressScenarioManager


@when('I assign a random workload to each client for "{duration:d}" seconds')
def step_create_stress_manager(context, duration):
    context.sc_manager = StressScenarioManager(duration=duration)
    ns_list = context.net_mgr.client_namespaces
    context.results = asyncio.run(context.sc_manager.start(ns_list))
