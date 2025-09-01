from strands import Agent, tool
from tools import web_search, http_request

grant_agent = Agent(
    system_prompt='''
    You are a Grant Eligibility Agent for Singapore housing grants. The user will ask about housing grantes.
    Before searching the web, ask the user for information needed to determine grant eligibility.
    Only ask the user once for all the information you need. The information you need to ask includes:
    - What is your citizenship status? (e.g., Singapore Citizen, Permanent Resident, Foreigner)
    - What is your marital status? (e.g., Single, Married, Divorced)
    - How old are you?
    - If married, what is your spouse's citizenship status?
    - How many children do you have (if any), and what are their ages?
    - Are you a first-time home buyer?
    - Have you owned any property before?
    - What is your gross monthly household income?
    - What type of flat are you looking to buy? (e.g., HDB, EC, Private)
    - What is the location of the flat you are interested in?
    - What size of flat are you looking for? (e.g., 2-room, 3-room, 4-room, 5-room, Executive)
    - Are you purchasing the flat with family members? If so, what are their citizenship statuses?
    - Are you applying under any priority schemes? (e.g., Married Child Priority, Multi-Generation Priority)
    Search the web only once or twice for up-to-date information and summarize clearly.
    Always use official sources like HDB, CPF, or gov.sg websites.
    Do not repeat the same grant multiple times. 
    Do not call web_search repeatedly. If you have found official information, stop and summarize.
    If the user do not have any elligible grants, return "No Elligible Grants".
     ''',
    tools=[web_search, http_request]

)

'''
@tool
def call_grant_agent(query: str):
    user_info = grant_agent(query)
    search = "Singapore HDB housing grants eligibility site:hdb.gov.sg OR site:cpf.gov.sg OR site:gov.sg"
    results = web_search(search, max_results=3)
    summary = []
    seen = set()

    if isinstance(results, list):
        for i in results:
            text = http_request(i['link'])
            grants = grant_agent(
                f"Extract a structured list of housing grants with names, eligibility criteria, and amounts from this text:\n\n{text}"
            )
            if isinstance(grants, list):
                for g in grants:
                    name = g.get("name")
                    amount = g.get("amount")
                    if name and name not in seen:
                        seen.add(name)
                        summary.append(f"{name}: {g.get('eligibility', 'No eligibility info')} - Amount: {amount if amount else 'N/A'}")
    if not summary:
        return "No Eligible Grants"

    return "### Your Grant Eligibility\n\n" + "\n".join(summary)
'''