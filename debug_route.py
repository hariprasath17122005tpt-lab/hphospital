
import os
import sys
from app import create_app
from app.models.models import db, User, Patient, HealthData
from flask import url_for

def test_exercise_route():
    app = create_app()
    with app.app_context():
        # Find a patient user
        user = User.query.filter_by(role='PATIENT').first()
        if not user:
            print("No patient user found in DB to test with.")
            return

        print(f"Testing with user: {user.username}")
        
        # Simulate being logged in
        with app.test_request_context('/patient/exercise-plan'):
            from flask_login import login_user
            login_user(user)
            
            try:
                from app.routes.patient import exercise_plan
                print("Calling exercise_plan route function...")
                response = exercise_plan()
                print("Route function returned successfully.")
            except Exception as e:
                import traceback
                print("\n--- ERROR DETECTED ---")
                print(f"Type: {type(e).__name__}")
                print(f"Message: {str(e)}")
                print("Traceback:")
                print(traceback.format_exc())

if __name__ == "__main__":
    test_exercise_route()
