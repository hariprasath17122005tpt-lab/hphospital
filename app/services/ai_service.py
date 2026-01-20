import ollama
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LocalAIService:
    """
    Service to interact with local Ollama AI models.
    Uses hospital-trained custom medical model for intelligent responses.
    """
    
    MODEL_NAME = "hospital-medical-ai"
    
    SYSTEM_PROMPT = """
    You are a professional Medical Information Assistant.
    Your goal is to provide helpful, clear, and medically-grounded information.
    
    STRICT RULES:
    1. You are NOT a doctor. Never provide a formal diagnosis.
    2. Never suggest specific medicine dosages.
    3. For emergencies (chest pain, severe bleeding, etc.), strictly tell the user to call emergency services immediately.
    4. Keep your response between 5 to 6 clear lines.
    5. Always end with: "Please consult a qualified healthcare professional for medical advice."
    6. Do not hallucinate. If you don't know, say you don't have information on that topic.
    7. Maintain a polite, professional, and empathetic tone.
    8. Focus on general health knowledge and symptom information.
    """
    
    @staticmethod
    def get_ai_response(user_message):
        """
        Sends a message to the local Ollama neural-chat model and returns the response.
        This uses the actual AI model for intelligent responses.
        """
        try:
            logger.info(f"Sending request to local AI ({LocalAIService.MODEL_NAME})...")
            
            response = ollama.chat(
                model=LocalAIService.MODEL_NAME,
                messages=[
                    {'role': 'system', 'content': LocalAIService.SYSTEM_PROMPT},
                    {'role': 'user', 'content': user_message},
                ],
                options={
                    'temperature': 0.7,  # Balanced for coherent but creative responses
                    'num_predict': 300,  # Allow longer, complete responses
                    'top_k': 40,  # Better response quality
                    'top_p': 0.9,  # Nucleus sampling
                }
            )
            
            content = response['message']['content'].strip()
            
            # Ensure medical disclaimer is present
            if "consult a qualified healthcare professional" not in content.lower() and "emergency" not in content.lower():
                content += "\n\nPlease consult a qualified healthcare professional for medical advice."
                
            return content

        except Exception as e:
            logger.error(f"Ollama Error: {str(e)}")
            return f"❌ Error connecting to AI model: {str(e)}. Please ensure Ollama is running with: `ollama serve` and the model is available."
