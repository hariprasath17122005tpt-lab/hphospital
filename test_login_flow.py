import requests
import sys
from urllib.parse import urljoin

BASE_URL = 'http://localhost:5000'

# Create a session to persist cookies
session = requests.Session()

print("=" * 60)
print("TESTING PATIENT LOGIN AND DASHBOARD ACCESS")
print("=" * 60)

# Step 1: Get the login page to obtain CSRF token
print("\n1. Getting patient login page...")
try:
    r = session.get(urljoin(BASE_URL, '/patient/login'), timeout=10)
    print(f"   Status: {r.status_code}")
    if 'csrf_token' in r.text:
        print("   ✓ Login page loaded successfully")
    else:
        print("   ✗ CSRF token not found in login page")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Step 2: Post login credentials
print("\n2. Attempting login with username: fake, password: fake...")
try:
    # Get CSRF token from form using regex
    import re
    csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', r.text)
    csrf_token = csrf_match.group(1) if csrf_match else ''
    if csrf_token:
        print(f"   CSRF Token: {csrf_token[:20]}...")
    else:
        print("   Warning: Could not find CSRF token")
    
    login_data = {
        'username': 'fake',
        'password': 'fake',
        'csrf_token': csrf_token
    }
    
    r = session.post(
        urljoin(BASE_URL, '/patient/login'),
        data=login_data,
        timeout=10,
        allow_redirects=False
    )
    print(f"   Status: {r.status_code}")
    print(f"   Cookies after login: {list(session.cookies.keys())}")
    
    if r.status_code == 302:
        print(f"   ✓ Redirected to: {r.headers.get('Location', 'N/A')}")
    elif 'Login successful' in r.text:
        print("   ✓ Login successful message found")
    else:
        print(f"   Response length: {len(r.text)}")
        if 'Invalid' in r.text:
            print("   ✗ Invalid credentials message found")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Step 3: Access the dashboard
print("\n3. Accessing patient dashboard...")
try:
    r = session.get(
        urljoin(BASE_URL, '/patient/dashboard'),
        timeout=10,
        allow_redirects=False
    )
    print(f"   Status: {r.status_code}")
    
    if r.status_code == 200:
        print("   ✓ Dashboard accessed successfully (200 OK)")
        if 'health' in r.text.lower() or 'dashboard' in r.text.lower():
            print("   ✓ Dashboard content loaded")
        else:
            print("   ✗ Dashboard content not found in response")
    elif r.status_code == 302:
        location = r.headers.get('Location', 'N/A')
        print(f"   ✗ Redirected to: {location}")
        if 'login' in location:
            print("   ✗ Session expired - redirected back to login!")
    else:
        print(f"   ✗ Unexpected status code")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Step 4: Test multiple sidebar routes in sequence
sidebar_routes = [
    ('/patient/prescriptions', 'Prescriptions'),
    ('/patient/lab_reports', 'Lab Reports'),
    ('/patient/appointments', 'Appointments'),
    ('/patient/billing', 'Billing'),
]

for route, name in sidebar_routes:
    print(f"\n5. Testing {name} ({route})...")
    try:
        r = session.get(
            urljoin(BASE_URL, route),
            timeout=10,
            allow_redirects=False
        )
        print(f"   Status: {r.status_code}")
        
        if r.status_code == 200:
            print(f"   ✓ {name} accessed successfully")
        elif r.status_code == 302:
            location = r.headers.get('Location', 'N/A')
            print(f"   ✗ Redirected to: {location}")
            if 'login' in location:
                print(f"   ✗ Session expired on {name} - redirected back to login!")
                break  # Stop testing if session fails
        else:
            print(f"   ✗ Unexpected status code: {r.status_code}")
    except Exception as e:
        print(f"   ✗ Error accessing {name}: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
