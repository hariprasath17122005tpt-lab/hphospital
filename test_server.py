#!/usr/bin/env python
"""
Simple test server to diagnose issues
"""
from app import create_app

print("Creating app...")
app = create_app('development')

print("✅ App created successfully")
print("Starting server on 127.0.0.1:5000...")

# Test with Flask dev server with threading
app.run(
    host='127.0.0.1',
    port=5000,
    debug=True,
    use_reloader=False,
    use_debugger=True,
    threaded=True
)
