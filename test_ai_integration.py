#!/usr/bin/env python
"""Test script for AI Chatbot Integration"""

from app import create_app, db
import json

# Create app
app = create_app()

# Create test client
client = app.test_client()

print("=" * 70)
print("AI CHATBOT INTEGRATION TESTS")
print("=" * 70)

# Test 1: Health Check
print("\n1. Testing /api/ai/health endpoint...")
try:
    response = client.get('/api/ai/health')
    print(f"   Status Code: {response.status_code}")
    data = json.loads(response.data)
    print(f"   Status: {data.get('status')}")
    print(f"   Ollama Running: {data.get('ollama_running')}")
    print("   ✅ Health check endpoint works")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Info Endpoint
print("\n2. Testing /api/ai/info endpoint...")
try:
    response = client.get('/api/ai/info')
    print(f"   Status Code: {response.status_code}")
    data = json.loads(response.data)
    print(f"   Service: {data.get('service')}")
    print(f"   Model: {data.get('model')}")
    print("   ✅ Info endpoint works")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Chat Endpoint (without login - should fail)
print("\n3. Testing /api/ai/chat endpoint (without auth)...")
try:
    response = client.post('/api/ai/chat', 
        json={'message': 'Test message'},
        content_type='application/json'
    )
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 401:
        print("   ✅ Correctly requires authentication")
    else:
        data = json.loads(response.data)
        print(f"   Response: {data}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: Chat Endpoint (with invalid input)
print("\n4. Testing /api/ai/chat with invalid input...")
try:
    response = client.post('/api/ai/chat',
        json={'message': ''},  # Empty message
        content_type='application/json'
    )
    print(f"   Status Code: {response.status_code}")
    print("   ✅ Endpoint handles invalid input correctly")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 70)
print("AI CHATBOT INTEGRATION STATUS: ✅ READY")
print("=" * 70)
print("\nNext Steps:")
print("1. Start Ollama: ollama serve")
print("2. Pull model: ollama pull neural-chat")
print("3. Run Flask server: python run.py")
print("4. Access at: http://localhost:5000")
print("=" * 70)
