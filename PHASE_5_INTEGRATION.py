"""
PHASE 5: HOSPITAL SYSTEM INTEGRATION
How to integrate AI Medical Chatbot into Hospital Management System
"""

# ==========================================
# OPTION 1: PYTHON INTEGRATION
# ==========================================

"""
If your Hospital Management System is built with Python/Flask,
add this to your main Flask app:
"""

# In your main hospital system app.py, add:

from PHASE_2_FLASK_BACKEND import app as chatbot_app
from flask import Flask

# Create main hospital app
hospital_app = Flask(__name__)

# Register chatbot as blueprint
hospital_app.register_blueprint(
    chatbot_app,
    url_prefix='/hospital/ai'
)

# Now chatbot endpoints are:
# POST /hospital/ai/api/ai-chat
# GET /hospital/ai/api/health
# GET /hospital/ai/api/ai-info


# ==========================================
# OPTION 2: MICROSERVICES (RECOMMENDED)
# ==========================================

"""
Run Flask chatbot as separate service:

Hospital System (Port 3000/5001)
          |
          v
AI Chatbot Service (Port 5000)
          |
          v
Ollama Server (Port 11434)

Benefits:
- Chatbot can restart independently
- No memory leaks in main system
- Easy to scale
- Can run on different machines
"""


# ==========================================
# OPTION 3: JAVASCRIPT/FRONTEND INTEGRATION
# ==========================================

# HTML/JavaScript Example

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Hospital Management - AI Assistant</title>
    <style>
        .chatbot-container {
            max-width: 600px;
            margin: 20px auto;
            border: 1px solid #ccc;
            border-radius: 8px;
            padding: 20px;
            background: #f9f9f9;
        }
        
        .chatbot-header {
            background: #2196F3;
            color: white;
            padding: 15px;
            border-radius: 8px 8px 0 0;
            margin: -20px -20px 20px -20px;
        }
        
        .chatbot-messages {
            height: 400px;
            overflow-y: auto;
            margin-bottom: 20px;
            padding: 10px;
            background: white;
            border-radius: 4px;
        }
        
        .message {
            margin-bottom: 10px;
            padding: 10px;
            border-radius: 4px;
        }
        
        .message.user {
            background: #E3F2FD;
            text-align: right;
        }
        
        .message.bot {
            background: #F5F5F5;
        }
        
        .input-group {
            display: flex;
            gap: 10px;
        }
        
        #userInput {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        
        #sendBtn {
            padding: 10px 20px;
            background: #2196F3;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        
        .disclaimer {
            background: #FFF3E0;
            padding: 10px;
            border-left: 4px solid #FF9800;
            margin-top: 10px;
            font-size: 12px;
            color: #666;
        }
        
        .loading {
            text-align: center;
            color: #999;
            font-style: italic;
        }
    </style>
</head>
<body>

<div class="chatbot-container">
    <div class="chatbot-header">
        <h2>🏥 Hospital AI Assistant</h2>
        <p style="margin: 5px 0 0 0; font-size: 12px;">General Medical Information</p>
    </div>
    
    <div class="chatbot-messages" id="chatMessages"></div>
    
    <div class="input-group">
        <input 
            type="text" 
            id="userInput" 
            placeholder="Ask a medical question (e.g., 'I have a fever')"
            onkeypress="if(event.key=='Enter') sendMessage()"
        />
        <button id="sendBtn" onclick="sendMessage()">Send</button>
    </div>
    
    <div class="disclaimer">
        ⚠️ This chatbot provides general medical information only. 
        It is NOT a replacement for professional medical advice. 
        Always consult a qualified healthcare professional for diagnosis and treatment.
    </div>
</div>

<script>
    const API_URL = 'http://localhost:5000/api/ai-chat';
    
    function addMessage(text, isUser) {
        const messagesDiv = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message ' + (isUser ? 'user' : 'bot');
        messageDiv.textContent = text;
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    async function sendMessage() {
        const input = document.getElementById('userInput');
        const message = input.value.trim();
        
        if (!message) return;
        
        // Add user message
        addMessage(message, true);
        input.value = '';
        
        // Show loading
        addMessage('Thinking...', false);
        
        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });
            
            if (!response.ok) {
                const error = await response.json();
                addMessage('Error: ' + error.error, false);
                return;
            }
            
            const data = await response.json();
            
            // Remove loading message and add response
            const messagesDiv = document.getElementById('chatMessages');
            messagesDiv.removeChild(messagesDiv.lastChild);
            
            addMessage(data.response, false);
            
        } catch (error) {
            const messagesDiv = document.getElementById('chatMessages');
            messagesDiv.removeChild(messagesDiv.lastChild);
            addMessage('Error: Cannot connect to AI service. Make sure the backend is running.', false);
        }
    }
    
    // Welcome message
    window.addEventListener('load', () => {
        addMessage('Hello! I am your Hospital AI Assistant. I can provide general medical information. What would you like to know?', false);
    });
</script>

</body>
</html>
"""


# ==========================================
# INTEGRATION CHECKLIST
# ==========================================

INTEGRATION_CHECKLIST = """
HOSPITAL SYSTEM INTEGRATION CHECKLIST
=====================================

PHASE 1: SETUP
[] Install Ollama (https://ollama.ai)
[] Download Neural Chat model: ollama pull neural-chat
[] Verify Ollama runs: ollama serve
[] Install Python dependencies: pip install flask flask-cors requests

PHASE 2: BACKEND SETUP
[] Copy PHASE_2_FLASK_BACKEND.py to hospital system folder
[] Copy PHASE_3_SYSTEM_PROMPT.py to hospital system folder
[] Test Flask server: python PHASE_2_FLASK_BACKEND.py
[] Verify health endpoint: curl http://localhost:5000/api/health

PHASE 3: INTEGRATION
[] Create chatbot UI component (see HTML template above)
[] Add chatbot button/tab to hospital system dashboard
[] Connect frontend to /api/ai-chat endpoint
[] Add disclaimer text (mandatory)

PHASE 4: TESTING
[] Run PHASE_4_TESTING.py
[] Test with sample queries (fever, headache, pain)
[] Verify error handling
[] Test edge cases

PHASE 5: DEPLOYMENT
[] Set Ollama to run as Windows service
[] Configure Flask for production (production WSGI server)
[] Add logging and monitoring
[] Set up backup/restart scripts
[] Add to hospital system documentation

PHASE 6: MONITORING
[] Monitor Ollama memory usage
[] Monitor Flask response times
[] Track error logs
[] Regular model updates

DOCUMENTATION
[] Add to user manual
[] Add disclaimer on every AI response
[] Create admin guide
[] Document troubleshooting steps
"""


# ==========================================
# IMPORTANT DISCLAIMERS
# ==========================================

LEGAL_DISCLAIMER = """
MANDATORY DISCLAIMERS FOR HOSPITAL SYSTEM
==========================================

Every AI response MUST include:

"⚠️ DISCLAIMER: This chatbot provides general medical information only.
It is NOT a replacement for professional medical advice, diagnosis, or treatment.
Always consult a qualified healthcare professional for your specific medical condition.
In case of emergency, call 911 or visit the nearest hospital immediately."

This must appear:
1. On every chatbot page
2. At the end of every AI response
3. In the system documentation
4. During user registration/onboarding
"""


# ==========================================
# DATABASE CONSIDERATIONS
# ==========================================

DATABASE_CONSIDERATIONS = """
If you want to save chat history in your hospital system:

1. Create chat_history table:

CREATE TABLE chat_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_message TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    processing_time_ms INT,
    model_version VARCHAR(50),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

2. Modify PHASE_2_FLASK_BACKEND.py to save to database:

from your_db import save_chat_history

@app.route('/api/ai-chat', methods=['POST'])
def ai_chat():
    # ... existing code ...
    
    # Save to database
    save_chat_history(
        user_id=current_user.id,
        user_message=user_message,
        ai_response=ai_response,
        processing_time_ms=processing_time
    )

3. Create chat history view for administrators to review

4. Follow HIPAA/medical data privacy regulations
"""


# ==========================================
# PERFORMANCE CONSIDERATIONS
# ==========================================

PERFORMANCE_TIPS = """
OPTIMIZATION TIPS
=================

1. RESPONSE TIME
   - Current: 2-5 seconds per response
   - Acceptable for medical context (safety > speed)
   - If slower, check GPU: nvidia-smi

2. MEMORY OPTIMIZATION
   - Neural Chat 7B uses ~6-8GB VRAM
   - RAM usage: ~4-6GB
   - Monitor with Task Manager
   - If OOM errors, use quantized model

3. CONCURRENT USERS
   - Flask can handle ~10 concurrent requests
   - For more users, use:
     * Gunicorn: gunicorn -w 4 PHASE_2_FLASK_BACKEND:app
     * Docker: containerize the service
     * Load balancer: distribute requests

4. MODEL CACHING
   - Ollama keeps model in memory
   - First request: 5-10 seconds
   - Subsequent: 2-3 seconds
   - Normal behavior

5. UPGRADE PATH
   - Larger model: Use Mistral 7B (similar performance)
   - Faster: Use TinyLlama (smaller, less accurate)
   - Better: Use 13B model (needs more VRAM)
"""


# ==========================================
# TROUBLESHOOTING INTEGRATION
# ==========================================

TROUBLESHOOTING = """
COMMON INTEGRATION ISSUES
==========================

ISSUE: "Cannot connect to AI service"
FIX:
  1. Check Ollama is running: ollama serve
  2. Check Flask is running: python PHASE_2_FLASK_BACKEND.py
  3. Check port 5000 is not blocked
  4. Check firewall settings

ISSUE: "Slow responses (>20 seconds)"
FIX:
  1. Check GPU: nvidia-smi
  2. Close other applications
  3. Restart Ollama and Flask
  4. Check system temperature (might throttle)

ISSUE: "Out of memory errors"
FIX:
  1. Close other applications
  2. Use quantized model: ollama pull neural-chat:7b-v3-q4_0
  3. Reduce num_ctx in PHASE_2_FLASK_BACKEND.py

ISSUE: "Model not responding"
FIX:
  1. Reinstall model: ollama pull neural-chat --insecure
  2. Check disk space for model
  3. Restart Ollama service

ISSUE: "CORS errors in frontend"
FIX:
  1. Flask-CORS is already enabled
  2. Check frontend URL in browser console
  3. Verify API endpoint is correct
"""


if __name__ == "__main__":
    print("=" * 80)
    print("PHASE 5: HOSPITAL SYSTEM INTEGRATION")
    print("=" * 80)
    
    print("\n" + INTEGRATION_CHECKLIST)
    print("\n" + "=" * 80)
    print(LEGAL_DISCLAIMER)
    print("\n" + "=" * 80)
    print(DATABASE_CONSIDERATIONS)
    print("\n" + "=" * 80)
    print(PERFORMANCE_TIPS)
    print("\n" + "=" * 80)
    print(TROUBLESHOOTING)
    
    print("\n" + "=" * 80)
    print("HTML TEMPLATE (save as chatbot.html)")
    print("=" * 80)
    print(HTML_TEMPLATE)
