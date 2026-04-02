from app import create_app, db
from app.models.models import User, Patient
from flask import url_for

app = create_app()

def debug_dashboard():
    with app.app_context():
        user = User.query.filter_by(username='john_patient').first()
        if not user:
            # try 'patient'
            user = User.query.filter_by(username='patient').first()
            
        if not user:
            print("No test user found.")
            return

        print(f"Debugging as user: {user.username} (ID: {user.id})")
        
        with app.test_request_context('/patient/dashboard'):
            from flask_login import login_user
            login_user(user)
            
            from app.routes.patient import dashboard
            try:
                response = dashboard()
                print("Dashboard function returned successfully.")
                if hasattr(response, 'status_code'):
                    print(f"Status Code: {response.status_code}")
                else:
                    print("Returned string/template data.")
            except Exception as e:
                import traceback
                print(f"Caught Error in dashboard(): {e}")
                print(traceback.format_exc())

if __name__ == "__main__":
    debug_dashboard()
