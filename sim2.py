import requests
import re
import urllib.parse
from pprint import pprint
import base64
import json

BASE_URL = "http://127.0.0.1:5000"
session = requests.Session()

def decode_flask_cookie(cookie_value):
    try:
        # Flask cookies append '.' and a signature. The first part is base64
        payload = cookie_value.split(".")[0]
        # Pad base64
        payload += "=" * ((4 - len(payload) % 4) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception as e:
        return f"Error decoding: {e}"

def run_test():
    r1 = session.get(f"{BASE_URL}/patient/login")
    match = re.search(r'name="csrf_token" value="([^"]+)"', r1.text)
    csrf_token = match.group(1)
    
    data = {
        'csrf_token': csrf_token,
        'username': 'patient',
        'password': 'patient123'
    }
    r2 = session.post(f"{BASE_URL}/patient/login", data=data, allow_redirects=False)
    
    flask_cookie = session.cookies.get('session')
    print(f"Encoded Cookie: {flask_cookie}")
    print(f"Decoded Cookie: {decode_flask_cookie(flask_cookie)}")
    
if __name__ == '__main__':
    run_test()
