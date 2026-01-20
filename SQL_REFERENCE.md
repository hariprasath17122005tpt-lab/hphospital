# 🏥 SQL Code Reference - Hospital Management System

## Complete SQL Documentation

---

## Database Configuration

```sql
-- Database: hospital_db
-- User: hospital_user
-- Password: Mysql
-- Host: localhost
-- Port: 3306
```

---

## User Management Queries

### Create Admin User
```sql
-- Create user account
INSERT INTO users (username, email, password_hash, role, hospital_id, is_active) 
VALUES ('admin_user', 'admin@hospital.com', 'hashed_password', 'admin', 1, TRUE);
```

### Create Doctor User
```sql
-- Create doctor account
INSERT INTO users (username, email, password_hash, role, hospital_id, is_active) 
VALUES ('dr_sharma', 'dr.sharma@hospital.com', 'hashed_password', 'doctor', 1, TRUE);

-- Create doctor profile
INSERT INTO doctors (user_id, first_name, last_name, specialization, license_number, hospital_id, verified) 
VALUES (2, 'Rajesh', 'Sharma', 'Cardiology', 'MED123456', 1, TRUE);
```

### Create Patient User
```sql
-- Create patient account
INSERT INTO users (username, email, password_hash, role, hospital_id, is_active) 
VALUES ('patient_john', 'john@email.com', 'hashed_password', 'patient', 1, TRUE);

-- Create patient profile
INSERT INTO patients (user_id, hospital_id, first_name, last_name, age, gender, blood_type, phone) 
VALUES (3, 1, 'John', 'Doe', 35, 'Male', 'O+', '9876543210');
```

### Get All Users
```sql
SELECT id, username, email, role, is_active, created_at FROM users ORDER BY created_at DESC;
```

### Update User Password
```sql
UPDATE users SET password_hash = 'new_hash' WHERE username = 'admin_user';
```

### Deactivate User
```sql
UPDATE users SET is_active = FALSE WHERE id = 5;
```

---

## Patient Management Queries

### Get All Patients with Contact Info
```sql
SELECT p.id, p.first_name, p.last_name, p.age, p.gender, p.blood_type, p.phone, u.email
FROM patients p
JOIN users u ON p.user_id = u.id
ORDER BY p.created_at DESC;
```

### Get Patient Medical History
```sql
SELECT 
    p.first_name, p.last_name,
    p.medical_history,
    p.allergies,
    p.current_medications,
    p.blood_type
FROM patients p
WHERE p.id = 1;
```

### Update Patient Information
```sql
UPDATE patients 
SET 
    medical_history = 'Updated history',
    allergies = 'Penicillin',
    current_medications = 'Aspirin 100mg daily'
WHERE id = 1;
```

### Get Patient Health Data
```sql
SELECT 
    hd.id,
    hd.systolic_bp, hd.diastolic_bp,
    hd.heart_rate,
    hd.diabetes_risk,
    hd.heart_disease_risk,
    hd.bmi, hd.bmi_category,
    hd.recorded_at
FROM health_data hd
WHERE hd.patient_id = 1
ORDER BY hd.recorded_at DESC
LIMIT 10;
```

### Record Patient Health Data
```sql
INSERT INTO health_data (
    patient_id, systolic_bp, diastolic_bp, heart_rate,
    fasting_sugar, diabetes_risk, heart_disease_risk,
    bmi, bmi_category, stress_level
) VALUES (
    1, 120, 80, 72,
    95, 15.5, 8.2,
    24.5, 'Normal', 'Medium'
);
```

---

## Doctor Management Queries

### Get All Doctors with Specialization
```sql
SELECT 
    d.id, d.first_name, d.last_name,
    d.specialization, d.qualification,
    d.experience_years, d.consultation_fee,
    d.verified, u.email
FROM doctors d
JOIN users u ON d.user_id = u.id
ORDER BY d.specialization, d.last_name;
```

### Get Verified Doctors
```sql
SELECT * FROM doctors WHERE verified = TRUE ORDER BY specialization;
```

### Get Doctor Availability
```sql
SELECT id, first_name, last_name, specialization, availability_hours
FROM doctors
WHERE hospital_id = 1 AND verified = TRUE;
```

### Update Doctor Information
```sql
UPDATE doctors 
SET 
    specialization = 'Orthopedic Surgery',
    consultation_fee = 500,
    availability_hours = 'Mon-Fri 9AM-5PM, Sat 9AM-1PM'
WHERE id = 1;
```

### Verify Doctor
```sql
UPDATE doctors SET verified = TRUE WHERE license_number = 'MED123456';
```

---

## Appointment Management Queries

### Book Appointment
```sql
INSERT INTO appointments (patient_id, doctor_id, appointment_date, reason, status)
VALUES (1, 2, '2025-12-30 14:00:00', 'Regular checkup', 'pending');
```

### Get Appointments for Patient
```sql
SELECT 
    a.id, a.appointment_date, a.reason, a.status,
    d.first_name, d.last_name, d.specialization,
    a.created_at
FROM appointments a
JOIN doctors d ON a.doctor_id = d.id
WHERE a.patient_id = 1
ORDER BY a.appointment_date DESC;
```

### Get Appointments for Doctor
```sql
SELECT 
    a.id, a.appointment_date, a.reason, a.status,
    p.first_name, p.last_name, p.phone,
    a.created_at
FROM appointments a
JOIN patients p ON a.patient_id = p.id
WHERE a.doctor_id = 2
ORDER BY a.appointment_date;
```

### Get Today's Appointments
```sql
SELECT 
    a.id, a.appointment_date, a.reason, a.status,
    p.first_name as patient_name, d.first_name as doctor_name
FROM appointments a
JOIN patients p ON a.patient_id = p.id
JOIN doctors d ON a.doctor_id = d.id
WHERE DATE(a.appointment_date) = CURDATE()
ORDER BY a.appointment_date;
```

### Update Appointment Status
```sql
UPDATE appointments 
SET status = 'completed', notes = 'Patient doing well'
WHERE id = 5;
```

### Cancel Appointment
```sql
UPDATE appointments SET status = 'cancelled' WHERE id = 5;
```

---

## Prescription Management Queries

### Create Prescription
```sql
INSERT INTO prescriptions (
    patient_id, doctor_id, appointment_id,
    medicine_name, dosage, frequency, duration_days, instructions
) VALUES (
    1, 2, 5,
    'Amoxicillin', '500mg', '3 times daily', 7, 'Take with food'
);
```

### Get Patient Prescriptions
```sql
SELECT 
    p.id, p.medicine_name, p.dosage, p.frequency,
    p.duration_days, p.instructions,
    p.prescribed_at, p.status,
    d.first_name, d.last_name
FROM prescriptions p
JOIN doctors d ON p.doctor_id = d.id
WHERE p.patient_id = 1 AND p.status = 'active'
ORDER BY p.prescribed_at DESC;
```

### Get Active Prescriptions
```sql
SELECT 
    p.id, p.patient_id, p.medicine_name,
    p.dosage, p.frequency, p.prescribed_at,
    pat.first_name, pat.last_name
FROM prescriptions p
JOIN patients pat ON p.patient_id = pat.id
WHERE p.status = 'active' AND p.expires_at > NOW()
ORDER BY p.prescribed_at DESC;
```

### Update Prescription Status
```sql
UPDATE prescriptions 
SET status = 'completed'
WHERE id = 3 AND expires_at < NOW();
```

---

## AI Chatbot Queries

### Log Chatbot Interaction
```sql
INSERT INTO ai_chatbot_history (user_id, patient_id, question, answer, query_type, confidence_score)
VALUES (3, 1, 'What are symptoms of diabetes?', 'Symptoms include...', 'medical_info', 0.95);
```

### Get User Chat History
```sql
SELECT 
    ch.id, ch.question, ch.answer,
    ch.query_type, ch.confidence_score,
    ch.created_at
FROM ai_chatbot_history ch
WHERE ch.patient_id = 1
ORDER BY ch.created_at DESC
LIMIT 20;
```

### Get Popular Chatbot Queries
```sql
SELECT 
    query_type, COUNT(*) as count,
    AVG(confidence_score) as avg_confidence
FROM ai_chatbot_history
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY query_type
ORDER BY count DESC;
```

### Get Low Confidence Responses
```sql
SELECT id, question, answer, confidence_score, created_at
FROM ai_chatbot_history
WHERE confidence_score < 0.7
ORDER BY confidence_score ASC;
```

---

## Medical Records Queries

### Create Medical Record
```sql
INSERT INTO medical_records (
    patient_id, doctor_id, record_type, record_title,
    record_description, diagnosis, treatment_plan
) VALUES (
    1, 2, 'Lab Report', 'Blood Test Results',
    'Complete blood count test',
    'Normal results, no abnormalities',
    'Continue current medications'
);
```

### Get Patient Medical Records
```sql
SELECT 
    m.id, m.record_type, m.record_title,
    m.record_description, m.diagnosis,
    m.created_at, d.first_name, d.last_name
FROM medical_records m
JOIN doctors d ON m.doctor_id = d.id
WHERE m.patient_id = 1
ORDER BY m.created_at DESC;
```

### Search Medical Records
```sql
SELECT * FROM medical_records
WHERE patient_id = 1 AND record_type = 'Lab Report'
ORDER BY created_at DESC;
```

---

## Doctor-Patient Messaging Queries

### Send Message
```sql
INSERT INTO messages (patient_id, doctor_id, message_text, sender_type)
VALUES (1, 2, 'Hi doctor, I have been experiencing headaches', 'patient');
```

### Get Conversation History
```sql
SELECT 
    m.id, m.message_text, m.sender_type,
    m.created_at, m.is_read
FROM messages m
WHERE (m.patient_id = 1 AND m.doctor_id = 2)
ORDER BY m.created_at DESC;
```

### Get Unread Messages for User
```sql
SELECT COUNT(*) as unread_count
FROM messages
WHERE doctor_id = 2 AND is_read = FALSE;
```

### Mark Messages as Read
```sql
UPDATE messages 
SET is_read = TRUE
WHERE doctor_id = 2 AND is_read = FALSE;
```

---

## Hospital Management Queries

### Get Hospital Info
```sql
SELECT * FROM hospitals WHERE id = 1;
```

### Get Hospital Statistics
```sql
SELECT 
    h.name,
    (SELECT COUNT(*) FROM patients WHERE hospital_id = h.id) as total_patients,
    (SELECT COUNT(*) FROM doctors WHERE hospital_id = h.id AND verified = TRUE) as total_doctors,
    (SELECT COUNT(*) FROM appointments WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) 
     AND patient_id IN (SELECT id FROM patients WHERE hospital_id = h.id)) as appointments_this_month
FROM hospitals h
WHERE h.id = 1;
```

---

## Notifications Queries

### Create Notification
```sql
INSERT INTO notifications (user_id, title, message, notification_type)
VALUES (3, 'Appointment Reminder', 'Your appointment with Dr. Sharma is tomorrow at 2 PM', 'reminder');
```

### Get User Notifications
```sql
SELECT id, title, message, notification_type, is_read, created_at
FROM notifications
WHERE user_id = 3
ORDER BY created_at DESC
LIMIT 10;
```

### Mark Notification as Read
```sql
UPDATE notifications SET is_read = TRUE WHERE id = 5;
```

---

## Statistical Queries

### Patient Statistics
```sql
SELECT 
    COUNT(*) as total_patients,
    AVG(age) as avg_age,
    COUNT(CASE WHEN gender = 'Male' THEN 1 END) as male_count,
    COUNT(CASE WHEN gender = 'Female' THEN 1 END) as female_count
FROM patients
WHERE hospital_id = 1;
```

### Health Risk Analysis
```sql
SELECT 
    COUNT(*) as total,
    ROUND(AVG(diabetes_risk), 2) as avg_diabetes_risk,
    ROUND(AVG(heart_disease_risk), 2) as avg_heart_disease_risk,
    ROUND(AVG(hypertension_risk), 2) as avg_hypertension_risk,
    AVG(bmi) as avg_bmi
FROM health_data
WHERE recorded_at >= DATE_SUB(NOW(), INTERVAL 90 DAY);
```

### Doctor Performance
```sql
SELECT 
    d.first_name, d.last_name, d.specialization,
    COUNT(a.id) as total_appointments,
    COUNT(CASE WHEN a.status = 'completed' THEN 1 END) as completed,
    COUNT(CASE WHEN a.status = 'pending' THEN 1 END) as pending
FROM doctors d
LEFT JOIN appointments a ON d.id = a.doctor_id
WHERE d.hospital_id = 1
GROUP BY d.id
ORDER BY total_appointments DESC;
```

---

## Database Maintenance Queries

### Check Database Size
```sql
SELECT 
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) as size_mb
FROM information_schema.tables
WHERE table_schema = 'hospital_db'
ORDER BY size_mb DESC;
```

### Total Database Size
```sql
SELECT 
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as total_size_mb
FROM information_schema.tables
WHERE table_schema = 'hospital_db';
```

### Count Records in Each Table
```sql
SELECT 
    'hospitals' as table_name, COUNT(*) as row_count FROM hospitals
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
```

### Delete Old Records (Cleanup)
```sql
-- Delete chat history older than 6 months
DELETE FROM ai_chatbot_history 
WHERE created_at < DATE_SUB(NOW(), INTERVAL 6 MONTH);

-- Delete old notifications
DELETE FROM notifications 
WHERE created_at < DATE_SUB(NOW(), INTERVAL 3 MONTH) AND is_read = TRUE;
```

---

## Backup and Restore

### Backup Command (PowerShell)
```powershell
mysqldump -u hospital_user -pMysql hospital_db > hospital_db_backup_$(Get-Date -Format 'yyyyMMdd').sql
```

### Restore Command (PowerShell)
```powershell
mysql -u hospital_user -pMysql hospital_db < hospital_db_backup.sql
```

### Scheduled Backup Script
```powershell
# Create scheduled_backup.ps1
$backup_dir = "C:\hospital_backups"
$date = Get-Date -Format "yyyyMMdd_HHmmss"
$backup_file = "$backup_dir\hospital_db_$date.sql"

mysqldump -u hospital_user -pMysql hospital_db > $backup_file
Write-Host "Backup completed: $backup_file"
```

---

## User and Permission Management

### Create Database User
```sql
CREATE USER 'hospital_user'@'localhost' IDENTIFIED BY 'Mysql';
GRANT ALL PRIVILEGES ON hospital_db.* TO 'hospital_user'@'localhost';
FLUSH PRIVILEGES;
```

### Create Read-Only User
```sql
CREATE USER 'hospital_readonly'@'localhost' IDENTIFIED BY 'ReadPassword123';
GRANT SELECT ON hospital_db.* TO 'hospital_readonly'@'localhost';
FLUSH PRIVILEGES;
```

### Revoke Privileges
```sql
REVOKE ALL PRIVILEGES ON hospital_db.* FROM 'hospital_user'@'localhost';
DROP USER 'hospital_user'@'localhost';
```

---

## Useful Index Queries

### Show All Indexes
```sql
SELECT 
    TABLE_NAME, COLUMN_NAME, INDEX_NAME
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = 'hospital_db'
ORDER BY TABLE_NAME, SEQ_IN_INDEX;
```

### Create Additional Index for Performance
```sql
CREATE INDEX idx_health_data_patient_recorded 
ON health_data(patient_id, recorded_at DESC);

CREATE INDEX idx_messages_unread 
ON messages(doctor_id, is_read) 
WHERE is_read = FALSE;
```

---

## Version Info
- **Created**: December 27, 2025
- **Database**: MySQL 8.0+
- **Character Set**: utf8mb4
- **Collation**: utf8mb4_unicode_ci
