from flask import Flask, request, jsonify, render_template_string
import os
import sys

# Add the project root to path so we can import the engine
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.ml_models.strict_medical_chatbot import StrictMedicalChatbot

app = Flask(__name__)
chatbot = StrictMedicalChatbot()

# Modern, premium UI template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>STRICT Medical AI Chatbot</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #2563eb;
            --bg-dark: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f8fafc;
            --text-dim: #94a3b8;
        }
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-main);
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .chat-container {
            width: 100%;
            max-width: 600px;
            background: var(--card-bg);
            border-radius: 20px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.1);
            height: 80vh;
        }
        .header {
            padding: 20px;
            background: rgba(37, 99, 235, 0.1);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 1.5rem;
            color: #60a5fa;
            font-weight: 600;
        }
        .header p {
            margin: 5px 0 0;
            font-size: 0.8rem;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .chat-box {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .message {
            max-width: 85%;
            padding: 12px 18px;
            border-radius: 15px;
            font-size: 0.95rem;
            line-height: 1.5;
            white-space: pre-line;
        }
        .user-message {
            align-self: flex-end;
            background: var(--primary);
            color: white;
            border-bottom-right-radius: 2px;
        }
        .bot-message {
            align-self: flex-start;
            background: #334155;
            color: var(--text-main);
            border-bottom-left-radius: 2px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        .input-area {
            padding: 20px;
            background: rgba(15, 23, 42, 0.5);
            display: flex;
            gap: 10px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }
        input {
            flex: 1;
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 12px 15px;
            color: white;
            outline: none;
            transition: border-color 0.2s;
        }
        input:focus {
            border-color: var(--primary);
        }
        button {
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 10px 20px;
            cursor: pointer;
            font-weight: 600;
            transition: opacity 0.2s;
        }
        button:hover {
            opacity: 0.9;
        }
        .status {
            font-size: 0.75rem;
            color: #10b981;
            margin-top: 5px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="header">
            <h1>🛡️ MedGuard STRICT AI</h1>
            <p>Dataset-Only Verification System</p>
            <div class="status">● System Online - No LLM Hallucinations</div>
        </div>
        <div class="chat-box" id="chatBox">
            <div class="message bot-message">Hello! I am a strict medical chatbot. I only provide information stored in my verified database. How can I help you?</div>
        </div>
        <div class="input-area">
            <input type="text" id="userInput" placeholder="Ask about fever, asthma, etc..." onkeypress="if(event.key === 'Enter') sendMessage()">
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        const chatBox = document.getElementById('chatBox');
        const userInput = document.getElementById('userInput');

        async function sendMessage() {
            const text = userInput.value.trim();
            if (!text) return;

            // Add user message
            addMessage(text, 'user-message');
            userInput.value = '';

            try {
                const response = await fetch('/get_response', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });
                const data = await response.json();
                addMessage(data.response, 'bot-message');
            } catch (error) {
                addMessage("❌ Error connecting to server.", 'bot-message');
            }
        }

        function addMessage(text, className) {
            const div = document.createElement('div');
            div.className = `message ${className}`;
            div.innerText = text;
            chatBox.appendChild(div);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/get_response', methods=['POST'])
def get_bot_response():
    data = request.json
    user_message = data.get('message', '')
    response = chatbot.get_response(user_message)
    return jsonify({"response": response})

if __name__ == '__main__':
    print("Starting STRICT Medical Chatbot Server...")
    app.run(debug=True, port=5005)
