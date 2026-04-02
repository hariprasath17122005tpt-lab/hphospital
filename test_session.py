import requests
from bs4 import BeautifulSoup

def test_session():
    session = requests.Session()
    
    # Get login page to grab CSRF token
    login_url = "http://localhost:5000/patient/login"
    r1 = session.get(login_url)
    soup = BeautifulSoup(r1.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrf_token'})
    if csrf_token:
        csrf_token = csrf_token.get('value')
    else:
        print("No CSRF token found on login page!")

    # Perform login
    # Assuming there's a patient user, or create one first.
    # We can try to use a dummy one if we don't have one, or just try the login request.
    # What's a valid patient user? 
    # Try username 'fake', password 'fake' which might not work, but we can register one first.
    
    # 1. Register a test patient
    register_url = "http://localhost:5000/patient/register"
    r_reg = session.get(register_url)
    soup_reg = BeautifulSoup(r_reg.text, 'html.parser')
    csrf_token = soup_reg.find('input', {'name': 'csrf_token'})
    csrf_token = csrf_token.get('value') if csrf_token else ''

    reg_data = {
        'csrf_token': csrf_token,
        'username': 'testpat',
        'email': 'testpat@p.com',
        'password': 'password',
        'confirm_password': 'password',
        'first_name': 'Test',
        'last_name': 'Pat',
        'age': '25',
        'gender': 'Male',
        'phone': '1234567890'
    }
    r_reg_post = session.post(register_url, data=reg_data)
    
    # 2. Login
    login_data = {
        'csrf_token': csrf_token,
        'username': 'testpat',
        'password': 'password'
    }
    r2 = session.post(login_url, data=login_data, allow_redirects=True)
    
    # Dashboard check
    print("Dashboard status:", r2.status_code)
    print("Dashboard URL:", r2.url)
    
    # 3. Try to hit profile from dashboard
    profile_url = "http://localhost:5000/patient/profile"
    r3 = session.get(profile_url, allow_redirects=False)
    
    print("Profile requested. Status:", r3.status_code)
    print("Profile Location header:", r3.headers.get("Location", "None"))
    if r3.status_code == 302:
        print("Redirected to:", r3.headers.get("Location", ""))
        if "login" in r3.headers.get("Location", ""):
            print("SESSION DROPPED!")
        else:
            print("Session alive, just simple redirect")
    else:
        print("Session ALIVE! Page loaded successfully.")

if __name__ == "__main__":
    test_session()
