#!/usr/bin/env python
"""
🏥 AI-Enabled Doctor-Patient Health Management System
QUICK START GUIDE

This script helps you get started quickly!
"""

import os
import sys
from pathlib import Path

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_section(text):
    """Print section header"""
    print(f"\n✓ {text}")

def main():
    print_header("🏥 HEALTH MANAGEMENT SYSTEM - QUICK START")
    
    print("\n📋 WHAT YOU HAVE:")
    features = [
        "✓ Complete Flask web application",
        "✓ Patient & Doctor roles with separate interfaces",
        "✓ AI-powered health risk predictions",
        "✓ Personalized diet & exercise plans",
        "✓ Doctor-Patient appointment & chat system",
        "✓ Health data tracking & analytics",
        "✓ Professional responsive UI with Bootstrap",
        "✓ Production-ready code with security",
    ]
    for feature in features:
        print(f"  {feature}")
    
    print_header("🚀 GETTING STARTED")
    
    print("""
STEP 1: Install Dependencies
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Command:
    pip install -r requirements.txt

This installs:
  • Flask (web framework)
  • Flask-SQLAlchemy (database ORM)
  • Flask-Login (authentication)
  • Scikit-learn (ML models)
  • And more...


STEP 2: Optional - Initialize Database with Sample Data
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Command:
    python init_db.py

This creates:
  ✓ 9 database tables
  ✓ 3 sample patients
  ✓ 3 sample doctors
  ✓ Test credentials for logging in

Sample Credentials:
  Patient:
    • john_patient / password123
    • sarah_patient / password123
    • mike_patient / password123

  Doctor:
    • dr_smith / password123
    • dr_williams / password123
    • dr_brown / password123


STEP 3: Run the Application
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Command:
    python run.py

Output should show:
  * Running on http://127.0.0.1:5000
  * Debug mode: on


STEP 4: Open Your Browser
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Visit:
    http://localhost:5000

You should see:
  ✓ Home page with "Doctor" and "Patient" login buttons
  ✓ Professional UI with navigation
  ✓ Login/Register options
""")
    
    print_header("🎮 TESTING THE APPLICATION")
    
    print("""
TEST AS PATIENT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Click "Login as Patient" or visit:
   http://localhost:5000/patient/login

2. Login with:
   Username: john_patient
   Password: password123

3. On dashboard, click "Record Health Data"

4. Enter sample data:
   • Blood Pressure: 140/90
   • Sugar Levels: 150 (fasting), 200 (random)
   • Heart Rate: 88 bpm
   • Symptoms: headache, tiredness
   • Sleep: 6 hours

5. Submit and view AI analysis:
   ✓ See health risk levels (Diabetes, Heart, BP)
   ✓ View personalized diet plan
   ✓ Get exercise recommendations
   ✓ Get symptom analysis

6. Optional: Book appointment with doctor


TEST AS DOCTOR:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Click "Login as Doctor" or visit:
   http://localhost:5000/doctor/login

2. Login with:
   Username: dr_smith
   Password: password123

3. On dashboard, you'll see:
   ✓ Total patients
   ✓ Today's appointments
   ✓ Pending appointment requests
   ✓ Unread messages
   ✓ Critical patient alerts

4. Click "View Patients" to see patient list

5. Click on a patient to view:
   ✓ Full health history
   ✓ All vital signs and AI predictions
   ✓ Past appointments
   ✓ Previous prescriptions

6. Optional: Write prescription or send message
""")
    
    print_header("📁 KEY FILES")
    
    print("""
MAIN APPLICATION FILES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
app/__init__.py              Flask app initialization
app/models/models.py        Database models (User, Patient, Doctor, etc.)
app/routes/                 URL routes & logic
  ├── main.py              Home page routes
  ├── auth.py              Login/Register routes
  ├── patient.py           Patient features
  └── doctor.py            Doctor features
app/ml_models/health_ai.py  AI/ML prediction models
app/templates/              HTML templates
app/static/                 CSS, JavaScript, images

CONFIGURATION FILES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
config.py                   Flask configuration
.env                        Environment variables
requirements.txt            Python dependencies
run.py                      Start the app
init_db.py                  Initialize database

DOCUMENTATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
README.md                   Main documentation
SETUP_GUIDE.md             Detailed setup instructions
PROJECT_SUMMARY.md         Complete project overview
IMPLEMENTATION_CHECKLIST.md What's been implemented
API_ROUTES.md              All available routes
QUICK_START.py             This file!
""")
    
    print_header("🎯 COMMON TASKS")
    
    print("""
CHANGE DATABASE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Default: SQLite (file-based, no setup needed)
Production: MySQL

To use MySQL:
1. Create database: CREATE DATABASE hospital_db;
2. Edit .env: DATABASE_URL=mysql+pymysql://user:pass@localhost/hospital_db
3. Install: pip install pymysql


RESET DATABASE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python init_db.py

This will:
✓ Drop all existing tables
✓ Create new tables
✓ Add sample data


CHANGE PORT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Default: 5000
Command: python run.py --port 5001


VIEW DATABASE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Database file: hospital.db (SQLite)
Or use: sqlite3 hospital.db
Or use DB browser tool
""")
    
    print_header("🆘 TROUBLESHOOTING")
    
    print("""
ERROR: "Port 5000 is already in use"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Solution: python run.py --port 5001


ERROR: "ModuleNotFoundError: No module named 'flask'"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Solution: pip install -r requirements.txt


ERROR: "Database connection failed"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Solution: python init_db.py


ERROR: "Login credentials don't work"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Solution: python init_db.py (create sample data again)


Can't access /patient/dashboard after login
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Solution: 
1. Clear browser cookies
2. Logout and login again
3. Check that you're using patient login (not doctor)
""")
    
    print_header("📚 DOCUMENTATION FILES")
    
    print("""
For more detailed information, check:

1. README.md
   • Project overview
   • Features list
   • Technology stack

2. SETUP_GUIDE.md
   • Step-by-step installation
   • Database setup
   • Configuration

3. PROJECT_SUMMARY.md
   • Complete architecture
   • AI/ML models explanation
   • Security features

4. IMPLEMENTATION_CHECKLIST.md
   • What's been completed
   • Statistics
   • Future enhancements

5. API_ROUTES.md
   • All available routes
   • URL patterns
   • Sample credentials
""")
    
    print_header("🚀 NEXT STEPS")
    
    print("""
1. ✓ Install dependencies
2. ✓ Initialize database  
3. ✓ Run application
4. ✓ Test as patient and doctor
5. → Customize colors and branding
6. → Add more features
7. → Deploy to production
""")
    
    print_header("💡 TIPS")
    
    print("""
• Use modern browser (Chrome, Firefox, Edge, Safari)
• JavaScript must be enabled
• Keep terminal window open while app is running
• Check browser console (F12) for JavaScript errors
• Check terminal for Python errors
• Use Ctrl+C to stop the server
• Always backup database before resetting
• Test with sample data first
""")
    
    print_header("✅ YOU'RE ALL SET!")
    
    print("""
Your AI-Powered Health Management System is ready!

Next: Run these commands in order
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. pip install -r requirements.txt
2. python init_db.py
3. python run.py
4. Open http://localhost:5000

Happy coding! 🎉
""")

if __name__ == '__main__':
    main()
