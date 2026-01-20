"""
PHASE 2: FLASK CHATBOT BACKEND
Hospital Management System - AI Medical Chatbot Feature

Features:
- /api/ai-chat endpoint for medical queries
- Ollama integration (local AI model)
- Safety system prompt
- Error handling
- Response formatting
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import logging
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import safety prompt from phase 3
from PHASE_3_SYSTEM_PROMPT import MEDICAL_CHATBOT_SYSTEM_PROMPT

# ==========================================
# CONFIGURATION
# ==========================================

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "neural-chat"  # Using Neural Chat 7B

# Ollama generation parameters
OLLAMA_PARAMS = {
    "temperature": 0.3,  # Lower = more conservative, less hallucination
    "top_p": 0.9,        # Nucleus sampling
    "num_predict": 200,  # Max tokens in response (~5-6 lines)
    "num_ctx": 512,      # Context window (keep small for VRAM efficiency)
}

# ==========================================
# FLASK APP INITIALIZATION
# ==========================================

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# ==========================================
# HEALTH CHECK - Verify Ollama is running
# ==========================================

def check_ollama_health():
    """Check if Ollama server is running"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        return response.status_code == 200
    except:
        return False


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    ollama_running = check_ollama_health()
    
    return jsonify({
        "status": "ok" if ollama_running else "error",
        "ollama": "running" if ollama_running else "not_running",
        "timestamp": datetime.now().isoformat(),
        "service": "Hospital AI Chatbot"
    }), 200 if ollama_running else 503


@app.route('/api/ai-chat', methods=['POST'])
def ai_chat():
    """
    Main chatbot endpoint
    
    Request:
    {
        "message": "I have a fever"
    }
    
    Response:
    {
        "success": true,
        "response": "A fever is...",
        "timestamp": "2025-12-19T10:30:00",
        "model": "neural-chat",
        "processing_time_ms": 2500
    }
    """
    
    try:
        import time
        start_time = time.time()
        
        # Get message from request
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'message' field in request"
            }), 400
        
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({
                "success": False,
                "error": "Message cannot be empty"
            }), 400
        
        if len(user_message) > 500:
            return jsonify({
                "success": False,
                "error": "Message too long (max 500 characters)"
            }), 400
        
        logger.info(f"User query: {user_message}")
        
        # ==========================================
        # CALL OLLAMA AI MODEL
        # ==========================================
        
        # Prepare the request to Ollama
        ollama_request = {
            "model": OLLAMA_MODEL,
            "prompt": user_message,
            "system": MEDICAL_CHATBOT_SYSTEM_PROMPT,
            "stream": False,
            **OLLAMA_PARAMS
        }
        
        # Send to Ollama
        logger.info("Sending request to Ollama...")
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=ollama_request,
            timeout=60
        )
        
        # Check if request succeeded
        if response.status_code != 200:
            logger.error(f"Ollama error: {response.status_code}")
            return jsonify({
                "success": False,
                "error": "AI model error",
                "details": response.text
            }), 503
        
        # Parse response
        ollama_response = response.json()
        ai_response = ollama_response.get('response', '').strip()
        
        if not ai_response:
            return jsonify({
                "success": False,
                "error": "No response from AI model"
            }), 500
        
        # ==========================================
        # POST-PROCESS RESPONSE
        # ==========================================
        
        # Clean up response (remove extra whitespace)
        ai_response = ' '.join(ai_response.split())
        
        # Ensure response ends with safety disclaimer if not present
        if "consult" not in ai_response.lower():
            ai_response += " Please consult a healthcare professional for proper medical advice."
        
        processing_time = int((time.time() - start_time) * 1000)
        
        logger.info(f"Response generated in {processing_time}ms")
        
        # ==========================================
        # RETURN SUCCESS RESPONSE
        # ==========================================
        
        return jsonify({
            "success": True,
            "response": ai_response,
            "user_message": user_message,
            "timestamp": datetime.now().isoformat(),
            "model": OLLAMA_MODEL,
            "processing_time_ms": processing_time
        }), 200
    
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Ollama server")
        return jsonify({
            "success": False,
            "error": "Ollama server is not running",
            "hint": "Run 'ollama serve' in a terminal"
        }), 503
    
    except requests.exceptions.Timeout:
        logger.error("Ollama request timeout")
        return jsonify({
            "success": False,
            "error": "AI model response timeout",
            "hint": "Model took too long to respond. Try again."
        }), 504
    
    except json.JSONDecodeError:
        logger.error("Invalid JSON response from Ollama")
        return jsonify({
            "success": False,
            "error": "Invalid response from AI model"
        }), 500
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ==========================================
# INFO ENDPOINT
# ==========================================

@app.route('/api/ai-info', methods=['GET'])
def ai_info():
    """Get chatbot information"""
    return jsonify({
        "name": "Hospital AI Medical Chatbot",
        "version": "1.0",
        "purpose": "General medical information only",
        "model": OLLAMA_MODEL,
        "model_size": "7B parameters",
        "hardware_requirements": "16GB RAM, RTX 3050",
        "safety_level": "Medical safety prompt enabled",
        "endpoints": [
            "POST /api/ai-chat - Send medical query",
            "GET /api/health - Server health check",
            "GET /api/ai-info - This info"
        ],
        "disclaimer": "This chatbot provides general medical information only. Not a replacement for professional medical advice.",
        "timestamp": datetime.now().isoformat()
    }), 200


# ==========================================
# ERROR HANDLERS
# ==========================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500


# ==========================================
# STARTUP MESSAGE
# ==========================================

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("🏥 HOSPITAL MANAGEMENT SYSTEM - AI MEDICAL CHATBOT")
    print("=" * 80)
    print("\n📋 CONFIGURATION:")
    print(f"   Model: {OLLAMA_MODEL}")
    print(f"   Ollama Server: {OLLAMA_BASE_URL}")
    print(f"   Temperature: {OLLAMA_PARAMS['temperature']} (conservative)")
    print(f"   Max tokens: {OLLAMA_PARAMS['num_predict']}")
    
    print("\n🔌 API ENDPOINTS:")
    print("   POST /api/ai-chat - Send medical query")
    print("   GET  /api/health - Check server health")
    print("   GET  /api/ai-info - Get chatbot info")
    
    print("\n⚠️  REQUIREMENTS:")
    print("   ✅ Ollama must be running (ollama serve)")
    print("   ✅ Neural Chat model downloaded (ollama pull neural-chat)")
    print("   ✅ CUDA/GPU support for RTX 3050")
    
    print("\n🚀 STARTING SERVER:")
    print("   URL: http://localhost:5000")
    print("   Debug: False (Production ready)")
    print("=" * 80 + "\n")
    
    # Check Ollama before starting
    if not check_ollama_health():
        print("⚠️  WARNING: Ollama server is not running!")
        print("   Please run: ollama serve")
        print("   in another terminal before making API requests.\n")
    
    # Start Flask server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )
