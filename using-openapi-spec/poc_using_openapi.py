# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

"""
DESCRIPTION:
    This sample demonstrates how to use basic agent operations with function tools from
    the Azure Agents service using a synchronous client with Azure Monitor tracing.
    View the results in the "Tracing" tab in your Azure AI Foundry project page.

USAGE:
    python sample_agents_functions_with_azure_monitor_tracing.py

    Before running the sample:

    pip install azure-ai-projects azure-identity opentelemetry-sdk azure-monitor-opentelemetry

    Set these environment variables with your own values:
    1) PROJECT_CONNECTION_STRING - The project connection string, as found in the overview page of your
       Azure AI Foundry project.
    2) MODEL_DEPLOYMENT_NAME - The deployment name of the AI model, as found under the "Name" column in 
       the "Models + endpoints" tab in your Azure AI Foundry project.
    3) AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED - Optional. Set to `true` to trace the content of chat
       messages, which may contain personal data. False by default.
"""
from typing import Any, Callable, Set

import os, time, json
from azure.ai.projects import AIProjectClient
from azure.ai.projects.telemetry import trace_function
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import FunctionTool, RequiredFunctionToolCall, SubmitToolOutputsAction, ToolOutput
from opentelemetry import trace
import jsonref
from azure.monitor.opentelemetry import configure_azure_monitor
from azure.ai.projects.models import OpenApiTool, OpenApiAnonymousAuthDetails, OpenApiConnectionSecurityScheme, OpenApiConnectionAuthDetails
import db_helper
from dotenv import load_dotenv
load_dotenv(".env")


project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(), conn_str=os.environ["PROJECT_CONNECTION_STRING"]
)

# Enable Azure Monitor tracing
application_insights_connection_string = project_client.telemetry.get_connection_string()
if not application_insights_connection_string:
    print("Application Insights was not enabled for this project.")
    print("Enable it via the 'Tracing' tab in your AI Foundry project page.")
    exit()
configure_azure_monitor(connection_string=application_insights_connection_string)

scenario = os.path.basename(__file__)
tracer = trace.get_tracer(__name__)


# The trace_func decorator will trace the function call and enable adding additional attributes
# to the span in the function implementation. Note that this will trace the function parameters and their values.
@trace_function()
def fetch_cases(query: str) -> str:
    """
    Fetches the cases information for the specified query.

    :param query(str): The query to fetch cases for.
    :return: Cases information as a JSON string.
    :rtype: str
    """
    # In a real-world scenario, you'd integrate with a cases API.
    # Here, we'll mock the response.
    cases_data = db_helper.get_from_db(query)

    # Adding attributes to the current span
    span = trace.get_current_span()
    span.set_attribute("requested_query", query)

    cases_json = json.dumps(cases_data)
    return cases_json


# Statically defined user functions for fast reference
user_functions: Set[Callable[..., Any]] = {
    fetch_cases,
}

@trace_function()
def get_openapi_spec():
    with open('./cases_openapi.json', 'r') as f:
        openapi_spec = jsonref.load(f)

    auth = OpenApiAnonymousAuthDetails()

    # Initialize agent OpenAPI tool using the read in OpenAPI spec
    openapi = OpenApiTool(name="open_cases", spec=openapi_spec, description="Fetches the cases information for the specified query.", auth=auth)
    return openapi

# Initialize function tool with user function
functions = FunctionTool(functions=user_functions)
openapi = get_openapi_spec()

with tracer.start_as_current_span(scenario):
    with project_client:
        # Create an agent and run user's request with function calls
        agent = project_client.agents.create_agent(
            model=os.environ["MODEL_DEPLOYMENT_NAME"],
            name="cases-assistant",
            instructions="You are a helpful assistant",
            #tools=functions.definitions,
            tools=openapi.definitions
        )
        print(f"Created agent, ID: {agent.id}")

        thread = project_client.agents.create_thread()
        print(f"Created thread, ID: {thread.id}")

        message = project_client.agents.create_message(
            thread_id=thread.id,
            role="user",
            content="Retrieves case data with this query: 'Water leaking from the apartment above'",
        )
        print(f"Created message, ID: {message.id}")

        run = project_client.agents.create_run(thread_id=thread.id, assistant_id=agent.id)
        print(f"Created run, ID: {run.id}")

        while run.status in ["queued", "in_progress", "requires_action"]:
            time.sleep(1)
            run = project_client.agents.get_run(thread_id=thread.id, run_id=run.id)
            print(f"Current run status: {run.status}")

            if run.status == "requires_action" and isinstance(run.required_action, SubmitToolOutputsAction):
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                #print(f"Tool calls: {tool_calls}")
                if not tool_calls:
                    print("No tool calls provided - cancelling run")
                    project_client.agents.cancel_run(thread_id=thread.id, run_id=run.id)
                    break

                tool_outputs = []
                for tool_call in tool_calls:
                    if isinstance(tool_call, RequiredFunctionToolCall):
                        try:
                            output = functions.execute(tool_call)
                            tool_outputs.append(
                                ToolOutput(
                                    tool_call_id=tool_call.id,
                                    output=output,
                                )
                            )
                        except Exception as e:
                            print(f"Error executing tool_call {tool_call.id}: {e}")

                print(f"Tool outputs: {tool_outputs}")
                if tool_outputs:
                    project_client.agents.submit_tool_outputs_to_run(
                        thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs
                    )

            print(f"Current run status: {run.status}")

        print(f"Run completed with status: {run.status}")

        # Delete the agent when done
        # project_client.agents.delete_agent(agent.id)
        # print("Deleted agent")

        # Fetch and log all messages
        messages = project_client.agents.list_messages(thread_id=thread.id)
        print(f"Messages: {messages}")