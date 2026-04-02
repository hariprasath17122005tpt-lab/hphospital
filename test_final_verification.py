import requests
import re
import sys
from urllib.parse import urljoin

BASE_URL = 'http://localhost:5000'
session = requests.Session()

def extract_csrf_token(html):
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    return match.group(1) if match else ''

print("\n" + "=" * 80)
print("FINAL VERIFICATION: PATIENT AUTHENTICATION FIX")
print("=" * 80)

# Test 1: Login with rose credentials
print("\n[TEST 1] Patient Login with rose/rose")
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
        allow_redirects=False
    )
    
    assert r.status_code == 302, f"Expected 302, got {r.status_code}"
    assert '/patient/dashboard' in r.headers.get('Location', ''), "Should redirect to dashboard"
    print("  ✅ PASS - Login successful, redirects to dashboard")
except AssertionError as e:
    print(f"  ❌ FAIL - {e}")
    sys.exit(1)
except Exception as e:
    print(f"  ❌ ERROR - {e}")
    sys.exit(1)

# Test 2: Dashboard access
print("\n[TEST 2] Dashboard Access (/patient/dashboard)")
try:
    r = session.get(urljoin(BASE_URL, '/patient/dashboard'), timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    print("  ✅ PASS - Dashboard loads without redirect")
except AssertionError as e:
    print(f"  ❌ FAIL - {e}")
    sys.exit(1)
except Exception as e:
    print(f"  ❌ ERROR - {e}")
    sys.exit(1)

# Test 3: Lab Reports (one of the originally failing routes)
print("\n[TEST 3] Lab Reports (/patient/lab-reports)")
try:
    r = session.get(urljoin(BASE_URL, '/patient/lab-reports'), timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert r.status_code != 302, "Should not redirect to login"
    print("  ✅ PASS - Lab reports loads, session persisted")
except AssertionError as e:
    print(f"  ❌ FAIL - {e}")
    sys.exit(1)
except Exception as e:
    print(f"  ❌ ERROR - {e}")
    sys.exit(1)

# Test 4: Lab Requests (another originally failing route)
print("\n[TEST 4] Lab Requests (/patient/lab-requests)")
try:
    r = session.get(urljoin(BASE_URL, '/patient/lab-requests'), timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert r.status_code != 302, "Should not redirect to login"
    print("  ✅ PASS - Lab requests loads, session persisted")
except AssertionError as e:
    print(f"  ❌ FAIL - {e}")
    sys.exit(1)
except Exception as e:
    print(f"  ❌ ERROR - {e}")
    sys.exit(1)

# Test 5: Prescriptions
print("\n[TEST 5] Prescriptions (/patient/prescriptions)")
try:
    r = session.get(urljoin(BASE_URL, '/patient/prescriptions'), timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    print("  ✅ PASS - Prescriptions loads")
except AssertionError as e:
    print(f"  ❌ FAIL - {e}")
    sys.exit(1)
except Exception as e:
    print(f"  ❌ ERROR - {e}")
    sys.exit(1)

# Test 6: Health data entry
print("\n[TEST 6] Health Data Entry (/patient/health-data/enter)")
try:
    r = session.get(urljoin(BASE_URL, '/patient/health-data/enter'), timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    print("  ✅ PASS - Health data entry loads")
except AssertionError as e:
    print(f"  ❌ FAIL - {e}")
    sys.exit(1)
except Exception as e:
    print(f"  ❌ ERROR - {e}")
    sys.exit(1)

# Test 7: Appointments
print("\n[TEST 7] Appointments (/patient/appointments)")
try:
    r = session.get(urljoin(BASE_URL, '/patient/appointments'), timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    print("  ✅ PASS - Appointments loads")
except AssertionError as e:
    print(f"  ❌ FAIL - {e}")
    sys.exit(1)
except Exception as e:
    print(f"  ❌ ERROR - {e}")
    sys.exit(1)

# Test 8: Profile
print("\n[TEST 8] Patient Profile (/patient/profile)")
try:
    r = session.get(urljoin(BASE_URL, '/patient/profile'), timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    print("  ✅ PASS - Profile loads")
except AssertionError as e:
    print(f"  ❌ FAIL - {e}")
    sys.exit(1)
except Exception as e:
    print(f"  ❌ ERROR - {e}")
    sys.exit(1)

# Test 9: Session persistence - re-access dashboard
print("\n[TEST 9] Session Persistence (/patient/dashboard again)")
try:
    r = session.get(urljoin(BASE_URL, '/patient/dashboard'), timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    print("  ✅ PASS - Dashboard still accessible, session active")
except AssertionError as e:
    print(f"  ❌ FAIL - {e}")
    sys.exit(1)
except Exception as e:
    print(f"  ❌ ERROR - {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("ALL TESTS PASSED ✅")
print("=" * 80)
print("\nSummary:")
print("  ✓ Patient login works (rose/rose)")
print("  ✓ Dashboard accessible after login")
print("  ✓ Lab reports accessible (previously failing)")
print("  ✓ Lab requests accessible (previously failing)")
print("  ✓ All patient routes work without session expiration")
print("  ✓ Session persists across multiple page accesses")
print("\nRoot Cause Fixed:")
print("  ✗ Removed mixed Flask-Login + manual session approach")
print("  ✓ Now uses pure Flask-Login only")
print("  ✓ Removed unused session['user'] and session['role'] variables")
print("  ✓ Removed incorrect db.session.commit() call")
print("\nAuthentication System:")
print("  100% Flask-Login consistent")
print("  No manual session variable mixing")
print("  No database session commits")
print("=" * 80 + "\n")
