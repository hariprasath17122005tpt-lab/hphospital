#!/usr/bin/env python
"""
Hospital Server - Fixed binding
"""
from app import create_app
import sys

try:
    print("\n" + "="*70)
    print("🏥 HOSPITAL MANAGEMENT SYSTEM")
    print("="*70)
    print("Creating Flask application...")
    
    app = create_app('development')
    
    print("✅ App created successfully")
    print("\nStarting server...")
    print("  Host: 0.0.0.0")
    print("  Port: 5000")
    print("  URL: http://localhost:5000")
    print("="*70 + "\n")
    
    # Try to run with all options
    app.run(
        host='0.0.0.0',  # Listen on all interfaces
        port=5000,
        debug=False,
        use_reloader=False,
        use_debugger=False,
        threaded=True
    )
except KeyboardInterrupt:
    print("\n\nServer stopped.")
    sys.exit(0)
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
