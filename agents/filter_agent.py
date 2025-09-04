from strands import Agent
from tools import filter_and_rank

filter_agent = Agent(
    system_prompt='''
    You are a Property Filter Agent.
    Your task is to take property listings and:
    - Filter them based on user criteria (e.g. budget, location, ammenities, etc.)
    - Rank them by relevance
    - Summarize the reason for ranking them this way
    Input: A list of properties (or summary text) and user preferences
    Output: Filtered & summarized list of properties
    ''',
    tools=[filter_and_rank]
)