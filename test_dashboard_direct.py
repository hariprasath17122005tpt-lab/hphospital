"""Force-login as patient and test dashboard - bypassing password."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv('.env.production' if os.path.exists('.env.production') else '.env')

from app import create_app
from app.models.models import db, User, Patient, UserRole, Prescription
from flask_login import login_user

app = create_app()
app.config['WTF_CSRF_ENABLED'] = False
app.config['TESTING'] = True

output = []

with app.app_context():
    with app.test_client() as client:
        # Force login as patient_john (user_id=3)
        patient_user = User.query.filter_by(username='patient_john').first()
        if not patient_user:
            patient_user = User.query.filter_by(role=UserRole.PATIENT).first()
        
        output.append(f"Using patient: id={patient_user.id} username={patient_user.username}")
        
        # Force login via test request context
        with client.session_transaction() as sess:
            sess['_user_id'] = str(patient_user.id)
        
        # Now hit the dashboard
        resp = client.get('/patient/dashboard')
        body = resp.data.decode('utf-8', errors='replace')
        
        output.append(f"Dashboard response status: {resp.status_code}")
        output.append(f"Response length: {len(body)} chars")
        
        if 'FIXED DASHBOARD ERROR' in body:
            error_start = body.index('FIXED DASHBOARD ERROR')
            error_text = body[error_start:error_start+500]
            output.append(f"")
            output.append(f"ERROR FOUND:")
            output.append(error_text)
        elif resp.status_code == 200:
            # Check for common dashboard elements
            has_health = 'health' in body.lower()
            has_patient = 'patient' in body.lower()
            output.append(f"Contains 'health': {has_health}")
            output.append(f"Contains 'patient': {has_patient}")
            output.append(f"DASHBOARD LOADED SUCCESSFULLY!")
        elif resp.status_code == 302:
            output.append(f"Redirect to: {resp.headers.get('Location', 'unknown')}")
        else:
            output.append(f"First 300 chars: {body[:300]}")

result = '\n'.join(output)
with open('dashboard_final_result.txt', 'w', encoding='utf-8') as f:
    f.write(result)
print("Done. Check dashboard_final_result.txt")
