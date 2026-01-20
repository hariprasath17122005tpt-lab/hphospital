#!/usr/bin/env python
"""
Startup script using Waitress WSGI server
This avoids Flask's native server issues on Windows
"""
import os
import sys
import ssl

# Fix SSL issues
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
from waitress import serve

app = create_app(os.getenv('FLASK_ENV', 'development'))

@app.shell_context_processor
def make_shell_context():
    return {'db': db}

if __name__ == '__main__':
    print("=" * 70)
    print("HOSPITAL MANAGEMENT SYSTEM")
    print("=" * 70)
    print("Server running at: http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 70)
    
    try:
        print("\n🚀 Starting Waitress server...\n")
        serve(app, host='127.0.0.1', port=5000, _quiet=False)
    except KeyboardInterrupt:
        print("\nServer stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
