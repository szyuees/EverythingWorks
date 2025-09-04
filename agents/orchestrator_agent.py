from strands import Agent, tool
from agents.property_agent import property_agent
from agents.grant_agent import grant_agent
from agents.filter_agent import filter_agent
from agents.writer_agent import writer_agent


@tool
def call_property_agent(query: str):
    return property_agent(query)

@tool
def call_grant_agent(query: str):
    return grant_agent(query)

@tool
def call_filter_agent(query: str):
    return filter_agent(query)

@tool
def call_writer_agent(query: str):
    return writer_agent(query)

orchestrator = Agent(
    system_prompt="""
    You are a Housing Chatbot orchestrator.
    Decide which agents to call based on the user's query:
    - For property search use call_property_agent
    - For filtering & ranking use call_filter_agent
    - For repayment calculation use call_writer_agent
    - For grant eligibility use call_grant_agent
    """,
    tools=[call_property_agent, call_writer_agent, call_grant_agent]
)