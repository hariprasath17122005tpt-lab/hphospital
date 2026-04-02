import requests
import sys
from urllib.parse import urljoin

BASE_URL = 'http://localhost:5000'

# Create a session to persist cookies
session = requests.Session()

print("=" * 60)
print("COMPREHENSIVE PATIENT AUTHENTICATION TEST")
print("=" * 60)

def test_route(name, path, expected_status=200):
    """Test a specific route and return True if it works as expected"""
    print(f"\nTesting {name} ({path})...")
    try:
        r = session.get(urljoin(BASE_URL, path), timeout=10, allow_redirects=False)
        print(f"   Status: {r.status_code}")

        if r.status_code == expected_status:
            print(f"   ✓ {name} works correctly")
            return True
        elif r.status_code == 302:
            location = r.headers.get('Location', 'N/A')
            print(f"   ✗ Redirected to: {location}")
            if 'login' in location:
                print(f"   ✗ SESSION LOST - Redirected back to login!")
                return False
            else:
                print(f"   ? Unexpected redirect (not to login)")
                return False
        else:
            print(f"   ✗ Unexpected status code: {r.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

# Step 1: Get the login page
print("\n1. Getting patient login page...")
try:
    r = session.get(urljoin(BASE_URL, '/patient/login'), timeout=10)
    print(f"   Status: {r.status_code}")
    if 'csrf_token' in r.text:
        print("   ✓ Login page loaded successfully")
    else:
        print("   ✗ CSRF token not found in login page")
        sys.exit(1)
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Step 2: Register account (if not already)
print("\n2. Creating test patient account (rose)...")
try:
    rr = session.get(urljoin(BASE_URL, '/patient/register'), timeout=10)
    if rr.status_code != 200:
        print(f"   ✗ Failed to access registration page ({rr.status_code})")
        sys.exit(1)

    import re
    csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', rr.text)
    register_csrf = csrf_match.group(1) if csrf_match else ''

    register_data = {
        'username': 'rose',
        'email': 'rose@example.com',
        'password': 'rose',
        'confirm_password': 'rose',
        'first_name': 'Rose',
        'last_name': 'H',
        'age': '30',
        'gender': 'Female',
        'phone': '+1234567890',
        'csrf_token': register_csrf
    }

    rreg = session.post(urljoin(BASE_URL, '/patient/register'), data=register_data, timeout=10, allow_redirects=False)
    print(f"   Status: {rreg.status_code}")
    if rreg.status_code in (302, 200):
        print("   ✓ Registration request processed")
    else:
        print("   ✗ Registration failed")
        sys.exit(1)
except Exception as e:
    print(f"   ✗ Error during registration: {e}")
    sys.exit(1)

# Step 3: Login
print("\n3. Attempting login with username: rose, password: rose...")
try:
    rl = session.get(urljoin(BASE_URL, '/patient/login'), timeout=10)
    csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', rl.text)
    csrf_token = csrf_match.group(1) if csrf_match else ''

    login_data = {
        'username': 'rose',
        'password': 'rose',
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
        location = r.headers.get('Location', 'N/A')
        print(f"   ✓ Redirected to: {location}")
        if '/patient/dashboard' in location:
            print("   ✓ Login successful - redirected to dashboard")
        else:
            print("   ? Unexpected redirect location after login")
    else:
        print(f"   ✗ Login failed with status: {r.status_code}")
        sys.exit(1)

except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Step 3: Test all patient routes
routes_to_test = [
    ('Dashboard', '/patient/dashboard', 200),
    ('Prescriptions', '/patient/prescriptions', 200),
    ('Appointments', '/patient/appointments', 200),
    ('Lab Reports', '/patient/lab-reports', 200),  # Note: hyphen, not underscore
    ('Billing', '/patient/billing', 200),
    ('Profile', '/patient/profile', 200),
    ('Health Data Entry', '/patient/enter_health_data', 200),
]

all_passed = True
for name, path, expected_status in routes_to_test:
    if not test_route(name, path, expected_status):
        all_passed = False

print("\n" + "=" * 60)
if all_passed:
    print("🎉 ALL TESTS PASSED - Authentication is working correctly!")
    print("If you're still experiencing issues in the browser:")
    print("1. Clear browser cache and cookies for localhost:5000")
    print("2. Try incognito/private browsing mode")
    print("3. Hard refresh (Ctrl+F5)")
    print("4. Check browser console for JavaScript errors")
else:
    print("❌ SOME TESTS FAILED - There are authentication issues")
print("=" * 60)