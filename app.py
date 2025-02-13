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
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("chatbot.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are Narabot, a kind and empathetic mental health assistant from NaraTherapy.
Your primary role is to provide emotional support, self-care tips, and a safe space for users to express themselves.
- Always use a warm and encouraging tone.
- Validate the user's feelings and offer compassionate guidance.
- Provide self-care advice, mindfulness exercises, and stress management techniques.
- Avoid giving medical advice or diagnosing conditions. Instead, suggest seeking professional help when necessary.
- But be very expressive, give them good detailed responses let them be encouraged to talk to you and be impressed too
- If a user expresses distress or crisis-level emotions, encourage them to reach out to a professional helpline.
- Keep responses friendly, concise, and supportive, ensuring users feel heard and valued. 
- If off-topic, you should answer them but also gently redirect them like saying By the way, I'm best at discussing mental well-being! Would you like to explore self-care or stress management tips? 😊.
"""

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
        """Checks for restricted terms and provides support for emergencies."""
        for term in self.config.blocked_terms:
            if term.lower() in text.lower():
                return False, f"I noticed some concerning words. If you're struggling, please reach out to {self.config.emergency_resources['crisis_line']} for immediate support. You're not alone. ❤️"

        emergency_terms = ["suicide", "kill", "die", "hurt", "harm", "emergency", "crisis"]
        if any(term in text.lower() for term in emergency_terms):
            return False, "I'm here for you. If you're feeling overwhelmed, please contact a crisis helpline or talk to someone you trust. You matter. 💙"

        return True, None

    def needs_redirect(self, text: str) -> bool:
        """Detects if a message is off-topic and should be gently redirected."""
        return not any(keyword.lower() in text.lower() for keyword in self.config.topic_keywords)


class MentalHealthChatbot:
    def __init__(self):
        self.load_config()
        self.moderator = ContentModerator(self.safety_config)

        # Initialize Gemini
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel("gemini-pro")
        self.chat = self.model.start_chat(history=[])

        # Initialize conversation memory
        self.conversation_history = []

    def load_config(self):
        """Load configuration from YAML"""
        with open("config.yaml", "r") as file:
            config = yaml.safe_load(file)
            self.safety_config = SafetyConfig(**config["safety"])


    async def get_response(self, message: str, history: List[List[str]]) -> str:
        """Processes user input and generates a response."""
        try:
            # Safety checks
            is_safe, warning = self.moderator.check_content(message)
            if not is_safe:
                return warning

            # Prepend system instructions to the message
            formatted_message = f"{SYSTEM_PROMPT}\n\nUser: {message}"

            # Generate AI response
            response = self.chat.send_message(formatted_message)

            return response.text

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return "Oops! I'm having trouble processing your request. Could you try rephrasing? 💡"
        
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return "Oops! I'm having trouble processing your request. Could you try rephrasing? 💡"

def create_interface() -> gr.ChatInterface:
    """Creates the Gradio chat interface."""
    chatbot = MentalHealthChatbot()

    chat_interface = gr.ChatInterface(
        fn=chatbot.get_response,
        title="Chat with Narabot 🧘‍♂️",
        description="I'm Narabot, here to support your mental well-being with friendly conversation and self-care tips. 💙",
        examples=[
            "I'm feeling anxious about my upcoming presentation",
            "Can you suggest some mindfulness exercises?",
            "How can I manage stress better?",
            "I'm having trouble sleeping lately",
            "Tell me something interesting!",
        ],
        theme=gr.themes.Soft(),
    )

    return chat_interface

if __name__ == "__main__":
    interface = create_interface()
    interface.launch(share=True)
