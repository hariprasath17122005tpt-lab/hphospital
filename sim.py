import requests
import re
import urllib.parse
from pprint import pprint

BASE_URL = "http://127.0.0.1:5000"
# Also try 0.0.0.0 and localhost
session = requests.Session()

def run_test():
    print("--- 1. Loading patient login page ---")
    try:
        r1 = session.get(f"{BASE_URL}/patient/login")
    except Exception as e:
        print(f"Server not running at {BASE_URL}: {e}")
        return
        
    if r1.status_code != 200:
        print(f"Failed: {r1.status_code}")
        return
        
    print(f"Cookies after GET: {session.cookies.get_dict()}")
    # Extract CSRF token
    # The html has: <input type="hidden" name="csrf_token" value="..." />
    match = re.search(r'name="csrf_token" value="([^"]+)"', r1.text)
    if not match:
        print("No CSRF token found via regex! Try alternative.")
        return 
    csrf_token = match.group(1)
    
    print("\n--- 2. Logging in with patient123 ---")
    data = {
        'csrf_token': csrf_token,
        'username': 'patient',
        'password': 'patient123'
    }
    r2 = session.post(f"{BASE_URL}/patient/login", data=data, allow_redirects=False)
    print(f"Status: {r2.status_code}")
    print(f"Location: {r2.headers.get('Location')}")
    print(f"Set-Cookie: {r2.headers.get('Set-Cookie')}")
    print(f"Cookies after login: {session.cookies.get_dict()}")
    
    print("\n--- 3. Accessing /patient/dashboard ---")
    r3 = session.get(f"{BASE_URL}/patient/dashboard", allow_redirects=False)
    print(f"Dashboard Status: {r3.status_code}")
    print(f"Dashboard Location: {r3.headers.get('Location')}")
    
    print("\n--- 4. Accessing /patient/book-appointment ('clicking a link') ---")
    r4 = session.get(f"{BASE_URL}/patient/book-appointment", allow_redirects=False)
    print(f"Book Appt Status: {r4.status_code}")
    print(f"Book Appt Location: {r4.headers.get('Location')}")
    if r4.status_code == 302 and "login" in r4.headers.get('Location', ''):
        print("SESSION DROPPED!")
    else:
        print("SESSION PERSISTED FINE.")

if __name__ == '__main__':
    run_test()
