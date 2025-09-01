from strands import Agent
from tools import repayment_duration
writer_agent = Agent(
    system_prompt="You are a Writer Agent. Format top-k listings and optionally include repayment info.",
    tools=[repayment_duration]
)