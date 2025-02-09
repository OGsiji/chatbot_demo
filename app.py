# app.py
import os
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass
import yaml
import gradio as gr
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chatbot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SafetyConfig:
    """Configuration for safety parameters and content moderation"""
    blocked_terms: List[str]
    topic_keywords: List[str]
    max_response_length: int
    emergency_resources: Dict[str, str]

class ContentModerator:
    """Handles content moderation and safety checks"""
    
    def __init__(self, config: SafetyConfig):
        self.config = config
    
    def check_content(self, text: str) -> tuple[bool, Optional[str]]:
        # Check for blocked terms
        for term in self.config.blocked_terms:
            if term.lower() in text.lower():
                return False, f"I noticed some concerning content. Here are some resources that might help: {self.config.emergency_resources['crisis_line']}"
        
        # Check for emergency keywords
        emergency_terms = ['suicide', 'kill', 'die', 'hurt', 'harm', 'emergency', 'crisis']
        if any(term in text.lower() for term in emergency_terms):
            return False, "If you're having thoughts of self-harm or experiencing a crisis, please contact emergency services or call the crisis helpline immediately."
        
        return True, None

    def validate_scope(self, text: str) -> bool:
        """Ensure conversation stays within mental health topics"""
        return any(keyword.lower() in text.lower() for keyword in self.config.topic_keywords)

class MentalHealthChatbot:
    def __init__(self):
        self.load_config()
        self.moderator = ContentModerator(self.safety_config)
        
        # Initialize Gemini
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel('gemini-pro')
        self.chat = self.model.start_chat(history=[])
        
        # Initialize conversation memory
        self.conversation_history = []
    
    def load_config(self):
        """Load configuration from YAML"""
        with open('config.yaml', 'r') as file:
            config = yaml.safe_load(file)
            self.safety_config = SafetyConfig(**config['safety'])
    
    async def get_response(self, message: str, history: List[List[str]]) -> str:
        """Process message and return response"""
        try:
            # Safety checks
            is_safe, warning = self.moderator.check_content(message)
            if not is_safe:
                return warning
            
            if not self.moderator.validate_scope(message):
                return "I'm here to help with mental health topics. Could you please rephrase your question in that context?"
            
            # Generate response
            response = self.chat.send_message(message)
            return response.text
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return "I apologize, but I'm having trouble processing your request. Please try again."

def create_interface() -> gr.ChatInterface:
    """Create Gradio interface"""
    chatbot = MentalHealthChatbot()
    
    chat_interface = gr.ChatInterface(
        fn=chatbot.get_response,
        title="Mental Health Support Chat",
        description="I'm here to help you with mental health topics, stress management, and coping strategies.",
        examples=[
            "I'm feeling anxious about my upcoming presentation",
            "Can you suggest some mindfulness exercises?",
            "How can I manage stress better?",
            "I'm having trouble sleeping lately"
        ],
        theme=gr.themes.Soft(),
    )
    
    return chat_interface

if __name__ == "__main__":
    interface = create_interface()
    interface.launch(share=True)