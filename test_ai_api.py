#!/usr/bin/env python
"""
Test script for AI Chatbot API
Tests the Flask endpoint with the Ollama model
"""

import requests
import json
import time

# API endpoint
BASE_URL = "http://localhost:5000"
AI_ENDPOINT = f"{BASE_URL}/api/ai/chat"
HEALTH_ENDPOINT = f"{BASE_URL}/api/ai/health"

def test_health():
    """Test if the AI service is healthy"""
    print("\n" + "="*70)
    print("🔍 CHECKING AI SERVICE HEALTH")
    print("="*70)
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ AI Service: HEALTHY")
            print(f"   Status: {data.get('status')}")
            print(f"   Ollama Running: {data.get('ollama_running')}")
            print(f"   Model: {data.get('model')}")
            return True
        else:
            print(f"❌ AI Service: UNHEALTHY (Status: {response.status_code})")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Could not connect to Flask API")
        print(f"   Error: {str(e)}")
        print(f"   Make sure Flask is running: python run_server.py")
        return False

def test_ai_chat(question):
    """Test the AI chat endpoint"""
    print("\n" + "="*70)
    print(f"🤖 TESTING AI CHATBOT")
    print(f"Question: {question}")
    print("="*70)
    
    try:
        payload = {
            "message": question,
            "history": []
        }
        
        response = requests.post(AI_ENDPOINT, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ AI Response Received!")
                print(f"\n📝 Answer:")
                print("-" * 70)
                print(data.get('response', 'No response'))
                print("-" * 70)
                print(f"\n⏱️  Response Time: {data.get('response_time', 'Unknown')}s")
                return True
            else:
                print(f"❌ AI Error: {data.get('error')}")
                print(f"   Details: {data.get('details')}")
                return False
        else:
            print(f"❌ API Error (Status: {response.status_code})")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Could not reach AI endpoint")
        print(f"   Error: {str(e)}")
        return False

def main():
    print("\n" + "="*70)
    print("🏥 HOSPITAL AI CHATBOT - API TESTING")
    print("="*70)
    print(f"\nTesting endpoints at: {BASE_URL}")
    
    # Test 1: Health check
    health_ok = test_health()
    
    if not health_ok:
        print("\n⚠️  Flask server is not running!")
        print("   Start it with: python run_server.py")
        return
    
    # Test 2-4: Multiple AI questions
    questions = [
        "What is normal blood pressure?",
        "What are symptoms of diabetes?",
        "How to treat a common cold?"
    ]
    
    results = []
    for question in questions:
        success = test_ai_chat(question)
        results.append(success)
        time.sleep(1)  # Small delay between requests
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    print(f"Health Check: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"AI Chat Tests: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("\n✅ ALL TESTS PASSED - AI CHATBOT IS FULLY OPERATIONAL!")
    else:
        print("\n⚠️  Some tests failed - Please check the errors above")
    
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
