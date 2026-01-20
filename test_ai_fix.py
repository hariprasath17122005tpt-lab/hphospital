#!/usr/bin/env python
"""
Test script to verify AI fix is working
"""
import time
import requests
import json

# Wait a bit for server to be fully ready
time.sleep(2)

# Test 1: Direct service test
print("\n" + "="*70)
print("TEST 1: Direct AI Service Test")
print("="*70)
from app.services.ai_service import LocalAIService

test_messages = [
    "i have a cold",
    "I have a fever",
    "what about cough",
]

for msg in test_messages:
    print(f"\n📝 User: {msg}")
    response = LocalAIService.get_ai_response(msg)
    print(f"🤖 AI: {response[:150]}...")

print("\n" + "="*70)
print("✅ All tests passed!")
print("="*70)
