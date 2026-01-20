-- ============================================================================
-- Hospital Management System - MySQL Database Setup
-- Password: Mysql
-- ============================================================================

-- Create the database
CREATE DATABASE IF NOT EXISTS hospital_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE hospital_db;

-- ============================================================================
-- TABLE: hospitals
-- ============================================================================
CREATE TABLE IF NOT EXISTS hospitals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) UNIQUE NOT NULL,
    domain_prefix VARCHAR(50) UNIQUE,
    address TEXT,
    contact_email VARCHAR(120),
    branding_config LONGTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_domain (domain_prefix)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: users
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    role ENUM('patient', 'doctor', 'admin') NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    hospital_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_role (role),
    INDEX idx_hospital_id (hospital_id),
    FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: patients
-- ============================================================================
CREATE TABLE IF NOT EXISTS patients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNIQUE NOT NULL,
    hospital_id INT,
    first_name VARCHAR(80) NOT NULL,
    last_name VARCHAR(80) NOT NULL,
    age INT,
    gender VARCHAR(20),
    weight FLOAT,
    height FLOAT,
    blood_type VARCHAR(10),
    medical_history LONGTEXT,
    allergies TEXT,
    current_medications TEXT,
    emergency_contact VARCHAR(100),
    phone VARCHAR(20),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_hospital_id (hospital_id),
    INDEX idx_first_name (first_name),
    INDEX idx_last_name (last_name),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: doctors
-- ============================================================================
CREATE TABLE IF NOT EXISTS doctors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNIQUE NOT NULL,
    first_name VARCHAR(80) NOT NULL,
    last_name VARCHAR(80) NOT NULL,
    specialization VARCHAR(100) NOT NULL,
    qualification VARCHAR(200),
    license_number VARCHAR(50) UNIQUE NOT NULL,
    experience_years INT,
    hospital_id INT,
    phone VARCHAR(20),
    clinic_address TEXT,
    consultation_fee FLOAT,
    availability_hours VARCHAR(200),
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_license (license_number),
    INDEX idx_specialization (specialization),
    INDEX idx_hospital_id (hospital_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: health_data
-- ============================================================================
CREATE TABLE IF NOT EXISTS health_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    systolic_bp INT,
    diastolic_bp INT,
    fasting_sugar FLOAT,
    random_sugar FLOAT,
    heart_rate INT,
    ecg_slope VARCHAR(50),
    st_depression FLOAT,
    symptoms TEXT,
    diabetes_risk FLOAT,
    heart_disease_risk FLOAT,
    hypertension_risk FLOAT,
    bmi FLOAT,
    bmi_category VARCHAR(50),
    smoking BOOLEAN,
    alcohol BOOLEAN,
    exercise_minutes INT,
    sleep_hours FLOAT,
    stress_level VARCHAR(50),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_patient_id (patient_id),
    INDEX idx_recorded_at (recorded_at),
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: appointments
-- ============================================================================
CREATE TABLE IF NOT EXISTS appointments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    appointment_date DATETIME NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_patient_id (patient_id),
    INDEX idx_doctor_id (doctor_id),
    INDEX idx_appointment_date (appointment_date),
    INDEX idx_status (status),
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: prescriptions
-- ============================================================================
CREATE TABLE IF NOT EXISTS prescriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    appointment_id INT,
    medicine_name VARCHAR(200) NOT NULL,
    dosage VARCHAR(100),
    frequency VARCHAR(100),
    duration_days INT,
    instructions TEXT,
    status VARCHAR(50) DEFAULT 'active',
    prescribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_patient_id (patient_id),
    INDEX idx_doctor_id (doctor_id),
    INDEX idx_appointment_id (appointment_id),
    INDEX idx_status (status),
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: messages (Doctor-Patient Communication)
-- ============================================================================
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    message_text LONGTEXT NOT NULL,
    sender_type ENUM('patient', 'doctor') NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_patient_id (patient_id),
    INDEX idx_doctor_id (doctor_id),
    INDEX idx_created_at (created_at),
    INDEX idx_is_read (is_read),
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: ai_chatbot_history (For storing AI chatbot interactions)
-- ============================================================================
CREATE TABLE IF NOT EXISTS ai_chatbot_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    patient_id INT,
    question TEXT NOT NULL,
    answer LONGTEXT NOT NULL,
    query_type VARCHAR(100),
    confidence_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_patient_id (patient_id),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: medical_records
-- ============================================================================
CREATE TABLE IF NOT EXISTS medical_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    record_type VARCHAR(100),
    record_title VARCHAR(200) NOT NULL,
    record_description LONGTEXT,
    file_path VARCHAR(500),
    test_results LONGTEXT,
    diagnosis TEXT,
    treatment_plan TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_patient_id (patient_id),
    INDEX idx_doctor_id (doctor_id),
    INDEX idx_record_type (record_type),
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: notifications
-- ============================================================================
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT,
    notification_type VARCHAR(50),
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_is_read (is_read),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Sample Data (Optional)
-- ============================================================================

-- Insert a hospital
INSERT INTO hospitals (name, contact_email, address) VALUES 
('City Hospital', 'info@cityhospital.com', '123 Main Street, Healthcare City');

-- Insert users (password hashes should be generated by app, using placeholder)
INSERT INTO users (username, email, password_hash, role, hospital_id) VALUES 
('admin_user', 'admin@cityhospital.com', 'hashed_password_here', 'admin', 1),
('dr_sharma', 'dr.sharma@cityhospital.com', 'hashed_password_here', 'doctor', 1),
('patient_john', 'john@email.com', 'hashed_password_here', 'patient', 1);

-- Insert doctor profile
INSERT INTO doctors (user_id, first_name, last_name, specialization, license_number, hospital_id) VALUES 
(2, 'Rajesh', 'Sharma', 'Cardiology', 'LIC123456', 1);

-- Insert patient profile
INSERT INTO patients (user_id, hospital_id, first_name, last_name, age, gender, blood_type, phone) VALUES 
(3, 1, 'John', 'Doe', 35, 'Male', 'O+', '9876543210');

-- ============================================================================
-- Create MySQL User for Application
-- ============================================================================
-- Run this command separately with MySQL root credentials
-- CREATE USER 'hospital_user'@'localhost' IDENTIFIED BY 'Mysql';
-- GRANT ALL PRIVILEGES ON hospital_db.* TO 'hospital_user'@'localhost';
-- FLUSH PRIVILEGES;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- SELECT COUNT(*) as Total_Tables FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'hospital_db';
-- SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'hospital_db';
