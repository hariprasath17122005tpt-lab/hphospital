import os
import logging
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Lazy-loaded local chatbot singleton
_local_chatbot = None


def _get_local_chatbot():
    """Return (and cache) the local dataset-based medical chatbot."""
    global _local_chatbot
    if _local_chatbot is None:
        try:
            from app.ml_models.strict_medical_chatbot import StrictMedicalChatbot
            _local_chatbot = StrictMedicalChatbot()
        except Exception as e:
            logger.error(f"Failed to load local chatbot: {e}")
    return _local_chatbot


class LocalAIService:
    """
    AI Service with automatic fallback:
      1. Groq Cloud API (if GROQ_API_KEY is set)
      2. Local dataset-based medical chatbot (always available)
    """

    MODEL_NAME = "llama-3.3-70b-versatile"

    SYSTEM_PROMPT = """
    You are a professional Medical Information Assistant for a hospital management system.
    Your goal is to provide helpful, clear, and medically-grounded information.

    STRICT RULES:
    1. You are NOT a doctor. Never provide a formal diagnosis.
    2. Never suggest specific medicine dosages.
    3. For emergencies (chest pain, severe bleeding, difficulty breathing, etc.), immediately tell the user to call emergency services or visit the ER.
    4. Keep your response concise - between 3 to 5 clear sentences.
    5. Always end with: "Please consult a qualified healthcare professional for medical advice."
    6. Do not hallucinate. If you don't know, say you don't have information on that topic.
    7. Maintain a polite, professional, and empathetic tone.
    8. Focus on general health knowledge and symptom information.
    """

    @staticmethod
    def get_ai_response(user_message):
        """Get AI response — tries Groq Cloud first, falls back to local dataset."""
        logger.info(f"[AI] AI Service called with message: {user_message[:50]}...")

        api_key = os.getenv('GROQ_API_KEY')

        # If Groq is configured, use cloud AI
        if api_key and api_key != "YOUR_GROQ_KEY_HERE":
            result = LocalAIService._call_groq(user_message, api_key)
            if result is not None:
                return result
            # Groq failed — fall through to local chatbot

        # Fallback: local dataset chatbot
        return LocalAIService._call_local_chatbot(user_message)

    @staticmethod
    def _call_groq(user_message, api_key):
        """Call Groq Cloud API. Returns response text or None on failure."""
        api_url = "https://api.groq.com/openai/v1/chat/completions"
        model = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')

        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": LocalAIService.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.7,
                "max_tokens": 400
            }

            logger.info("[CLOUD] Sending request to Groq API...")
            response = requests.post(api_url, headers=headers, json=payload, timeout=15)

            if response.status_code == 200:
                data = response.json()
                ai_text = data['choices'][0]['message']['content'].strip()
                logger.info(f"[OK] Groq response received ({len(ai_text)} chars)")
                return LocalAIService._format_response(ai_text)

            logger.warning(f"[WARN] Groq returned {response.status_code}, falling back to local")
            return None

        except Exception as e:
            logger.warning(f"[WARN] Groq request failed ({e}), falling back to local")
            return None

    @staticmethod
    def _call_local_chatbot(user_message):
        """Use the local dataset-based medical chatbot."""
        chatbot = _get_local_chatbot()
        if chatbot:
            try:
                response = chatbot.get_response(user_message)
                logger.info("[LOCAL] Local chatbot response returned")
                return response
            except Exception as e:
                logger.error(f"[ERROR] Local chatbot failed: {e}")

        return (
            "I'm sorry, I couldn't process your request right now. "
            "Please consult a qualified healthcare professional for medical advice."
        )

    @staticmethod
    def _format_response(content):
        """Ensure medical disclaimer is present."""
        if "consult a qualified healthcare professional" not in content.lower() and "emergency" not in content.lower():
            content += "\n\nPlease consult a qualified healthcare professional for medical advice."
        return content
