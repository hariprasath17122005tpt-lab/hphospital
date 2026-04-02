import requests
import re
from pprint import pprint

# Base config
BASE_URL = "http://127.0.0.1:5000"
session = requests.Session()

def run_test():
    print("--- 1. Loading patient login page ---")
    r1 = session.get(f"{BASE_URL}/patient/login")
    if r1.status_code != 200:
        print(f"Failed to reach login page: {r1.status_code}")
        # maybe it's running on localhost instead of 127.0.0.1
        return
        
    # Extract CSRF
    match = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', r1.text)
    if not match:
        print("No CSRF token found!")
        return 
    csrf_token = match.group(1)
    print(f"CSRF Token: {csrf_token}")
    
    # Check cookies
    print(f"Cookies after GET: {session.cookies.get_dict()}")

    # To test login properly without doing a real registration, 
    # Can we just query what happens on an unauthenticated dashboard request?
    print("\n--- 2. Trying to access dashboard without auth ---")
    r2 = session.get(f"{BASE_URL}/patient/dashboard", allow_redirects=False)
    print(f"Status: {r2.status_code}")
    print(f"Location: {r2.headers.get('Location')}")
    print(f"Set-Cookie: {r2.headers.get('Set-Cookie')}")

if __name__ == '__main__':
    run_test()
