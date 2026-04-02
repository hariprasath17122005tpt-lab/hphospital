#!/usr/bin/env python
"""
Test login functionality
"""
import requests
import re

BASE_URL = 'http://localhost:5000'

# Create a session to maintain cookies
session = requests.Session()

# Step 1: Get the login page to extract CSRF token
print("Step 1: Fetching login page...")
response = session.get(f'{BASE_URL}/patient/login')
print(f"Status: {response.status_code}")
print(f"Cookies: {session.cookies}")

# Parse HTML to find CSRF token using regex
match = re.search(r'name="csrf_token"\s+value="([^"]+)"', response.text)

if match:
    csrf_token = match.group(1)
    print(f"[OK] CSRF Token found: {csrf_token[:20]}...")
else:
    print("[NO] CSRF Token NOT found in form")
    print("Looking for csrf_token in HTML:")
    if 'csrf_token' in response.text:
        print("  Found 'csrf_token' in HTML")
        # Show snippet around it
        idx = response.text.find('csrf_token')
        print(response.text[idx:idx+200])
    else:
        print("  'csrf_token' not found anywhere")

# Step 2: Submit login form
print("\nStep 2: Submitting login form...")
login_data = {
    'csrf_token': csrf_token if match else '',
    'username': 'john_patient',
    'password': 'password123'
}

print(f"Sending: {login_data}")
response = session.post(f'{BASE_URL}/patient/login', data=login_data, allow_redirects=False, headers={'Content-Type': 'application/x-www-form-urlencoded'})
print(f"Status: {response.status_code}")
print(f"Location: {response.headers.get('Location', 'N/A')}")
print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")

print("\nResponse content (first 2000 chars):")
content = response.text[:2000]
print(content)

# Look for flash messages
if 'alert' in response.text:
    print("\n[ALERT FOUND] Flash message detected in response")
if 'Invalid username' in response.text:
    print("[ERROR] Invalid username message found")
if 'Login successful' in response.text:
    print("[SUCCESS] Login successful message found")
