# AI-Enabled Doctor-Patient Smart Health Management System

A comprehensive web application that connects doctors and patients with AI-powered health monitoring, diagnosis assistance, and personalized health recommendations.

## 🌟 Features

### For Patients
- **Health Data Recording**: Track BP, blood sugar, heart rate, and other vital signs
- **AI Health Analysis**: Get risk predictions for diabetes, heart disease, and hypertension
- **Symptom Checker**: AI-powered symptom analysis with condition suggestions
- **Personalized Diet Plans**: AI-generated meal plans based on health conditions
- **Exercise Recommendations**: Tailored workout plans for your health status
- **Appointment Booking**: Schedule consultations with verified doctors
- **Doctor Chat**: Direct messaging with your healthcare providers
- **Health History**: Track your health improvements over time
- **Prescription Access**: View and manage prescriptions from doctors

### For Doctors
- **Patient Management**: View and manage your patient list
- **Patient Records**: Access complete health history and data
- **Appointment Management**: Accept/reject/complete appointment requests
- **Prescription Writing**: Create and send digital prescriptions
- **Patient Communication**: Chat directly with patients
- **Real-time Alerts**: Get notified of critical patient conditions
- **Analytics Dashboard**: View patient population health statistics
- **Doctor Assistant**: AI tools to help with recommendations and analysis

## 🛠️ Technology Stack

### Frontend
- HTML5, CSS3, JavaScript
- Bootstrap 5
- jQuery
- Font Awesome Icons

### Backend
- Flask 2.3.0
- Python 3.8+
- Flask-Login (Authentication)
- Flask-SQLAlchemy (ORM)

### Database
- MySQL (or SQLite for development)

### AI/ML
- Scikit-learn (Machine Learning Models)
- NLTK (Natural Language Processing)
- Pandas & NumPy

## 📋 Prerequisites

- Python 3.8 or higher
- MySQL Server (optional, SQLite works for development)
- pip (Python package manager)

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
cd hospital
```

### 2. Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# or
source venv/bin/activate  # On macOS/Linux
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Database

**Option A: Using SQLite (Development)**
No configuration needed, it will auto-create.

**Option B: Using MySQL (Production)**
```bash
# Edit .env file
DATABASE_URL=mysql+pymysql://username:password@localhost/hospital_db

# Create database
mysql -u root -p
CREATE DATABASE hospital_db;
EXIT;
```

### 5. Initialize Database
```bash
python
>>> from app import create_app, db
>>> app = create_app()
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

### 6. Run the Application
```bash
python run.py
```

Visit `http://localhost:5000` in your browser.

## 📁 Project Structure

```
hospital/
├── app/
│   ├── __init__.py                 # Flask app initialization
│   ├── models/
│   │   └── models.py               # Database models
│   ├── routes/
│   │   ├── main.py                 # Main routes
│   │   ├── auth.py                 # Authentication routes
│   │   ├── patient.py              # Patient routes
│   │   └── doctor.py               # Doctor routes
│   ├── ml_models/
│   │   └── health_ai.py            # AI/ML models
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css           # Custom styles
│   │   └── js/
│   │       └── main.js             # JavaScript functions
│   └── templates/
│       ├── base.html               # Base template
│       ├── index.html              # Home page
│       ├── patient_login.html      # Patient login
│       ├── patient_register.html   # Patient registration
│       ├── doctor_login.html       # Doctor login
│       ├── doctor_register.html    # Doctor registration
│       ├── patient/                # Patient templates
│       └── doctor/                 # Doctor templates
├── config.py                       # Configuration
├── run.py                          # Entry point
├── requirements.txt                # Dependencies
└── .env                            # Environment variables
```

## 🎯 Default Credentials

After initial setup, you can create accounts for:

### As Patient:
- Go to `/patient/register`
- Fill in your health profile
- Login at `/patient/login`

### As Doctor:
- Go to `/doctor/register`
- Fill in medical credentials
- Admin verification required (currently auto-approved in dev)
- Login at `/doctor/login`

## 🤖 AI/ML Models Included

1. **Diabetes Risk Predictor**
   - Features: Age, BMI, Fasting Sugar, Random Sugar, Family History
   - Output: Risk percentage (0-100%)

2. **Heart Disease Risk Predictor**
   - Features: Age, BP, Heart Rate, Smoking, Cholesterol
   - Output: Risk percentage (0-100%)

3. **Hypertension Risk Predictor**
   - Features: Current BP, Age, BMI
   - Output: Risk percentage (0-100%)

4. **Symptom Checker**
   - NLP-based symptom analysis
   - Suggests possible conditions
   - Provides quick remedies

5. **Diet Plan Generator**
   - Personalizes based on:
     - Diabetes risk
     - BP status
     - BMI category
     - Heart disease risk

6. **Exercise Plan Generator**
   - Customized workout recommendations
   - Based on health conditions
   - Age-appropriate intensity

## 🔒 Security Features

- Password hashing with Werkzeug
- Session management with Flask-Login
- CSRF protection
- SQL injection protection via ORM
- Role-based access control (Patient/Doctor)

## 📊 Database Schema

### Key Tables:
- `users` - Authentication & Role management
- `patients` - Patient profiles & health info
- `doctors` - Doctor profiles & credentials
- `health_data` - Patient health records
- `appointments` - Appointment scheduling
- `prescriptions` - Doctor prescriptions
- `messages` - Chat/messages
- `diet_plans` - Personalized diets
- `exercise_plans` - Exercise routines

## 🌐 API Endpoints

### Patient
- `GET /patient/dashboard` - Dashboard
- `POST /patient/health-data/enter` - Record health data
- `GET /patient/health-results/<id>` - View AI analysis
- `GET /patient/diet-plan` - View diet plan
- `GET /patient/exercise-plan` - View exercise plan
- `GET/POST /patient/appointments` - Manage appointments
- `GET /patient/chat/<doctor_id>` - Chat with doctor
- `POST /patient/api/send-message/<doctor_id>` - Send message

### Doctor
- `GET /doctor/dashboard` - Dashboard
- `GET /doctor/patients` - Patient list
- `GET /doctor/patient/<id>` - View patient details
- `GET/POST /doctor/appointments` - Manage appointments
- `POST /doctor/appointments/<id>/approve` - Approve appointment
- `GET/POST /doctor/prescription/write/<patient_id>` - Write prescription
- `GET /doctor/chat/<patient_id>` - Chat with patient
- `GET /doctor/analytics` - View analytics

## 🚀 Future Enhancements

- [ ] Integration with wearable devices (smartwatches)
- [ ] Voice-based input and commands
- [ ] Video consultations
- [ ] Medical report OCR (image to text)
- [ ] Mental health assessment
- [ ] Mobile app (React Native)
- [ ] Advanced analytics dashboard
- [ ] Integration with health APIs
- [ ] Prescription refill automation
- [ ] Insurance integration

## 📝 Environment Variables

```env
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your_secret_key_here
DATABASE_URL=sqlite:///hospital.db
SQLALCHEMY_TRACK_MODIFICATIONS=False
```

## 🐛 Troubleshooting

### Database errors:
```bash
# Reset database
python
>>> from app import create_app, db
>>> app = create_app()
>>> with app.app_context():
...     db.drop_all()
...     db.create_all()
>>> exit()
```

### Import errors:
```bash
pip install --upgrade -r requirements.txt
```

### Port already in use:
```bash
python run.py --port 5001
```

## 📄 License

This project is open source and available under the MIT License.

## 👥 Contributors

Created as a comprehensive healthcare management solution combining AI/ML with medical practice.

## 📞 Support

For issues and questions, please create an issue in the repository.

---

**Happy coding! 🏥💻**
