from dotenv import load_dotenv
load_dotenv()

import os
import gradio as gr
from agents.orchestrator_agent import orchestrator
import logging
import boto3
from datetime import datetime
import json
os.environ['GRADIO_ANALYTICS_ENABLED'] = 'False'


# Import new core systems
from core.mcp_context_manager import MCPContextManager
from tools import initialize_rag_system

# --- Enhanced Logging ---
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logger.info("Starting Enhanced Housing Assistant with RAG + MCP")

class EnhancedChatbotWithContext:
    def __init__(self, agent, context_manager):
        self.agent = agent
        self.context_manager = context_manager
        self.history = []
        self.user_sessions = {}
    
    def ask(self, user_message: str, user_id: str = "default_user"):
        """Enhanced ask with context management"""
        
        # Get user context if MCP is available
        context_prompt = ""
        if self.context_manager:
            try:
                user_context = self.context_manager.get_user_context(user_id)
                context_prompt = self._build_context_prompt(user_context)
                
                # Extract and update profile from message
                self._extract_profile_updates(user_id, user_message)
                
            except Exception as e:
                logger.warning(f"Context management error: {e}")
        
        # Build conversation with context
        self.history.append(("user", user_message))
        
        conversation = context_prompt + "\n\n" if context_prompt else ""
        for role, msg in self.history[-3:]:  # Keep last 3 exchanges
            conversation += f"{role.upper()}: {msg}\n"
        
        response = self.agent(conversation)
        self.history.append(("assistant", response))
        
        # Enhance response formatting
        enhanced_response = self._enhance_response(response, user_id)
        
        return enhanced_response
    
    def _build_context_prompt(self, user_context):
        """Build context prompt for agent"""
        profile = user_context.get('profile', {})
        completion = user_context.get('completion_score', 0)
        
        context_items = []
        if profile.get('citizenship_status'):
            context_items.append(f"Citizenship: {profile['citizenship_status']}")
        if profile.get('gross_monthly_income'):
            context_items.append(f"Income: ${profile['gross_monthly_income']:,.0f}")
        if profile.get('preferred_locations'):
            context_items.append(f"Preferred areas: {', '.join(profile['preferred_locations'])}")
        
        if context_items:
            return f"USER CONTEXT - Profile completion: {completion:.0%} | " + " | ".join(context_items)
        return ""
    
    def _extract_profile_updates(self, user_id, message):
        """Extract profile information from user message"""
        if not self.context_manager:
            return
        
        message_lower = message.lower()
        updates = {}
        
        # Extract citizenship
        if 'citizen' in message_lower:
            updates['citizenship_status'] = 'Singapore Citizen'
        elif 'pr' in message_lower or 'permanent resident' in message_lower:
            updates['citizenship_status'] = 'Permanent Resident'
        
        # Extract income (simple regex)
        import re
        income_match = re.search(r'\$?(\d{1,2},?\d{3,})', message)
        if income_match:
            income = int(income_match.group(1).replace(',', ''))
            if income > 1000:  # Reasonable income threshold
                updates['gross_monthly_income'] = float(income)
        
        # Extract locations (Singapore areas)
        sg_areas = ['tampines', 'jurong', 'woodlands', 'punggol', 'sengkang', 'bishan', 'toa payoh', 
                   'bedok', 'hougang', 'ang mo kio', 'clementi', 'bukit batok', 'yishun']
        mentioned_areas = [area for area in sg_areas if area in message_lower]
        if mentioned_areas:
            current_areas = self.context_manager.user_profiles[user_id].preferred_locations or []
            updates['preferred_locations'] = list(set(current_areas + mentioned_areas))
        
        if updates:
            self.context_manager.update_user_profile(user_id, **updates)
            logger.info(f"Updated profile for {user_id}: {updates}")
    
    def _enhance_response(self, response, user_id):
        """Enhance response with context-aware elements"""
        if not self.context_manager:
            return response
        
        try:
            context = self.context_manager.get_user_context(user_id)
            completion = context.get('completion_score', 0)
            
            # Add profile completion indicator
            if completion < 0.8:
                missing_info = []
                profile = context.get('profile', {})
                
                if not profile.get('citizenship_status'):
                    missing_info.append('citizenship status')
                if not profile.get('gross_monthly_income'):
                    missing_info.append('income level')
                if not profile.get('preferred_locations'):
                    missing_info.append('preferred locations')
                
                if missing_info:
                    completion_note = f"\n\n💡 **To provide better recommendations**: Share your {', '.join(missing_info[:2])}"
                    # Corrected line: Convert response to string before concatenation
                    response = str(response) + completion_note
            
            return response
            
        except Exception as e:
            logger.warning(f"Response enhancement error: {e}")
            return response
# Initialize systems
try:
    # Initialize RAG system
    rag_status = initialize_rag_system()
    logger.info(f"RAG Status: {rag_status}")

    # Initialize MCP Context Manager
    context_manager = MCPContextManager()
    logger.info("MCP Context Manager initialized")

    # Initialize the enhanced chatbot
    chatbot = EnhancedChatbotWithContext(orchestrator, context_manager)

except Exception as e:
    logger.error(f"Initialization error: {e}")
    context_manager = None
    chatbot = None

# Initialize enhanced chatbot
if context_manager:
    chatbot = EnhancedChatbotWithContext(orchestrator, context_manager)
else:
    # Fallback to basic chatbot if MCP fails
    class BasicChatbot:
        def __init__(self, agent):
            self.agent = agent
            self.history = []
        
        def ask(self, user_message: str, user_id: str = "default_user"):
            self.history.append(("user", user_message))
            conversation = ""
            for role, msg in self.history:
                conversation += f"{role.upper()}: {msg}\n"
            response = self.agent(conversation)
            self.history.append(("assistant", response))
            return response
    
    chatbot = BasicChatbot(orchestrator)

# --- Enhanced Gradio Interface with Custom Layout ---
with gr.Blocks(
    title="Enhanced Singapore Housing Assistant",
    theme=gr.themes.Soft(primary_hue="indigo", secondary_hue="blue")
) as iface:
    
    # Header
    gr.HTML("""
    <div style="text-align: center; padding: 20px; background: linear-gradient(90deg, #4f46e5, #3b82f6); color: white; border-radius: 12px; margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 2em;">🏠 Enhanced Singapore Housing Assistant</h1>
        <p style="font-size: 18px; margin: 5px 0 0;">AI-powered housing guidance with personalisation, context memory, and real-time insights</p>
    </div>
    """)

    with gr.Row():
        # Main conversation area
        with gr.Column(scale=3):
            chatbot_interface = gr.Chatbot(
                type="messages",
                label="💬 Chat with Housing Assistant",
                height=500,
                show_label=True,
                avatar_images=("🧑", "🤖")
            )
            
            user_input = gr.Textbox(
                placeholder="Type your housing question here (e.g., 'What grants do I qualify for?')",
                lines=3,
                autofocus=True,
                show_label=False
            )
            
            with gr.Row():
                submit_btn = gr.Button("🚀 Send", variant="primary")
                clear_btn = gr.Button("🔄 New Conversation", variant="secondary")

        # Sidebar with guidance & context
        with gr.Column(scale=1):
            gr.Markdown("### 🎯 Quick Start")
            sample_buttons = [
                "What housing grants am I eligible for as a Singapore citizen?",
                "Help me find a 4-room HDB flat in Tampines under $500k",
                "I earn $6000/month, what's my housing budget?",
                "Compare BTO vs resale HDB flats"
            ]
            for sample_query in sample_buttons:
                gr.Button(sample_query, size="sm").click(
                    lambda q=sample_query: q,
                    outputs=user_input
                )
            
            gr.Markdown("### 📊 Profile Progress")
            profile_progress = gr.Label("Loading context...")
            
            gr.Markdown("### ⚡ Features")
            gr.Markdown("""
            - ✅ Remembers your **citizenship, income, locations**
            - 📚 Uses **official HDB/CPF sources**
            - 💡 Compares **BTO, resale, and private options**
            - 🔍 Real-time property listing support
            """)

    # Session state
    session_state = gr.State()
    history_state = gr.State([])

    # Chat handler
    def process_chat(message, history, session_id):
        if not message.strip():
            return history, "", session_id, "⚠️ No input given."
        
        try:
            history = history or []
            
            # Append user message with 'role' and 'content'
            history.append({'role': 'user', 'content': message})

            # Call your chatbot logic
            response = chatbot.ask(message, user_id=session_id)
            
            # Extract the response text safely
            response_text = str(getattr(response, "content", getattr(response, "text", response)))
            
            # Append bot response with 'role' and 'content'
            history.append({'role': 'assistant', 'content': response_text})

            # Update context progress
            context = context_manager.get_user_context(session_id)
            completion = context.get("completion_score", 0)
            progress_label = f"Profile completion: {completion:.0%}"
            
            return history, "", session_id, progress_label
            
        except Exception as e:
            logger.error(f"Error in process_chat: {e}")
            history.append({'role': 'assistant', 'content': f"❌ Error: {str(e)}"})
            return history, "", session_id, "⚠️ Error fetching profile progress"

    # Events
    submit_btn.click(
        process_chat,
        inputs=[user_input, chatbot_interface, session_state],
        outputs=[chatbot_interface, user_input, session_state, profile_progress]
    )

    clear_btn.click(
        lambda: ([], "", f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "Profile reset"),
        inputs=None,
        outputs=[chatbot_interface, user_input, session_state, profile_progress]
    )
if __name__ == "__main__":
    iface.launch(server_name="0.0.0.0", server_port=7860)
