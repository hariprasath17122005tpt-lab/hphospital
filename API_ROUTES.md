# 🌐 API Routes & URLs Reference Guide

## Home & Authentication Routes

```
GET  /                                      Home Page (Role Selection)
GET  /about                                 About Page
GET  /contact                               Contact Page
GET  /features                              Features Page
```

## Patient Routes

### Authentication
```
GET  /patient/register                      Patient Registration Page
POST /patient/register                      Submit Patient Registration
GET  /patient/login                         Patient Login Page
POST /patient/login                         Submit Patient Login
GET  /logout                                Logout (Both Roles)
```

### Dashboard & Profile
```
GET  /patient/dashboard                     Patient Dashboard
GET  /patient/profile                       View Patient Profile
GET  /patient/profile/edit                  Edit Profile Page
POST /patient/profile/edit                  Submit Profile Update
```

### Health Data
```
GET  /patient/health-data/enter             Health Data Entry Form
POST /patient/health-data/enter             Submit Health Data
GET  /patient/health-results/<id>           View AI Health Analysis
GET  /patient/health-history                Health History & Trends
```

### Recommendations
```
GET  /patient/diet-plan                     View Personalized Diet Plan
GET  /patient/exercise-plan                 View Personalized Exercise Plan
```

### Appointments
```
GET  /patient/appointments                  View All Appointments
GET  /patient/appointments/book             Appointment Booking Form
POST /patient/appointments/book             Book Appointment
```

### Communication
```
GET  /patient/chat/<doctor_id>              Chat with Doctor
POST /patient/api/send-message/<doctor_id> Send Message (API)
```

### Prescriptions
```
GET  /patient/prescriptions                 View All Prescriptions
```

---

## Doctor Routes

### Authentication
```
GET  /doctor/register                       Doctor Registration Page
POST /doctor/register                       Submit Doctor Registration
GET  /doctor/login                          Doctor Login Page
POST /doctor/login                          Submit Doctor Login
GET  /logout                                Logout (Both Roles)
```

### Dashboard & Profile
```
GET  /doctor/dashboard                      Doctor Dashboard
GET  /doctor/profile                        View Doctor Profile
GET  /doctor/profile/edit                   Edit Profile Page
POST /doctor/profile/edit                   Submit Profile Update
```

### Patient Management
```
GET  /doctor/patients                       View Patient List
GET  /doctor/patient/<id>                   View Patient Detailed Record
```

### Appointments
```
GET  /doctor/appointments                   View Appointments (all/filtered)
POST /doctor/appointments/<id>/approve      Approve Appointment
POST /doctor/appointments/<id>/reject       Reject Appointment
POST /doctor/appointments/<id>/complete     Complete Appointment
```

### Prescriptions & Medical Records
```
GET  /doctor/prescription/write/<patient_id>       Prescription Form
POST /doctor/prescription/write/<patient_id>       Submit Prescription
```

### Communication
```
GET  /doctor/chat/<patient_id>              Chat with Patient
POST /doctor/api/send-message/<patient_id> Send Message (API)
```

### Analytics
```
GET  /doctor/analytics                      Analytics Dashboard
```

---

## API Endpoints (JSON Responses)

### General APIs
```
GET  /api/health-status                     API Health Check
```

### Patient APIs
```
POST /patient/api/send-message/<doctor_id>
Content-Type: application/json
Body: { "message": "Hello doctor" }
Response: { "success": true, "message_id": 123 }
```

### Doctor APIs
```
POST /doctor/api/send-message/<patient_id>
Content-Type: application/json
Body: { "message": "Take this medication" }
Response: { "success": true, "message_id": 124 }

POST /doctor/appointments/<id>/approve
Response: { "success": true }

POST /doctor/appointments/<id>/reject
Response: { "success": true }

POST /doctor/appointments/<id>/complete
Response: { "success": true }
```

---

## Query Parameters

### Appointments Filtering
```
GET /doctor/appointments?status=pending      Filter by status
GET /doctor/appointments?status=confirmed    
GET /doctor/appointments?status=completed    
GET /doctor/appointments?status=all          All appointments
```

---

## URL Pattern Summary

| Resource | Patient URL | Doctor URL |
|----------|-------------|-----------|
| Dashboard | `/patient/dashboard` | `/doctor/dashboard` |
| Profile | `/patient/profile` | `/doctor/profile` |
| Patients | - | `/doctor/patients` |
| Health Data | `/patient/health-data/enter` | - |
| Appointments | `/patient/appointments` | `/doctor/appointments` |
| Chat | `/patient/chat/<doctor_id>` | `/doctor/chat/<patient_id>` |
| Analytics | - | `/doctor/analytics` |

---

## Response Status Codes

```
200 OK                  Request successful
201 Created             Resource created
302 Found               Redirect
400 Bad Request         Invalid input
403 Forbidden           Access denied (role)
404 Not Found           Resource not found
500 Server Error        Server error
```

---

## Error Handling

All routes include error handling:
```python
- 404: Page not found
- 403: Access denied (role-based)
- 500: Server error
- Custom validation errors
```

---

## Session & Authentication

- Sessions managed by Flask-Login
- Login required for most routes (via @login_required decorator)
- Role checks via @patient_required and @doctor_required decorators

---

## Form Data Formats

### Health Data Form
```
POST /patient/health-data/enter
Data:
- systolic_bp (integer)
- diastolic_bp (integer)
- fasting_sugar (float)
- random_sugar (float)
- heart_rate (integer)
- symptoms (text)
- exercise_minutes (integer)
- sleep_hours (float)
- stress_level (select: Low/Medium/High)
- smoking (checkbox)
- alcohol (checkbox)
```

### Appointment Booking Form
```
POST /patient/appointments/book
Data:
- doctor_id (integer)
- appointment_date (datetime)
- reason (text)
```

### Prescription Form
```
POST /doctor/prescription/write/<patient_id>
Data:
- appointment_id (integer, optional)
- medicines (text)
- dosage (text)
- frequency (text)
- duration (text)
- instructions (text)
- diet_recommendations (text)
- exercise_recommendations (text)
```

---

## Quick Reference Table

### Patient Login Credentials (Sample)
```
Username: john_patient
Password: password123
Email: john@patient.com

Username: sarah_patient
Password: password123
Email: sarah@patient.com

Username: mike_patient
Password: password123
Email: mike@patient.com
```

### Doctor Login Credentials (Sample)
```
Username: dr_smith
Password: password123
Email: dr.smith@hospital.com
Specialization: Cardiology

Username: dr_williams
Password: password123
Email: dr.williams@hospital.com
Specialization: Endocrinology

Username: dr_brown
Password: password123
Email: dr.brown@hospital.com
Specialization: General Practice
```

---

## Navigation Flow

### Patient Flow
```
Home → Register → Login → Dashboard → Record Health → View Analysis → 
Book Appointment → Chat with Doctor → View Prescription → Track Progress
```

### Doctor Flow
```
Home → Register → Login → Dashboard → View Patients → 
Manage Appointments → Write Prescription → Chat with Patient → View Analytics
```

---

## Important Notes

1. All date/time parameters use ISO format: `YYYY-MM-DDTHH:MM`
2. All passwords must be minimum 6 characters
3. All email addresses must be unique
4. Doctor license numbers must be unique
5. Patient ages must be between 1-120
6. All decimal values (BP, sugar, etc.) use standard units
7. Messages support up to 1000 characters
8. Prescriptions are auto-timestamped

---

**Last Updated:** November 2025
**Version:** 1.0.0
