import requests
import re

session = requests.Session()

# Get login page
r = session.get('http://localhost:5000/patient/login')
csrf = re.search(r'name="csrf_token"\s+value="([^"]+)"', r.text)
csrf_token = csrf.group(1) if csrf else ''

print('Testing fake/fake login...')
r = session.post('http://localhost:5000/patient/login', data={
    'username': 'fake',
    'password': 'fake',
    'csrf_token': csrf_token
}, allow_redirects=False)

print(f'Login status: {r.status_code}')
print(f'Cookies: {session.cookies}')

# Try dashboard
r = session.get('http://localhost:5000/patient/dashboard', allow_redirects=False)
print(f'Dashboard status: {r.status_code}')

if r.status_code == 302:
    print(f'REDIRECTED to: {r.headers.get("Location")}')
    print('ERROR: Session not persisting!')
else:
    print('OK: Dashboard accessible')
