"""
QUICK START GUIDE: AI MEDICAL CHATBOT FOR HOSPITAL SYSTEM
Complete step-by-step instructions to get everything running
"""

# ==========================================
# STEP 1: DOWNLOAD & INSTALL OLLAMA (5 minutes)
# ==========================================

STEP_1 = """
STEP 1: DOWNLOAD & INSTALL OLLAMA
==================================

1. Visit: https://ollama.ai
2. Click "Download for Windows"
3. Run the installer (ollama-windows.exe)
4. Follow the wizard (accept defaults)
5. Restart your computer (optional but recommended)

Verify installation in PowerShell:
  ollama --version

Should output: ollama version X.X.X (or similar)
"""

# ==========================================
# STEP 2: DOWNLOAD AI MODEL (5-10 minutes)
# ==========================================

STEP_2 = """
STEP 2: DOWNLOAD NEURAL CHAT MODEL
===================================

This is the AI model that will power the chatbot.

1. Open PowerShell (Windows Terminal)
2. Run command:
   
   ollama pull neural-chat

3. Wait for download (model is ~4GB)
   You'll see: "downloading..."
   
4. When complete, you'll see "success"

The model is automatically stored in:
C:\\Users\\<YourName>\\.ollama\\models
"""

# ==========================================
# STEP 3: INSTALL PYTHON DEPENDENCIES (3 minutes)
# ==========================================

STEP_3 = """
STEP 3: INSTALL PYTHON DEPENDENCIES
====================================

1. Open PowerShell in hospital folder
   (Right-click folder > Open in Terminal)

2. Run command:
   
   pip install -r AI_CHATBOT_REQUIREMENTS.txt

3. Wait for installation

Libraries installed:
   - flask (web framework)
   - flask-cors (enable API access)
   - requests (make HTTP calls)
"""

# ==========================================
# STEP 4: START OLLAMA SERVER (1 minute)
# ==========================================

STEP_4 = """
STEP 4: START OLLAMA SERVER
============================

This keeps the AI model running.

1. Open NEW PowerShell window (don't close it during testing)
2. Run command:
   
   ollama serve

3. You should see:
   "loading model"
   "listening on 127.0.0.1:11434"

4. KEEP THIS WINDOW OPEN while using the chatbot

The server stays running at: http://localhost:11434
"""

# ==========================================
# STEP 5: START FLASK SERVER (1 minute)
# ==========================================

STEP_5 = """
STEP 5: START FLASK BACKEND SERVER
===================================

This provides the API endpoints.

1. Open ANOTHER NEW PowerShell window
2. Navigate to hospital folder:
   cd "C:\\Users\\harip\\OneDrive\\Desktop\\hospital"

3. Run command:
   
   python PHASE_2_FLASK_BACKEND.py

4. You should see:
   "Hospital Management System - AI Medical Chatbot"
   "Starting server..."
   "Running on http://localhost:5000"

5. KEEP THIS WINDOW OPEN while using the chatbot

The API server stays running at: http://localhost:5000
"""

# ==========================================
# STEP 6: TEST THE CHATBOT (5 minutes)
# ==========================================

STEP_6 = """
STEP 6: TEST WITH AUTOMATED TEST SUITE
=======================================

This runs comprehensive tests.

1. Open ANOTHER NEW PowerShell window
2. Navigate to hospital folder:
   cd "C:\\Users\\harip\\OneDrive\\Desktop\\hospital"

3. Run command:
   
   python PHASE_4_TESTING.py

4. Follow the prompts
5. The test will run multiple queries
6. Check results at the end

Expected output:
   ✅ PASS: Health Check
   ✅ PASS: Info Endpoint
   ✅ PASS: Chat Test (fever)
   ✅ PASS: Chat Test (medicine)
   ... etc

If all pass, system is working correctly!
"""

# ==========================================
# STEP 7: TEST MANUALLY (5 minutes)
# ==========================================

STEP_7 = """
STEP 7: MANUAL API TEST
=======================

Test the API directly using curl.

In PowerShell:

curl -X POST http://localhost:5000/api/ai-chat `
  -H "Content-Type: application/json" `
  -d '{"message": "I have a fever"}'

Expected response:
{
  "success": true,
  "response": "A fever is when...",
  "model": "neural-chat",
  "processing_time_ms": 2500
}

Try other queries:
  - "Can I take paracetamol?"
  - "Stomach pain treatment"
  - "What causes headaches?"
"""

# ==========================================
# STEP 8: USE IN FRONTEND (10 minutes)
# ==========================================

STEP_8 = """
STEP 8: INTEGRATE INTO HOSPITAL SYSTEM
======================================

Option A: Use HTML Frontend (Simplest)
--------------------------------------

1. Create file: chatbot.html
2. Copy the HTML template from PHASE_5_INTEGRATION.py
3. Open chatbot.html in browser
4. Type your medical question
5. Click Send
6. AI responds in 2-5 seconds

Option B: Integrate into Python Web App
----------------------------------------

If your hospital system uses Flask:

# In your main app.py:
from PHASE_2_FLASK_BACKEND import app as chatbot_app
app.register_blueprint(chatbot_app, url_prefix='/hospital/ai')

Then use endpoints:
  POST /hospital/ai/api/ai-chat
  GET  /hospital/ai/api/health

Option C: Integrate into React/Vue/Angular
--------------------------------------------

JavaScript fetch example:

const response = await fetch('http://localhost:5000/api/ai-chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: 'I have a fever' })
});

const data = await response.json();
console.log(data.response);
"""

# ==========================================
# TERMINAL SETUP SUMMARY
# ==========================================

TERMINAL_SETUP = """
FINAL SETUP: YOU NEED 3 TERMINAL WINDOWS
=========================================

Window 1 - OLLAMA SERVER
------------------------
Command: ollama serve
Status: Keep running
Output: "listening on 127.0.0.1:11434"

Window 2 - FLASK API
--------------------
Command: python PHASE_2_FLASK_BACKEND.py
Status: Keep running
Output: "Running on http://localhost:5000"

Window 3 - YOUR WORK (Testing/Frontend)
---------------------------------------
Command: Run tests or use frontend
Status: For testing only
Can open/close as needed

IMPORTANT:
Don't close Windows 1 and 2!
They must stay open while using the chatbot.
"""

# ==========================================
# EXAMPLE RESPONSES
# ==========================================

EXAMPLE_RESPONSES = """
EXAMPLE: WHAT THE CHATBOT OUTPUTS
==================================

Input: "I have a fever"
Output:
-------
A fever is when your body temperature rises above 98.6°F (37°C), 
usually in response to an infection like a cold, flu, or bacterial infection. 
Common causes include viral or bacterial infections. To manage a fever, 
rest adequately, stay hydrated with water and clear fluids, and monitor your temperature. 
If your fever exceeds 104°F (40°C), you develop a rash, experience severe headache, 
or the fever lasts more than 3-5 days, seek medical attention immediately. 
Please consult a healthcare professional for diagnosis and treatment.


Input: "Can I take paracetamol?"
Output:
-------
Paracetamol (acetaminophen) is a common over-the-counter medication used for pain relief 
and fever reduction. However, whether it's safe for you depends on your personal medical history, 
current medications, allergies, liver condition, and the underlying cause of your symptoms. 
Some people should avoid paracetamol due to liver disease or other contraindications. 
Never take any medication without first consulting a pharmacist or doctor about whether 
it's appropriate for your specific situation and health status. 
Please consult a healthcare professional for personalized medical advice.


Input: "Stomach pain treatment"
Output:
-------
Stomach pain can have numerous causes ranging from minor indigestion to serious conditions, 
so proper diagnosis is important. Common causes include indigestion, gas, food sensitivity, 
gastritis, or more serious conditions like appendicitis or ulcers. For mild stomach pain, 
rest and avoiding heavy, spicy, or fatty foods may help. Drink plenty of water and herbal teas. 
Seek immediate medical attention if you experience severe pain, vomiting blood, bloody stools, 
severe abdominal distension, or pain that persists for more than a few days. 
Please consult a healthcare professional for proper diagnosis and treatment.
"""

# ==========================================
# TROUBLESHOOTING QUICK REFERENCE
# ==========================================

TROUBLESHOOTING_QUICK = """
QUICK TROUBLESHOOTING
====================

❌ "Connection refused to localhost:5000"
→ Flask is not running
→ Run: python PHASE_2_FLASK_BACKEND.py in new terminal

❌ "Cannot connect to Ollama"
→ Ollama server is not running
→ Run: ollama serve in new terminal

❌ "Model not found: neural-chat"
→ Model not downloaded
→ Run: ollama pull neural-chat

❌ "Slow responses (>20 sec)"
→ Check GPU: nvidia-smi
→ May be using CPU instead of GPU
→ Restart Ollama and Flask

❌ "Out of memory error"
→ Close other applications
→ Reduce other processes
→ Restart computer if needed

❌ "API returns 503 error"
→ Ollama server crashed
→ Restart: ollama serve

❌ "Response quality is poor"
→ Temperature too high (more random)
→ Increase context: num_ctx=1024
→ This is normal for local models

❌ "Port 5000 already in use"
→ Another app using port
→ Find: netstat -ano | findstr :5000
→ Change port in PHASE_2_FLASK_BACKEND.py
"""

# ==========================================
# COMPLETE QUICK START
# ==========================================

COMPLETE_QUICK_START = f"""
╔════════════════════════════════════════════════════════════════════════════╗
║       HOSPITAL AI MEDICAL CHATBOT - COMPLETE QUICK START GUIDE             ║
║                          (Total time: ~45 minutes)                         ║
╚════════════════════════════════════════════════════════════════════════════╝

{STEP_1}

{STEP_2}

{STEP_3}

{STEP_4}

{STEP_5}

{STEP_6}

{STEP_7}

{STEP_8}

{TERMINAL_SETUP}

{EXAMPLE_RESPONSES}

{TROUBLESHOOTING_QUICK}

╔════════════════════════════════════════════════════════════════════════════╗
║                        YOU'RE ALL SET!                                     ║
║  The AI Medical Chatbot is now running and ready for integration.          ║
║                                                                            ║
║  Key Points:                                                               ║
║  ✅ Runs completely locally (no internet needed)                           ║
║  ✅ Safe medical information (not a replacement for doctors)               ║
║  ✅ Responsive (2-5 seconds per answer)                                   ║
║  ✅ Scales to hospital system                                             ║
║                                                                            ║
║  Next Steps:                                                               ║
║  1. Keep Ollama and Flask running                                         ║
║  2. Use HTML frontend (chatbot.html) for testing                         ║
║  3. Integrate into hospital system following PHASE_5_INTEGRATION.py      ║
║  4. Add disclaimer to every user-facing component                        ║
║                                                                            ║
║  Support:                                                                  ║
║  - Check troubleshooting above if issues                                  ║
║  - Review PHASE documentation files for details                          ║
║  - All code is commented for easy modification                           ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

if __name__ == "__main__":
    print(COMPLETE_QUICK_START)
    
    # Write to file too
    with open("QUICK_START_AI_CHATBOT.txt", "w") as f:
        f.write(COMPLETE_QUICK_START)
    
    print("\n✅ Quick start guide saved to: QUICK_START_AI_CHATBOT.txt")
