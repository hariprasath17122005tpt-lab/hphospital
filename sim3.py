from app import create_app, db
from app.models.models import User
from flask import session
from flask_login import login_user
import os

app = create_app(os.getenv('FLASK_ENV', 'development'))

with app.test_request_context():
    with app.app_context():
        # Get patient
        user = User.query.filter_by(username='patient').first()
        if not user:
            print("User patient not found")
        else:
            print(f"User ID: {user.id}")
            print(f"get_id(): {user.get_id()}")
            
            # mock login
            login_user(user)
            print(f"Session dictionary after login: {dict(session)}")
