
import requests
import sys

BASE_URL = 'http://127.0.0.1:5000'

# Based on route definitions in auth.py without a blueprint prefix
routes_to_check = [
    '/',
    '/patient/login',
    '/patient/register',
    '/doctor/login',
    '/doctor/register'
]

print(f"Checking application health at {BASE_URL}...")
error_count = 0

for route in routes_to_check:
    url = f"{BASE_URL}{route}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print(f"✅ {route}: OK (200)")
        else:
            print(f"❌ {route}: FAILED ({response.status_code})")
            error_count += 1
    except Exception as e:
        print(f"❌ {route}: ERROR - {str(e)}")
        error_count += 1

if error_count == 0:
    print("\nAll public pages verified successfully.")
else:
    print(f"\nFound {error_count} errors.")
