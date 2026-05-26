DELETE FROM hospital_charges;
DELETE FROM consultation_fees;

INSERT INTO consultation_fees (consultation_type, fee_amount, is_active) VALUES
('New Consultation', 500, 1),
('Follow-up', 300, 1),
('Specialist Consultation', 1000, 1),
('Emergency Consultation', 800, 1),
('Super Specialist', 1500, 1),
('Tele-consultation', 400, 1),
('Second Opinion', 2000, 1),
('Paediatric Consultation', 600, 1),
('Gynaecology Consultation', 700, 1),
('Dental Consultation', 500, 1);

INSERT INTO hospital_charges (charge_name, charge_category, default_price, is_active) VALUES
-- REGISTRATION & ADMIN (10)
('Registration Fee', 'Admin', 100, 1),
('Admission Charges', 'Admin', 200, 1),
('Medical Record Charges', 'Admin', 50, 1),
('Discharge Summary Charges', 'Admin', 100, 1),
('Medical Certificate Fee', 'Admin', 200, 1),
('Insurance Form Processing', 'Admin', 150, 1),
('Birth Certificate Fee', 'Admin', 100, 1),
('Death Certificate Fee', 'Admin', 100, 1),
('Transfer Summary Fee', 'Admin', 150, 1),
('Medico-Legal Case (MLC) Fee', 'Admin', 500, 1),

-- ROOM & BOARD (16)
('Room Rent - General Ward (per day)', 'Room', 1500, 1),
('Room Rent - Semi-Private (per day)', 'Room', 3000, 1),
('Room Rent - Private AC (per day)', 'Room', 5000, 1),
('Room Rent - Deluxe (per day)', 'Room', 8000, 1),
('Room Rent - Suite (per day)', 'Room', 12000, 1),
('Room Rent - ICU (per day)', 'Room', 10000, 1),
('Room Rent - NICU (per day)', 'Room', 12000, 1),
('Room Rent - PICU (per day)', 'Room', 10000, 1),
('Room Rent - CCU (per day)', 'Room', 10000, 1),
('Room Rent - HDU (per day)', 'Room', 7000, 1),
('Room Rent - Isolation (per day)', 'Room', 6000, 1),
('Room Rent - Labour Room (per day)', 'Room', 5000, 1),
('Day Care Charges', 'Room', 2000, 1),
('Extra Bed / Attendant (per day)', 'Room', 500, 1),
('Diet / Food Charges (per day)', 'Room', 300, 1),
('Linen Charges', 'Room', 100, 1),

-- DOCTOR / PROFESSIONAL FEES (14)
('Consultant Visit (per visit)', 'Professional', 500, 1),
('Specialist Opinion', 'Professional', 1000, 1),
('Super Specialist Opinion', 'Professional', 1500, 1),
('Surgeon Charges', 'Professional', 0, 1),
('Assistant Surgeon Charges', 'Professional', 0, 1),
('Anaesthesia Charges', 'Professional', 0, 1),
('Physiotherapist Consultation', 'Professional', 400, 1),
('Dietician Consultation', 'Professional', 300, 1),
('Psychologist / Psychiatrist', 'Professional', 800, 1),
('Dental Surgeon Charges', 'Professional', 0, 1),
('Ophthalmologist Charges', 'Professional', 0, 1),
('ENT Specialist Charges', 'Professional', 0, 1),
('Paediatrician Visit', 'Professional', 600, 1),
('Gynaecologist Visit', 'Professional', 700, 1),

-- NURSING (6)
('Nursing Charges - General (per day)', 'Nursing', 500, 1),
('Nursing Charges - ICU (per day)', 'Nursing', 1500, 1),
('Special Nursing (per shift 8hr)', 'Nursing', 1000, 1),
('Night Nursing Charges', 'Nursing', 800, 1),
('Nursing Procedure Charges', 'Nursing', 300, 1),
('Home Nursing Visit', 'Nursing', 1500, 1),

-- LAB - HAEMATOLOGY (12)
('Complete Blood Count (CBC)', 'Lab-Haematology', 300, 1),
('Haemoglobin (Hb)', 'Lab-Haematology', 100, 1),
('Platelet Count', 'Lab-Haematology', 150, 1),
('ESR (Erythrocyte Sedimentation Rate)', 'Lab-Haematology', 100, 1),
('Peripheral Blood Smear', 'Lab-Haematology', 200, 1),
('Reticulocyte Count', 'Lab-Haematology', 200, 1),
('Prothrombin Time (PT/INR)', 'Lab-Haematology', 300, 1),
('APTT', 'Lab-Haematology', 350, 1),
('Bleeding Time / Clotting Time', 'Lab-Haematology', 150, 1),
('Blood Grouping and Rh Typing', 'Lab-Haematology', 200, 1),
('Cross Match', 'Lab-Haematology', 300, 1),
('Coombs Test (Direct/Indirect)', 'Lab-Haematology', 400, 1),

-- LAB - BIOCHEMISTRY (22)
('Blood Sugar - Fasting', 'Lab-Biochemistry', 100, 1),
('Blood Sugar - PP', 'Lab-Biochemistry', 100, 1),
('Blood Sugar - Random', 'Lab-Biochemistry', 80, 1),
('HbA1c (Glycated Haemoglobin)', 'Lab-Biochemistry', 400, 1),
('Lipid Profile', 'Lab-Biochemistry', 500, 1),
('Liver Function Test (LFT)', 'Lab-Biochemistry', 600, 1),
('Kidney Function Test (KFT/RFT)', 'Lab-Biochemistry', 500, 1),
('Serum Creatinine', 'Lab-Biochemistry', 200, 1),
('Blood Urea', 'Lab-Biochemistry', 150, 1),
('Serum Uric Acid', 'Lab-Biochemistry', 200, 1),
('Serum Electrolytes (Na/K/Cl)', 'Lab-Biochemistry', 400, 1),
('Serum Calcium', 'Lab-Biochemistry', 200, 1),
('Serum Magnesium', 'Lab-Biochemistry', 250, 1),
('Serum Phosphorus', 'Lab-Biochemistry', 200, 1),
('Serum Protein / Albumin', 'Lab-Biochemistry', 250, 1),
('Bilirubin (Total/Direct)', 'Lab-Biochemistry', 200, 1),
('SGOT / SGPT (AST/ALT)', 'Lab-Biochemistry', 300, 1),
('Alkaline Phosphatase (ALP)', 'Lab-Biochemistry', 200, 1),
('GGT (Gamma GT)', 'Lab-Biochemistry', 300, 1),
('Amylase / Lipase', 'Lab-Biochemistry', 500, 1),
('LDH (Lactate Dehydrogenase)', 'Lab-Biochemistry', 400, 1),
('CPK / CK-MB', 'Lab-Biochemistry', 500, 1),

-- LAB - SEROLOGY / IMMUNOLOGY (12)
('Thyroid Profile (T3/T4/TSH)', 'Lab-Serology', 500, 1),
('Free T3 / Free T4', 'Lab-Serology', 400, 1),
('Vitamin D (25-OH)', 'Lab-Serology', 600, 1),
('Vitamin B12', 'Lab-Serology', 600, 1),
('Ferritin', 'Lab-Serology', 500, 1),
('Iron Studies (TIBC/Iron/Ferritin)', 'Lab-Serology', 800, 1),
('CRP (C-Reactive Protein)', 'Lab-Serology', 400, 1),
('Procalcitonin', 'Lab-Serology', 1500, 1),
('Troponin I / T', 'Lab-Serology', 500, 1),
('D-Dimer', 'Lab-Serology', 700, 1),
('NT-proBNP', 'Lab-Serology', 1500, 1),
('PSA (Prostate Specific Antigen)', 'Lab-Serology', 600, 1),

-- LAB - MICROBIOLOGY (8)
('Blood Culture and Sensitivity', 'Lab-Microbiology', 600, 1),
('Urine Culture and Sensitivity', 'Lab-Microbiology', 500, 1),
('Sputum Culture', 'Lab-Microbiology', 500, 1),
('Wound Swab Culture', 'Lab-Microbiology', 500, 1),
('Stool Culture', 'Lab-Microbiology', 500, 1),
('AFB Staining / TB Culture', 'Lab-Microbiology', 400, 1),
('Fungal Culture', 'Lab-Microbiology', 600, 1),
('Sensitivity Testing (MIC)', 'Lab-Microbiology', 800, 1),

-- LAB - SCREENING (8)
('HIV 1 & 2 Screening', 'Lab-Screening', 300, 1),
('HBsAg (Hepatitis B)', 'Lab-Screening', 300, 1),
('HCV (Hepatitis C) Antibody', 'Lab-Screening', 400, 1),
('VDRL / RPR (Syphilis)', 'Lab-Screening', 200, 1),
('Dengue NS1 Antigen', 'Lab-Screening', 500, 1),
('Dengue IgM / IgG', 'Lab-Screening', 600, 1),
('Malaria (Rapid/Smear)', 'Lab-Screening', 300, 1),
('Widal Test (Typhoid)', 'Lab-Screening', 200, 1),

-- LAB - URINE & STOOL (6)
('Urine Routine & Microscopy', 'Lab-Urine', 150, 1),
('Urine Microalbumin', 'Lab-Urine', 400, 1),
('24hr Urine Protein', 'Lab-Urine', 300, 1),
('Urine Pregnancy Test (UPT)', 'Lab-Urine', 100, 1),
('Stool Routine & Microscopy', 'Lab-Urine', 150, 1),
('Stool Occult Blood', 'Lab-Urine', 200, 1),

-- LAB - HORMONES & TUMOR MARKERS (10)
('Cortisol (Morning/Evening)', 'Lab-Hormones', 500, 1),
('Prolactin', 'Lab-Hormones', 500, 1),
('FSH / LH', 'Lab-Hormones', 500, 1),
('Estradiol / Progesterone', 'Lab-Hormones', 600, 1),
('Testosterone', 'Lab-Hormones', 500, 1),
('Beta HCG (Pregnancy)', 'Lab-Hormones', 500, 1),
('CA-125 (Ovarian Marker)', 'Lab-Hormones', 800, 1),
('CA 19-9 (Pancreatic Marker)', 'Lab-Hormones', 800, 1),
('CEA (Tumour Marker)', 'Lab-Hormones', 700, 1),
('AFP (Alpha Fetoprotein)', 'Lab-Hormones', 600, 1),

-- RADIOLOGY (14)
('X-Ray - Single View', 'Radiology', 400, 1),
('X-Ray - Two Views', 'Radiology', 600, 1),
('X-Ray - Chest PA', 'Radiology', 400, 1),
('X-Ray - Abdomen', 'Radiology', 500, 1),
('X-Ray - Spine', 'Radiology', 500, 1),
('Ultrasound (USG) - Abdomen', 'Radiology', 1200, 1),
('Ultrasound (USG) - Pelvis', 'Radiology', 1000, 1),
('Ultrasound (USG) - KUB', 'Radiology', 1000, 1),
('USG - Obstetric (Pregnancy)', 'Radiology', 1200, 1),
('USG - Doppler Study', 'Radiology', 2000, 1),
('CT Scan - Plain', 'Radiology', 3500, 1),
('CT Scan - Contrast', 'Radiology', 5000, 1),
('CT Angiography', 'Radiology', 8000, 1),
('HRCT Chest', 'Radiology', 4000, 1),

-- MRI (6)
('MRI - Brain Plain', 'MRI', 6000, 1),
('MRI - Brain Contrast', 'MRI', 8000, 1),
('MRI - Spine', 'MRI', 6000, 1),
('MRI - Abdomen', 'MRI', 7000, 1),
('MRI - Joint / Extremity', 'MRI', 5000, 1),
('MRI - Whole Body', 'MRI', 15000, 1),

-- MAMMOGRAPHY & DEXA (3)
('Mammography (Both Breasts)', 'Imaging', 1500, 1),
('Bone Densitometry (DEXA)', 'Imaging', 2000, 1),
('OPG (Dental X-Ray)', 'Imaging', 500, 1),

-- CARDIAC (8)
('ECG (12-Lead)', 'Cardiac', 300, 1),
('2D Echocardiography', 'Cardiac', 2000, 1),
('TMT / Stress Test', 'Cardiac', 1500, 1),
('Holter Monitoring (24hr)', 'Cardiac', 3000, 1),
('Coronary Angiography', 'Cardiac', 15000, 1),
('Angioplasty (PTCA) - Single Stent', 'Cardiac', 80000, 1),
('Pacemaker Implantation', 'Cardiac', 100000, 1),
('Cardiac Catheterization', 'Cardiac', 20000, 1),

-- NEURO (4)
('EEG (Electroencephalogram)', 'Neuro', 1500, 1),
('EMG / NCV Study', 'Neuro', 2500, 1),
('Video EEG Monitoring', 'Neuro', 5000, 1),
('Evoked Potentials (VEP/BERA)', 'Neuro', 2000, 1),

-- ENDOSCOPY / GI (6)
('Upper GI Endoscopy (OGD)', 'Endoscopy', 3000, 1),
('Colonoscopy', 'Endoscopy', 5000, 1),
('Sigmoidoscopy', 'Endoscopy', 3000, 1),
('ERCP', 'Endoscopy', 15000, 1),
('Bronchoscopy', 'Endoscopy', 4000, 1),
('Cystoscopy', 'Endoscopy', 5000, 1),

-- PULMONOLOGY (3)
('Spirometry / PFT', 'Pulmonology', 800, 1),
('Sleep Study (Polysomnography)', 'Pulmonology', 5000, 1),
('Thoracentesis', 'Pulmonology', 2000, 1),

-- PROCEDURE / TREATMENT (22)
('IV Fluids Administration', 'Procedure', 200, 1),
('Injection Charges (IV/IM/SC)', 'Procedure', 100, 1),
('Blood Transfusion (per unit)', 'Procedure', 1500, 1),
('Platelet Transfusion', 'Procedure', 3000, 1),
('FFP Transfusion', 'Procedure', 2000, 1),
('Packed RBC Transfusion', 'Procedure', 1800, 1),
('Dressing - Minor', 'Procedure', 300, 1),
('Dressing - Major', 'Procedure', 800, 1),
('Wound Debridement', 'Procedure', 2000, 1),
('Catheterization (Urinary)', 'Procedure', 500, 1),
('Ryles Tube Insertion', 'Procedure', 300, 1),
('Central Line Insertion', 'Procedure', 3000, 1),
('Arterial Line Insertion', 'Procedure', 2000, 1),
('Lumbar Puncture', 'Procedure', 2000, 1),
('Biopsy - FNAC', 'Procedure', 1500, 1),
('Biopsy - Excision', 'Procedure', 3000, 1),
('Paracentesis / Ascitic Tap', 'Procedure', 1500, 1),
('Pleural Tap', 'Procedure', 2000, 1),
('Intercostal Drainage (ICD)', 'Procedure', 5000, 1),
('Suturing - Minor (< 5 stitches)', 'Procedure', 500, 1),
('Suturing - Major (> 5 stitches)', 'Procedure', 1500, 1),
('Plaster / Cast Application', 'Procedure', 1000, 1),

-- DIALYSIS (4)
('Haemodialysis (per session)', 'Dialysis', 3000, 1),
('Peritoneal Dialysis', 'Dialysis', 2500, 1),
('CRRT (per day)', 'Dialysis', 15000, 1),
('AV Fistula Creation', 'Dialysis', 15000, 1),

-- ONCOLOGY (4)
('Chemotherapy Administration', 'Oncology', 0, 1),
('Radiotherapy (per session)', 'Oncology', 0, 1),
('Brachytherapy', 'Oncology', 0, 1),
('PET-CT Scan', 'Oncology', 15000, 1),

-- OPERATION THEATRE (12)
('OT Charges - Minor Surgery', 'OT', 3000, 1),
('OT Charges - Intermediate', 'OT', 5000, 1),
('OT Charges - Major Surgery', 'OT', 8000, 1),
('OT Charges - Super Major', 'OT', 15000, 1),
('OT Consumables / Disposables', 'OT', 0, 1),
('Surgical Implants / Prosthesis', 'OT', 0, 1),
('Suture Material', 'OT', 500, 1),
('Surgical Stapler', 'OT', 3000, 1),
('Laparoscopy Charges', 'OT', 5000, 1),
('Cautery Charges', 'OT', 1000, 1),
('Tourniquet Charges', 'OT', 500, 1),
('C-Arm (Fluoroscopy) Usage', 'OT', 3000, 1),

-- OXYGEN & VENTILATOR (8)
('Oxygen - Per Hour', 'Oxygen', 100, 1),
('Oxygen - Per Day', 'Oxygen', 1500, 1),
('Oxygen Cylinder', 'Oxygen', 500, 1),
('Nebulization (per session)', 'Oxygen', 150, 1),
('High Flow Nasal Cannula (per day)', 'Oxygen', 2500, 1),
('Ventilator Charges (per day)', 'Ventilator', 5000, 1),
('BiPAP / CPAP (per day)', 'Ventilator', 3000, 1),
('NIV (Non-Invasive Ventilation)', 'Ventilator', 4000, 1),

-- PHYSIOTHERAPY & REHAB (6)
('Physiotherapy Session', 'Physio', 500, 1),
('Occupational Therapy', 'Physio', 400, 1),
('Speech Therapy', 'Physio', 500, 1),
('Rehabilitation Session', 'Physio', 600, 1),
('Chest Physiotherapy', 'Physio', 300, 1),
('Post-Operative Physio', 'Physio', 500, 1),

-- EMERGENCY (8)
('Emergency Room Charges', 'Emergency', 1000, 1),
('Emergency Consultation', 'Emergency', 800, 1),
('Trauma Care Charges', 'Emergency', 2000, 1),
('Resuscitation / CPR Charges', 'Emergency', 5000, 1),
('Defibrillation', 'Emergency', 3000, 1),
('Emergency Intubation', 'Emergency', 2000, 1),
('Poison Management', 'Emergency', 3000, 1),
('Snake Bite / Animal Bite Kit', 'Emergency', 2000, 1),

-- AMBULANCE (6)
('Ambulance - Basic (within city)', 'Ambulance', 1500, 1),
('Ambulance - AC (within city)', 'Ambulance', 2500, 1),
('Ambulance - Advanced Life Support', 'Ambulance', 5000, 1),
('Ambulance - Neonatal', 'Ambulance', 8000, 1),
('Ambulance - Per KM (outstation)', 'Ambulance', 25, 1),
('Dead Body Van', 'Ambulance', 2000, 1),

-- OBSTETRICS & GYNAECOLOGY (8)
('Normal Delivery Charges', 'OB-GYN', 15000, 1),
('Caesarean Section (LSCS)', 'OB-GYN', 35000, 1),
('Episiotomy Charges', 'OB-GYN', 2000, 1),
('D&C / Evacuation', 'OB-GYN', 5000, 1),
('Hysterectomy Charges', 'OB-GYN', 0, 1),
('IUD Insertion', 'OB-GYN', 500, 1),
('Pap Smear', 'OB-GYN', 500, 1),
('Colposcopy', 'OB-GYN', 2000, 1),

-- ORTHOPAEDICS (6)
('Fracture Reduction (Closed)', 'Ortho', 3000, 1),
('Fracture Fixation (Open/ORIF)', 'Ortho', 0, 1),
('Joint Replacement (TKR/THR)', 'Ortho', 0, 1),
('Arthroscopy', 'Ortho', 15000, 1),
('Traction Charges (per day)', 'Ortho', 500, 1),
('Crepe Bandage / Splint', 'Ortho', 300, 1),

-- OPHTHALMOLOGY (4)
('Cataract Surgery (Phaco)', 'Eye', 15000, 1),
('IOL Implant Charges', 'Eye', 0, 1),
('Retinal Laser', 'Eye', 5000, 1),
('Fundoscopy', 'Eye', 500, 1),

-- ENT (4)
('Tonsillectomy', 'ENT', 10000, 1),
('Septoplasty', 'ENT', 15000, 1),
('Myringotomy / Grommet', 'ENT', 5000, 1),
('Audiometry / Hearing Test', 'ENT', 500, 1),

-- DENTAL (4)
('Tooth Extraction (Simple)', 'Dental', 500, 1),
('Tooth Extraction (Surgical)', 'Dental', 2000, 1),
('Root Canal Treatment', 'Dental', 3000, 1),
('Scaling / Cleaning', 'Dental', 800, 1),

-- PHARMACY & CONSUMABLES (6)
('Medicines (as per pharmacy bill)', 'Pharmacy', 0, 1),
('Surgical Consumables', 'Consumables', 0, 1),
('Disposables / PPE Kit', 'Consumables', 500, 1),
('Gloves / Syringes / Cannula', 'Consumables', 0, 1),
('Catheter / Urobag', 'Consumables', 300, 1),
('Blood Bag Charges', 'Consumables', 500, 1),

-- MISCELLANEOUS (6)
('Documentation Charges', 'Misc', 100, 1),
('Photocopying Charges', 'Misc', 50, 1),
('Courier Charges (reports)', 'Misc', 100, 1),
('Attendant Pass Charges', 'Misc', 50, 1),
('Parking Charges', 'Misc', 50, 1),
('Miscellaneous Charges', 'Misc', 0, 1);
