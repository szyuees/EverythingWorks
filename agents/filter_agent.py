from strands import Agent
from tools import filter_and_rank

filter_agent = Agent(
    system_prompt="You are a Filter & Rank Agent. Filter listings by user criteria and return top-k.",
    tools=[filter_and_rank]
)