# Walk-in Patient Management System

## Overview

The Hospital Management System has been upgraded to support **walk-in patients without requiring login accounts**. This allows reception staff and lab employees to register patients manually and maintain their medical history independently of user accounts.

### Key Features

✅ **Patient Registration Without Login**
- Register walk-in patients with minimal information
- No need to create user accounts
- Faster patient intake process

✅ **Unique Patient Identification (UHID)**
- Automatic generation of unique IDs: `PAT-YYYY-XXXX`
- Example: `PAT-2026-0001`, `PAT-2026-0002`
- Ensures patient records are never confused

✅ **Duplicate Detection**
- Intelligent matching by name, phone, and age
- Similarity scoring to prevent duplicate records
- Staff can choose to use existing patient records

✅ **Patient Search**
- Search by UHID, name, or phone number
- Instant results for quick patient lookup
- Filter by registration type (walk-in vs registered)

✅ **History Management**
- Complete patient history preserved
- Lab orders linked to patient (not user account)
- Prescriptions and medical records accessible
- Works with both walk-in and registered patients

✅ **Professional Integration**
- Doctors access patients using UHID
- Lab staff create orders for walk-in patients
- Complete workflow without user login requirement

## Architecture

### Database Schema

#### Patient Model Changes

```python
class Patient(db.Model):
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # User relationship (now optional)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=True)
    
    # Unique hospital ID
    uhid = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    # Standard patient info
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(20), index=True)  # Indexed for search
    address = db.Column(db.Text)
    
    # Walk-in indicator
    is_walk_in = db.Column(db.Boolean, default=False)
    
    # Methods
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def display_name(self):
        return f"{self.full_name} ({self.uhid})"
    
    def is_registered_user(self):
        return self.user_id is not None
```

### API Endpoints

All endpoints require authentication and appropriate role (RECEPTIONIST, LAB_STAFF, DOCTOR, ADMIN).

#### 1. Register Walk-in Patient

**POST** `/walkin/api/register`

Register a new walk-in patient without user account.

**Request Body:**
```json
{
    "first_name": "Ravi",
    "last_name": "Kumar",
    "age": 35,
    "gender": "Male",
    "phone": "9876543210",  // Optional but recommended
    "address": "123 Main St"  // Optional
}
```

**Response (Success):**
```json
{
    "success": true,
    "patient": {
        "id": 1234,
        "uhid": "PAT-2026-0001",
        "name": "Ravi Kumar",
        "display_name": "Ravi Kumar (PAT-2026-0001)",
        "age": 35,
        "gender": "Male",
        "phone": "9876543210",
        "is_walk_in": true,
        "has_account": false
    },
    "message": "Patient Ravi Kumar (PAT-2026-0001) registered successfully"
}
```

**Response (Duplicate Warning):**
```json
{
    "success": false,
    "error": "Duplicate warning",
    "code": "POSSIBLE_DUPLICATE",
    "duplicates": [
        {
            "id": 999,
            "uhid": "PAT-2026-0050",
            "name": "Ravi Kumar",
            "phone": "9876543210",
            "similarity": 0.95,
            "reason": "Name match (95%)"
        }
    ]
}
```

#### 2. Search Patients

**GET** `/walkin/api/search?q=PAT-2026-0001&limit=10`

Search patients by UHID, name, or phone.

**Query Parameters:**
- `q` (required): Search query (UHID, name, or phone)
- `limit` (optional): Max results (default: 10, max: 100)

**Response:**
```json
{
    "success": true,
    "patients": [
        {
            "id": 1234,
            "uhid": "PAT-2026-0001",
            "name": "Ravi Kumar",
            "display_name": "Ravi Kumar (PAT-2026-0001)",
            "age": 35,
            "gender": "Male",
            "phone": "9876543210",
            "is_walk_in": true,
            "has_account": false,
            "created_at": "2026-03-29T10:30:00"
        }
    ],
    "total": 1
}
```

#### 3. Find Similar Patients

**POST** `/walkin/api/find-similar`

Find patients with similar information to detect duplicates.

**Request Body:**
```json
{
    "name": "Ravi Kumar",
    "phone": "9876543210",
    "age": 35,
    "threshold": 0.7
}
```

**Response:**
```json
{
    "success": true,
    "similar": [
        {
            "id": 999,
            "uhid": "PAT-2026-0050",
            "name": "Ravi Kumar",
            "phone": "9876543210",
            "age": 35,
            "gender": "Male",
            "similarity": 0.95,
            "reason": "Name match (95%)",
            "is_walk_in": true
        }
    ],
    "total": 1
}
```

#### 4. Get Patient Details

**GET** `/walkin/api/get/<patient_id>`

Get detailed patient information including history.

**Response:**
```json
{
    "success": true,
    "patient": {
        "id": 1234,
        "uhid": "PAT-2026-0001",
        "name": "Ravi Kumar",
        "display_name": "Ravi Kumar (PAT-2026-0001)",
        "age": 35,
        "gender": "Male",
        "phone": "9876543210",
        "address": "123 Main St",
        "blood_type": "O+",
        "allergies": "Penicillin",
        "medical_history": "Diabetes Type 2",
        "is_walk_in": true,
        "has_account": false,
        "lab_orders_count": 5,
        "prescriptions_count": 3,
        "appointments_count": 2,
        "created_at": "2026-03-29T10:30:00",
        "updated_at": "2026-03-29T14:00:00"
    }
}
```

#### 5. Get Patient by UHID

**GET** `/walkin/api/get-by-uhid/<uhid>`

Get patient using their UHID.

**Example:** `/walkin/api/get-by-uhid/PAT-2026-0001`

#### 6. Update Patient

**PUT** `/walkin/api/update/<patient_id>`

Update patient information.

**Allowed Fields:**
- `age`, `phone`, `address`
- `allergies`, `medical_history`, `emergency_contact`
- `blood_type`

**Request Body:**
```json
{
    "phone": "9876543211",
    "allergies": "Penicillin, Aspirin"
}
```

#### 7. List All Patients

**GET** `/walkin/api/list?limit=20&offset=0&is_walk_in=true`

Get paginated list of patients.

**Query Parameters:**
- `limit` (optional): Results per page (default: 20, max: 100)
- `offset` (optional): Pagination offset (default: 0)
- `is_walk_in` (optional): Filter by type (true/false)

**Response:**
```json
{
    "success": true,
    "patients": [...],
    "total": 250,
    "limit": 20,
    "offset": 0
}
```

## UI Pages

### 1. Patient Registration Page
**URL:** `/walkin/register`

Allows staff to register new walk-in patients.

**Features:**
- Form validation
- Real-time duplicate detection
- Displays generated UHID
- Clear success confirmation

**Workflow:**
1. Staff enters patient details (First Name, Last Name, Age, Gender, optional Phone/Address)
2. System checks for duplicates
3. If duplicates found, staff can choose to use existing record
4. Otherwise, new patient is registered with auto-generated UHID
5. Staff is shown UHID for reference

### 2. Patient Search Page
**URL:** `/walkin/select`

Search and select patients from the system.

**Features:**
- Full-text search by UHID, name, or phone
- Tab filters (All, Walk-in Only, Registered)
- Instant results with patient details
- Click to select patient for further workflow

**Display Info:**
- Patient Name
- UHID (prominently displayed)
- Age, Gender, Phone
- Registration type (Walk-in / Registered)
- Quick action buttons

## Workflow Examples

### Workflow 1: Lab Test for Walk-in Patient

```
1. Patient arrives at reception without appointment
2. Reception staff opens /walkin/register or /walkin/select
3. If new patient:
   a. Click "Register New Patient"
   b. Enter name, age, gender
   c. System generates UHID (e.g., PAT-2026-0001)
   d. Click "Continue"
4. Lab staff selects patient from search
5. Lab staff creates test order (linked to patient_id, not user_id)
6. Doctor views results using patient UHID
```

### Workflow 2: Returning Walk-in Patient

```
1. Patient returns (may not have account)
2. Reception staff opens /walkin/select
3. Search by UHID or phone: "PAT-2026-0001" or "9876543210"
4. Click on patient record
5. System shows complete history:
   - Previous lab tests
   - Earlier prescriptions
   - Health data
   - Appointments
6. Continue with new consultation/test
```

### Workflow 3: Doctor Accessing Walk-in Patient

```
1. Doctor receives reception queue entry with patient UHID
2. Clicks on patient link (uses patient_id, not user_id)
3. Can view:
   - Patient demographics
   - Complete medical history
   - Previous prescriptions
   - Lab results
   - Health data
4. Can create new prescriptions
5. Can request lab tests
6. No user account login by patient needed
```

## Database Migration

### Option 1: Automatic Migration (Recommended)

The system will automatically handle migration on next restart:

```bash
# The app detects missing columns and adds them automatically
# No manual intervention required
# Just restart the Flask application
```

### Option 2: Manual SQL Migration

If automatic migration fails, run the migration script:

```bash
# MySQL
mysql -u hospital_user -p hospital_db < migrate_walkin_patients.sql

# Or execute in MySQL client
mysql> SOURCE /path/to/migrate_walkin_patients.sql;
```

### Migration Script Details

The migration:
1. Adds `uhid` column (VARCHAR(20), UNIQUE, NOT NULL)
2. Adds `is_walk_in` column (BOOLEAN, DEFAULT FALSE)
3. Modifies `user_id` to allow NULL values
4. Creates indexes for search optimization:
   - `idx_phone` - fast phone search
   - `idx_uhid` - instant UHID lookup
5. Populates UHID for existing patients in format PAT-YYYY-XXXX

### Post-Migration Verification

```sql
-- Check total patients
SELECT COUNT(*) as total FROM patients;

-- Check unique UHIDs
SELECT COUNT(DISTINCT uhid) as unique_uhids FROM patients;

-- Check walk-in patients
SELECT COUNT(*) as walkin FROM patients WHERE is_walk_in = TRUE;

-- Check registered patients
SELECT COUNT(*) as registered FROM patients WHERE user_id IS NOT NULL;

-- Check for duplicate UHIDs
SELECT uhid, COUNT(*) as count FROM patients GROUP BY uhid HAVING count > 1;
```

## Integration with Existing Modules

### Lab Module

✅ **Already Compatible**
- Lab orders accept `patient_id` (not requiring `user_id`)
- Walk-in lab visits are fully supported via `SOURCE_WALK_IN`
- Billing is linked to `patient_id`
- No changes needed

### Doctor Module

✅ **Already Compatible**
- Doctor endpoints use `patient_id`
- Access control checks work with both registered and walk-in patients
- Prescriptions linked to `patient_id`
- Appointments work with patient records
- No changes needed

### Reception Module

⚠️ **Partial Update Needed**
- Existing `register_walkin` endpoint uses old flow (creates temp user)
- Can continue using or migrate to new PatientService
- New `/walkin/*` endpoints provide modern flow

## Security Considerations

### Access Control

- All walk-in endpoints require authentication
- Required roles: `RECEPTIONIST`, `LAB_STAFF`, `DOCTOR`, `ADMIN`, `HOST`
- Patient records are HIPAA-relevant (no direct public access)

### Data Validation

- UHID generation ensures uniqueness automatically
- Duplicate detection prevents data entry errors
- Phone number validation for search accuracy
- Age validation (0-150 years)

### Audit Trail

```python
# All patient creation is logged
logger.info(f"Walk-in patient created: {uhid} - {patient.full_name}")

# All updates are logged
logger.info(f"Patient {patient.uhid} updated by {current_user.username}")
```

## Testing

### Test Walk-in Registration

```bash
# 1. Open registration page
http://localhost:5000/walkin/register

# 2. Fill form:
First Name: John
Last Name: Doe
Age: 45
Gender: Male
Phone: 9999999999

# 3. Expected Result:
- UHID generated: PAT-2026-XXXX
- Record created successfully
- Links to patient record
```

### Test Patient Search

```bash
# 1. Open search page
http://localhost:5000/walkin/select

# 2. Search by UHID
Query: PAT-2026-0001

# 3. Search by name
Query: John Doe

# 4. Search by phone
Query: 9999999999

# Expected: Patient found with all details
```

### Test for Duplicates

```bash
# 1. Register patient:
Name: Jane Smith, Age: 30, Phone: 8888888888

# 2. Try to register again with same data
# 3. System detects duplicate
# 4. Asks to use existing record

# Expected: Prevents duplicate creation
```

## FAQs

### Q: Do walk-in patients need to create accounts?
**A:** No! That's the whole point. They can be treated and have lab tests without any account.

### Q: What if a walk-in patient returns later?
**A:** Search by UHID, name, or phone. Their complete history is preserved.

### Q: Can a walk-in patient become a registered user later?
**A:** Yes! A user account can be linked to an existing patient record by setting the `user_id`.

### Q: What's the UHID format?
**A:** `PAT-YYYY-XXXX` where YYYY is the current year and XXXX is a 4-digit sequence (0001, 0002, etc.)

### Q: Can doctors create prescriptions for walk-in patients?
**A:** Yes! Prescriptions are linked by `patient_id`, so both walk-in and registered patients work.

### Q: What if two walk-in patients have the same name and age?
**A:** Each gets a unique UHID. Phone number uniqueness and duplicate detection helps identify them.

### Q: Is patient data exportable?
**A:** Yes, through the lab/doctor modules. Patient UHID makes record-keeping consistent.

## Troubleshooting

### Patient Search Returns Empty

**Causes:**
- Database migration incomplete
- Search terms don't match
- Indexes not created

**Fix:**
```sql
-- Verify data exists
SELECT COUNT(*) FROM patients;

-- Rebuild indexes
REPAIR TABLE patients;
```

### UHID Generation Fails

**Causes:**
- Database constraint violation
- Duplicate UHID attempted

**Fix:**
```sql
-- Check for duplicates
SELECT uhid, COUNT(*) FROM patients GROUP BY uhid HAVING COUNT(*) > 1;

-- Fix duplicates by regenerating
UPDATE patients SET uhid = '' WHERE uhid = 'PAT-2026-0001';
```

### Walk-in Endpoints Return 403 Forbidden

**Causes:**
- Not authenticated
- Wrong role for access

**Fix:**
- Login as RECEPTIONIST, LAB_STAFF, or DOCTOR
- Check user role in database

## API Version

Current Version: **1.0**
Last Updated: March 29, 2026

## Support

For issues or questions:
1. Check the logs: `logs/app.log`
2. Verify database migration: `SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='patients';`
3. Test endpoints with Postman or curl
4. Review error responses for specific error codes
