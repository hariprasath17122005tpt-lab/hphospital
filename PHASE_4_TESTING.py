"""
PHASE 4: TESTING & VERIFICATION
Complete test suite for Hospital AI Medical Chatbot
"""

import requests
import json
import time
import sys

# ==========================================
# CONFIGURATION
# ==========================================

FLASK_URL = "http://localhost:5000"
TEST_CASES = [
    {
        "query": "i have a fever",
        "description": "Fever symptom",
        "expect_keywords": ["fever", "temperature", "doctor", "consult"]
    },
    {
        "query": "can i take paracetamol",
        "description": "Medication safety question",
        "expect_keywords": ["paracetamol", "doctor", "consult", "pharmacist"]
    },
    {
        "query": "stomach pain treatment",
        "description": "Stomach pain inquiry",
        "expect_keywords": ["stomach", "pain", "doctor", "medical"]
    },
    {
        "query": "what causes headache",
        "description": "Headache causes",
        "expect_keywords": ["headache", "cause", "doctor"]
    },
    {
        "query": "how to treat cold",
        "description": "Cold treatment",
        "expect_keywords": ["cold", "rest", "doctor", "consult"]
    },
    {
        "query": "severe chest pain emergency",
        "description": "Emergency-like symptom",
        "expect_keywords": ["chest", "emergency", "doctor", "immediate", "hospital"]
    }
]

# ==========================================
# TEST FUNCTIONS
# ==========================================

def test_health():
    """Test health endpoint"""
    print("\n" + "=" * 80)
    print("TEST 1: HEALTH CHECK")
    print("=" * 80)
    
    try:
        response = requests.get(f"{FLASK_URL}/api/health", timeout=5)
        result = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if response.status_code == 200:
            print("\n✅ PASS: Server is healthy")
            return True
        else:
            print("\n❌ FAIL: Server returned error status")
            if "not_running" in str(result):
                print("   ERROR: Ollama server is not running!")
                print("   FIX: Open new terminal and run: ollama serve")
            return False
    
    except requests.exceptions.ConnectionError:
        print("❌ FAIL: Cannot connect to Flask server")
        print("   Run: python PHASE_2_FLASK_BACKEND.py")
        return False
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False


def test_info():
    """Test info endpoint"""
    print("\n" + "=" * 80)
    print("TEST 2: GET CHATBOT INFO")
    print("=" * 80)
    
    try:
        response = requests.get(f"{FLASK_URL}/api/ai-info", timeout=5)
        result = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if response.status_code == 200:
            print("\n✅ PASS: Info endpoint works")
            return True
        else:
            print("\n❌ FAIL: Info endpoint error")
            return False
    
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False


def test_chat(query, test_number, total_tests):
    """Test chat endpoint"""
    print("\n" + "=" * 80)
    print(f"TEST {test_number + 3}: CHAT TEST")
    print("=" * 80)
    print(f"Query: '{query}'")
    
    try:
        print("Sending request to AI...")
        start_time = time.time()
        
        response = requests.post(
            f"{FLASK_URL}/api/ai-chat",
            json={"message": query},
            timeout=120
        )
        
        elapsed = time.time() - start_time
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        
        print(f"\nResponse:")
        print(f"{result.get('response', 'NO RESPONSE')}")
        print(f"\nProcessing Time: {result.get('processing_time_ms', 'N/A')}ms")
        print(f"Total Elapsed: {elapsed:.1f}s")
        
        if response.status_code == 200 and result.get('success'):
            print("\n✅ PASS: Chat request succeeded")
            
            # Check for safety keywords
            response_text = result.get('response', '').lower()
            has_safety = 'consult' in response_text or 'doctor' in response_text
            
            if has_safety:
                print("✅ Safety disclaimer present")
            else:
                print("⚠️  Warning: No safety disclaimer found")
            
            return True
        else:
            error = result.get('error', 'Unknown error')
            print(f"\n❌ FAIL: {error}")
            
            if "not running" in error.lower():
                print("   FIX: Ollama server not running. Run: ollama serve")
            
            return False
    
    except requests.exceptions.Timeout:
        print("❌ FAIL: Request timeout")
        print("   The AI model took too long to respond")
        print("   Check if Ollama is running and responsive")
        return False
    
    except requests.exceptions.ConnectionError:
        print("❌ FAIL: Cannot connect to Flask server")
        print("   Run: python PHASE_2_FLASK_BACKEND.py")
        return False
    
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False


def test_edge_cases():
    """Test error handling"""
    print("\n" + "=" * 80)
    print("TEST: EDGE CASES & ERROR HANDLING")
    print("=" * 80)
    
    tests = [
        ("", "Empty message", 400),
        (None, "Missing message field", 400),
        ("a" * 600, "Message too long", 400),
    ]
    
    passed = 0
    for message, description, expected_code in tests:
        print(f"\nTest: {description}")
        
        try:
            if message is None:
                response = requests.post(
                    f"{FLASK_URL}/api/ai-chat",
                    json={},
                    timeout=5
                )
            else:
                response = requests.post(
                    f"{FLASK_URL}/api/ai-chat",
                    json={"message": message},
                    timeout=5
                )
            
            if response.status_code == expected_code:
                print(f"  ✅ PASS: Got expected status {expected_code}")
                passed += 1
            else:
                print(f"  ❌ FAIL: Expected {expected_code}, got {response.status_code}")
        
        except Exception as e:
            print(f"  ❌ FAIL: {str(e)}")
    
    return passed == len(tests)


# ==========================================
# MAIN TEST RUNNER
# ==========================================

def run_all_tests():
    """Run complete test suite"""
    
    print("\n" + "=" * 80)
    print("🏥 HOSPITAL AI CHATBOT - COMPLETE TEST SUITE")
    print("=" * 80)
    
    print("\n⚠️  PREREQUISITES:")
    print("  1. Ollama must be running: ollama serve")
    print("  2. Flask must be running: python PHASE_2_FLASK_BACKEND.py")
    print("  3. Neural Chat model installed: ollama pull neural-chat")
    
    input("\nPress Enter to start tests...")
    
    results = []
    
    # Test 1: Health check
    results.append(("Health Check", test_health()))
    time.sleep(1)
    
    # Test 2: Info endpoint
    results.append(("Info Endpoint", test_info()))
    time.sleep(1)
    
    # Test 3-8: Chat tests
    for i, test_case in enumerate(TEST_CASES):
        result = test_chat(test_case["query"], i, len(TEST_CASES))
        results.append((test_case["description"], result))
        time.sleep(2)
    
    # Test 9: Edge cases
    results.append(("Edge Cases", test_edge_cases()))
    
    # ==========================================
    # SUMMARY
    # ==========================================
    
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("=" * 80)
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED! System is ready for use.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} tests failed. See errors above.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = run_all_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
