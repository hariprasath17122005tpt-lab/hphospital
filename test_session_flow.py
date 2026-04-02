#!/usr/bin/env python
"""
Test script to debug session flow and authentication issues
"""
import requests
import json
import time
from urllib.parse import urlparse, parse_qs

BASE_URL = 'http://localhost:5000'

def test_login_and_api():
    print("=" * 60)
    print("TESTING SESSION RECOVERY FLOW")
    print("=" * 60)
    
    session = requests.Session()
    
    # Step 1: Login
    print("\n[STEP 1] Logging in as reception123...")
    login_url = f'{BASE_URL}/staff/login'
    login_data = {
        'username': 'reception123',
        'password': 'receptionopen',
        'staff_role': 'RECEPTIONIST'
    }
    
    resp = session.post(login_url, data=login_data, allow_redirects=True)
    print(f"  Status: {resp.status_code}")
    print(f"  Final URL: {resp.url}")
    print(f"  Cookies: {session.cookies.get_dict()}")
    
    # Check if we can see the dashboard
    if 'dashboard' in resp.url or resp.status_code == 200:
        print("  ✅ Logged in successfully")
    else:
        print("  ❌ Login failed or redirected unexpectedly")
        print(f"  Response HTML (first 500 chars): {resp.text[:500]}")
        return
    
    # Step 2: Check session cookie for _user_id
    print("\n[STEP 2] Checking session cookie...")
    session_cookie = session.cookies.get('session')
    if session_cookie:
        print(f"  Session cookie found (length: {len(session_cookie)})")
        # Try to decode (won't work without secret key, but we can see it exists)
        print(f"  First 50 chars: {session_cookie[:50]}")
    else:
        print("  ❌ No session cookie found!")
        return
    
    # Step 3: Test find-similar API
    print("\n[STEP 3] Testing /api/patients/find-similar...")
    api_url = f'{BASE_URL}/api/patients/find-similar'
    api_data = {
        'name': 'Test Patient',
        'phone': '9876543210',
        'age': 30,
        'threshold': 0.6
    }
    headers = {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json'
    }
    
    resp = session.post(api_url, json=api_data, headers=headers)
    print(f"  Status: {resp.status_code}")
    print(f"  Response: {resp.text[:500]}")
    
    if resp.status_code == 200:
        try:
            data = resp.json()
            if data.get('success'):
                print("  ✅ API call successful!")
            else:
                print(f"  ❌ API returned failure: {data.get('error')}")
        except:
            print(f"  ❌ Could not parse JSON response")
    elif resp.status_code == 401:
        print(f"  ❌ Unauthorized (401) - Session not recovered!")
    else:
        print(f"  ❌ Unexpected status: {resp.status_code}")
    
    # Step 4: Test register-walkin API
    print("\n[STEP 4] Testing /reception/api/register-walkin...")
    walkin_url = f'{BASE_URL}/reception/api/register-walkin'
    walkin_data = {
        'first_name': 'Test',
        'last_name': 'Patient',
        'phone': '9876543210',
        'age': 30,
        'gender': 'Male',
        'reason': 'General Consultation',
        'doctor_id': None
    }
    
    resp = session.post(walkin_url, json=walkin_data, headers=headers)
    print(f"  Status: {resp.status_code}")
    print(f"  Response: {resp.text[:500]}")
    
    if resp.status_code == 200:
        try:
            data = resp.json()
            if data.get('success'):
                print(f"  ✅ Registration successful! Token: {data.get('token')}")
            else:
                print(f"  ❌ Registration failed: {data.get('error')}")
        except:
            print(f"  ❌ Could not parse JSON response")
    elif resp.status_code == 401:
        print(f"  ❌ Unauthorized (401) - Session not recovered!")
    else:
        print(f"  ❌ Unexpected status: {resp.status_code}")

if __name__ == '__main__':
    print("Make sure Flask server is running on http://localhost:5000")
    print("Press Enter to continue...")
    input()
    
    try:
        test_login_and_api()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
