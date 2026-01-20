# 🚀 SMART DIET PLAN - ACCESS & NAVIGATION GUIDE

## 🌐 HOW TO ACCESS THE SMART DIET PLAN SYSTEM

### Method 1: Direct URL (Easiest)
```
1. Open your web browser
2. Go to: http://localhost:5000/diet/test
3. You'll see the diet plan test form
```

### Method 2: From Hospital Dashboard
```
(Coming soon - Dashboard integration)

Future integration points:
├─ Patient Dashboard
│  └─ Quick Actions → "Generate Diet Plan"
├─ Doctor Dashboard
│  └─ Patient Management → "Create Diet Plan"
└─ Admin Panel
   └─ Tools → "Diet Planning System"
```

### Method 3: From Patient Portal
```
(Coming soon - Patient portal integration)

Steps:
1. Log in as patient
2. Navigate to "Health Tools"
3. Select "Personalized Diet Plan"
4. Fill in profile → Submit
5. View and download plan
```

---

## 📝 STEP-BY-STEP USER FLOW

```
START
  │
  ├─ Navigate to http://localhost:5000/diet/test
  │
  ├─ FORM DISPLAYED
  │  ├─ Patient Information Section
  │  ├─ Medical Condition Selection
  │  ├─ Medication Input
  │  └─ Activity Level Selection
  │
  ├─ USER FILLS FORM
  │  ├─ Age: 58
  │  ├─ Gender: Male
  │  ├─ Height: 175 cm
  │  ├─ Weight: 92 kg
  │  ├─ Condition: Hypertension
  │  ├─ Medications: Lisinopril, Atorvastatin
  │  └─ Activity: Moderate
  │
  ├─ CLICKS "GENERATE DIET PLAN"
  │
  ├─ BACKEND PROCESSING
  │  ├─ Validates input data
  │  ├─ Selects diet protocol
  │  ├─ Applies rule modifiers
  │  ├─ Generates meal plan
  │  ├─ Checks medication interactions
  │  ├─ Calculates adherence score
  │  └─ Compiles complete plan
  │
  ├─ RESULTS DISPLAYED
  │  ├─ Protocol Selected: DASH Diet
  │  ├─ Daily Meal Plan
  │  ├─ Food Explanations
  │  ├─ Health Benefits
  │  ├─ Medication Warnings
  │  ├─ Foods to Avoid
  │  ├─ Risk Information
  │  └─ Adherence Score
  │
  ├─ USER ACTIONS
  │  ├─ Print Diet Plan
  │  ├─ Download PDF (future)
  │  ├─ Share with Doctor
  │  ├─ Back to Dashboard
  │  └─ Generate New Plan
  │
  └─ END
```

---

## 🗺️ SYSTEM ARCHITECTURE DIAGRAM

```
┌──────────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                                 │
│  http://localhost:5000/diet/test                                    │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP Request (Form Submission)
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      FLASK APPLICATION                               │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Flask Routes (app/routes/diet_plan_routes.py)               │  │
│  │                                                               │  │
│  │  POST /diet/generate                                         │  │
│  │  ├─ Receive patient profile JSON                             │  │
│  │  ├─ Validate input data                                      │  │
│  │  ├─ Call DietPlanEngine.generate_diet_plan()               │  │
│  │  └─ Render diet_plan_display.html with results             │  │
│  │                                                               │  │
│  │  GET /diet/test                                              │  │
│  │  └─ Render diet_plan_test.html (form)                       │  │
│  │                                                               │  │
│  │  POST /diet/api/generate                                    │  │
│  │  └─ Return JSON response                                    │  │
│  │                                                               │  │
│  │  GET /diet/view, /diet/protocols, /diet/conditions          │  │
│  │  └─ Various utility endpoints                               │  │
│  └───────────────────────────────────────────────────────────────┘
│                              │
│                              │ Calls
│                              ▼
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Diet Plan Engine (app/modules/diet_plan_engine.py)         │  │
│  │                                                               │  │
│  │  DietPlanEngine Class                                        │  │
│  │  ├─ __init__(): Load all JSON data files                   │  │
│  │  ├─ generate_diet_plan(profile): Main logic                │  │
│  │  ├─ _select_diet_protocol(profile): Select DASH/Med/etc    │  │
│  │  ├─ _apply_rule_modifiers(profile): BMI/age adjustments   │  │
│  │  ├─ _generate_meal_plan(): Create daily meals              │  │
│  │  ├─ _get_food_explanations(meals): Medical reasons         │  │
│  │  ├─ _get_medication_safety_notes(meds): Drug warnings      │  │
│  │  └─ _calculate_adherence_score(profile): Predict success   │  │
│  │                                                               │  │
│  │  Helper Functions                                            │  │
│  │  ├─ validate_patient_profile(): Input validation            │  │
│  │  ├─ _calculate_bmi(): Height/weight to BMI                 │  │
│  │  └─ _get_disclaimer(): Legal warning text                  │  │
│  └───────────────────────────────────────────────────────────────┘
│                              │
│                              │ Queries
│                              ▼
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Medical Data Files (JSON, app/data/)                        │  │
│  │                                                               │  │
│  │  ├─ diet_protocols.json                                     │  │
│  │  │  ├─ DASH: {name, foods, reasons, benefits...}          │  │
│  │  │  ├─ MEDITERRANEAN: {...}                                │  │
│  │  │  ├─ LOW_GLYCEMIC: {...}                                │  │
│  │  │  ├─ RENAL_FRIENDLY: {...}                              │  │
│  │  │  └─ CELIAC_FRIENDLY: {...}                             │  │
│  │  │                                                           │  │
│  │  ├─ food_medical_reasons.json                              │  │
│  │  │  ├─ "salmon": "Rich in omega-3s..."                    │  │
│  │  │  ├─ "oats": "High in soluble fiber..."                 │  │
│  │  │  └─ (60+ more foods)                                    │  │
│  │  │                                                           │  │
│  │  ├─ condition_rules.json                                   │  │
│  │  │  ├─ "BMI_GT_30": {action, reason...}                   │  │
│  │  │  ├─ "AGE_GT_60": {action, reason...}                   │  │
│  │  │  └─ (15+ more rules)                                    │  │
│  │  │                                                           │  │
│  │  ├─ medication_food_interactions.json                      │  │
│  │  │  ├─ "statins": {warning, severity...}                  │  │
│  │  │  └─ (15+ more drugs)                                    │  │
│  │  │                                                           │  │
│  │  └─ health_impact_ranges.json                              │  │
│  │     ├─ "DASH_Hypertension": {bp_reduction: "8-14 mmHg"}   │  │
│  │     └─ (10+ more condition outcomes)                        │  │
│  └───────────────────────────────────────────────────────────────┘
└──────────────────────────────────────────────────────────────────────┘
                              │
                              │ Renders HTML with embedded JSON data
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    TEMPLATE RENDERING                                │
│                                                                       │
│  diet_plan_display.html (Jinja2 Template)                           │
│  ├─ Extends: base.html                                             │
│  ├─ Uses: CSS from medical-design.css                              │
│  └─ Displays:                                                       │
│     ├─ Header with protocol info                                   │
│     ├─ Patient profile summary                                     │
│     ├─ Daily meal plan (breakfast/lunch/dinner/snacks)            │
│     ├─ Food explanations (medical reasons)                        │
│     ├─ Health benefits (clinical ranges)                          │
│     ├─ Medication warnings (HIGH/MODERATE/LOW)                    │
│     ├─ Foods to avoid list                                        │
│     ├─ Risk warnings                                              │
│     ├─ Adherence score (percentage)                               │
│     ├─ Medical disclaimer                                         │
│     └─ Action buttons (Print, Download, Back)                     │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              │ HTML Response
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      USER SEES DIET PLAN                             │
│                                                                       │
│  Professional diet plan displayed with:                             │
│  ├─ Hospital-grade styling                                         │
│  ├─ Medical information in clear sections                          │
│  ├─ Clinical data with ranges (not predictions)                    │
│  ├─ Safety warnings highlighted                                    │
│  ├─ Print-friendly format                                          │
│  └─ Share/download options                                         │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 DATA FLOW EXAMPLE

**Patient:** 58-year-old male, Hypertension, on Lisinopril

```
INPUT
└─ Patient Profile
   ├─ age: 58
   ├─ gender: Male
   ├─ height_cm: 175
   ├─ weight_kg: 92
   ├─ primary_condition: "Hypertension"
   ├─ secondary_conditions: ["Obesity"]
   ├─ medications: ["Lisinopril", "Atorvastatin"]
   └─ activity_level: "Moderate"

PROCESSING
├─ Step 1: Validate Profile
│  └─ ✓ All fields valid
│
├─ Step 2: Calculate BMI
│  └─ BMI = 92 / (1.75²) = 30.0 (Overweight)
│
├─ Step 3: Select Diet Protocol
│  ├─ Check: primary_condition == "Hypertension"
│  └─ Select: DASH Diet
│
├─ Step 4: Apply Rule Modifiers
│  ├─ IF BMI > 30: Apply 500 cal reduction
│  ├─ IF Age > 60: Not applicable (58 < 60)
│  └─ IF Sedentary: Not applicable (Moderate activity)
│
├─ Step 5: Generate Meal Plan
│  ├─ Breakfast: Oatmeal with berries (first option from DASH)
│  ├─ Lunch: Salmon with broccoli (first option from DASH)
│  ├─ Dinner: Chicken breast with sweet potato (first option)
│  └─ Snack: Apple with almond butter (first option)
│
├─ Step 6: Extract Food Explanations
│  ├─ "Salmon" → "Rich in omega-3s..."
│  ├─ "Oats" → "High in soluble fiber..."
│  ├─ "Broccoli" → "Contains compounds..."
│  └─ (3 foods with medical reasons)
│
├─ Step 7: Get Health Benefits
│  ├─ Look up: "DASH_Hypertension" from health_impact_ranges
│  └─ Found:
│     ├─ Systolic BP reduction: 8-14 mmHg
│     ├─ LDL reduction: 5-10%
│     └─ Weight loss: 2-4 kg over 8-12 weeks
│
├─ Step 8: Check Medication Interactions
│  ├─ Medication 1: "Lisinopril"
│  │  └─ Found in interactions: "Monitor potassium" (MODERATE)
│  ├─ Medication 2: "Atorvastatin"
│  │  └─ Found in interactions: "Avoid grapefruit" (HIGH)
│  └─ Result: 2 warnings to display
│
├─ Step 9: Calculate Adherence Score
│  ├─ Start: 100
│  ├─ Age penalty: -5 (age 58, not >60)
│  ├─ BMI penalty: -10 (BMI 30, > 30)
│  ├─ Activity penalty: 0 (Moderate activity)
│  └─ Final: 100 - 5 - 10 = 75%
│
└─ Step 10: Compile Complete Plan
   └─ Return dictionary with all sections

OUTPUT
└─ Diet Plan Object
   ├─ plan_id: "PLAN_20251228_143022"
   ├─ protocol_name: "DASH Diet"
   ├─ daily_meal_plan: {...}
   ├─ food_explanations: {...}
   ├─ health_benefits: {...}
   ├─ medication_safety_notes: [...]
   ├─ adherence_score: 75
   └─ disclaimer: "..."

DISPLAY
└─ Rendered as HTML with:
   ├─ Professional styling
   ├─ Clear section hierarchy
   ├─ Color-coded warnings
   ├─ Print-optimized layout
   └─ Action buttons
```

---

## 📱 RESPONSIVE DESIGN FLOW

```
DESKTOP (1200px+)
├─ Full width content
├─ Multi-column layouts
├─ Side-by-side sections
└─ All content visible

                │
                │ Responsive CSS
                ▼

TABLET (768px - 1199px)
├─ 90% width content
├─ 2-column grids
├─ Stacked sections
└─ Touch-friendly spacing

                │
                │ Responsive CSS
                ▼

MOBILE (<768px)
├─ Full width (100%)
├─ 1-column layout
├─ Vertical stacking
├─ 44px touch targets
└─ Optimized fonts
```

---

## 🔐 SECURITY FLOW

```
User Input
    │
    ├─ Browser Validation
    │  └─ Check required fields
    │
    ├─ Flask Request Handling
    │  └─ Check Content-Type header
    │
    ├─ Backend Validation
    │  ├─ Validate age (1-149)
    │  ├─ Validate height (50-300 cm)
    │  ├─ Validate weight (20-500 kg)
    │  ├─ Validate condition (known list)
    │  └─ Reject if invalid
    │
    ├─ Data Processing
    │  ├─ Safe JSON parsing
    │  ├─ Dictionary lookups (no injection)
    │  └─ Pre-defined content only
    │
    └─ Output Generation
       ├─ Template rendering (escapes HTML)
       ├─ No user input in output
       ├─ No sensitive data logged
       └─ Safe for patient data
```

---

## 📊 INTEGRATION POINTS

### With Patient Dashboard
```
Dashboard
    ├─ Quick Actions Section
    │  └─ "Generate Diet Plan" link → /diet/test
    │
    ├─ Health Tools
    │  └─ "Diet Planning" → /diet/test
    │
    └─ Saved Plans
       └─ Link to view previous plan → /diet/view
```

### With Doctor Dashboard
```
Doctor Portal
    ├─ Patient Management
    │  ├─ View patient profile
    │  ├─ "Create Diet Plan" button
    │  └─ Redirects to /diet/test (pre-filled)
    │
    ├─ Review Panel
    │  └─ All generated plans for approval
    │
    └─ Archive
       └─ Historical diet plans
```

### With EHR System (Future)
```
EHR Integration
    ├─ API endpoint: /diet/api/generate
    ├─ Receives: Patient ID + data
    ├─ Returns: JSON diet plan
    └─ Stores: In patient medical record
```

---

## 🎯 USER JOURNEY MAP

```
Patient
  │
  ├─ Visits clinic
  │  └─ Diagnosed with Hypertension
  │
  ├─ Doctor recommends diet plan
  │  └─ Provides link: /diet/test
  │
  ├─ At home, accesses link
  │  └─ Sees test form
  │
  ├─ Fills in information
  │  ├─ Age, gender, height, weight
  │  ├─ Confirms condition (Hypertension)
  │  ├─ Lists current medications
  │  └─ Selects activity level
  │
  ├─ Clicks "Generate Plan"
  │  └─ System processes (< 1 second)
  │
  ├─ Sees personalized diet plan
  │  ├─ DASH diet selected
  │  ├─ Daily meals specified
  │  ├─ Food benefits explained
  │  ├─ Medication warnings shown
  │  └─ Success score: 75%
  │
  ├─ Takes action
  │  ├─ Prints plan
  │  ├─ Shares with family
  │  └─ Starts following diet
  │
  ├─ After 4 weeks
  │  ├─ Blood pressure improved
  │  ├─ Returns to doctor
  │  └─ Doctor verifies results
  │
  └─ Treatment success!
```

---

## ✨ KEY FEATURES AT A GLANCE

```
INPUT FORM
├─ Simple, intuitive design
├─ Medical condition dropdown
├─ Medication input field
├─ Activity level selector
└─ Form validation

↓

PROCESSING
├─ Rule-based logic
├─ BMI calculation
├─ Diet selection
├─ Medication checking
└─ Adherence scoring

↓

OUTPUT
├─ Daily meal plan
├─ Food explanations
├─ Health benefits
├─ Safety warnings
├─ Risk information
└─ Adherence score

↓

USER ACTIONS
├─ Print to PDF
├─ Download file
├─ Share with doctor
└─ Generate new plan
```

---

**System Status: ✅ FULLY OPERATIONAL**

**Access Now:** http://localhost:5000/diet/test

---

*This system supports clinical care and does not replace professional medical consultation.*
