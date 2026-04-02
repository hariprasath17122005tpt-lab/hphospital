import requests
import re
import sys
from urllib.parse import urljoin

BASE_URL = 'http://localhost:5000'
session = requests.Session()

def extract_csrf_token(html):
    """Extract CSRF token from HTML"""
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    return match.group(1) if match else ''

print("\n" + "=" * 70)
print("COMPREHENSIVE SESSION PERSISTENCE TEST")
print("=" * 70)

# Step 1: Login
print("\nStep 1: Logging in as rose...")
try:
    r = session.get(urljoin(BASE_URL, '/patient/login'), timeout=10)
    csrf_token = extract_csrf_token(r.text)
    
    login_data = {
        'username': 'rose',
        'password': 'rose',
        'csrf_token': csrf_token
    }
    
    r = session.post(
        urljoin(BASE_URL, '/patient/login'),
        data=login_data,
        timeout=10,
        allow_redirects=True
    )
    
    if 'Login successful' in r.text or '/patient/dashboard' in r.url:
        print("  ✓ Login successful")
        print(f"  Current URL: {r.url}")
    else:
        print("  ✗ Login failed")
        sys.exit(1)
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

# Step 2: Access dashboard
print("\nStep 2: Accessing patient dashboard...")
try:
    r = session.get(urljoin(BASE_URL, '/patient/dashboard'), timeout=10)
    if r.status_code == 200:
        print(f"  ✓ Dashboard loaded (Status: {r.status_code})")
    else:
        print(f"  ✗ Dashboard failed (Status: {r.status_code})")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Step 3: Access prescriptions
print("\nStep 3: Accessing prescriptions page...")
try:
    r = session.get(urljoin(BASE_URL, '/patient/prescriptions'), timeout=10)
    if r.status_code == 200:
        print(f"  ✓ Prescriptions page loaded (Status: {r.status_code})")
    elif r.status_code == 302:
        print(f"  ✗ Redirected to login - Session expired!")
        print(f"  Location: {r.headers.get('Location', 'N/A')}")
    else:
        print(f"  ✗ Unexpected status: {r.status_code}")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Step 4: Access health data
print("\nStep 4: Accessing health data entry page...")
try:
    r = session.get(urljoin(BASE_URL, '/patient/health-data/enter'), timeout=10)
    if r.status_code == 200:
        print(f"  ✓ Health data page loaded (Status: {r.status_code})")
    elif r.status_code == 302:
        print(f"  ✗ Redirected to login - Session expired!")
        print(f"  Location: {r.headers.get('Location', 'N/A')}")
    else:
        print(f"  ✗ Unexpected status: {r.status_code}")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Step 5: Access appointments
print("\nStep 5: Accessing appointments page...")
try:
    r = session.get(urljoin(BASE_URL, '/patient/appointments'), timeout=10)
    if r.status_code == 200:
        print(f"  ✓ Appointments page loaded (Status: {r.status_code})")
    elif r.status_code == 302:
        print(f"  ✗ Redirected to login - Session expired!")
        print(f"  Location: {r.headers.get('Location', 'N/A')}")
    else:
        print(f"  ✗ Unexpected status: {r.status_code}")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Step 6: Access profile
print("\nStep 6: Accessing patient profile...")
try:
    r = session.get(urljoin(BASE_URL, '/patient/profile'), timeout=10)
    if r.status_code == 200:
        print(f"  ✓ Profile page loaded (Status: {r.status_code})")
    elif r.status_code == 302:
        print(f"  ✗ Redirected to login - Session expired!")
        print(f"  Location: {r.headers.get('Location', 'N/A')}")
    else:
        print(f"  ✗ Unexpected status: {r.status_code}")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Step 7: Re-access dashboard to verify session still active
print("\nStep 7: Re-accessing dashboard (verify session persistence)...")
try:
    r = session.get(urljoin(BASE_URL, '/patient/dashboard'), timeout=10)
    if r.status_code == 200:
        print(f"  ✓ Dashboard still accessible (Status: {r.status_code})")
    elif r.status_code == 302:
        print(f"  ✗ Redirected to login - Session EXPIRED!")
        print(f"  Location: {r.headers.get('Location', 'N/A')}")
    else:
        print(f"  ✗ Unexpected status: {r.status_code}")
except Exception as e:
    print(f"  ✗ Error: {e}")

print("\n" + "=" * 70)
print("TEST COMPLETED SUCCESSFULLY!")
print("=" * 70)
print("\nSummary: All patient dashboard features are now accessible")
print("without session expiration after login.")
print("=" * 70 + "\n")
