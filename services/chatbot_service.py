import os
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

class ChatbotService:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_CHATBOT_KEY', '').strip()
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Try to find an available model
            try:
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                
                # Preferred models in order
                preferred = [
                    'models/gemini-2.5-flash',
                    'models/gemini-2.0-flash',
                    'models/gemini-1.5-flash',
                    'models/gemini-1.5-flash-latest',
                    'models/gemini-pro'
                ]
                
                selected_model = None
                for p in preferred:
                    if p in available_models:
                        selected_model = p
                        break
                
                if not selected_model and available_models:
                    # Fallback to the first available flash model
                    flash_models = [m for m in available_models if 'flash' in m.lower()]
                    selected_model = flash_models[0] if flash_models else available_models[0]
                
                if selected_model:
                    logger.info(f"Chatbot using model: {selected_model}")
                    self.model = genai.GenerativeModel(selected_model.replace('models/', ''))
                else:
                    self.model = None
            except Exception as e:
                logger.error(f"Error listing Gemini models: {str(e)}")
                # Hard fallback to 1.5-flash and hope for the best
                self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    def get_chat_response(self, messages, user_profile=None):
        """
        Generates a response from Gemini based on chat history and user profile.
        
        Args:
            messages (list): List of dicts with 'role' and 'content' keys.
            user_profile (dict, optional): User profile data for personalization.
            
        Returns:
            str: AI response text or error message.
        """
        if not self.model:
            return "AI assistant is temporarily unavailable. Please try again later."

        try:
            # System instructions
            system_prompt = (
                "You are a reliable Indian investment assistant.\\n\\n"
                "Rules:\\n"
                "- Use real, well-known Indian market facts only.\\n"
                "- Keep answers short (1–3 lines).\\n"
                "- Use simple language (no jargon).\\n"
                "- You may mention popular Indian companies or sectors as examples.\\n"
                "- Never guarantee returns or say 'buy/sell now'.\\n"
                "- Add light caution like 'for awareness' or 'for tracking'.\\n\\n"
                "Avoid:\\n"
                "- Long explanations\\n"
                "- Legal or SEBI warnings\\n"
                "- Saying 'I cannot suggest'\\n\\n"
                "Tone: clear, honest, practical."
            )

            # Personalization context
            context_prompt = ""
            if user_profile:
                age = user_profile.get('age', 'not specified')
                risk = user_profile.get('risk_tolerance', 'medium')
                horizon = user_profile.get('investment_horizon', 'not specified')
                total_value = user_profile.get('total_portfolio_value', 0)
                
                context_prompt = (
                    f"User Profile Context: Use this info if relevant but do not repeat it unless asked. "
                    f"Age: {age}, Risk Tolerance: {risk}, Investment Horizon: {horizon}, "
                    f"Current Portfolio Value: ₹{total_value:,.2f}.\n"
                )

            # Prepare the history for Gemini
            
            history = []
            for msg in messages[-3:]:
                role = "user" if msg['role'] == 'user' else "model"
                history.append({"role": role, "parts": [msg['content']]})

            # Combine system prompt, context, and the latest user message
           
            
            # Start a chat session
            chat = self.model.start_chat(history=history)
            
            # Injecting system and context as a single instruction if history is empty
           
            full_prompt = f"{system_prompt}\n{context_prompt}\nUser message: {messages[-1]['content']}"
            
            response = chat.send_message(full_prompt)
            return response.text.strip()

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Gemini Chatbot Exception: {str(e)}\n{error_details}")
            # Check if it was a safety block or other response issue
            if 'response' in locals() and hasattr(response, 'candidates'):
                 logger.error(f"Response safety ratings: {response.candidates[0].safety_ratings}")
            
            return "AI assistant is temporarily unavailable. Please try again later."
