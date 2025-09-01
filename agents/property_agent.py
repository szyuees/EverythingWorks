from strands import Agent
from tools import web_search, http_request


property_agent = Agent(
    system_prompt="You are a Property Search Agent. Find web listings for flats.",
    tools=[web_search, http_request]
)