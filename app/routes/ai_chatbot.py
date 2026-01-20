"""
AI Medical Chatbot Integration for Healthcare System
Routes for AI chatbot functionality
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
import requests
import logging
from datetime import datetime
from app.models.models import db

# Import ChatHistory only when needed to avoid circular imports
try:
    from app.models.models import ChatHistory
except ImportError:
    ChatHistory = None

# Create blueprint
ai_bp = Blueprint('ai_chatbot', __name__, url_prefix='/api/ai')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "neural-chat"
API_TIMEOUT = 60

# Medical Safety System Prompt
MEDICAL_SYSTEM_PROMPT = """You are a helpful medical information assistant for a hospital management system. 
Your role is to provide accurate, safe medical information to help patients understand their conditions better.

CRITICAL RULES:
1. NEVER diagnose patients or claim to diagnose
2. NEVER prescribe specific medications or dosages
3. NEVER provide emergency medical advice
4. ALWAYS recommend consulting a healthcare professional
5. Provide general medical information only
6. Be clear about limitations of AI assistance
7. Use simple, patient-friendly language
8. Include appropriate disclaimers

For emergency situations (chest pain, severe bleeding, difficulty breathing), 
ALWAYS respond with: "This requires immediate medical attention. Please call emergency services or go to the nearest hospital immediately."

Keep responses concise (5-6 lines) and medically accurate.
Always end with a recommendation to consult a healthcare professional."""


class MedicalChatbotService:
    """Service for handling AI chatbot interactions"""
    
    @staticmethod
    def check_ollama_health():
        """Check if Ollama server is running"""
        try:
            response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {str(e)}")
            return False
    
    @staticmethod
    def get_ai_response(message):
        """Get response from Ollama AI model"""
        try:
            # Prepare request to Ollama
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": message,
                "system": MEDICAL_SYSTEM_PROMPT,
                "temperature": 0.3,  # Conservative to prevent hallucination
                "top_p": 0.9,
                "num_predict": 200,  # ~5-6 lines
                "stream": False
            }
            
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                timeout=API_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response": result.get("response", "").strip(),
                    "model": OLLAMA_MODEL
                }
            else:
                return {
                    "success": False,
                    "error": f"Ollama returned status {response.status_code}"
                }
                
        except requests.Timeout:
            return {
                "success": False,
                "error": "Request timeout. Model may be processing a large request."
            }
        except requests.ConnectionError:
            return {
                "success": False,
                "error": "Cannot connect to Ollama server. Please ensure Ollama is running."
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {
                "success": False,
                "error": f"Internal error: {str(e)}"
            }


# ==========================================
# Routes
# ==========================================

@ai_bp.route('/health', methods=['GET'])
def health_check():
    """Check if AI chatbot service is healthy"""
    ollama_running = MedicalChatbotService.check_ollama_health()
    
    return jsonify({
        "status": "healthy" if ollama_running else "degraded",
        "ollama_running": ollama_running,
        "model": OLLAMA_MODEL,
        "timestamp": datetime.utcnow().isoformat()
    }), 200 if ollama_running else 503


@ai_bp.route('/info', methods=['GET'])
def info():
    """Get AI chatbot information"""
    return jsonify({
        "service": "Hospital AI Medical Chatbot",
        "model": OLLAMA_MODEL,
        "version": "1.0.0",
        "features": [
            "Medical information lookup",
            "Symptom explanation",
            "General health guidance",
            "Hospital integration"
        ],
        "limitations": [
            "Not a diagnosis tool",
            "Cannot prescribe medication",
            "Cannot provide emergency advice",
            "Always recommend doctor consultation"
        ],
        "endpoints": {
            "health": "GET /api/ai/health",
            "info": "GET /api/ai/info",
            "chat": "POST /api/ai/chat"
        }
    }), 200


@ai_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    """
    Main chat endpoint for medical queries
    
    Request JSON:
    {
        "message": "User's medical question"
    }
    
    Response JSON:
    {
        "success": true/false,
        "response": "AI's answer",
        "model": "neural-chat",
        "user_id": 123,
        "timestamp": "2025-12-23T..."
    }
    """
    
    try:
        # Validate request
        if not request.is_json:
            return jsonify({
                "success": False,
                "error": "Request must be JSON"
            }), 400
        
        data = request.get_json()
        message = data.get('message', '').strip()
        
        # Validate message
        if not message:
            return jsonify({
                "success": False,
                "error": "Message cannot be empty"
            }), 400
        
        if len(message) > 500:
            return jsonify({
                "success": False,
                "error": "Message too long (max 500 characters)"
            }), 400
        
        # Check Ollama health
        if not MedicalChatbotService.check_ollama_health():
            return jsonify({
                "success": False,
                "error": "AI service unavailable. Please ensure Ollama is running."
            }), 503
        
        # Get AI response
        ai_response = MedicalChatbotService.get_ai_response(message)
        
        if not ai_response["success"]:
            return jsonify(ai_response), 500
        
        # Save chat to database (if ChatHistory model exists)
        try:
            if ChatHistory:
                chat_entry = ChatHistory(
                    user_id=current_user.id,
                    user_message=message,
                    ai_response=ai_response["response"],
                    model_used=ai_response["model"],
                    timestamp=datetime.utcnow()
                )
                db.session.add(chat_entry)
                db.session.commit()
                chat_id = chat_entry.id
            else:
                chat_id = None
        except Exception as e:
            logger.warning(f"Could not save chat to database: {str(e)}")
            chat_id = None
        
        # Return successful response
        return jsonify({
            "success": True,
            "response": ai_response["response"],
            "model": ai_response["model"],
            "user_id": current_user.id,
            "chat_id": chat_id,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500


@ai_bp.route('/chat-history', methods=['GET'])
@login_required
def get_chat_history():
    """Get chat history for current user"""
    if not ChatHistory:
        return jsonify({
            "success": False,
            "error": "Chat history feature not available"
        }), 503
    
    try:
        # Fetch chat history
        chats = ChatHistory.query.filter_by(user_id=current_user.id)\
            .order_by(ChatHistory.timestamp.desc())\
            .limit(50)\
            .all()
        
        history = [{
            "id": chat.id,
            "user_message": chat.user_message,
            "ai_response": chat.ai_response,
            "timestamp": chat.timestamp.isoformat(),
            "model": chat.model_used
        } for chat in chats]
        
        return jsonify({
            "success": True,
            "count": len(history),
            "history": history
        }), 200
    
    except Exception as e:
        logger.error(f"Chat history error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to fetch chat history: {str(e)}"
        }), 500


@ai_bp.route('/clear-history', methods=['POST'])
@login_required
def clear_chat_history():
    """Clear chat history for current user"""
    if not ChatHistory:
        return jsonify({
            "success": False,
            "error": "Chat history feature not available"
        }), 503
    
    try:
        ChatHistory.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Chat history cleared"
        }), 200
    
    except Exception as e:
        logger.error(f"Clear history error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to clear chat history: {str(e)}"
        }), 500
