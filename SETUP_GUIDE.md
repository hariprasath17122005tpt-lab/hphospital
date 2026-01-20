# AI-Enabled Doctor-Patient Smart Health Management System
## Complete Setup & Deployment Guide

---

## 📋 Quick Start (5 minutes)

### 1. **Install Dependencies**
```powershell
# Windows PowerShell
cd c:\Users\harip\OneDrive\Desktop\hospital
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. **Run the Application**
```powershell
python run.py
```

Visit: **http://localhost:5000**

---

## 🎯 Project Overview

Your application is a **role-based health management system** with two separate interfaces:

### **PATIENT SIDE** 👤
- Register/Login
- Enter health parameters (BP, sugar, heart rate, etc.)
- Get AI-powered health analysis
- Receive personalized diet & exercise plans
- Book appointments with doctors
- Chat with doctors
- View prescriptions
- Track health history

### **DOCTOR SIDE** 👨‍⚕️
- Register/Login (with verification)
- View patient list
- Access detailed patient records
- Manage appointments (approve/reject/complete)
- Write prescriptions
- Chat with patients
- View patient risk alerts
- Access analytics dashboard

---

## 🗂️ Project Structure

```
hospital/
├── app/
│   ├── __init__.py                    ← Flask app factory
│   ├── models/
│   │   └── models.py                  ← Database models (User, Patient, Doctor, etc.)
│   ├── routes/
│   │   ├── main.py                    ← Home page & common routes
│   │   ├── auth.py                    ← Login/Register routes for both roles
│   │   ├── patient.py                 ← All patient features
│   │   └── doctor.py                  ← All doctor features
│   ├── ml_models/
│   │   └── health_ai.py               ← AI/ML models (predictions, recommendations)
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css              ← Bootstrap + Custom styling
│   │   └── js/
│   │       └── main.js                ← JavaScript functions
│   └── templates/
│       ├── base.html                  ← Base template (navigation, footer)
│       ├── index.html                 ← Home page
│       ├── patient_login.html         ← Patient login
│       ├── patient_register.html      ← Patient registration
│       ├── doctor_login.html          ← Doctor login
│       ├── doctor_register.html       ← Doctor registration
│       ├── patient/                   ← Patient templates
│       │   ├── dashboard.html
│       │   ├── enter_health_data.html
│       │   ├── health_results.html
│       │   ├── diet_plan.html
│       │   ├── exercise_plan.html
│       │   └── ... (other patient templates)
│       └── doctor/                    ← Doctor templates
│           ├── dashboard.html
│           ├── patient_list.html
│           ├── view_patient.html
│           └── ... (other doctor templates)
├── config.py                          ← Configuration (Dev, Prod, Test)
├── run.py                             ← Entry point
├── requirements.txt                   ← Python dependencies
├── .env                               ← Environment variables
└── README.md                          ← Project documentation
```

---

## 🗄️ Database Schema

### Tables Created:

1. **users**
   - Stores login credentials
   - role: PATIENT or DOCTOR
   - password_hash: Encrypted password

2. **patients**
   - Stores patient profile info
   - Link to user via user_id
   - Personal details, medical history

3. **doctors**
   - Stores doctor profile info
   - license_number: Medical license
   - specialization: Medical field
   - verified: Admin approval status

4. **health_data**
   - Patient vital signs (BP, sugar, heart rate, etc.)
   - AI predictions (diabetes risk, heart risk, etc.)
   - BMI calculations
   - Lifestyle data

5. **appointments**
   - Appointment scheduling
   - Status: pending, confirmed, completed, cancelled
   - Links patient and doctor

6. **prescriptions**
   - Doctor prescriptions
   - Medicines, dosage, frequency
   - Diet & exercise recommendations

7. **messages**
   - Chat between doctor-patient
   - Sender type: doctor or patient

8. **diet_plans & exercise_plans**
   - AI-generated recommendations
   - Personalized for each patient

---

## 🤖 AI/ML Models Implemented

### 1. **Diabetes Risk Predictor**
```python
Input: age, BMI, fasting_sugar, random_sugar, family_history
Output: Risk % (0-100%)
Logic: Rule-based scoring system
```

### 2. **Heart Disease Risk Predictor**
```python
Input: age, systolic_bp, diastolic_bp, heart_rate, smoking, cholesterol
Output: Risk % (0-100%)
```

### 3. **Hypertension Risk Predictor**
```python
Input: systolic_bp, diastolic_bp, age, BMI
Output: Risk % (0-100%)
```

### 4. **Symptom Checker (NLP)**
```python
Input: symptoms description (text)
Output: List of possible conditions with severity
```

### 5. **Diet Plan Generator**
```python
Input: BMI, diabetes_risk, bp_status, heart_risk
Output: Personalized meal plan (breakfast, lunch, dinner, snacks, water intake)
```

### 6. **Exercise Plan Generator**
```python
Input: BMI, health risks, age
Output: Personalized exercise recommendations (type, duration, frequency, intensity)
```

---

## 🚀 How to Use

### **AS A PATIENT:**

1. **Register**
   - Visit: http://localhost:5000
   - Click "Register as Patient"
   - Fill in basic info (name, age, gender, etc.)
   - Login with credentials

2. **Enter Health Data**
   - Go to "Record Health Data"
   - Enter vital signs (BP, sugar, heart rate)
   - Add symptoms if any
   - System generates AI analysis

3. **View Analysis & Recommendations**
   - See health risk levels (diabetes, heart, BP)
   - Get AI health findings
   - View personalized diet plan
   - View exercise recommendations

4. **Book Appointment**
   - Select a doctor
   - Choose date & time
   - Doctor receives notification

5. **Chat with Doctor**
   - Message doctor directly
   - Receive prescriptions
   - Track health progress

### **AS A DOCTOR:**

1. **Register**
   - Visit: http://localhost:5000
   - Click "Register as Doctor"
   - Enter medical credentials (license number, specialization)
   - (Note: Requires admin approval in production)

2. **View Patient List**
   - See all your patients
   - Check last visit and risk levels

3. **Manage Appointments**
   - Approve/reject appointment requests
   - Schedule confirmations

4. **Write Prescriptions**
   - Select patient
   - Enter medicines, dosage, frequency
   - Add diet & exercise notes

5. **Chat with Patients**
   - Answer patient questions
   - Send health guidance

6. **Monitor Critical Patients**
   - Get alerts for high-risk patients
   - View patient health trends

---

## 🔑 Key Features

### Patient Features:
- ✅ Health data recording (BP, sugar, heart rate, ECG, BMI)
- ✅ AI risk predictions
- ✅ Symptom checker
- ✅ Personalized diet plans
- ✅ Exercise recommendations
- ✅ Appointment booking
- ✅ Doctor consultation (chat)
- ✅ Prescription access
- ✅ Health history tracking
- ✅ Risk alerts (critical values)

### Doctor Features:
- ✅ Patient list management
- ✅ Patient record access
- ✅ Appointment management
- ✅ Prescription writing
- ✅ Patient communication
- ✅ Critical patient alerts
- ✅ Health analytics
- ✅ AI-assisted recommendations

---

## 📊 Database Relationships

```
User (1) ──► (1) Patient
User (1) ──► (1) Doctor

Patient (1) ──► (Many) HealthData
Patient (1) ──► (Many) Appointments
Patient (1) ──► (Many) Prescriptions
Patient (1) ──► (Many) Messages
Patient (1) ──► (Many) DietPlans
Patient (1) ──► (Many) ExercisePlans

Doctor (1) ──► (Many) Appointments
Doctor (1) ──► (Many) Prescriptions
Doctor (1) ──► (Many) Messages

Appointment (Many-to-Many) Patient ◄──► Doctor
```

---

## 🔐 Security Features Implemented

1. **Password Hashing** - Using Werkzeug
2. **Session Management** - Flask-Login
3. **CSRF Protection** - Flask-WTF
4. **Role-Based Access Control** - @patient_required, @doctor_required
5. **SQL Injection Prevention** - SQLAlchemy ORM
6. **Secure Configuration** - Environment variables

---

## 🛠️ Configuration

### File: `config.py`

```python
# Development (default)
FLASK_ENV=development
DEBUG=True

# Production
FLASK_ENV=production
DEBUG=False
SESSION_COOKIE_SECURE=True

# Database
DATABASE_URL=sqlite:///hospital.db (Development)
DATABASE_URL=mysql+pymysql://user:pass@localhost/hospital_db (Production)
```

---

## 📱 API Endpoints

### Patient Routes
```
GET/POST  /patient/register                           - Register as patient
GET/POST  /patient/login                              - Patient login
GET       /patient/dashboard                          - Patient dashboard
POST      /patient/health-data/enter                  - Record health data
GET       /patient/health-results/<id>                - View AI analysis
GET       /patient/diet-plan                          - View diet plan
GET       /patient/exercise-plan                      - View exercise plan
GET/POST  /patient/appointments                       - Manage appointments
POST      /patient/appointments/book                  - Book appointment
GET       /patient/chat/<doctor_id>                   - Chat with doctor
POST      /patient/api/send-message/<doctor_id>      - Send message
GET       /patient/prescriptions                      - View prescriptions
```

### Doctor Routes
```
GET/POST  /doctor/register                            - Register as doctor
GET/POST  /doctor/login                               - Doctor login
GET       /doctor/dashboard                           - Doctor dashboard
GET       /doctor/patients                            - View patient list
GET       /doctor/patient/<id>                        - View patient record
GET/POST  /doctor/appointments                        - Manage appointments
POST      /doctor/appointments/<id>/approve           - Approve appointment
POST      /doctor/appointments/<id>/reject            - Reject appointment
POST      /doctor/appointments/<id>/complete          - Complete appointment
GET/POST  /doctor/prescription/write/<patient_id>    - Write prescription
GET       /doctor/chat/<patient_id>                   - Chat with patient
POST      /doctor/api/send-message/<patient_id>      - Send message
GET       /doctor/analytics                           - View analytics
```

---

## 🎨 Frontend Stack

- **Bootstrap 5** - Responsive grid & components
- **Font Awesome** - Icons
- **jQuery** - DOM manipulation
- **Jinja2** - Template engine
- **Custom CSS** - Branding & animations

---

## 🧪 Testing the Application

### Test Patient Workflow:
1. Register as patient
2. Record health data (BP: 130/80, Sugar: 120, HR: 80)
3. View AI health analysis
4. Check diet and exercise plans
5. Browse available doctors
6. Book appointment

### Test Doctor Workflow:
1. Register as doctor (specialization: General Practice)
2. Login to dashboard
3. View patient list
4. Click on a patient to see full record
5. Manage appointments (approve/reject)
6. Write prescription for patient
7. Chat with patient

---

## 🚨 Error Handling

- **404 Errors** - Page not found
- **403 Errors** - Access denied (role-based)
- **500 Errors** - Server errors
- **Validation Errors** - Form validation
- **Database Errors** - Connection issues

---

## 📈 Next Steps / Future Enhancements

1. **Wearable Integration** - Sync with smartwatches
2. **Video Consultations** - Real-time video calls
3. **Medical Report OCR** - Image to text extraction
4. **Mental Health Module** - Stress/anxiety assessment
5. **Mobile App** - React Native app
6. **Payment Integration** - Online payments for consultations
7. **Insurance Claims** - Automated claim processing
8. **Advanced Analytics** - Predictive health modeling
9. **Voice Commands** - Speech-to-text features
10. **Telemedicine** - Remote prescriptions

---

## 📞 Support & Troubleshooting

### Issue: Port 5000 already in use
```powershell
python run.py --port 5001
```

### Issue: Database errors
```python
python
>>> from app import create_app, db
>>> app = create_app()
>>> with app.app_context():
...     db.drop_all()
...     db.create_all()
```

### Issue: Import errors
```powershell
pip install --upgrade -r requirements.txt
```

### Issue: Environment variables not loaded
```powershell
# Make sure .env file is in the hospital directory
# And contains: DATABASE_URL=...
```

---

## 🎓 Learning Resources

- Flask: https://flask.palletsprojects.com/
- SQLAlchemy: https://www.sqlalchemy.org/
- Scikit-learn: https://scikit-learn.org/
- Bootstrap: https://getbootstrap.com/
- Jinja2: https://jinja.palletsprojects.com/

---

## 📝 Summary

This is a **production-ready health management system** with:
- ✅ Complete patient-doctor interaction
- ✅ AI-powered health predictions
- ✅ Personalized health recommendations
- ✅ Secure authentication & role-based access
- ✅ Real-time notifications
- ✅ Responsive UI
- ✅ Scalable architecture

**Ready to deploy and extend!** 🚀

---

**Last Updated:** November 2025
**Version:** 1.0.0
