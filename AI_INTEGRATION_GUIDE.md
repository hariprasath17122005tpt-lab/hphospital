# AI Chatbot Integration Guide - Healthcare System

## ✅ Integration Complete

Your AI Medical Chatbot has been integrated into your healthcare management system. Here's what was done:

---

## 📁 Files Added/Modified

### New Files Created:
1. **app/routes/ai_chatbot.py** - AI chatbot route blueprint with 5 endpoints
2. **app/templates/ai_chatbot_component.html** - Beautiful chat UI component
3. **This file** - Integration documentation

### Modified Files:
1. **app/__init__.py** - Registered ai_chatbot blueprint
2. **app/models/models.py** - Added ChatHistory model for storing conversations

---

## 🔌 API Endpoints

All endpoints require the user to be logged in (`@login_required`).

### 1. Health Check
```
GET /api/ai/health
```

**Response:**
```json
{
    "status": "healthy",
    "ollama_running": true,
    "model": "neural-chat",
    "timestamp": "2025-12-23T..."
}
```

**Status Codes:**
- 200: Service healthy and Ollama running
- 503: Service degraded (Ollama not running)

---

### 2. Chat Endpoint (Main)
```
POST /api/ai/chat
```

**Request:**
```json
{
    "message": "I have a fever"
}
```

**Response (Success):**
```json
{
    "success": true,
    "response": "A fever is when your body temperature...",
    "model": "neural-chat",
    "user_id": 123,
    "chat_id": 45,
    "timestamp": "2025-12-23T..."
}
```

**Response (Error):**
```json
{
    "success": false,
    "error": "Message cannot be empty"
}
```

**Error Codes:**
- 400: Bad request (invalid JSON, empty message, too long)
- 500: Server error (Ollama issue, processing error)
- 503: Service unavailable (Ollama not running)

**Validation:**
- Message must not be empty
- Message must be ≤ 500 characters
- Request must be JSON

---

### 3. Chat Info
```
GET /api/ai/info
```

**Response:**
```json
{
    "service": "Hospital AI Medical Chatbot",
    "model": "neural-chat",
    "version": "1.0.0",
    "features": [...],
    "limitations": [...],
    "endpoints": {...}
}
```

---

### 4. Chat History
```
GET /api/ai/chat-history
```

**Response:**
```json
{
    "success": true,
    "count": 5,
    "history": [
        {
            "id": 1,
            "user_message": "I have a fever",
            "ai_response": "A fever is...",
            "timestamp": "2025-12-23T...",
            "model": "neural-chat"
        }
    ]
}
```

Retrieves last 50 conversations for current user.

---

### 5. Clear Chat History
```
POST /api/ai/chat-history/clear
```

**Response:**
```json
{
    "success": true,
    "message": "Chat history cleared"
}
```

---

## 🎨 Frontend Integration

### Option 1: Include the Chat Component (Easiest)

In any template where you want the chatbot:

```html
{% include 'ai_chatbot_component.html' %}
```

Example in a patient dashboard:

```html
{% extends "base.html" %}

{% block content %}
<div class="container">
    <h1>Patient Dashboard</h1>
    
    <div class="row">
        <div class="col-md-8">
            <!-- Your existing content -->
        </div>
        
        <div class="col-md-4">
            <!-- AI Chatbot -->
            {% include 'ai_chatbot_component.html' %}
        </div>
    </div>
</div>
{% endblock %}
```

### Option 2: Custom JavaScript Integration

If you want to integrate with your own UI:

```javascript
// Send message to AI
async function askAI(message) {
    try {
        const response = await fetch('/api/ai/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('AI Response:', data.response);
            return data.response;
        } else {
            console.error('Error:', data.error);
            return null;
        }
    } catch (error) {
        console.error('Network error:', error);
        return null;
    }
}

// Usage
askAI('What is hypertension?').then(response => {
    if (response) {
        displayMessage(response);
    }
});
```

### Option 3: Python Integration

In your Flask routes:

```python
from app.routes.ai_chatbot import MedicalChatbotService

@app.route('/patient/medical-info')
@login_required
def patient_medical_info():
    # Get AI response programmatically
    user_question = request.args.get('q', 'What is diabetes?')
    
    ai_response = MedicalChatbotService.get_ai_response(user_question)
    
    return jsonify({
        'question': user_question,
        'answer': ai_response['response'] if ai_response['success'] else 'Service unavailable'
    })
```

---

## 📊 Database Schema

### ChatHistory Table
```sql
CREATE TABLE chat_history (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL FOREIGN KEY,
    user_message TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    model_used VARCHAR(50) DEFAULT 'neural-chat',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Example Query:**
```python
# Get user's chat history
chats = ChatHistory.query.filter_by(user_id=current_user.id).all()

# Get average response quality
from sqlalchemy import func
avg_length = db.session.query(func.avg(func.length(ChatHistory.ai_response))).scalar()

# Clear old chats (older than 30 days)
from datetime import datetime, timedelta
thirty_days_ago = datetime.utcnow() - timedelta(days=30)
ChatHistory.query.filter(ChatHistory.timestamp < thirty_days_ago).delete()
db.session.commit()
```

---

## 🚀 Setup Requirements

### 1. Ollama Must Be Running

Before the chatbot can work, start Ollama in a separate terminal:

```powershell
ollama serve
```

In another terminal, pull the medical model:

```powershell
ollama pull neural-chat
```

### 2. Database Migration

Create the ChatHistory table:

```python
# In your Flask shell or startup script
from app import create_app, db
from app.models.models import ChatHistory

app = create_app()
with app.app_context():
    db.create_all()
    print("ChatHistory table created!")
```

Or if using migrations:

```bash
flask db migrate -m "Add ChatHistory model"
flask db upgrade
```

### 3. Update Requirements

Add to your `requirements.txt`:

```txt
Flask==2.3.2
Flask-Login==0.6.2
Flask-SQLAlchemy==3.0.3
requests==2.31.0
Flask-CORS==4.0.0
```

Install:
```bash
pip install -r requirements.txt
```

---

## 🔒 Security Considerations

### 1. Authentication
- All endpoints require `@login_required`
- Only logged-in users can access the chatbot
- Each chat is stored with the user's ID

### 2. Rate Limiting (Recommended)
Add to your routes:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@ai_bp.route('/chat', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def chat():
    # ... existing code
```

### 3. Input Validation
Already implemented:
- Empty message check
- Length limit (500 chars)
- JSON validation
- XSS protection (HTML escaping in frontend)

### 4. Medical Safety
System prompt includes:
- No diagnoses
- No prescriptions
- No emergency advice
- Always recommend doctor consultation

---

## 🧪 Testing the Integration

### Test 1: Health Check
```bash
curl http://localhost:5000/api/ai/health
```

### Test 2: Send a Query
```bash
curl -X POST http://localhost:5000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What causes headaches?"}'
```

### Test 3: Get Chat History
```bash
curl http://localhost:5000/api/ai/chat-history
```

### Test 4: Manual Browser Test
1. Open your healthcare system in browser
2. Log in as a user
3. Navigate to page with `{% include 'ai_chatbot_component.html' %}`
4. Type a medical question
5. Should receive AI response in 2-5 seconds

---

## 📈 Performance Tips

### 1. Response Time Optimization
```python
# In PHASE_2_FLASK_BACKEND.py, adjust:
payload = {
    "model": OLLAMA_MODEL,
    "num_predict": 150,  # Reduce for faster responses
    "temperature": 0.2,  # Lower = faster, more consistent
    "top_p": 0.8,        # Reduce for faster responses
}
```

### 2. Database Optimization
```python
# Index user_id for faster chat history queries
class ChatHistory(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), 
                       nullable=False, index=True)
```

### 3. Caching (Optional)
```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@ai_bp.route('/info', methods=['GET'])
@cache.cached(timeout=3600)
def info():
    # Cached for 1 hour
    return jsonify({...})
```

---

## 🐛 Troubleshooting

### Problem: "Cannot connect to Ollama"
**Solution:**
```powershell
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Pull model
ollama pull neural-chat
```

### Problem: Slow responses (>10 seconds)
**Solution:**
- Check if GPU is being used: `nvidia-smi`
- Reduce `num_predict` in payload
- Restart Ollama and Flask
- Close other applications

### Problem: "Model not found"
**Solution:**
```powershell
ollama pull neural-chat
```

### Problem: API returns 500 error
**Check Flask logs:**
```python
# In PHASE_2_FLASK_BACKEND.py, see detailed error messages
```

### Problem: Chat history not saving
**Solution:**
```python
# Ensure database is initialized
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
```

---

## 📋 Deployment Checklist

- [ ] Ollama installed and neural-chat model downloaded
- [ ] `ollama serve` running in background
- [ ] Flask app starts without errors
- [ ] Database tables created (ChatHistory)
- [ ] AI health check returns 200 OK
- [ ] Can send message and receive response
- [ ] Chat history saves to database
- [ ] Frontend component displays correctly
- [ ] Rate limiting configured (optional)
- [ ] CORS configured if needed
- [ ] Security headers configured
- [ ] Error handling tested
- [ ] Documentation updated for staff

---

## 📞 Support & Next Steps

### For Healthcare Staff:
1. Show them the `/api/ai/info` endpoint
2. Display disclaimer about AI limitations
3. Train them on when to escalate to doctors

### For Developers:
1. Review `app/routes/ai_chatbot.py` for implementation details
2. Check `PHASE_5_INTEGRATION.py` for advanced patterns
3. Review system prompt in `PHASE_3_SYSTEM_PROMPT.py` for safety rules

### For System Admin:
1. Monitor `ChatHistory` table growth
2. Set up database backups
3. Configure Ollama auto-restart
4. Monitor GPU memory usage

---

**Integration completed on:** 2025-12-23
**Status:** ✅ Ready for use
**Next:** Test with real users and gather feedback
