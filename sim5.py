from flask import Flask, session
from flask_login import LoginManager, UserMixin, login_user
import json
from base64 import urlsafe_b64encode

app = Flask(__name__)
app.secret_key = 'test-secret'
app.config['SESSION_COOKIE_NAME'] = 'session'

login_manager = LoginManager()
login_manager.init_app(app)

class TestUser(UserMixin):
    def __init__(self, id):
        self.id = id
        
@login_manager.user_loader
def load_user(user_id):
    return TestUser(user_id)

@app.route('/login')
def login():
    session.permanent = True
    login_user(TestUser(123))
    # Flask sets the cookie at the end of the request
    return 'Logged in'

if __name__ == '__main__':
    with app.test_client() as c:
        response = c.get('/login')
        print(response.headers.get('Set-Cookie'))
