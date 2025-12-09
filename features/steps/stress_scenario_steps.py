import asyncio
from behave import given, when, then
from src.stress_scenario_manager import StressScenarioManager


@given(
    'a stress scenario manager with duration "{duration:d}" seconds and download URL "{download_url}"'
)
def step_create_stress_manager(context, duration, download_url):
    context.sc_manager = StressScenarioManager(duration, download_url)


@when('I start the stress test')
def step_start_stress_test(context):
    ns_list = context.net_mgr.client_namespaces
    context.results = asyncio.run(context.sc_manager.start(ns_list))


@then('I should see results for each namespace')
def step_validate_stress_test_results(context):
    assert hasattr(context, "results"), "Stress test never started!"
    assert len(context.results) > 0, "No namespace results found!"
