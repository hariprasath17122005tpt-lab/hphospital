import os
import sys
import ssl

# Fix SSL certificate issues on Windows FIRST before any other imports
try:
    _create_unverified_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_context

# Suppress warnings
import warnings
warnings.filterwarnings('ignore')

from app import create_app, db

app = create_app(os.getenv('FLASK_ENV', 'development'))

@app.shell_context_processor
def make_shell_context():
    """Add objects to shell context"""
    return {'db': db}

if __name__ == '__main__':
    print("=" * 70)
    print("HOSPITAL MANAGEMENT SYSTEM - STARTING")
    print("=" * 70)
    print("Access the application at: http://localhost:5000")
    print("=" * 70)
    
    # ✅ Chatbot will load on first API request
    
    # Simple Flask server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=True,
        use_debugger=True,
        threaded=True
    )
