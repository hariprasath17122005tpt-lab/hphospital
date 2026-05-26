"""
Vercel Serverless Function Entry Point
Routes all requests through the Flask application
"""
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import app module
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set Flask environment
os.environ.setdefault('FLASK_ENV', 'production')

try:
    from app import create_app
    
    # Create Flask app instance
    app = create_app(os.environ.get('FLASK_ENV', 'production'))
    
except Exception as e:
    print(f"Error creating Flask app: {e}")
    import traceback
    traceback.print_exc()
    
    # Fallback app for debugging
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def error():
        return f"Error initializing app: {str(e)}", 500


# Expose app for Vercel
if __name__ != "__main__":
    # For Vercel production
    application = app
else:
    # For local testing
    if __name__ == "__main__":
        app.run(host='0.0.0.0', port=5000, debug=False)
