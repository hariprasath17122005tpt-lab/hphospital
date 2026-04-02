import requests
from urllib.parse import urljoin
import re

BASE_URL = 'http://localhost:5000'
session = requests.Session()

print('=== AUTHENTICATION TEST ===')

# Get login page
r = session.get(urljoin(BASE_URL, '/patient/login'))
print(f'Login page: {r.status_code}')

# Extract CSRF token
csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', r.text)
csrf_token = csrf_match.group(1) if csrf_match else ''
print(f'CSRF token found: {len(csrf_token) > 0}')

# Login
login_data = {'username': 'fake', 'password': 'fake', 'csrf_token': csrf_token}
r = session.post(urljoin(BASE_URL, '/patient/login'), data=login_data, allow_redirects=False)
print(f'Login response: {r.status_code}')

# Test routes
routes = ['/patient/dashboard', '/patient/prescriptions', '/patient/appointments']
for route in routes:
    r = session.get(urljoin(BASE_URL, route), allow_redirects=False)
    status = r.status_code
    redirect = r.headers.get('Location', '') if status == 302 else ''
    print(f'{route}: {status} {"-> " + redirect if redirect else ""}')