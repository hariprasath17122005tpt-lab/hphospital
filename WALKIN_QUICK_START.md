# Walk-in Patient System - Quick Start Guide

## For Reception Staff

### 1. Register a New Walk-in Patient (No Account Required)

**Steps:**
1. Patient arrives without an appointment
2. Go to: **http://[hospital-site]/walkin/register**
3. Fill in patient details:
   - **First Name** ✓ (required)
   - **Last Name** (optional)
   - **Age** ✓ (required) 
   - **Gender** ✓ (required) - Select from Male / Female / Other
   - **Phone** (optional but recommended) - helps detect duplicates
   - **Address** (optional)
4. Click **"Register Patient"**
5. System generates a unique **Patient ID (UHID)** automatically
   - Example: `PAT-2026-0001`
6. Your patient is registered! Note down the UHID for records.

### 2. Find an Existing Patient

**Steps:**
1. Go to: **http://[hospital-site]/walkin/select**
2. Search by any of these:
   - **UHID** (Patient ID): `PAT-2026-0001`
   - **Patient Name**: `Ravi Kumar` or just `Ravi`
   - **Phone Number**: `9876543210`
3. Press Enter or click **Search** button
4. Results show all matching patients with their:
   - Name and UHID
   - Age, Gender, Phone
   - Registration type (Walk-in / Registered)
5. Click on a patient to select them

### 3. Use Existing Patient for Lab Tests

**Step-by-step:**
1. Patient returns or needs lab test
2. Go to **Patient Search** (`/walkin/select`)
3. Search for patient by UHID, name, or phone
4. Click on the patient record
5. You'll be sent to Lab Dashboard for that patient
6. Create lab order (don't need to register again!)

### 4. If You Find Similar Patients

**What it means:**
- System found a patient with similar name/phone
- Helps prevent duplicate records
- Example: "Ravi Kumar" might already exist

**What to do:**
1. Read the warning carefully
2. Check if it's the same person:
   - Same phone number?
   - Same age (within 2 years)?
   - Name looks familiar?
3. If YES → Click **"Use This Patient"** (don't create duplicate)
4. If NO → Click **"Create New Record"** anyway (if really different person)

---

## For Lab Staff

### 1. Create Lab Order for Walk-in Patient

**Scenario:** Patient arrives for lab test without any prior record

**Steps:**
1. Click **Lab Module** → **Create Order**
2. First, find/register the patient:
   - Option A: Patient exists → **Search** by UHID/name/phone
   - Option B: Patient is new → **Register** via `/walkin/register`
3. Once patient is selected:
   - Choose test(s): Blood Test, X-Ray, ECG, etc.
   - Set source as "WALK_IN"
   - No doctor assignment needed
4. Generate billing and collect payment
5. Create lab order
6. Patient can get tested immediately!

### 2. View Patient History Before Lab Test

**Steps:**
1. Go to **Patient Search** (`/walkin/select`)
2. Search for patient
3. Click patient record to see:
   - ✓ Previous lab tests done
   - ✓ Blood type (if available)
   - ✓ Allergies (important!)
   - ✓ Medical history
   - ✓ Previous prescriptions

**Why important:**
- Helps lab technician prepare properly
- Avoids duplicate testing
- Checks for allergies to test materials

### 3. Quick Patient Registration (New Walk-in)

**When patient doesn't exist in system:**

1. Go to: **http://[hospital-site]/walkin/register**
2. **Minimal info needed:**
   - First Name (required)
   - Age (required)
   - Gender (required)
3. **Optional but helpful:**
   - Last Name
   - Phone number (prevents duplicates)
4. Click **Register**
5. **System generates UHID** - Write it down!
6. Continue with lab test order

---

## For Doctors

### 1. Access Walk-in Patient Records

**Scenario:** Reception sends patient for consultation

**Steps:**
1. Reception provides **Patient UHID** or directs you to patient
2. Go to **Doctor** module → **Patients**
3. Search by UHID, name, or patient ID
4. Click patient name
5. See complete patient history:
   - ✓ Basic info (age, gender, phone)
   - ✓ Health data (BP, blood sugar, etc.)
   - ✓ Previous lab results
   - ✓ Past prescriptions
   - ✓ Medical history & allergies

### 2. Prescribe for Walk-in Patient

**Same as regular patient:**
1. View patient record
2. Click **"Write Prescription"**
3. Fill prescription details
4. Save
5. Patient gets prescription (doesn't need user account!)

### 3. Order Lab Tests

**For walk-in patient:**
1. View patient record
2. Click **"Request Lab Test"**
3. Select test(s)
4. Prescription is linked to patient UHID
5. Lab receives order automatically

### 4. View All Patients (Registered & Walk-in)

**In Doctor Dashboard:**
- Shows **all patients** you've consulted
- Both registered users AND walk-in patients
- Same functionality for both types

---

## Important Notes

### ✓ What You Need to Know

1. **UHID is permanent** - Once assigned, patient keeps the same ID
2. **Walk-in patients are tracked** - Full history is maintained
3. **No login required** - Patient doesn't need account
4. **Phone helps** - Entering phone prevents duplicates
5. **Search is instant** - Uses UHID, name, or phone

### ⚠️ Common Mistakes to Avoid

| Mistake | Problem | Solution |
|---------|---------|----------|
| Register same patient twice | Duplicate records | Check phone number before registering |
| Lose UHID | Can't find patient again | Write it down or search by name/phone |
| Don't fill required fields | Registration fails | Age, Gender mandatory |
| Spell name differently | Can't find patient later | Check how name was entered |

### 🔐 Access Control

Only these staff can use walk-in system:
- ✓ Receptionists
- ✓ Lab Staff  
- ✓ Doctors
- ✓ Admins

(Cannot be accessed by patients directly)

---

## Common Workflows

### Workflow A: Simple Lab Test (Walk-in)

```
Patient arrives
       ↓
Reception: Does patient exist? (Search: /walkin/select)
       ↓
[NOT FOUND] → Register new: /walkin/register
[FOUND] → Use existing record
       ↓
Lab: Create test order
       ↓
Patient does test
       ↓
Results ready
```

### Workflow B: Consultation + Prescription (Walk-in)

```
Patient arrives
       ↓
Reception: Register or find patient
       ↓
Doctor: View patient record
       ↓
Doctor: Write prescription
       ↓
Doctor: Request lab tests (if needed)
       ↓
Pharmacy: Process prescription
       ↓
Lab: Process test order
```

### Workflow C: Returning Patient

```
Patient returns (with UHID or phone)
       ↓
Reception: Search by UHID/phone
       ↓
Recognize! View history
       ↓
No re-registration needed!
       ↓
Continue with consultation/tests
```

---

## Quick Reference: URLs

| Function | URL |
|----------|-----|
| Register New Patient | `/walkin/register` |
| Search Patient | `/walkin/select` |
| API: Register | `POST /walkin/api/register` |
| API: Search | `GET /walkin/api/search?q=...` |
| API: Get Patient | `GET /walkin/api/get/<id>` |
| API: Find Duplicates | `POST /walkin/api/find-similar` |

---

## Keyboard Shortcuts (Quick Keys)

In search page:
- **Tab** - Focus search box
- **Enter** - Execute search
- **Escape** - Clear search

In registration form:
- **Tab** - Move to next field
- **Shift+Tab** - Move to previous field
- **Enter** - Submit form (from button)

---

## Troubleshooting Quick Fixes

### "Patient not found"
→ Try searching by phone instead of name (less typos)
→ Check spelling of name

### "Cannot register - possible duplicate"
→ System found similar patient
→ Click "Use Existing Patient" if it's the same person
→ Click "Create New" to register anyway (if different)

### "UHID not showing"
→ Registration might have failed
→ Go to Search and verify patient was created
→ Refresh page and try again

### "Access Denied"
→ Login with RECEPTIONIST, LAB_STAFF, or DOCTOR account
→ Regular patient accounts cannot access walk-in module

---

## Tips for Success

1. **Always enter phone number** - Helps system find duplicates
2. **Write down UHID** - Makes future searches easier  
3. **Check spelling** - Affects search results
4. **Use precise age** - Helps identify correct patient
5. **Verify patient before prescribing** - Double-check UHID matches

---

**Still have questions?** Check the full documentation: `WALKIN_PATIENT_SYSTEM.md`
