#!/usr/bin/env python
"""
Simple Flask development server runner
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

if __name__ == '__main__':
    print("=" * 70)
    print("HOSPITAL MANAGEMENT SYSTEM")
    print("=" * 70)
    print("Server running at: http://localhost:5000")
    print("=" * 70)
    
    try:
        from app import create_app
        app = create_app(os.getenv('FLASK_ENV', 'development'))
        
        # Run with threadless simple server
        app.run(
            host='127.0.0.1',
            port=5000,
            debug=True,
            use_reloader=True,
            use_debugger=True,
            threaded=False
        )
    except KeyboardInterrupt:
        print("\n✋ Server stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
