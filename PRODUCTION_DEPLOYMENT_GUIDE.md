# PATIENT IDENTITY SYSTEM - PRODUCTION DEPLOYMENT GUIDE

**Version:** 1.0  
**Status:** ✅ **PRODUCTION READY**  
**Last Updated:** March 29, 2026  

---

## 📋 TABLE OF CONTENTS

1. [Quick Start](#quick-start)
2. [System Architecture](#system-architecture)
3. [Database Setup](#database-setup)
4. [API Endpoints Reference](#api-endpoints-reference)
5. [Integration Checklist](#integration-checklist)
6. [Troubleshooting](#troubleshooting)
7. [Performance Tuning](#performance-tuning)
8. [Security Verification](#security-verification)

---

## 🚀 QUICK START

### Option 1: Bash Script Deployment (Linux/Mac)

```bash
# Make script executable
chmod +x deploy_patient_system.sh

# Run deployment
./deploy_patient_system.sh

# Or rollback to previous state
./deploy_patient_system.sh rollback
```

**What the script does:**
1. ✅ Checks Python, MySQL, Flask environment
2. ✅ Backs up current database
3. ✅ Runs database migrations
4. ✅ Verifies code structure
5. ✅ Validates Python syntax
6. ✅ Tests database functionality
7. ✅ Starts Flask application
8. ✅ Updates Docker (if using containers)

### Option 2: Manual Deployment

#### Step 1: Environment Setup
```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install/update dependencies
pip install -r requirements.txt
```

#### Step 2: Database Backup
```bash
# Backup existing database
mysqldump -u root -p hospital_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### Step 3: Database Migration
```bash
# Python method - creates/updates tables
python3 << 'EOF'
from app import create_app
from app.models.models import db
from config import config

app = create_app(config['production'])
with app.app_context():
    db.create_all()
    print("✓ Database schema created/updated")
EOF
```

Or using Flask-Migrate:
```bash
flask db upgrade
```

#### Step 4: Verify Installation
```bash
# Test imports
python3 -c "
from app.models.models import Patient
from app.services.patient_service import PatientService
from app.routes.walkin import walkin_bp
print('✓ All components imported successfully')
"
```

#### Step 5: Start Application
```bash
# Development
python3 run.py

# Production (using gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

---

## 🏗️ SYSTEM ARCHITECTURE

### Database Schema

```
┌─────────────────────────────────────────────────────┐
│ PATIENTS TABLE (Core)                               │
├─────────────────────────────────────────────────────┤
│ id (PK)              INTEGER PRIMARY KEY             │
│ user_id (FK)         INTEGER UNIQUE NULLABLE         │
│ uhid ⭐ (UNIQUE)      VARCHAR(20) UNIQUE INDEX        │
│ first_name           VARCHAR(80)                     │
│ last_name            VARCHAR(80)                     │
│ age                  INTEGER                         │
│ gender               VARCHAR(20)                     │
│ phone 🔍 (INDEX)      VARCHAR(20) INDEX              │
│ address              TEXT                            │
│ blood_type           VARCHAR(10)                     │
│ medical_history      TEXT                            │
│ allergies            TEXT                            │
│ current_medications  TEXT                            │
│ emergency_contact    VARCHAR(100)                    │
│ is_walk_in ⭐         BOOLEAN (NEW)                   │
│ created_at           DATETIME                        │
│ updated_at           DATETIME                        │
└─────────────────────────────────────────────────────┘

Key Features:
⭐ New fields for walk-in support
🔍 Indexed for fast search
PK = Primary Key
FK = Foreign Key
```

### Service Layer Architecture

```
┌─────────────────────────────────────────────────────┐
│ PATIENT SERVICE (app/services/patient_service.py)   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ✓ generate_uhid()                                  │
│  ✓ create_walk_in_patient()                         │
│  ✓ create_registered_patient()                      │
│  ✓ find_similar_patients()                          │
│  ✓ search_patients()                                │
│  ✓ get_patient_by_uhid()                            │
│  ✓ update_patient()                                 │
│  ✓ get_patient_summary()                            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### API Layer Architecture

```
┌─────────────────────────────────────────────────────┐
│ WALKIN BLUEPRINT (app/routes/walkin.py)             │
├─────────────────────────────────────────────────────┤
│                                                     │
│  POST   /walkin/api/register                        │
│  GET    /walkin/api/search                          │
│  POST   /walkin/api/find-similar                    │
│  GET    /walkin/api/get/<id>                        │
│  GET    /walkin/api/get-by-uhid/<uhid>              │
│  PUT    /walkin/api/update/<id>                     │
│  GET    /walkin/api/list                            │
│                                                     │
│  GET    /walkin/register    (HTML form)             │
│  GET    /walkin/select      (search interface)      │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 🗄️ DATABASE SETUP

### Pre-Deployment Checklist

- [ ] MySQL server is running
- [ ] Database `hospital_db` exists
- [ ] User has SELECT, INSERT, UPDATE, DELETE, ALTER permissions
- [ ] Database backup taken
- [ ] Network connectivity verified (if remote DB)

### Create Database (if new)

```sql
-- Create database
CREATE DATABASE IF NOT EXISTS hospital_db 
  CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;

-- Create user (if needed)
CREATE USER 'hospital_user'@'localhost' IDENTIFIED BY 'secure_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON hospital_db.* TO 'hospital_user'@'localhost';
FLUSH PRIVILEGES;

-- Verify
SHOW DATABASES;
SHOW TABLES IN hospital_db;
```

### Verify UHID Column

```sql
-- Check if UHID column exists
DESC hospital_db.patients;

-- Should show:
-- uhid | varchar(20) | YES | UNI | NULL |

-- If missing, add it:
ALTER TABLE patients ADD COLUMN uhid VARCHAR(20) UNIQUE NOT NULL 
  DEFAULT CONCAT('PAT-', YEAR(NOW()), '-', LPAD(id, 4, '0'));

-- Create index
CREATE INDEX idx_uhid ON patients(uhid);
CREATE INDEX idx_phone ON patients(phone);
```

### Verify Nullable user_id

```sql
-- Check user_id nullability
DESC hospital_db.patients;

-- Should show:
-- user_id | int | YES | UNI | NULL |

-- If NOT NULL, change it:
ALTER TABLE patients MODIFY COLUMN user_id INT UNIQUE NULL;
```

---

## 🔌 API ENDPOINTS REFERENCE

### 1. Register Walk-In Patient

**Endpoint:** `POST /walkin/api/register`

**Authentication:** Required (Login)  
**Roles:** RECEPTIONIST, LAB_STAFF, DOCTOR, ADMIN, HOST

**Request:**
```json
{
    "first_name": "Rajesh",
    "last_name": "Kumar",
    "age": 45,
    "gender": "Male",
    "phone": "+91-9876543210",
    "address": "123 Main St, Delhi"
}
```

**Success Response (201):**
```json
{
    "success": true,
    "patient": {
        "id": 123,
        "uhid": "PAT-2026-0001",
        "name": "Rajesh Kumar",
        "age": 45,
        "gender": "Male",
        "phone": "+91-9876543210",
        "is_walk_in": true,
        "has_account": false
    },
    "message": "Patient PAT-2026-0001: Rajesh Kumar registered successfully"
}
```

**Duplicate Warning Response (409):**
```json
{
    "success": false,
    "code": "POSSIBLE_DUPLICATE",
    "error": "Duplicate warning",
    "duplicates": [
        {
            "id": 100,
            "uhid": "PAT-2026-0001",
            "name": "Rajesh Kumar",
            "similarity": 0.95,
            "reason": "Name match (95%)",
            "phone": "+91-9876543210"
        }
    ]
}
```

**Error Responses:**
- `400` - Missing/invalid required fields
- `403` - Access denied (wrong role)
- `500` - Server error

---

### 2. Search Patients

**Endpoint:** `GET /walkin/api/search?q=...&limit=10`

**Parameters:**
- `q` (required): Search query (UHID, name, or phone) - min 1 character
- `limit` (optional): Max results (default: 10, max: 100)

**Examples:**
```bash
# Search by UHID
GET /walkin/api/search?q=PAT-2026-0001

# Search by name
GET /walkin/api/search?q=rajesh&limit=5

# Search by phone
GET /walkin/api/search?q=9876543210
```

**Response:**
```json
{
    "success": true,
    "patients": [
        {
            "id": 123,
            "uhid": "PAT-2026-0001",
            "name": "Rajesh Kumar",
            "age": 45,
            "gender": "Male",
            "phone": "+91-9876543210",
            "is_walk_in": true
        }
    ],
    "total": 1
}
```

---

### 3. Find Similar Patients (Duplicate Detection)

**Endpoint:** `POST /walkin/api/find-similar`

**Request:**
```json
{
    "name": "Rajesh Kumar",
    "phone": "+91-9876543210",
    "age": 45,
    "threshold": 0.7
}
```

**Response:**
```json
{
    "success": true,
    "similar": [
        {
            "id": 123,
            "uhid": "PAT-2026-0001",
            "name": "Rajesh Kumar",
            "phone": "+91-9876543210",
            "age": 45,
            "similarity": 0.95,
            "reason": "Name match (95%)"
        }
    ],
    "total": 1
}
```

---

### 4. Get Patient Details

**Endpoint:** `GET /walkin/api/get/<patient_id>`

**Example:**
```bash
GET /walkin/api/get/123
```

**Response:**
```json
{
    "success": true,
    "patient": {
        "id": 123,
        "uhid": "PAT-2026-0001",
        "name": "Rajesh Kumar",
        "age": 45,
        "gender": "Male",
        "phone": "+91-9876543210",
        "address": "123 Main St, Delhi",
        "blood_type": "O+",
        "allergies": "Penicillin",
        "medical_history": "Diabetes Type 2",
        "is_walk_in": true,
        "has_account": false,
        "lab_orders_count": 5,
        "prescriptions_count": 3,
        "appointments_count": 2,
        "created_at": "2026-03-29T10:30:00"
    }
}
```

---

### 5. Get Patient by UHID

**Endpoint:** `GET /walkin/api/get-by-uhid/<uhid>`

**Example:**
```bash
GET /walkin/api/get-by-uhid/PAT-2026-0001
```

**Response:** Same as endpoint 4

---

### 6. Update Patient

**Endpoint:** `PUT /walkin/api/update/<patient_id>`

**Allowed Fields:**
- `age`, `phone`, `address`
- `allergies`, `blood_type`, `emergency_contact`
- `medical_history`

**Request:**
```json
{
    "age": 46,
    "phone": "+91-9876543211",
    "allergies": "Penicillin, Aspirin",
    "blood_type": "AB+"
}
```

**Response:**
```json
{
    "success": true,
    "patient": { ... updated patient ... },
    "message": "Patient information updated"
}
```

**Protected Fields (Cannot Update):**
- `id`, `uhid`, `user_id`, `created_at`, `is_walk_in`

---

### 7. List Patients

**Endpoint:** `GET /walkin/api/list?is_walk_in=true&limit=20&offset=0`

**Parameters:**
- `is_walk_in` (optional): "true" or "false"
- `limit` (optional): Max results per page (default: 20, max: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
{
    "success": true,
    "patients": [ ... ],
    "total": 150,
    "limit": 20,
    "offset": 0
}
```

---

## ✅ INTEGRATION CHECKLIST

### Before Going Live

- [ ] **Database:**
  - [ ] UHID column exists and is unique
  - [ ] user_id is nullable
  - [ ] is_walk_in column exists
  - [ ] Indexes created (uhid, phone)
  - [ ] Database backed up

- [ ] **Code:**
  - [ ] Patient model updated with new fields
  - [ ] PatientService imported from correct location
  - [ ] Walkin blueprint registered in app/__init__.py
  - [ ] All routes tested locally

- [ ] **Frontend:**
  - [ ] Register form accessible at /walkin/register
  - [ ] Search form accessible at /walkin/select
  - [ ] Forms linked to correct API endpoints
  - [ ] Error messages display properly

- [ ] **Lab Integration:**
  - [ ] Lab can create orders with patient_id only
  - [ ] source_type set to 'WALK_IN' for walk-in patients
  - [ ] doctor_id is NULL for walk-in orders

- [ ] **Doctor Integration:**
  - [ ] Doctor can search for walk-in patients
  - [ ] Doctor can view walk-in patient history
  - [ ] Doctor can create prescriptions for walk-in patients

- [ ] **Security:**
  - [ ] Login required for all endpoints
  - [ ] Role-based access control working
  - [ ] SQL injection protection active
  - [ ] CSRF tokens enabled

- [ ] **Performance:**
  - [ ] Database indexes verified
  - [ ] Search response time < 200ms
  - [ ] Register response time < 300ms

---

## 🆘 TROUBLESHOOTING

### Issue 1: "UHID column does not exist"

**Error Message:**
```
sqlalchemy.exc.OperationalError: (1054, "Unknown column 'patients.uhid'")
```

**Solution:**
```sql
-- Add UHID column
ALTER TABLE patients ADD COLUMN uhid VARCHAR(20) UNIQUE NOT NULL 
  DEFAULT CONCAT('PAT-', YEAR(NOW()), '-', LPAD(id, 4, '0'));

-- Verify
DESC patients;
```

---

### Issue 2: "user_id is NOT NULL in database"

**Error Message:**
```
Walk-in patient creation fails with constraint error
```

**Solution:**
```sql
-- Make user_id nullable
ALTER TABLE patients MODIFY COLUMN user_id INT UNIQUE NULL;

-- Verify
DESC patients;  -- Should show "YES" for Null column
```

---

### Issue 3: "Duplicate detection not working"

**Possible Causes:**
1. Threshold too high
2. Name spelling variations
3. Phone format inconsistencies

**Solution:**
```python
# Test duplicate detection
from app.services.patient_service import PatientService

similar = PatientService.find_similar_patients(
    name="Rajesh Kumar",
    age=45,
    phone="9876543210",
    threshold=0.6  # Lower threshold = more matches
)

for s in similar:
    print(f"{s['patient'].full_name} - {s['similarity']*100}%")
```

---

### Issue 4: "Search is slow"

**Solution:**
```sql
-- Verify indexes exist
SHOW INDEX FROM patients;

-- Should show:
-- Primary Key on id
-- Unique Index on uhid
-- Index on phone

-- If missing, create:
CREATE UNIQUE INDEX idx_uhid ON patients(uhid);
CREATE INDEX idx_phone ON patients(phone);
```

---

### Issue 5: "API returns 403 Forbidden"

**Causes:**
1. User not authenticated
2. User role not in allowed list
3. Session expired

**Solution:**
```python
# Check allowed roles in walkin.py
ALLOWED_ROLES = [
    UserRole.RECEPTIONIST,
    UserRole.LAB_STAFF,
    UserRole.DOCTOR,
    UserRole.ADMIN,
    UserRole.HOST
]

# Verify current user role
from flask_login import current_user
print(f"Current user role: {current_user.role}")
```

---

### Issue 6: "Blueprint not registered"

**Error:**
```
werkzeug.routing.exceptions.BuildError: Could not build url for endpoint 'walkin.register'
```

**Solution:**
```python
# In app/__init__.py, verify:
from app.routes.walkin import walkin_bp
app.register_blueprint(walkin_bp)

# Test import
python3 -c "from app.routes.walkin import walkin_bp; print('✓ Blueprint imports successfully')"
```

---

### Issue 7: "Cannot update protected fields"

**Expected Behavior:**
Cannot change UHID, user_id, created_at, is_walk_in

**Verification:**
```python
from app.services.patient_service import PatientService

patient = PatientService.get_patient_by_id(1)

# Try to update protected field (won't work)
PatientService.update_patient(patient, uhid="NEW-UHID")

# Verify it didn't change
assert patient.uhid == "OLD-UHID"  # Still original
```

---

### Issue 8: "Lab order creation fails for walk-in"

**Solution:**
```python
from app.models.models import LabOrder, Patient, db

patient = Patient.query.get(patient_id)

# IMPORTANT: Ensure source_type and doctor_id set correctly
lab_order = LabOrder(
    patient_id=patient.id,  # Required
    doctor_id=None,         # NULL for walk-in
    source_type='WALK_IN',  # Important!
    test_name='Complete Blood Count',
    status='PENDING'
)
db.session.add(lab_order)
db.session.commit()
```

---

## 📈 PERFORMANCE TUNING

### Database Optimization

```sql
-- Check current indexes
SHOW INDEX FROM patients;

-- Add missing indexes
ALTER TABLE patients ADD INDEX idx_created_at (created_at);
ALTER TABLE patients ADD INDEX idx_is_walk_in (is_walk_in);

-- Check query performance
EXPLAIN SELECT * FROM patients WHERE uhid = 'PAT-2026-0001';
-- Should show "const" in type column

-- Monitor slow queries
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 0.5;
```

### API Rate Limiting

```python
# In app/routes/walkin.py, add rate limiting
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@walkin_bp.route('/api/register', methods=['POST'])
@limiter.limit("10 per minute")  # Max 10 registrations per minute
def register_walkin_patient():
    # ...
```

### Caching

```python
# Cache patient searches
from flask import cache

@walkin_bp.route('/api/get-by-uhid/<uhid>')
@cache.cached(timeout=300)  # Cache for 5 minutes
def get_patient_by_uhid(uhid):
    # ...
```

---

## 🔒 SECURITY VERIFICATION

### Checklist

- [ ] **Authentication:**
  - [ ] All endpoints require login
  - [ ] Session tokens validated
  - [ ] Logout properly clears session

- [ ] **Authorization:**
  - [ ] Role-based access control enabled
  - [ ] Allowed roles: RECEPTIONIST, LAB_STAFF, DOCTOR, ADMIN, HOST
  - [ ] Other roles rejected (403)

- [ ] **Input Validation:**
  - [ ] All inputs sanitized
  - [ ] SQL injection prevented (using ORM)
  - [ ] XSS protection enabled
  - [ ] CSRF tokens checked

- [ ] **Data Protection:**
  - [ ] Patient data encrypted in transit (HTTPS)
  - [ ] Passwords hashed (bcrypt/werkzeug)
  - [ ] Sensitive fields not logged
  - [ ] Database backups encrypted

- [ ] **Audit Logging:**
  - [ ] All patient creates logged
  - [ ] All patient updates logged
  - [ ] Failed access attempts logged
  - [ ] Logs retained for compliance

### Test Security

```bash
# Test SQL injection protection
curl -X POST http://localhost:5000/walkin/api/register \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Raj\"--", "last_name": "Kumar", "age": 30, "gender": "Male"}'
# Should safely escape or reject

# Test CSRF protection
curl -X POST http://localhost:5000/walkin/api/register \
  -H "Content-Type: application/json" \
  -d '{...}'
# Should validate CSRF token

# Test authentication
curl -X GET http://localhost:5000/walkin/api/list
# Should return 403 or redirect to login
```

---

## 📞 SUPPORT & DOCUMENTATION

**For Staff:** See `WALKIN_QUICK_START.md`  
**For Developers:** See `PATIENT_IDENTITY_SYSTEM_COMPLETE.md`  
**For Deployment:** This file  
**For Examples:** See `PRODUCTION_USAGE_EXAMPLES.py`  
**For Testing:** See `test_patient_identity.py`

---

## ✨ SUCCESS INDICATORS

System is ready for production when:

✅ Database schema verified and backed up  
✅ All tests passing  
✅ API endpoints responding with correct data  
✅ Duplicate detection working  
✅ Lab/Doctor integration functional  
✅ Performance within acceptable limits  
✅ Security checks passing  
✅ Staff trained and ready  

---

**Deployment Status:** ✅ **READY FOR PRODUCTION**

System fully implemented, tested, and documented.

