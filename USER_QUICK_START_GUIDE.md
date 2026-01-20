# 🎯 QUICK USAGE GUIDE - Hospital AI Health Management System

## 🚀 Start Using the System

### 1. **Access the Application**
```
URL: http://127.0.0.1:5000
Status: ✅ Server Running
```

### 2. **Register or Login**

**For Patients:**
- Go to: `http://127.0.0.1:5000/patient/register`
- Fill in: Username, Email, Password
- Click: "Register as Patient"
- Then login at: `/patient/login`

**For Doctors:**
- Go to: `http://127.0.0.1:5000/doctor/register`
- Fill in: Username, Email, Password, Specialization
- Click: "Register as Doctor"
- Then login at: `/doctor/login`

---

## 📋 PATIENT GUIDE

### Dashboard Features

#### 1. **Record Health Data** 
- Click: "Record Health Data" button
- Enter vital signs:
  - Systolic BP (top number)
  - Diastolic BP (bottom number)
  - Heart Rate (beats per minute)
  - Fasting Sugar (mg/dL)
  - Random Sugar (mg/dL)
- Get instant AI analysis with risk scores

#### 2. **Book Appointment**
- Click: "Book Appointment" button
- Select: Doctor from dropdown
- Choose: Date and Time
- Enter: Reason for visit
- Click: "Book Appointment"
- Doctor will confirm

#### 3. **AI Image Analysis** ⭐ NEW
- Click: "AI Image Analysis" button
- Select: Image type (X-Ray, CT, MRI, etc.)
- Upload: Your medical image file
- Enter: Clinical context (optional)
- View: AI-generated analysis with findings

#### 4. **View Diet Plan**
- Click: "View Diet Plan" button
- Get personalized nutrition recommendations
- View: Calorie targets and meal suggestions
- Based on your health profile

#### 5. **View Exercise Plan**
- Click: "View Exercise Plan" button
- Get personalized fitness recommendations
- View: Activities and duration
- Based on your health profile

#### 6. **View Profile**
- Click: "Profile" in navigation
- View: Your personal information
- Click: "Edit Profile" to make changes

#### 7. **View Appointments**
- Click: "Appointments" link in navigation
- See: All your scheduled appointments
- Check: Status of each appointment

#### 8. **Chat with Doctor**
- Go to: Appointments page
- Click: "Chat" button next to doctor's name
- Send: Messages to your healthcare provider
- Real-time communication

---

## 👨‍⚕️ DOCTOR GUIDE

### Dashboard Features

#### 1. **View Patient List**
- Click: "Patient List" button
- See: All registered patients
- Click: "View Details" to see patient info

#### 2. **Manage Appointments**
- Click: "Appointments" button
- See: All scheduled appointments
- Click: "Confirm" to approve
- Click: "Cancel" if needed

#### 3. **View Patient Details**
- Go to: Patient List
- Click: "View Details" on a patient
- See: Medical history, health data, appointments

#### 4. **Write Prescriptions**
- Go to: Patient List
- Find: Patient name
- Click: "Write Prescription"
- Enter: Medications and instructions
- Submit: Prescription

#### 5. **Chat with Patient**
- Go to: Appointments
- Click: "Chat" next to patient name
- Send: Messages and guidance
- Real-time communication

#### 6. **View Analytics**
- Click: "Analytics" button
- See: Statistics and trends
- View: Patient demographics
- Track: Health conditions distribution

---

## 🖼️ MEDICAL IMAGE ANALYSIS - DETAILED GUIDE

### How to Upload & Analyze Medical Images

**Step 1: Navigate to Image Upload**
- Login as Patient
- Click: "AI Image Analysis" button on dashboard

**Step 2: Select Image Type**
Choose from:
- ✅ **X-Ray** - Chest, bone, dental X-rays
- ✅ **CT Scan** - CT or CAT scan images
- ✅ **MRI Scan** - Magnetic resonance images
- ✅ **Pathology Slide** - Tissue/biopsy samples
- ✅ **Dermatology** - Skin condition images
- ✅ **Ultrasound** - Ultrasound images
- ✅ **ECG/Cardiac** - Heart rhythm traces

**Step 3: Upload Image**
- Supported formats: JPEG, PNG, TIFF, BMP, GIF
- Max file size: 10MB
- Click: "Choose File" and select your image

**Step 4: Add Context (Optional)**
- Describe: Symptoms or concerns
- Example: "Found this spot on my leg"
- Helps: AI provide better analysis

**Step 5: Submit for Analysis**
- Click: "Upload & Analyze" button
- Wait: 5-10 seconds for AI processing
- View: Detailed analysis results

**Step 6: Review Results**
The analysis includes:
- 📊 **Confidence Score** - How sure the AI is (0-100%)
- 🔍 **Findings** - What the AI detected
- 📝 **Observations** - Additional details
- ⚠️ **Risk Level** - High/Medium/Low
- 💊 **Recommendations** - What to do next
- 🏷️ **Detected Conditions** - Potential issues

**Step 7: Share with Doctor**
- Print: Click "Print Report" button
- Share: Show results to your doctor
- Discuss: Medical recommendations

---

## ⚙️ TROUBLESHOOTING

### Problem: Can't login
**Solution:** Make sure you registered first, then try again

### Problem: Images won't upload
**Solution:** Check file format (JPEG, PNG, TIFF, BMP, GIF) and size (< 10MB)

### Problem: Server not responding
**Solution:** Make sure `python run.py` is running in terminal

### Problem: Missing appointment doctor
**Solution:** Doctor must register and be verified first

### Problem: Slow image analysis
**Solution:** This is normal for first upload. Subsequent uploads will be faster.

---

## 🔒 SECURITY TIPS

✅ **Do:**
- Change your password regularly
- Don't share your login credentials
- Use HTTPS in production
- Keep sensitive information private
- Verify doctor credentials

❌ **Don't:**
- Share your session/cookies
- Upload to public networks
- Leave computer unattended while logged in
- Use same password as other accounts
- Store passwords in plain text

---

## 📞 KEY INFORMATION

### System Features
- **Authentication:** Secure login with role-based access
- **AI Models:** 6 prediction models + medical imaging
- **Database:** Encrypted data storage
- **Communication:** Real-time chat system
- **Analysis:** Instant AI-powered recommendations

### Supported Image Types for Analysis
1. X-Rays (Chest, Bone, Dental)
2. CT Scans
3. MRI Images
4. Pathology Slides
5. Dermatology Photos
6. Ultrasound Images
7. ECG/Cardiac Traces

### Health Metrics Tracked
- Blood Pressure (Systolic/Diastolic)
- Heart Rate (BPM)
- Blood Sugar (Fasting & Random)
- BMI (Body Mass Index)
- Risk Scores (Diabetes, Heart, Hypertension)

---

## 📊 UNDERSTANDING YOUR HEALTH SCORES

### Risk Levels
- 🟢 **Low Risk** (0-30%) - Keep up healthy habits
- 🟡 **Medium Risk** (30-60%) - Make lifestyle changes
- 🔴 **High Risk** (60-100%) - Consult with doctor

### BMI Categories
- Underweight: < 18.5
- Normal: 18.5-24.9
- Overweight: 25-29.9
- Obese: 30+

### Blood Pressure
- Normal: < 120/80 mmHg
- Elevated: 120-129/<80 mmHg
- High BP Stage 1: 130-139/80-89 mmHg
- High BP Stage 2: ≥ 140/90 mmHg

### Blood Sugar
- Normal Fasting: 70-100 mg/dL
- Prediabetic: 100-125 mg/dL
- Diabetic: ≥ 126 mg/dL

---

## 🎓 BEST PRACTICES

### For Patients:
1. Record health data regularly
2. Follow doctor recommendations
3. Upload medical images for AI analysis
4. Maintain healthy lifestyle
5. Attend scheduled appointments
6. Take prescribed medications
7. Chat with doctor about concerns

### For Doctors:
1. Review patient histories
2. Approve/respond to appointments
3. Write detailed prescriptions
4. Analyze patient medical images
5. Use analytics for trends
6. Communicate regularly
7. Update patient information

---

## ✨ NEW FEATURES HIGHLIGHT

### 🌟 Medical Image Analysis
- Upload X-rays, CT scans, MRI images
- Get AI analysis powered by MedGemma-4B
- Receive professional recommendations
- Share results with your doctor
- Print comprehensive reports

### 🎯 AI Health Predictions
- Diabetes risk assessment
- Heart disease prediction
- Hypertension screening
- Personalized diet plans
- Customized exercise routines

### 💬 Direct Communication
- Chat with doctors
- Real-time messaging
- Prescription delivery
- Appointment confirmation
- Health guidance

---

## 🚀 GETTING STARTED CHECKLIST

- [ ] Access http://127.0.0.1:5000
- [ ] Register as Patient or Doctor
- [ ] Login to your account
- [ ] Complete your profile
- [ ] Record health data (Patient)
- [ ] Book appointment (Patient)
- [ ] Upload medical image (Patient) ⭐ NEW
- [ ] View AI analysis results
- [ ] Chat with healthcare provider
- [ ] Share results with doctor

---

## 📱 MOBILE ACCESS

The system is fully responsive and works on:
- ✅ Desktop computers
- ✅ Tablets
- ✅ Mobile phones
- ✅ Any modern browser

---

**Happy using! If you have any questions, refer to the comprehensive COMPLETE_IMPLEMENTATION_STATUS.md document.**

**System Status:** 🟢 **OPERATIONAL & READY**

Created: November 14, 2025
Version: 1.0
