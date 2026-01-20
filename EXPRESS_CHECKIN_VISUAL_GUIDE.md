# EXPRESS CHECK-IN SYSTEM - VISUAL GUIDE

## 🎯 User Flow Diagram

### Patient Flow
```
┌─────────────────────────────────────────────────────────────┐
│                    PATIENT DASHBOARD                         │
│                                                              │
│  [Express Check-in Button]                                   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│              EXPRESS CHECK-IN FORM PAGE                      │
│                                                              │
│  1️⃣  Why are you checking in?                              │
│      • Check-in Reason (text input)                         │
│      • Type of Visit (dropdown)                             │
│                                                              │
│  2️⃣  Your Current Symptoms                                 │
│      • Symptoms (textarea)                                  │
│      • Severity Level (dropdown)                            │
│                                                              │
│  3️⃣  Vital Signs (Optional)                                │
│      • Temperature °C                                       │
│      • Blood Pressure                                       │
│      • Heart Rate                                           │
│                                                              │
│  [Submit Check-in Request] [Back to Dashboard]              │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓ (POST /features/digital-checkin)
                 │
┌─────────────────────────────────────────────────────────────┐
│            DATABASE - patient_checkins TABLE                 │
│                                                              │
│  Status: 'pending'                                          │
│  ✓ All data saved                                          │
│  ✓ Doctor ID assigned                                      │
│  ✓ Timestamps created                                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│                    PATIENT DASHBOARD                         │
│                                                              │
│  ✅ Check-in Submitted!                                    │
│  Status: Waiting for doctor review...                       │
└─────────────────────────────────────────────────────────────┘
```

---

### Doctor Flow
```
┌─────────────────────────────────────────────────────────────┐
│                    DOCTOR DASHBOARD                          │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Express Check-ins Card                             │    │
│  │  ┌───────────────────────────────────────────────┐  │    │
│  │  │  📋 CLIPBOARD-CHECK ICON                      │  │    │
│  │  │                                                 │  │    │
│  │  │  Express Check-ins                            │  │    │
│  │  │  ┌─────────────────────┐                      │  │    │
│  │  │  │   5 (in blue)       │  Pending Requests    │  │    │
│  │  │  └─────────────────────┘                      │  │    │
│  │  │                                                 │  │    │
│  │  │  [View All] ← CLICK HERE                      │  │    │
│  │  └───────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  QUICK ACTIONS                                               │
│  [Manage Appointments]                                       │
│  [View Express Check-ins] ← NEW BUTTON                      │
│  [View All Patients]                                        │
│                                                              │
│  PENDING EXPRESS CHECK-INS (Latest 3)                       │
│  ┌─────────────────────────────────────────────┐            │
│  │ 👤 John Doe                                 │            │
│  │ 🏥 Reason: Follow-up for hypertension     │            │
│  │ 📊 Type: Follow-up | 🟢 Mild             │            │
│  │ 🕐 14:30                                   │            │
│  │ [Review & Accept]                          │            │
│  └─────────────────────────────────────────────┘            │
│  ┌─────────────────────────────────────────────┐            │
│  │ 👤 Jane Smith                              │            │
│  │ 🏥 Reason: New chest pain complaint       │            │
│  │ 📊 Type: New Complaint | 🔴 Severe       │            │
│  │ 🕐 14:15                                   │            │
│  │ [Review & Accept]                          │            │
│  └─────────────────────────────────────────────┘            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓ [View All] or [Review & Accept]
                 │
┌─────────────────────────────────────────────────────────────┐
│         PENDING CHECK-INS MANAGEMENT PAGE                    │
│         /features/doctor/pending-checkins                    │
│                                                              │
│  STATISTICS BAR                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Pending: 5       │  │ Accepted: 12     │                │
│  └──────────────────┘  └──────────────────┘                │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Rejected: 2      │  │ Completed: 18    │                │
│  └──────────────────┘  └──────────────────┘                │
│                                                              │
│  TABS: [Pending] [Accepted]                                │
│                                                              │
│  PENDING CHECK-INS (Grid View)                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  👤 John Doe                              14:30      │  │
│  │  ID: #1001                                           │  │
│  │                                                       │  │
│  │  🏥 Reason: Follow-up hypertension check            │  │
│  │                                                       │  │
│  │  [Follow-up] [Mild]                                 │  │
│  │                                                       │  │
│  │  Symptoms: Feeling dizzy, slight headache          │  │
│  │                                                       │  │
│  │  Vitals:                                            │  │
│  │  • Temp: 37.2°C                                    │  │
│  │  • BP: 145/92                                       │  │
│  │  • HR: 78 bpm                                       │  │
│  │                                                       │  │
│  │  ┌────────────────────────────────┐                │  │
│  │  │ ✅ Accept Check-in             │  ❌ Reject    │  │
│  │  └────────────────────────────────┘                │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  [Same layout repeats for other pending check-ins]         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                 │
                 ↓ [Accept Check-in] clicked
                 │
┌─────────────────────────────────────────────────────────────┐
│              ACCEPT MODAL DIALOG                             │
│                                                              │
│  ✅ Accept Check-in                                        │
│  ──────────────────                                        │
│                                                              │
│  You are accepting the check-in request from                │
│  John Doe                                                   │
│                                                              │
│  Notes (Optional)                                           │
│  ┌──────────────────────────────────────────┐              │
│  │ Add any notes about this check-in...     │              │
│  │                                          │              │
│  │ [Type notes here...]                     │              │
│  └──────────────────────────────────────────┘              │
│                                                              │
│  [Cancel]  [✅ Accept Check-in]                           │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓ (POST /features/doctor/checkin/1/accept)
                 │
┌─────────────────────────────────────────────────────────────┐
│            DATABASE UPDATE                                   │
│                                                              │
│  patient_checkins table:                                    │
│  id=1 {                                                     │
│    status: 'pending' → 'accepted'                          │
│    doctor_notes: 'Patient shows signs of...'              │
│    acceptance_time: 2025-12-28 14:35:42                   │
│    updated_at: 2025-12-28 14:35:42                        │
│  }                                                          │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│        PAGE RELOADS - STATISTICS UPDATED                    │
│                                                              │
│  ✅ Check-in from John Doe accepted!                       │
│                                                              │
│  STATISTICS BAR                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Pending: 4 ⬇️    │  │ Accepted: 13 ⬆️  │                │
│  └──────────────────┘  └──────────────────┘                │
│                                                              │
│  Check-in now in ACCEPTED tab                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Database Schema Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    USERS TABLE                               │
│  (Existing)                                                  │
│                                                              │
│  id (PK) | username | email | role | ...                   │
│  1       | john_doe | j@... | patient | ...                │
│  2       | dr_smith | dr@.. | doctor  | ...                │
└────┬──────────────────────────────────────────────┬──────────┘
     │                                              │
     ↓                                              ↓
┌─────────────────────────┐         ┌──────────────────────────┐
│   PATIENTS TABLE        │         │    DOCTORS TABLE         │
│   (Existing)            │         │    (Existing)            │
│                         │         │                          │
│ id (PK)                 │         │ id (PK)                  │
│ user_id (FK) → Users.id │         │ user_id (FK) → Users.id  │
│ ...                     │         │ ...                      │
└────┬───────────────────┘         └────┬─────────────────────┘
     │                                   │
     │           ┌───────────────────────┘
     │           │
     ├───────────┼──────────────────────────────────────────┐
     ↓           ↓                                          ↓
┌────────────────────────────────────────────────────────────────────┐
│                   PATIENT_CHECKINS TABLE (NEW)                     │
│                                                                    │
│  COLUMNS:                                                         │
│  ├─ id (PK) ........................... INTEGER                  │
│  ├─ patient_id (FK) → Patient.id ..... INTEGER                  │
│  ├─ doctor_id (FK) → Doctor.id ....... INTEGER                  │
│  ├─ check_in_reason .................. VARCHAR(255)              │
│  ├─ visit_type ....................... VARCHAR(50)               │
│  ├─ symptoms ......................... TEXT                       │
│  ├─ severity ......................... VARCHAR(50)                │
│  ├─ temperature ...................... FLOAT                     │
│  ├─ blood_pressure ................... VARCHAR(50)               │
│  ├─ heart_rate ....................... INTEGER                  │
│  ├─ status ........................... VARCHAR(50)                │
│  │   Values: 'pending', 'accepted',                             │
│  │          'rejected', 'completed'                             │
│  ├─ priority ......................... VARCHAR(50)                │
│  │   Values: 'low', 'normal', 'urgent'                          │
│  ├─ doctor_notes ..................... TEXT                       │
│  ├─ acceptance_time .................. DATETIME                  │
│  ├─ created_at ....................... DATETIME                  │
│  └─ updated_at ....................... DATETIME                  │
│                                                                    │
│  RELATIONSHIPS:                                                   │
│  patient ─────────→ Patient (backref: check_ins)                 │
│  doctor ──────────→ Doctor (backref: pending_check_ins)          │
│                                                                    │
│  INDEXES:                                                         │
│  ├─ PRIMARY KEY: id                                              │
│  ├─ FOREIGN KEY: patient_id                                      │
│  ├─ FOREIGN KEY: doctor_id                                       │
│  └─ INDEX: (doctor_id, status) for fast filtering               │
│                                                                    │
│  EXAMPLE DATA:                                                    │
│  ┌──────────────────────────────────────────────────────┐        │
│  │ id: 1                                                │        │
│  │ patient_id: 5                                        │        │
│  │ doctor_id: 2                                         │        │
│  │ check_in_reason: "Follow-up hypertension check"     │        │
│  │ visit_type: "follow-up"                             │        │
│  │ symptoms: "Dizziness, mild headache"                │        │
│  │ severity: "mild"                                    │        │
│  │ temperature: 37.2                                   │        │
│  │ blood_pressure: "145/92"                            │        │
│  │ heart_rate: 78                                      │        │
│  │ status: "pending"                                   │        │
│  │ priority: "normal"                                  │        │
│  │ doctor_notes: NULL                                  │        │
│  │ acceptance_time: NULL                               │        │
│  │ created_at: 2025-12-28 14:30:42                    │        │
│  │ updated_at: 2025-12-28 14:30:42                    │        │
│  └──────────────────────────────────────────────────────┘        │
└────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Status Lifecycle Diagram

```
                    ┌─────────────────────┐
                    │   CHECK-IN CREATED  │
                    │  status: 'pending'  │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                │                             │
                ↓                             ↓
         ┌─────────────┐            ┌─────────────────┐
         │   DOCTOR    │            │   DOCTOR        │
         │   ACCEPTS   │            │   REJECTS       │
         └──────┬──────┘            └────────┬────────┘
                │                            │
                ↓                            ↓
         ┌──────────────┐            ┌─────────────────┐
         │status:       │            │status:          │
         │'accepted'    │            │'rejected'       │
         │time: NOW     │            │notes: reason    │
         └──────┬───────┘            └────────┬────────┘
                │                            │
                │ (Doctor completes)         │ (Patient notified)
                ↓                            ↓
         ┌──────────────┐            ┌─────────────────┐
         │status:       │            │     END         │
         │'completed'   │            │(No further      │
         │notes: outcome│            │action)          │
         └──────────────┘            └─────────────────┘

STATUS TRANSITIONS:
  pending   → accepted  → completed
  pending   → rejected   → (end)
```

---

## 🎨 UI Components Location

```
DOCTOR DASHBOARD
│
├─ TOP STATISTICS ROW
│  ├─ Total Patients
│  ├─ Pending Appointments
│  ├─ Appointments This Week
│  ├─ Patient Alerts
│  └─ ✨ NEW: EXPRESS CHECK-INS ✨
│     └─ Shows count + "View All" button
│
├─ QUICK ACTIONS SECTION
│  ├─ Manage Appointments
│  ├─ ✨ NEW: View Express Check-ins ✨
│  ├─ View All Patients
│  ├─ Write Prescription
│  └─ View Analytics
│
├─ PATIENT LIST
│
└─ RIGHT SIDEBAR
   ├─ Quick Actions
   ├─ Today's Schedule
   └─ ✨ NEW: PENDING EXPRESS CHECK-INS (Top 3) ✨
      └─ Shows patient cards with Accept/Reject buttons
```

---

## 🖥️ Routes & Endpoints Map

```
PATIENT ROUTES:
├─ GET  /features/digital-checkin
│  └─ Shows check-in form
└─ POST /features/digital-checkin
   └─ Creates check-in, saves to DB, redirects with success

DOCTOR ROUTES:
├─ GET  /features/doctor/pending-checkins
│  └─ Shows management page with all pending/accepted check-ins
├─ POST /features/doctor/checkin/{id}/accept
│  └─ Updates status to 'accepted', saves notes
├─ POST /features/doctor/checkin/{id}/reject
│  └─ Updates status to 'rejected', saves reason
├─ POST /features/doctor/checkin/{id}/complete
│  └─ Updates status to 'completed', saves notes
└─ GET  /features/doctor/checkin/{id}
   └─ Returns JSON with check-in details

DOCTOR DASHBOARD ROUTE:
└─ GET /doctor/dashboard
   └─ Includes pending_checkins and pending_checkins_count
      in template context
```

---

## ✅ Checklist: What Works

- ✅ Patient fills check-in form
- ✅ Data saves to database
- ✅ Doctor sees pending count on dashboard
- ✅ Doctor sees pending check-ins in sidebar
- ✅ Doctor can view all check-ins on management page
- ✅ Doctor can accept check-in
- ✅ Doctor can reject check-in
- ✅ Doctor can complete check-in
- ✅ Doctor can add notes
- ✅ Statistics update in real-time
- ✅ Professional UI with modals
- ✅ Error handling
- ✅ Security verification

---

**All diagrams created: December 28, 2025**
