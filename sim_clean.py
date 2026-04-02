import requests
import re
import urllib.parse
from pprint import pformat
import base64
import json

BASE_URL = "http://127.0.0.1:5000"
session = requests.Session()

def decode_flask_cookie(cookie_value):
    try:
        payload = cookie_value.split(".")[0]
        if payload.startswith('.'):
            return "COMPRESSED"
        payload += "=" * ((4 - len(payload) % 4) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception as e:
        return f"Error decoding: {e}"

def run_test():
    log = []
    
    r1 = session.get(f"{BASE_URL}/patient/login")
    match = re.search(r'name="csrf_token".*?value="([^"]+)"', r1.text)
    csrf_token = match.group(1) if match else "NO_CSRF"
    
    log.append(f"GET /login Cookie: {session.cookies.get('session')}")
    log.append(f"Decoded GET Cookie: {decode_flask_cookie(session.cookies.get('session', ''))}")
    
    data = {
        'csrf_token': csrf_token,
        'username': 'patient',
        'password': 'patient123'
    }
    r2 = session.post(f"{BASE_URL}/patient/login", data=data, allow_redirects=False)
    
    log.append(f"POST /login Status: {r2.status_code}")
    log.append(f"POST /login Location: {r2.headers.get('Location')}")
    log.append(f"POST /login Set-Cookie: {r2.headers.get('Set-Cookie')}")
    log.append(f"POST /login Cookie: {session.cookies.get('session')}")
    log.append(f"Decoded POST Cookie: {decode_flask_cookie(session.cookies.get('session', ''))}")
    
    r3 = session.get(f"{BASE_URL}/patient/dashboard", allow_redirects=False)
    log.append(f"GET /dashboard Status: {r3.status_code}")
    log.append(f"GET /dashboard Location: {r3.headers.get('Location')}")
    
    with open("test_result.txt", "w") as f:
        f.write("\n".join(log))

if __name__ == '__main__':
    run_test()
