import gradio as gr
from agents.orchestrator_agent import orchestrator
import logging

# --- Logging (your setup) ---
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logger.info("Using DuckDuckGo for web search and AWS Bedrock model via Strands")

class ChatbotWithHistory:
    def __init__(self, agent):
        self.agent = agent
        self.history = []

    def ask(self, user_message: str):
        self.history.append(("user", user_message))

        conversation = ""
        for role, msg in self.history:
            conversation += f"{role.upper()}: {msg}\n"

        response = self.agent(conversation)

        self.history.append(("assistant", response))

        return response
    
chatbot = ChatbotWithHistory(orchestrator)

# --- Gradio interface ---
def chat_with_housing_bot(user_input):
    logger.info(f"User query: {user_input}")
    try:
        response = chatbot.ask(user_input)
        logger.info(f"Response: {response}")
        return response
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {e}"

iface = gr.Interface(
    fn=chat_with_housing_bot,
    inputs=gr.Textbox(
        label="Ask the Housing Chatbot",
        placeholder="I want to find out what housing grants I am eligible for...",
        lines=5
    ),
    outputs=gr.Textbox(label="Chatbot Response"),
    title="Singapore Housing Chatbot"
)

iface.launch()