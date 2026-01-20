#!/usr/bin/env python
"""
Hospital Management System Server - Stable Runner
Uses Waitress for better stability than Flask's development server
"""

import os
import sys
import ssl
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

# Fix SSL issues
try:
    _create_unverified_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_context

if __name__ == '__main__':
    print("=" * 80)
    print("🏥 HOSPITAL MANAGEMENT SYSTEM - STARTING SERVER")
    print("=" * 80)
    
    try:
        from app import create_app
        
        # Create Flask app
        print("📦 Creating Flask application...")
        app = create_app(os.getenv('FLASK_ENV', 'development'))
        
        print("✅ Flask app created successfully")
        print("\n" + "=" * 80)
        print("🌐 SERVER INFORMATION:")
        print("=" * 80)
        print(f"   URL: http://localhost:5000")
        print(f"   URL: http://127.0.0.1:5000")
        print(f"   Mode: Development")
        print(f"   Debug: OFF")
        print(f"   Status: STARTING...")
        print("=" * 80)
        print("\n⏳ Server starting (first load takes 5-10 seconds)...\n")
        
        # Try using Waitress (more stable)
        try:
            from waitress import serve
            print("📡 Using Waitress WSGI server (stable)")
            serve(
                app,
                host='127.0.0.1',
                port=5000,
                threads=4,
                connection_limit=1000,
                asyncore_loop_timeout=1,
                recv_bytes=8192,
                send_bytes=8192,
                _quiet=False
            )
        except ImportError:
            print("⚠️  Waitress not found, using Flask development server")
            # Fallback to Flask's development server with threading enabled
            app.run(
                host='127.0.0.1',
                port=5000,
                debug=False,
                use_reloader=False,
                use_debugger=False,
                threaded=True  # Enable threading for stability
            )
            
    except KeyboardInterrupt:
        print("\n\n✋ Server stopped by user (CTRL+C pressed)")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERROR STARTING SERVER:")
        print(f"   {str(e)}")
        print("\nTraceback:")
        import traceback
        traceback.print_exc()
        sys.exit(1)
