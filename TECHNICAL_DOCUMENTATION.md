# 🔧 TECHNICAL DOCUMENTATION - Hospital AI System

**Last Updated:** November 14, 2025
**Version:** 1.0 Production

---

## 📐 ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER (Frontend)                      │
│  Bootstrap 5 | Jinja2 Templates | jQuery | Responsive Design   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    HTTP/HTTPS
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                  APPLICATION LAYER (Flask)                       │
│  Routes | Authentication | Request Handling | Error Management  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    SQLAlchemy ORM
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    DATA LAYER (Database)                         │
│  SQLite (Dev) | MySQL/PostgreSQL Ready | 9 Tables | Relationships
└─────────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
   ┌─────────┐      ┌─────────────┐    ┌──────────────┐
   │ Health  │      │  Medical    │    │ Messaging &  │
   │   AI    │      │   Image     │    │ Chat System  │
   │ Models  │      │  Analyzer   │    │              │
   └─────────┘      └─────────────┘    └──────────────┘
                           │
                    MedGemma-4B
                   Hugging Face
```

---

## 📁 PROJECT STRUCTURE - DETAILED

```
hospital/
│
├── app/                                    # Main application package
│   ├── __init__.py                         # Flask app factory
│   │
│   ├── models/
│   │   └── models.py                       # SQLAlchemy ORM models (9 tables)
│   │       ├── User (id, username, email, password_hash, role, created_at)
│   │       ├── Patient (id, user_id, age, gender, phone, medical_history, allergies)
│   │       ├── Doctor (id, user_id, specialization, license_number, verified)
│   │       ├── HealthData (id, patient_id, vital signs, calculated risks)
│   │       ├── Appointment (id, patient_id, doctor_id, date, time, reason, status)
│   │       ├── Prescription (id, doctor_id, patient_id, medications, instructions)
│   │       ├── Message (id, doctor_id, patient_id, message, sender_type, is_read)
│   │       ├── DietPlan (id, patient_id, nutrition data, meals)
│   │       └── ExercisePlan (id, patient_id, activities, duration, frequency)
│   │
│   ├── routes/                             # Flask blueprints
│   │   ├── auth.py (340 lines)
│   │   │   ├── Patient registration & login
│   │   │   ├── Doctor registration & login
│   │   │   ├── Logout functionality
│   │   │   ├── @patient_required decorator
│   │   │   └── @doctor_required decorator
│   │   │
│   │   ├── main.py (180 lines)
│   │   │   ├── GET / - Home page
│   │   │   ├── GET /about - About page
│   │   │   └── Static page routes
│   │   │
│   │   ├── patient.py (440+ lines - ENHANCED)
│   │   │   ├── @patient_bp.route('/dashboard')
│   │   │   ├── @patient_bp.route('/profile')
│   │   │   ├── @patient_bp.route('/profile/edit', methods=['POST'])
│   │   │   ├── @patient_bp.route('/health-data/enter', methods=['GET', 'POST'])
│   │   │   ├── @patient_bp.route('/health-results/<health_id>')
│   │   │   ├── @patient_bp.route('/diet-plan')
│   │   │   ├── @patient_bp.route('/exercise-plan')
│   │   │   ├── @patient_bp.route('/appointments')
│   │   │   ├── @patient_bp.route('/appointments/book', methods=['GET', 'POST']) - ENHANCED
│   │   │   ├── @patient_bp.route('/prescriptions')
│   │   │   ├── @patient_bp.route('/chat/<doctor_id>')
│   │   │   ├── @patient_bp.route('/api/send-message/<doctor_id>', methods=['POST'])
│   │   │   ├── @patient_bp.route('/health-history')
│   │   │   ├── @patient_bp.route('/upload-medical-image', methods=['GET', 'POST']) - NEW
│   │   │   └── @patient_bp.route('/medical-images') - NEW
│   │   │
│   │   └── doctor.py (350+ lines - ENHANCED)
│   │       ├── @doctor_bp.route('/dashboard')
│   │       ├── @doctor_bp.route('/patients') - ENHANCED
│   │       ├── @doctor_bp.route('/patient/<patient_id>')
│   │       ├── @doctor_bp.route('/appointments') - ENHANCED
│   │       ├── @doctor_bp.route('/write-prescription/<patient_id>', methods=['POST'])
│   │       ├── @doctor_bp.route('/chat/<patient_id>')
│   │       ├── @doctor_bp.route('/update-appointment-status', methods=['POST'])
│   │       └── @doctor_bp.route('/analytics') - ENHANCED
│   │
│   ├── ml_models/                          # Machine Learning models
│   │   ├── health_ai.py (400+ lines)
│   │   │   ├── class HealthRiskPredictor
│   │   │   │   ├── predict_diabetes_risk()
│   │   │   │   ├── predict_heart_disease_risk()
│   │   │   │   ├── predict_hypertension_risk()
│   │   │   │   ├── calculate_bmi()
│   │   │   │   └── get_bmi_category()
│   │   │   ├── class SymptomChecker
│   │   │   │   └── analyze_symptoms()
│   │   │   ├── class DietPlanGenerator
│   │   │   │   └── generate_plan()
│   │   │   └── class ExercisePlanGenerator
│   │   │       └── generate_plan()
│   │   │
│   │   └── medical_image_analyzer.py (550+ lines - NEW)
│   │       └── class MedicalImageAnalyzer
│   │           ├── __init__() - Load MedGemma-4B model
│   │           ├── analyze_medical_image() - Main analysis method
│   │           ├── _analyze_with_medgemma() - Transformer-based analysis
│   │           ├── _analyze_locally() - Fallback analysis
│   │           ├── validate_medical_image() - File validation
│   │           ├── get_supported_formats() - JPEG, PNG, TIFF, BMP, GIF
│   │           └── _extract_image_properties() - Meta information
│   │
│   ├── templates/                          # Jinja2 templates
│   │   ├── base.html (200+ lines)
│   │   │   ├── Navigation bar (responsive)
│   │   │   ├── Flash message display
│   │   │   ├── Bootstrap grid layout
│   │   │   └── CSS/JS includes
│   │   │
│   │   ├── index.html - Home page
│   │   ├── doctor_login.html
│   │   ├── doctor_register.html
│   │   ├── patient_login.html
│   │   ├── patient_register.html
│   │   │
│   │   ├── patient/
│   │   │   ├── dashboard.html (230 lines - ENHANCED)
│   │   │   │   ├── Health status cards
│   │   │   │   ├── Latest health data display
│   │   │   │   ├── Risk score progress bars
│   │   │   │   ├── Upcoming appointments
│   │   │   │   └── Quick action buttons (including NEW AI Image button)
│   │   │   ├── profile.html (NEW)
│   │   │   ├── appointments.html (NEW)
│   │   │   ├── book_appointment.html (NEW)
│   │   │   ├── upload_medical_image.html (NEW)
│   │   │   ├── image_analysis_results.html (NEW)
│   │   │   ├── enter_health_data.html
│   │   │   ├── health_results.html
│   │   │   ├── diet_plan.html
│   │   │   ├── exercise_plan.html
│   │   │   └── [other existing templates]
│   │   │
│   │   └── doctor/
│   │       ├── dashboard.html
│   │       ├── patient_list.html (NEW)
│   │       ├── appointments.html (NEW)
│   │       ├── analytics.html (NEW)
│   │       └── [other existing templates]
│   │
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css (280+ lines custom CSS)
│   │   │       ├── Card styling
│   │   │       ├── Progress bars
│   │   │       ├── Responsive grid
│   │   │       ├── Button styling
│   │   │       └── Color schemes
│   │   │
│   │   └── js/
│   │       └── main.js (150+ lines)
│   │           ├── Form validation
│   │           ├── Progress bar initialization
│   │           ├── Event listeners
│   │           └── Client-side interactions
│   │
│   ├── uploads/                            # File storage (NEW)
│   │   └── medical_images/
│   │       └── [uploaded medical images]
│   │
│   └── __pycache__/                        # Python cache
│
├── config.py (100+ lines)
│   ├── SECRET_KEY configuration
│   ├── SQLALCHEMY_DATABASE_URI
│   ├── Flask configuration
│   └── Debug settings
│
├── run.py (50 lines)
│   └── Application entry point with debug mode
│
├── init_db.py (50 lines)
│   └── Database initialization script
│
├── requirements.txt (20+ packages)
│   ├── Flask==2.3.0
│   ├── SQLAlchemy==2.0.0
│   ├── Flask-Login
│   ├── Flask-WTF
│   ├── Werkzeug
│   ├── Pillow
│   ├── transformers
│   ├── torch
│   ├── bitsandbytes
│   ├── scikit-learn
│   ├── numpy
│   ├── pandas
│   ├── nltk
│   └── [others]
│
└── Documentation Files
    ├── README.md
    ├── SETUP_GUIDE.md
    ├── API_ROUTES.md
    ├── PROJECT_SUMMARY.md
    ├── COMPLETE_IMPLEMENTATION_STATUS.md (NEW)
    └── USER_QUICK_START_GUIDE.md (NEW)
```

---

## 🔌 API ENDPOINTS REFERENCE

### Authentication Routes (`/auth.py`)
```python
POST /patient/register      # Register new patient
POST /patient/login         # Login patient
POST /doctor/register       # Register new doctor
POST /doctor/login          # Login doctor
GET  /logout                # Logout user
```

### Patient Routes (`/patient.py`)
```python
GET  /patient/dashboard                      # Dashboard overview
GET  /patient/profile                        # View profile
POST /patient/profile/edit                   # Edit profile
GET  /patient/health-data/enter              # Enter health data form
POST /patient/health-data/enter              # Submit health data
GET  /patient/health-results/<id>            # View analysis results
GET  /patient/diet-plan                      # Get diet plan
GET  /patient/exercise-plan                  # Get exercise plan
GET  /patient/appointments                   # View appointments
GET  /patient/appointments/book              # Book appointment form
POST /patient/appointments/book              # Submit appointment (ENHANCED)
GET  /patient/prescriptions                  # View prescriptions
GET  /patient/chat/<doctor_id>               # Chat interface
POST /patient/api/send-message/<id>          # Send message
GET  /patient/health-history                 # Health history
GET  /patient/upload-medical-image           # Upload form (NEW)
POST /patient/upload-medical-image           # Submit upload (NEW)
GET  /patient/medical-images                 # View uploads (NEW)
```

### Doctor Routes (`/doctor.py`)
```python
GET  /doctor/dashboard                       # Dashboard overview
GET  /doctor/patients                        # Patient list (ENHANCED)
GET  /doctor/patient/<id>                    # View patient details
GET  /doctor/appointments                    # Appointment management (ENHANCED)
POST /doctor/write-prescription/<id>         # Write prescription
GET  /doctor/chat/<patient_id>               # Chat interface
POST /doctor/update-appointment-status       # Update appointment
GET  /doctor/analytics                       # Analytics dashboard (ENHANCED)
```

---

## 🗄️ DATABASE SCHEMA

### User Table
```sql
CREATE TABLE user (
    id INTEGER PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20),  -- 'patient' or 'doctor'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

### Patient Table
```sql
CREATE TABLE patient (
    id INTEGER PRIMARY KEY,
    user_id INTEGER FOREIGN KEY,
    age INTEGER,
    gender VARCHAR(20),
    phone VARCHAR(20),
    medical_history TEXT,
    allergies TEXT
)
```

### HealthData Table
```sql
CREATE TABLE health_data (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER FOREIGN KEY,
    systolic_bp INTEGER,
    diastolic_bp INTEGER,
    heart_rate INTEGER,
    fasting_sugar INTEGER,
    random_sugar INTEGER,
    bmi FLOAT,
    diabetes_risk FLOAT,
    heart_disease_risk FLOAT,
    hypertension_risk FLOAT,
    bmi_category VARCHAR(20),
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

### Appointment Table
```sql
CREATE TABLE appointment (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER FOREIGN KEY,
    doctor_id INTEGER FOREIGN KEY,
    date DATE,
    time TIME,
    reason TEXT,
    status VARCHAR(20),  -- 'pending', 'confirmed', 'completed', 'cancelled'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

[Additional tables: Prescription, Message, DietPlan, ExercisePlan, Doctor]

---

## 🤖 AI MODELS INTEGRATION

### 1. Medical Image Analyzer (NEW)
**File:** `app/ml_models/medical_image_analyzer.py`

**Model:** Google MedGemma-4B
- **Type:** Multimodal (Text + Image)
- **Parameters:** 4 Billion
- **Quantization:** 4-bit (bitsandbytes)
- **Framework:** Hugging Face Transformers + PyTorch

**Supported Image Types:**
```python
SUPPORTED_TYPES = {
    'xray': 'X-Ray Analysis (Chest, Bone, Dental)',
    'ct': 'CT Scan Analysis',
    'mri': 'MRI Scan Analysis',
    'pathology': 'Pathology Slide Analysis',
    'dermatology': 'Dermatology Image Analysis',
    'ultrasound': 'Ultrasound Analysis',
    'ecg': 'ECG/Cardiac Analysis'
}
```

**Usage Example:**
```python
from app.ml_models.medical_image_analyzer import MedicalImageAnalyzer

analyzer = MedicalImageAnalyzer()
results = analyzer.analyze_medical_image(
    image_path='path/to/xray.jpg',
    image_type='xray',
    clinical_context='Patient reports chest pain'
)

# Returns dict with:
# - findings: str
# - observations: str
# - recommendations: list
# - confidence_score: float (0-100)
# - risk_level: str ('Low', 'Medium', 'High')
# - detected_conditions: list
```

### 2. Health Risk Predictor
**File:** `app/ml_models/health_ai.py`

**Models Included:**
- Diabetes Risk Prediction
- Heart Disease Risk Prediction
- Hypertension Risk Prediction
- BMI Calculation & Classification
- Symptom Checking (NLP)
- Diet Plan Generation
- Exercise Plan Generation

---

## 🔐 SECURITY IMPLEMENTATION

### 1. Authentication
```python
# Using Flask-Login
@login_required                    # Require login
@patient_required                  # Require patient role
@doctor_required                   # Require doctor role

# Password hashing
from werkzeug.security import generate_password_hash, check_password_hash
```

### 2. File Upload Security
```python
from werkzeug.utils import secure_filename
import os

# File validation
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'tiff', 'bmp', 'gif'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
```

### 3. SQL Injection Prevention
```python
# Using SQLAlchemy ORM (parameterized queries)
user = User.query.filter_by(username=username).first()
```

### 4. XSS Protection
```python
# Jinja2 automatic escaping
{{ user_input }}  # Automatically escaped
{{ user_input|safe }}  # Only when explicitly marked safe
```

### 5. CSRF Protection
```python
# Flask-WTF
from flask_wtf.csrf import generate_csrf
```

---

## 📊 ERROR HANDLING

### Global Error Handlers
```python
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
```

### Form Validation
```python
# Client-side (Bootstrap)
<form class="needs-validation">

# Server-side
if not form.validate_on_submit():
    flash('Validation error', 'danger')
```

---

## 🚀 DEPLOYMENT CONSIDERATIONS

### Current Setup (Development)
```python
app = Flask(__name__)
app.config['DEBUG'] = True
app.run(debug=True, host='0.0.0.0', port=5000)
```

### Production Setup (Recommended)
```bash
# Use Gunicorn/uWSGI
gunicorn -w 4 -b 0.0.0.0:5000 run:app

# Use production database (PostgreSQL/MySQL)
DATABASE_URL = 'postgresql://user:password@localhost/hospital'

# Use HTTPS
SSL_CONTEXT = ('cert.pem', 'key.pem')

# Use Redis for caching
CACHE_TYPE = 'redis'
CACHE_REDIS_URL = 'redis://localhost:6379/0'
```

---

## 📈 PERFORMANCE OPTIMIZATION

### 1. Database Optimization
```python
# Use lazy loading where appropriate
db.session.options(joinedload(...))

# Index frequently queried fields
@index('idx_patient_user_id')
user_id = db.Column(...)
```

### 2. Image Processing Optimization
```python
# 4-bit quantization for MedGemma
BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_quant_type='nf4'
)
```

### 3. Caching Strategy
```python
# Cache AI predictions
@cache.cached(timeout=3600, key_prefix='predictions')
def predict_risk(patient_id):
    ...
```

---

## 🧪 TESTING APPROACH

### Unit Tests
```python
def test_patient_registration():
    response = client.post('/patient/register', data={...})
    assert response.status_code == 200

def test_health_data_entry():
    response = client.post('/patient/health-data/enter', data={...})
    assert HealthData.query.count() == 1
```

### Integration Tests
```python
def test_appointment_workflow():
    # Register patient and doctor
    # Create appointment
    # Verify it appears in both dashboards
```

### Load Testing
```bash
# Use Apache Bench or similar
ab -n 1000 -c 10 http://localhost:5000/
```

---

## 📚 DEPENDENCIES

### Core Framework
- `Flask==2.3.0` - Web framework
- `SQLAlchemy==2.0.0` - ORM
- `Flask-Login` - Authentication
- `Flask-WTF` - Form validation & CSRF
- `Werkzeug` - Utilities

### AI/ML
- `transformers` - Hugging Face models
- `torch` - Deep learning
- `bitsandbytes` - Quantization
- `scikit-learn` - Machine learning
- `numpy` - Numerical computing
- `pandas` - Data manipulation
- `nltk` - NLP

### Image Processing
- `Pillow` - Image library

### Database
- `SQLite` - Development (automatic)
- `PyMySQL` - MySQL support
- `psycopg2` - PostgreSQL support

---

## 🔍 MONITORING & LOGGING

### Application Logging
```python
import logging

logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)
```

### Database Query Monitoring
```python
from sqlalchemy import event

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    logger.info(f"Query: {statement}")
```

---

## 📞 SUPPORT & MAINTENANCE

### Regular Maintenance Tasks
1. Database optimization (indexes, cleanup)
2. Security updates (dependencies, patches)
3. Performance monitoring
4. User feedback integration
5. Model retraining/updating
6. Backup and recovery testing

### Common Issues & Solutions
- See TROUBLESHOOTING.md for detailed solutions
- Check logs in `app.log`
- Verify database connectivity
- Test API endpoints with Postman

---

**Document Version:** 1.0
**Created:** November 14, 2025
**Status:** Complete
