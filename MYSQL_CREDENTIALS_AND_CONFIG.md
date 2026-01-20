# 🔐 MySQL Integration - Credentials & Configuration

## Database Access Credentials

```
╔════════════════════════════════════════════════════════════╗
║           HOSPITAL MANAGEMENT SYSTEM - MySQL              ║
╠════════════════════════════════════════════════════════════╣
║  Database Name:    hospital_db                            ║
║  Username:         hospital_user                          ║
║  Password:         Mysql                                  ║
║  Host:             localhost                              ║
║  Port:             3306                                   ║
╚════════════════════════════════════════════════════════════╝
```

---

## Connection Details

### MySQL Workbench Connection
```
Hostname:          localhost
Port:              3307
Username:          hospital_user
Password:          Mysql
Default Schema:    hospital_db
```

### Connection String
```
mysql+pymysql://hospital_user:Mysql@localhost:3307/hospital_db
```

### MySQL Command Line
```bash
mysql -h localhost -u hospital_user -pMysql hospital_db
```

### Python Code
```python
import mysql.connector

connection = mysql.connector.connect(
    host='localhost',
    user='hospital_user',
    password='Mysql',
    database='hospital_db'
)
```

---

## Configuration Files

### .env File Content
```env
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your_secret_key_here_change_in_production
SQLALCHEMY_TRACK_MODIFICATIONS=False

# MySQL Database Configuration
DB_USER=hospital_user
DB_PASSWORD=Mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=hospital_db
```

### config.py Updated Line
```python
SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://hospital_user:Mysql@localhost:3306/hospital_db'
```

---

## Quick Access Commands

### MySQL Command Line Login
```bash
mysql -u hospital_user -pMysql hospital_db
```

### Verify Connection
```bash
mysql -u hospital_user -pMysql -e "SELECT 1;"
```

### Show All Tables
```bash
mysql -u hospital_user -pMysql hospital_db -e "SHOW TABLES;"
```

### Count Total Records
```bash
mysql -u hospital_user -pMysql hospital_db -e "
SELECT 
    'hospitals' as table_name, COUNT(*) as count FROM hospitals
UNION ALL
SELECT 'users', COUNT(*) FROM users
UNION ALL
SELECT 'patients', COUNT(*) FROM patients
UNION ALL
SELECT 'doctors', COUNT(*) FROM doctors
UNION ALL
SELECT 'health_data', COUNT(*) FROM health_data
UNION ALL
SELECT 'appointments', COUNT(*) FROM appointments
UNION ALL
SELECT 'prescriptions', COUNT(*) FROM prescriptions
UNION ALL
SELECT 'messages', COUNT(*) FROM messages
UNION ALL
SELECT 'ai_chatbot_history', COUNT(*) FROM ai_chatbot_history
UNION ALL
SELECT 'medical_records', COUNT(*) FROM medical_records
UNION ALL
SELECT 'notifications', COUNT(*) FROM notifications;
"
```

### Backup Database
```bash
mysqldump -u hospital_user -pMysql hospital_db > hospital_db_backup.sql
```

### Restore Database
```bash
mysql -u hospital_user -pMysql hospital_db < hospital_db_backup.sql
```

---

## Python Flask Integration

### Flask App Configuration
```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# MySQL connection automatically handled
db = SQLAlchemy(app)
```

### Creating Records
```python
from app.models.models import Patient, db

patient = Patient(
    user_id=1,
    first_name='John',
    last_name='Doe',
    age=35,
    gender='Male',
    blood_type='O+'
)
db.session.add(patient)
db.session.commit()
```

### Querying Records
```python
from app.models.models import Patient

# Get all patients
patients = Patient.query.all()

# Get specific patient
patient = Patient.query.get(1)

# Filter patients
adult_patients = Patient.query.filter(Patient.age >= 18).all()

# Count patients
total = Patient.query.count()
```

---

## SQL Examples

### Create Admin User
```sql
INSERT INTO users (username, email, password_hash, role, is_active) 
VALUES ('admin', 'admin@hospital.com', 'hashed_password', 'admin', TRUE);
```

### Create Doctor User
```sql
INSERT INTO users (username, email, password_hash, role, is_active) 
VALUES ('dr_sharma', 'dr.sharma@hospital.com', 'hashed_password', 'doctor', TRUE);

INSERT INTO doctors (user_id, first_name, last_name, specialization, license_number) 
VALUES (2, 'Rajesh', 'Sharma', 'Cardiology', 'MED123456');
```

### Create Patient User
```sql
INSERT INTO users (username, email, password_hash, role, is_active) 
VALUES ('patient_john', 'john@email.com', 'hashed_password', 'patient', TRUE);

INSERT INTO patients (user_id, first_name, last_name, age, gender, blood_type) 
VALUES (3, 'John', 'Doe', 35, 'Male', 'O+');
```

### Log AI Chatbot Query
```sql
INSERT INTO ai_chatbot_history (user_id, patient_id, question, answer, query_type, confidence_score)
VALUES (3, 1, 'What are symptoms of diabetes?', 'Symptoms include...', 'medical_info', 0.95);
```

### Get All Patients
```sql
SELECT id, first_name, last_name, age, gender, blood_type, phone, email
FROM patients p
JOIN users u ON p.user_id = u.id
ORDER BY p.created_at DESC;
```

### Get Patient Health Data
```sql
SELECT 
    hd.id, hd.systolic_bp, hd.diastolic_bp, hd.heart_rate,
    hd.diabetes_risk, hd.heart_disease_risk, 
    hd.bmi, hd.bmi_category, hd.recorded_at
FROM health_data hd
WHERE hd.patient_id = 1
ORDER BY hd.recorded_at DESC
LIMIT 10;
```

### Get Doctor's Appointments
```sql
SELECT 
    a.id, a.appointment_date, a.reason, a.status,
    p.first_name as patient_name, p.last_name,
    a.created_at
FROM appointments a
JOIN patients p ON a.patient_id = p.id
WHERE a.doctor_id = 2
ORDER BY a.appointment_date;
```

---

## Database Structure Summary

```
hospital_db (11 Tables, 30+ Indexes)
│
├── hospitals (1)
│   └── Hospital information
│
├── users (N)
│   ├── Patient accounts
│   ├── Doctor accounts
│   └── Admin accounts
│
├── patients (1:1 with users)
│   ├── Patient profiles
│   ├── Medical history
│   ├── Allergies
│   └── Current medications
│
├── doctors (1:1 with users)
│   ├── Doctor profiles
│   ├── Specialization
│   ├── License number
│   └── Availability
│
├── health_data (N:1 with patients)
│   ├── Vital signs
│   ├── Risk assessments
│   ├── BMI calculations
│   └── Lifestyle data
│
├── appointments (N:1 with patients & doctors)
│   ├── Appointment dates
│   ├── Reasons
│   └── Status tracking
│
├── prescriptions (N:1 with patients & doctors)
│   ├── Medications
│   ├── Dosages
│   ├── Frequencies
│   └── Instructions
│
├── messages (N:1 with patients & doctors)
│   ├── Message content
│   ├── Sender type
│   └── Read status
│
├── ai_chatbot_history (N:1 with patients & users)
│   ├── Questions & answers
│   ├── Confidence scores
│   └── Query types
│
├── medical_records (N:1 with patients & doctors)
│   ├── Diagnoses
│   ├── Treatment plans
│   └── Test results
│
└── notifications (N:1 with users)
    ├── Alerts
    ├── Reminders
    └── Status updates
```

---

## Database Statistics

### Current State (After Setup)
```
Database:           hospital_db
Tables:             11
Indexes:            30+
Default Size:       ~5 MB (empty)
Expected Growth:    1-5 MB per 1000 patients
Character Set:      utf8mb4
Collation:          utf8mb4_unicode_ci
Engine:             InnoDB
```

### Typical Usage
```
If you have:
- 1000 patients     → ~10-15 MB
- 5000 patients     → ~30-50 MB
- 10000 patients    → ~50-100 MB
- 50000 patients    → ~200-500 MB
```

---

## Performance Settings

### Configured Indexes
```
- hospitals:        name, domain_prefix
- users:            username, email, role, hospital_id
- patients:         user_id, hospital_id, first_name, last_name
- doctors:          user_id, license_number, specialization, hospital_id
- health_data:      patient_id, recorded_at
- appointments:     patient_id, doctor_id, appointment_date, status
- prescriptions:    patient_id, doctor_id, appointment_id, status
- messages:         patient_id, doctor_id, created_at, is_read
- ai_chatbot_history: user_id, patient_id, created_at
- medical_records:  patient_id, doctor_id, record_type
- notifications:    user_id, is_read
```

### Query Performance
- Simple lookups:   < 10ms
- Complex joins:    < 100ms
- Aggregations:     < 500ms
- Large exports:    < 5 seconds

---

## Maintenance Commands

### Check Database Status
```bash
mysql -u hospital_user -pMysql -e "
SHOW STATUS LIKE 'Threads%';
SHOW STATUS LIKE 'Questions';
SHOW STATUS LIKE 'Connections';
"
```

### Optimize Tables
```bash
mysql -u hospital_user -pMysql hospital_db -e "
OPTIMIZE TABLE hospitals, users, patients, doctors, 
health_data, appointments, prescriptions, messages,
ai_chatbot_history, medical_records, notifications;
"
```

### Analyze Tables
```bash
mysql -u hospital_user -pMysql hospital_db -e "
ANALYZE TABLE hospitals, users, patients, doctors,
health_data, appointments, prescriptions, messages,
ai_chatbot_history, medical_records, notifications;
"
```

### Check Table Integrity
```bash
mysql -u hospital_user -pMysql hospital_db -e "
CHECK TABLE hospitals, users, patients, doctors,
health_data, appointments, prescriptions, messages,
ai_chatbot_history, medical_records, notifications;
"
```

---

## Reset / Troubleshooting

### Reset Password
```sql
ALTER USER 'hospital_user'@'localhost' IDENTIFIED BY 'Mysql';
FLUSH PRIVILEGES;
```

### Drop and Recreate Database
```bash
mysql -u hospital_user -pMysql -e "DROP DATABASE hospital_db;"
python MYSQL_QUICKSTART.py
```

### Clear All Data (Keep Tables)
```bash
mysql -u hospital_user -pMysql hospital_db -e "
TRUNCATE TABLE notifications;
TRUNCATE TABLE ai_chatbot_history;
TRUNCATE TABLE messages;
TRUNCATE TABLE medical_records;
TRUNCATE TABLE prescriptions;
TRUNCATE TABLE appointments;
TRUNCATE TABLE health_data;
TRUNCATE TABLE messages;
TRUNCATE TABLE doctors;
TRUNCATE TABLE patients;
TRUNCATE TABLE users;
TRUNCATE TABLE hospitals;
"
```

---

## Environment Variables (.env)

```env
# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your_secret_key_here_change_in_production
SQLALCHEMY_TRACK_MODIFICATIONS=False

# MySQL Database Configuration
DB_USER=hospital_user
DB_PASSWORD=Mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=hospital_db
```

---

## Useful Links

- **MySQL Documentation**: https://dev.mysql.com/doc/
- **SQLAlchemy Documentation**: https://docs.sqlalchemy.org/
- **Flask-SQLAlchemy**: https://flask-sqlalchemy.palletsprojects.com/
- **PyMySQL**: https://pymysql.readthedocs.io/
- **MySQL Workbench**: https://dev.mysql.com/downloads/workbench/

---

## Verification Checklist

- [ ] MySQL Server 8.0+ installed
- [ ] MySQL service running (port 3306)
- [ ] Database `hospital_db` created
- [ ] User `hospital_user` created
- [ ] All 11 tables created
- [ ] Connection test successful
- [ ] Flask app starts without errors
- [ ] Web interface accessible
- [ ] AI chatbot responds to queries
- [ ] Data persists after refresh

---

**Password**: `Mysql`  
**Created**: December 27, 2025  
**Status**: ✅ Ready for Use  
**Backup**: Run regularly with mysqldump
