from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from agents.orchestrator_agent import orchestrator
import logging
import boto3
from datetime import datetime
import json


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

# Initialize systems
try:
    # Initialize RAG system
    rag_status = initialize_rag_system()
    logger.info(f"RAG Status: {rag_status}")
    
    # Initialize MCP Context Manager
    context_manager = MCPContextManager()
    logger.info("MCP Context Manager initialized")
    
except Exception as e:
    logger.error(f"Initialization error: {e}")
    context_manager = None

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
                    response += completion_note
            
            return response
            
        except Exception as e:
            logger.warning(f"Response enhancement error: {e}")
            return response

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

# --- Enhanced Gradio Interface ---
def chat_with_enhanced_housing_bot(user_input, session_state):
    """Enhanced chat function with session management"""
    
    if not user_input.strip():
        return "", session_state
    
    # Create session ID if new
    if not session_state:
        session_state = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    logger.info(f"Session {session_state}: {user_input}")
    
    try:
        response = chatbot.ask(user_input, user_id=session_state)
        
        logger.info(f"Session {session_state} Response: {response[:100]}...")
        return response, session_state
        
    except Exception as e:
        logger.error(f"Session {session_state} Error: {e}")
        error_response = f"I encountered an error: {str(e)}\n\nPlease try rephrasing your question or contact support if the issue persists."
        return error_response, session_state

# Create enhanced interface
with gr.Blocks(title="Enhanced Singapore Housing Assistant", theme=gr.themes.Soft()) as iface:
    
    gr.HTML("""
    <div style="text-align: center; padding: 20px;">
        <h1>🏠 Enhanced Singapore Housing Assistant</h1>
        <p style="font-size: 18px; color: #666;">
            AI-powered housing guidance with personalized recommendations and comprehensive knowledge base
        </p>
    </div>
    """)
    
    with gr.Row():
        with gr.Column(scale=3):
            chatbot_interface = gr.Chatbot(
                label="Housing Assistant Conversation",
                height=500,
                show_label=True,
                bubble_full_width=False
            )
            
            user_input = gr.Textbox(
                label="Your Message",
                placeholder="Ask about housing grants, property search, eligibility requirements, or any housing-related questions...",
                lines=3,
                show_label=True
            )
            
            with gr.Row():
                submit_btn = gr.Button("Send Message", variant="primary", size="lg")
                clear_btn = gr.Button("New Conversation", variant="secondary")
        
        with gr.Column(scale=1):
            gr.Markdown("### 🎯 Quick Start")
            
            sample_buttons = [
                "What housing grants am I eligible for as a Singapore citizen?",
                "Help me find a 4-room HDB flat in Tampines under $500k",
                "I earn $6000/month, what's my housing budget?",
                "Compare BTO vs resale HDB flats"
            ]
            
            for sample_query in sample_buttons:
                gr.Button(
                    sample_query, 
                    size="sm"
                ).click(
                    lambda q=sample_query: q,
                    outputs=user_input
                )
            
            gr.Markdown("### ℹ️ Features")
            gr.Markdown("""
            - **Smart Context**: Remembers your preferences
            - **RAG Knowledge**: Official HDB/CPF information  
            - **Decision Support**: AI-powered recommendations
            - **Real-time Search**: Current property listings
            """)
    
    # Session state
    session_state = gr.State()
    
    def process_chat(message, history, session_id):
        if not message.strip():
            return history, "", session_id
        
        history = history or []
        history.append([message, None])
        
        response, new_session_id = chat_with_enhanced_housing_bot(message, session_id)
        history[-1][1] = response
        
        return history, "", new_session_id
    
    # Event handlers
    submit_btn.click(
        process_chat,
        inputs=[user_input, chatbot_interface, session_state],
        outputs=[chatbot_interface, user_input, session_state]
    )
    
    user_input.submit(
        process_chat,
        inputs=[user_input, chatbot_interface, session_state],
        outputs=[chatbot_interface, user_input, session_state]
    )
    
    clear_btn.click(
        lambda: ([], "", None),
        outputs=[chatbot_interface, user_input, session_state]
    )

if __name__ == "__main__":
    logger.info("🚀 Launching Enhanced Singapore Housing Assistant")
    logger.info("Features: RAG Knowledge Base, Context Management, Decision Support")
    
    iface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,  # Set to False for local only
        show_error=True
    )