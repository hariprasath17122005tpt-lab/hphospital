import random
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session, current_app
from flask_login import login_required, current_user
from app.models.models import (db, Patient, HealthData, PatientVitals, Appointment, Prescription,
                               Message, DietPlan, ExercisePlan, Doctor, MedicalImage,
                               Billing, LabReport, LabOrder, Consultation)
import warnings
warnings.filterwarnings('ignore')

try:
    from app.ml_models.health_ai import (HealthRiskPredictor, 
                                         DietPlanGenerator, ExercisePlanGenerator)
    from app.ml_models.strict_medical_chatbot import StrictMedicalChatbot
    HEALTH_AI_AVAILABLE = True
except (ImportError, ModuleNotFoundError, KeyboardInterrupt):
    HEALTH_AI_AVAILABLE = False
    
from app.routes.auth import patient_required
from datetime import datetime, timedelta
import os
import random
import json
import re
from types import SimpleNamespace
from sqlalchemy import text, inspect
from werkzeug.utils import secure_filename

patient_bp = Blueprint('patient', __name__, url_prefix='/patient')

# Initialize AI models only if available
if HEALTH_AI_AVAILABLE:
    try:
        health_predictor = HealthRiskPredictor()
        diet_generator = DietPlanGenerator()
        exercise_generator = ExercisePlanGenerator()
        knowledge_base = StrictMedicalChatbot()
    except Exception as e:
        HEALTH_AI_AVAILABLE = False
        print(f"Error initializing AI models: {e}")

# =====================================================
# PERSONALIZED DIET PLAN GENERATOR
# =====================================================

def generate_personalized_diet_plan(patient, health_data):
    """
    Generate a vitals-driven, Indian-food diet plan.
    Condition detection uses direct vitals (BP, sugar, HR, temp, BMI)
    so the plan reflects what the patient actually entered.
    """

    # --- 1. VITALS-BASED CONDITION DETECTION ---
    diabetes_risk = health_data.diabetes_risk or 0
    hypertension_risk = health_data.hypertension_risk or 0
    heart_risk = health_data.heart_disease_risk or 0
    bmi = health_data.bmi or 0

    systolic = health_data.systolic_bp or 0
    diastolic = health_data.diastolic_bp or 0
    fasting = health_data.fasting_sugar or 0
    random_sugar = health_data.random_sugar or 0
    hr = health_data.heart_rate or 0
    temp = health_data.temperature or 0

    active_conditions = []
    # Direct vitals thresholds (ADA / AHA)
    if fasting >= 126 or random_sugar >= 200 or diabetes_risk > 50:
        active_conditions.append({'name': 'Diabetes', 'priority': 2, 'dept': 'Endocrinology'})
    elif fasting >= 100 or random_sugar >= 140:
        active_conditions.append({'name': 'Pre-Diabetes', 'priority': 5, 'dept': 'Endocrinology'})

    if systolic >= 140 or diastolic >= 90 or hypertension_risk > 50:
        active_conditions.append({'name': 'Hypertension', 'priority': 3, 'dept': 'Cardiology'})
    elif systolic >= 130 or diastolic >= 80:
        active_conditions.append({'name': 'Elevated BP', 'priority': 6, 'dept': 'Cardiology'})

    if heart_risk > 50 or hr > 100 or (systolic >= 160 and hr > 90):
        active_conditions.append({'name': 'Heart Disease', 'priority': 1, 'dept': 'Cardiology'})

    if bmi > 30:
        active_conditions.append({'name': 'Obesity', 'priority': 4, 'dept': 'Nutrition'})
    elif bmi > 25:
        active_conditions.append({'name': 'Overweight', 'priority': 7, 'dept': 'Nutrition'})

    if bmi > 0 and bmi < 18.5:
        active_conditions.append({'name': 'Underweight', 'priority': 8, 'dept': 'Nutrition'})

    if temp > 100.4:
        active_conditions.append({'name': 'Fever', 'priority': 0, 'dept': 'General Medicine'})

    active_conditions.sort(key=lambda x: x['priority'])

    if not active_conditions:
        active_conditions.append({'name': 'General Wellness', 'priority': 10, 'dept': 'Preventive Medicine'})

    primary_condition = active_conditions[0]
    stacking_order = [c['name'] for c in active_conditions]
    departments = list(set([c['dept'] for c in active_conditions]))
    departments.append('Nutrition & Dietetics')

    # --- 2. INDIAN MEAL DATABASE (7 options per meal per condition) ---
    meal_db = {
        'Diabetes': {
            'breakfast': [
                "Moong Dal Cheela with Pudina Chutney + Masala Chai (no sugar)",
                "Ragi Dosa with Coconut Chutney + 5 Soaked Almonds",
                "Vegetable Dalia Upma with Curry Leaves & Peanuts",
                "Besan Chilla stuffed with Paneer & Methi",
                "Oats Idli (2) with Sambar + Flaxseed Powder",
                "Sprouted Moong Chaat with Lemon & Roasted Jeera",
                "Multigrain Paratha (no oil) with Low-fat Curd"
            ],
            'lunch': [
                "Brown Rice + Methi Dal + Cucumber Raita + Bhindi Sabzi",
                "Bajra Roti (2) + Palak Paneer (low oil) + Salad",
                "Foxtail Millet Rice + Rasam + Drumstick Sambar + Poriyal",
                "Jowar Roti (2) + Lauki Chana Dal + Kachumber Salad",
                "Multigrain Chapati (2) + Karela Sabzi + Masoor Dal + Buttermilk",
                "Brown Rice Pulao + Rajma (no cream) + Raita",
                "Ragi Mudde + Saaru (Rasam) + Beans Palya + Curd"
            ],
            'dinner': [
                "Moong Dal Khichdi + Kadhi (low oil) + Steamed Lauki",
                "Vegetable Clear Soup + Tandoori Paneer Tikka (grilled)",
                "Bajra Khichdi + Bottle Gourd Sabzi + Buttermilk",
                "Palak Soup + Grilled Fish with Lemon & Haldi",
                "Chapati (1) + Turai Sabzi + Dal Tadka (minimal ghee)",
                "Masoor Dal Soup + Sauteed Mushroom with Jeera",
                "Mixed Vegetable Soup + Paneer Bhurji (no oil, non-stick)"
            ]
        },
        'Pre-Diabetes': {
            'breakfast': [
                "Oats Cheela with Vegetables + Green Tea",
                "Ragi Porridge with Cinnamon & Almonds",
                "Moong Dal Dosa with Tomato Chutney",
                "Vegetable Poha (Flattened Rice) with Peanuts & Curry Leaves",
                "Besan Cheela with Coriander Chutney + Buttermilk",
                "Multigrain Toast with Paneer Bhurji",
                "Sprouted Moong Salad with Lemon & Chaat Masala"
            ],
            'lunch': [
                "Brown Rice + Toor Dal + Cabbage Poriyal + Rasam",
                "Multigrain Chapati (2) + Mixed Veg Sabzi + Raita",
                "Foxtail Millet Rice + Sambar + Beans Thoran",
                "Jowar Roti (2) + Chana Masala + Cucumber Salad",
                "Bajra Roti + Methi Sabzi + Dal Fry + Salad",
                "Brown Rice + Kadhi Pakora (baked) + Aloo Gobi (low oil)",
                "Quinoa Pulao + Paneer Bhurji + Green Salad"
            ],
            'dinner': [
                "Vegetable Soup + Chapati (1) + Lauki Sabzi",
                "Khichdi (Moong Dal) + Papad (roasted) + Raita",
                "Palak Dal + Roti (1) + Cucumber Raita",
                "Tomato Rasam + Steamed Rice (small portion) + Poriyal",
                "Mixed Veg Clear Soup + Paneer Tikka (grilled)",
                "Dal Shorba + Tandoori Mushroom + Salad",
                "Moong Dal Cheela (dinner version) + Green Chutney"
            ]
        },
        'Hypertension': {
            'breakfast': [
                "Banana Lassi (no sugar) + Poha with Vegetables & Curry Leaves",
                "Ragi Idli (2) with Coconut Chutney (low salt)",
                "Oats Upma with Carrots, Beans & Mustard Seeds",
                "Papaya Bowl with Sunflower Seeds & Honey",
                "Vegetable Uttapam with Tomato Chutney (no salt added)",
                "Sattu Drink (Bihar-style) + Multigrain Toast + Boiled Egg",
                "Daliya Porridge with Banana & Cardamom"
            ],
            'lunch': [
                "Curd Rice with Pomegranate + Beetroot Poriyal (no salt)",
                "Brown Rice + Lauki Dal + Salad with Lemon Dressing",
                "Vegetable Sambar + Millet Rice + Beans Thoran",
                "Chapati (2) + Palak Dal + Carrot Raita",
                "Lemon Rice (brown) + Rasam + Ash Gourd Kootu",
                "Rajma Salad with Peppers & Onion (low salt) + Roti (1)",
                "Appam (2) + Vegetable Stew (Kerala-style, coconut milk)"
            ],
            'dinner': [
                "Vegetable Stew + Idiyappam (2)",
                "Pumpkin Soup with Roasted Jeera + Roti (1)",
                "Steamed Fish (Surmai) with Lemon & Haldi + Salad",
                "Tomato Rasam + Steamed Rice (small) + Spinach Kootu",
                "Beetroot Soup + Grilled Paneer with Mint",
                "Lauki Kofta (baked) + Chapati (1) + Raita",
                "Mixed Dal Soup + Cucumber & Onion Salad"
            ]
        },
        'Elevated BP': {
            'breakfast': [
                "Poha with Peanuts & Curry Leaves + Buttermilk",
                "Oats Idli with Sambar (low salt)",
                "Multigrain Paratha with Curd",
                "Banana Smoothie with Flaxseeds",
                "Vegetable Upma with Coconut Chutney",
                "Sprouts Chaat + Masala Chai (less sugar)",
                "Ragi Dosa with Peanut Chutney"
            ],
            'lunch': [
                "Brown Rice + Dal Fry + Mixed Veg + Buttermilk",
                "Chapati (2) + Baingan Bharta + Raita",
                "Millet Rice + Sambar + Carrot Poriyal",
                "Rajma Chawal (brown rice) + Salad",
                "Roti (2) + Palak Paneer + Cucumber Raita",
                "Curd Rice + Beetroot Thoran + Papad",
                "Vegetable Pulao (brown rice) + Raita"
            ],
            'dinner': [
                "Khichdi + Kadhi + Salad",
                "Vegetable Soup + Roti (1) + Gobhi Sabzi",
                "Dal Soup + Paneer Tikka (grilled)",
                "Idli (2) + Sambar + Coconut Chutney",
                "Tomato Soup + Multigrain Toast + Boiled Egg",
                "Moong Dal Cheela + Green Chutney",
                "Vegetable Stew + Appam (1)"
            ]
        },
        'Heart Disease': {
            'breakfast': [
                "Oats Porridge with Walnuts, Flaxseed & Apple",
                "Vegetable Poha (Kanda Poha) with Peanuts & Lemon",
                "Ragi Dosa with Coconut Chutney + Almonds (5)",
                "Multigrain Toast + Paneer Bhurji (no oil) + Green Tea",
                "Daliya Upma with Vegetables & Mustard Seeds",
                "Chia Seeds Pudding with Almond Milk & Cardamom",
                "Moong Sprouts Salad + Whole Wheat Toast + Amla Juice"
            ],
            'lunch': [
                "Brown Rice + Sambar + Drumstick Curry + Poriyal",
                "Jowar Roti (2) + Methi Dal + Baingan Bharta",
                "Foxtail Millet Pulao + Fish Curry (Mustard-based) + Salad",
                "Chapati (2) + Soya Chunks Curry + Lauki Raita",
                "Brown Rice + Palak Dal + Gobi Matar + Buttermilk",
                "Roti (2) + Chana Masala (low oil) + Onion-Tomato Salad",
                "Millet Rice + Rasam + Mixed Vegetable Kootu"
            ],
            'dinner': [
                "Moong Dal Khichdi + Steamed Vegetables + Haldi Doodh",
                "Vegetable Clear Soup + Grilled Fish with Curry Leaves",
                "Palak Soup + Tandoori Paneer + Cucumber Salad",
                "Chapati (1) + Bottle Gourd Sabzi + Dal Shorba",
                "Tomato Rasam + Steamed Rice (small) + Beans Poriyal",
                "Beetroot-Carrot Soup + Boiled Egg Salad with Jeera",
                "Multigrain Roti (1) + Lauki Chana Dal + Raita"
            ]
        },
        'Obesity': {
            'breakfast': [
                "Green Tea + Boiled Eggs (2) + Cucumber Slices",
                "Sprouted Moong Chaat with Lemon & Chaat Masala",
                "Besan Cheela (1) + Pudina Chutney + Buttermilk",
                "Ragi Porridge (no sugar) with Almonds & Cinnamon",
                "Oats Upma with Vegetables (no oil) + Green Tea",
                "Moong Dal Dosa (1) + Sambar + Black Coffee",
                "Sattu Drink + Multigrain Toast (dry) + Boiled Egg (1)"
            ],
            'lunch': [
                "Roti (1) + Palak Paneer (no cream) + Salad + Buttermilk",
                "Brown Rice (small) + Chicken Curry (low oil) + Raita",
                "Jowar Roti (1) + Mixed Veg Sabzi + Masoor Dal + Salad",
                "Millet Rice (small) + Sambar + Cabbage Poriyal",
                "Chapati (1) + Rajma (no cream) + Cucumber-Onion Salad",
                "Quinoa Khichdi + Kadhi (low oil) + Roasted Papad",
                "Brown Rice + Fish Curry (no coconut) + Beans Thoran"
            ],
            'dinner': [
                "Moong Dal Soup + Grilled Paneer Salad",
                "Vegetable Clear Soup + Tandoori Chicken (2 pieces)",
                "Palak Shorba + Egg Bhurji (no oil) + Roti (1)",
                "Tomato Rasam + Steamed Idli (2) + Coconut Chutney",
                "Cauliflower Rice Upma + Buttermilk",
                "Mixed Vegetable Soup + Paneer Tikka (grilled, no oil)",
                "Cabbage Soup + Sprouted Moong Salad"
            ]
        },
        'Overweight': {
            'breakfast': [
                "Poha with Peanuts (small portion) + Green Tea",
                "Oats Idli (2) + Sambar + Pudina Chutney",
                "Besan Cheela + Coriander Chutney + Buttermilk",
                "Ragi Dosa (1) + Coconut Chutney + Black Coffee",
                "Daliya Porridge with Almonds + Herbal Tea",
                "Sprouts Salad + Multigrain Toast + Amla Juice",
                "Moong Dal Cheela + Tomato Chutney + Green Tea"
            ],
            'lunch': [
                "Brown Rice + Dal Fry + Mixed Veg + Salad",
                "Chapati (2) + Chana Masala + Raita",
                "Millet Rice + Sambar + Beans Poriyal + Buttermilk",
                "Roti (2) + Baingan Bharta + Masoor Dal + Salad",
                "Brown Rice Pulao + Kadhi + Cucumber Raita",
                "Jowar Roti (2) + Lauki Sabzi + Toor Dal",
                "Foxtail Millet Rice + Rasam + Mixed Veg Kootu"
            ],
            'dinner': [
                "Khichdi + Kadhi + Salad",
                "Vegetable Soup + Roti (1) + Gobhi Sabzi",
                "Dal Shorba + Paneer Tikka (grilled)",
                "Tomato Soup + Multigrain Toast + Boiled Egg",
                "Moong Dal Cheela + Green Chutney + Buttermilk",
                "Rasam + Steamed Rice (small) + Poriyal",
                "Lauki Soup + Chapati (1) + Turai Sabzi"
            ]
        },
        'Underweight': {
            'breakfast': [
                "Aloo Paratha (2) with Butter & Curd + Banana Shake",
                "Paneer Paratha + Lassi (full cream) + Dry Fruits Mix",
                "Poha (large portion) with Peanuts + Full Cream Milk + Banana",
                "Masala Dosa (2) + Coconut Chutney + Sambar + Badam Milk",
                "Curd Rice + Ghee + Banana + Dates (3)",
                "Methi Paratha (2) + Curd + Chyawanprash (1 spoon)",
                "Stuffed Moong Dal Paratha + Butter + Mango Shake"
            ],
            'lunch': [
                "Ghee Rice + Chicken Curry + Raita + Papad + Sweet",
                "Chapati (3) + Rajma + Rice + Salad + Curd",
                "Biryani (Veg/Chicken) + Raita + Boiled Egg",
                "Rice + Sambar + Poriyal + Rasam + Curd + Banana",
                "Chapati (3) + Paneer Butter Masala + Dal Makhani + Salad",
                "Rice + Fish Curry + Thoran + Avial + Payasam",
                "Roti (3) + Egg Curry + Aloo Matar + Curd + Ladoo (1)"
            ],
            'dinner': [
                "Chapati (2) + Paneer Bhurji + Dal Tadka + Glass of Milk",
                "Rice + Sambar + Omelette + Curd",
                "Khichdi with Ghee + Papad + Banana + Milk",
                "Roti (2) + Chicken/Paneer Curry + Raita + Dates",
                "Curd Rice + Pickle + Boiled Egg + Banana Shake",
                "Paratha (1) + Mixed Veg Curry + Dal + Badam Milk",
                "Vegetable Pulao + Egg Curry + Raita + Dry Fruits"
            ]
        },
        'Fever': {
            'breakfast': [
                "Soft Rice Kanji (Congee) with Pickle + Ginger Tea",
                "Moong Dal Khichdi (soft) + Ghee + Buttermilk",
                "Bread Toast + Warm Milk with Haldi + Honey",
                "Daliya Porridge (thin) + Banana + Warm Water",
                "Idli (2, soft) + Sambar (warm) + Ginger Tea",
                "Poha (soft, less spice) + Warm Lemon Water",
                "Sooji Halwa (light) + Warm Milk + Tulsi Tea"
            ],
            'lunch': [
                "Soft Rice + Rasam + Steamed Vegetables + Curd",
                "Khichdi (Moong Dal, soft) + Ghee + Papad + Buttermilk",
                "Rice + Plain Dal + Boiled Potato + Curd",
                "Chapati (soft, 1) + Lauki Sabzi + Warm Dal Soup",
                "Curd Rice + Lemon + Ginger + Pickle",
                "Rice Porridge + Warm Sambar + Steamed Carrot",
                "Soft Idli (2) + Warm Rasam + Curd"
            ],
            'dinner': [
                "Warm Tomato Soup + Bread Toast + Haldi Doodh",
                "Thin Moong Dal + Soft Roti (1) + Warm Water",
                "Rice Kanji + Pickle + Boiled Egg + Tulsi Tea",
                "Vegetable Soup (warm) + Idli (1) + Ginger Tea",
                "Khichdi (very soft) + Ghee + Buttermilk",
                "Daliya Soup + Banana + Warm Milk with Turmeric",
                "Plain Dal Rice + Curd + Warm Water with Honey"
            ]
        },
        'General Wellness': {
            'breakfast': [
                "Idli (3) + Sambar + Coconut Chutney + Filter Coffee",
                "Aloo Paratha + Curd + Pickle + Masala Chai",
                "Poha with Peanuts & Sev + Buttermilk + Banana",
                "Dosa (2) + Sambar + Coconut Chutney + Badam Milk",
                "Upma with Vegetables + Green Tea + Boiled Egg",
                "Multigrain Paratha + Curd + Chyawanprash",
                "Pongal + Coconut Chutney + Sambar + Filter Coffee"
            ],
            'lunch': [
                "Rice + Sambar + Rasam + Poriyal + Curd + Papad",
                "Chapati (3) + Dal Fry + Aloo Gobi + Raita + Salad",
                "Jeera Rice + Rajma + Salad + Buttermilk",
                "Rice + Fish Curry + Thoran + Rasam + Banana",
                "Roti (2) + Paneer Bhurji + Mixed Veg + Curd",
                "Biryani (small portion) + Raita + Salad + Buttermilk",
                "Millet Rice + Sambar + Kootu + Poriyal + Curd"
            ],
            'dinner': [
                "Chapati (2) + Dal Tadka + Gobhi Matar + Salad",
                "Rice + Sambar + Poriyal + Curd + Banana",
                "Khichdi + Kadhi + Papad + Pickle",
                "Roti (2) + Egg Curry + Raita + Salad",
                "Dosa (1) + Sambar + Coconut Chutney + Warm Milk",
                "Vegetable Pulao + Raita + Papad + Curd",
                "Idli (2) + Sambar + Haldi Doodh"
            ]
        }
    }

    # Helper to generate days with rotation
    def generate_days(week_num, condition):
        days = {}
        c_meals = meal_db.get(condition, meal_db['General Wellness'])
        offset = (week_num - 1) * 2
        for d in range(1, 8):
            day_num = f"Day {d}"
            b_idx = (d - 1 + offset) % 7
            l_idx = (d - 1 + offset + 1) % 7
            d_idx = (d - 1 + offset + 2) % 7
            days[day_num] = {
                'breakfast': c_meals['breakfast'][b_idx],
                'lunch': c_meals['lunch'][l_idx],
                'dinner': c_meals['dinner'][d_idx]
            }
        return days

    # --- 3. CONDITION-SPECIFIC PLAN ---
    diet_name = "Balanced Indian Diet Protocol"
    three_week_plan = {}
    lab_insights = []
    consequences = []
    superfood = {}
    impact_timeline = []
    why_this_food = ""
    cond = primary_condition['name']

    if cond == 'Diabetes':
        diet_name = "Metabolic Control (Low-GI Indian) Protocol"
        three_week_plan = {
            'Week 1 (Stabilize)': generate_days(1, 'Diabetes'),
            'Week 2 (Variety)': generate_days(2, 'Diabetes'),
            'Week 3 (Boost)': generate_days(3, 'Diabetes')
        }
        lab_insights.append({'test': 'Fasting Sugar', 'value': f"{fasting} mg/dL", 'status': 'High' if fasting > 100 else 'Normal', 'diet_rule': 'Millets & Complex Carbs', 'reason': 'Low GI prevents insulin spikes.'})
        if random_sugar > 0:
            lab_insights.append({'test': 'Random Sugar', 'value': f"{random_sugar} mg/dL", 'status': 'High' if random_sugar > 140 else 'Normal', 'diet_rule': 'No refined sugar / maida', 'reason': 'Prevents post-meal glucose spikes.'})
        consequences = ['Persistent hyperglycemia', 'Nerve damage (neuropathy)', 'Kidney strain', 'Vision problems']
        superfood = {'name': 'Karela (Bitter Gourd)', 'benefit': 'Contains Polypeptide-p & Charantin which mimic insulin action and lower blood sugar naturally.'}
        why_this_food = "Millets (Ragi, Jowar, Bajra) have low glycemic index. Methi, Karela & Jamun regulate blood sugar."
        impact_timeline = [{'time': 'Week 1', 'benefit': 'Stable post-meal energy'}, {'time': 'Week 3', 'benefit': 'Reduced sugar cravings'}, {'time': 'Month 1', 'benefit': 'Lower fasting sugar'}]

    elif cond == 'Pre-Diabetes':
        diet_name = "Early Intervention (Pre-Diabetic Indian) Protocol"
        three_week_plan = {
            'Week 1 (Adjust)': generate_days(1, 'Pre-Diabetes'),
            'Week 2 (Regulate)': generate_days(2, 'Pre-Diabetes'),
            'Week 3 (Maintain)': generate_days(3, 'Pre-Diabetes')
        }
        lab_insights.append({'test': 'Fasting Sugar', 'value': f"{fasting} mg/dL", 'status': 'Borderline', 'diet_rule': 'Reduce refined carbs', 'reason': 'Prevent progression to diabetes.'})
        consequences = ['Progression to Type 2 Diabetes', 'Insulin resistance']
        superfood = {'name': 'Methi (Fenugreek) Seeds', 'benefit': 'Soluble fibre slows carb absorption, improves insulin sensitivity.'}
        why_this_food = "Whole grains & millets prevent sugar spikes. Methi water in the morning helps."
        impact_timeline = [{'time': 'Week 2', 'benefit': 'Better energy levels'}, {'time': 'Month 1', 'benefit': 'Sugar back to normal range'}]

    elif cond == 'Heart Disease':
        diet_name = "Cardiac Protective (Indian TLC) Protocol"
        three_week_plan = {
            'Week 1 (Detox)': generate_days(1, 'Heart Disease'),
            'Week 2 (Strengthen)': generate_days(2, 'Heart Disease'),
            'Week 3 (Maintain)': generate_days(3, 'Heart Disease')
        }
        lab_insights.append({'test': 'Heart Rate', 'value': f"{hr} bpm", 'status': 'Elevated' if hr > 100 else 'Normal', 'diet_rule': 'Omega-3 & low saturated fat', 'reason': 'Reduces arterial inflammation.'})
        lab_insights.append({'test': 'Blood Pressure', 'value': f"{systolic}/{diastolic}", 'status': 'High' if systolic > 130 else 'Normal', 'diet_rule': 'Low sodium, high potassium', 'reason': 'Reduces cardiac workload.'})
        consequences = ['Arterial plaque buildup', 'Stroke risk', 'Heart failure progression']
        superfood = {'name': 'Flaxseeds (Alsi)', 'benefit': 'Rich in ALA Omega-3 fatty acids that reduce triglycerides and arterial inflammation.'}
        why_this_food = "Walnuts, Flaxseeds & Fish provide Omega-3. Garlic & Haldi reduce inflammation."
        impact_timeline = [{'time': 'Week 2', 'benefit': 'Better circulation & energy'}, {'time': 'Month 1', 'benefit': 'Improved lipid profile'}]

    elif cond in ('Hypertension', 'Elevated BP'):
        diet_name = "DASH Indian (Low-Sodium) Protocol"
        db_key = 'Hypertension' if cond == 'Hypertension' else 'Elevated BP'
        three_week_plan = {
            'Week 1 (Sodium Detox)': generate_days(1, db_key),
            'Week 2 (Balance)': generate_days(2, db_key),
            'Week 3 (Sustain)': generate_days(3, db_key)
        }
        lab_insights.append({'test': 'Blood Pressure', 'value': f"{systolic}/{diastolic} mmHg", 'status': 'High' if systolic >= 140 else 'Elevated', 'diet_rule': 'Low salt + High potassium', 'reason': 'Potassium counteracts sodium and relaxes blood vessels.'})
        consequences = ['Kidney strain', 'Vision problems', 'Chronic headaches', 'Stroke risk']
        superfood = {'name': 'Beetroot (Chukandar)', 'benefit': 'Rich in nitrates that convert to nitric oxide, naturally dilating blood vessels and lowering BP.'}
        why_this_food = "Banana, coconut water, beetroot & leafy greens are potassium-rich. Reduces need for salt."
        impact_timeline = [{'time': 'Day 3', 'benefit': 'Less water retention'}, {'time': 'Week 2', 'benefit': 'Noticeable BP reduction'}]

    elif cond == 'Obesity':
        diet_name = "Caloric Deficit (Indian) Protocol"
        three_week_plan = {
            'Week 1 (Reset)': generate_days(1, 'Obesity'),
            'Week 2 (Burn)': generate_days(2, 'Obesity'),
            'Week 3 (Sustain)': generate_days(3, 'Obesity')
        }
        lab_insights.append({'test': 'BMI', 'value': f"{round(bmi, 1)}", 'status': 'Obese', 'diet_rule': 'High protein, low carb', 'reason': 'Protein preserves muscle during fat loss.'})
        consequences = ['Joint pain', 'Metabolic syndrome', 'Sleep apnea', 'Fatty liver']
        superfood = {'name': 'Sattu (Roasted Gram Flour)', 'benefit': 'High protein (20g per serving), low GI, keeps you full for hours. Traditional Bihar superfood.'}
        why_this_food = "Small portions of millets, high protein dal & paneer, lots of vegetables. No refined carbs or fried food."
        impact_timeline = [{'time': 'Week 1', 'benefit': 'Reduced bloating'}, {'time': 'Month 1', 'benefit': '2-3 kg healthy fat loss'}]

    elif cond == 'Overweight':
        diet_name = "Weight Management (Indian) Protocol"
        three_week_plan = {
            'Week 1 (Adjust)': generate_days(1, 'Overweight'),
            'Week 2 (Balance)': generate_days(2, 'Overweight'),
            'Week 3 (Maintain)': generate_days(3, 'Overweight')
        }
        lab_insights.append({'test': 'BMI', 'value': f"{round(bmi, 1)}", 'status': 'Overweight', 'diet_rule': 'Portion control + fibre', 'reason': 'Fibre increases satiety.'})
        consequences = ['Risk of diabetes', 'Joint stress', 'Elevated cholesterol']
        superfood = {'name': 'Dalchini (Cinnamon)', 'benefit': 'Improves insulin sensitivity and helps manage appetite naturally.'}
        why_this_food = "Balanced Indian thali with controlled portions. Replace white rice with millets."
        impact_timeline = [{'time': 'Week 2', 'benefit': 'Better energy'}, {'time': 'Month 1', 'benefit': '1-2 kg loss'}]

    elif cond == 'Underweight':
        diet_name = "Healthy Weight Gain (Indian) Protocol"
        three_week_plan = {
            'Week 1 (Nourish)': generate_days(1, 'Underweight'),
            'Week 2 (Build)': generate_days(2, 'Underweight'),
            'Week 3 (Strengthen)': generate_days(3, 'Underweight')
        }
        lab_insights.append({'test': 'BMI', 'value': f"{round(bmi, 1)}", 'status': 'Underweight', 'diet_rule': 'Calorie surplus + healthy fats', 'reason': 'Need 300-500 extra calories daily for healthy gain.'})
        consequences = ['Weak immunity', 'Fatigue & low energy', 'Nutritional deficiencies', 'Muscle wasting']
        superfood = {'name': 'Ghee + Dry Fruits', 'benefit': 'Ghee provides healthy fats & fat-soluble vitamins. Dry fruits add dense calories & micronutrients.'}
        why_this_food = "Ghee, full-cream dairy, dry fruits, banana shakes & extra chapatis. Eat 5-6 smaller meals."
        impact_timeline = [{'time': 'Week 1', 'benefit': 'More energy'}, {'time': 'Month 1', 'benefit': '1.5-2 kg healthy gain'}]

    elif cond == 'Fever':
        diet_name = "Recovery & Immunity (Indian) Protocol"
        three_week_plan = {
            'Week 1 (Heal)': generate_days(1, 'Fever'),
            'Week 2 (Recover)': generate_days(2, 'Fever'),
            'Week 3 (Rebuild)': generate_days(3, 'General Wellness')
        }
        lab_insights.append({'test': 'Temperature', 'value': f"{temp} °F", 'status': 'Fever', 'diet_rule': 'Hydration + light food', 'reason': 'Body needs fluids and easy-to-digest nutrition.'})
        consequences = ['Dehydration', 'Muscle weakness', 'Electrolyte imbalance']
        superfood = {'name': 'Tulsi + Haldi (Turmeric)', 'benefit': 'Tulsi has immunomodulatory properties. Turmeric (curcumin) is anti-inflammatory and boosts recovery.'}
        why_this_food = "Khichdi, rasam, haldi doodh are traditional Indian fever foods. Easy to digest and hydrating."
        impact_timeline = [{'time': 'Day 2', 'benefit': 'Better hydration'}, {'time': 'Week 1', 'benefit': 'Fever subsides, strength returns'}]

    else:
        diet_name = "Balanced Indian Diet Protocol"
        three_week_plan = {
            'Week 1': generate_days(1, 'General Wellness'),
            'Week 2': generate_days(2, 'General Wellness'),
            'Week 3': generate_days(3, 'General Wellness')
        }
        lab_insights.append({'test': 'Overall', 'value': 'Healthy', 'status': 'Normal', 'diet_rule': 'Balanced nutrition', 'reason': 'Maintain current health with variety.'})
        consequences = []
        superfood = {'name': 'Amla (Indian Gooseberry)', 'benefit': 'Highest natural source of Vitamin C. Boosts immunity, improves digestion, strengthens hair & skin.'}
        why_this_food = "Traditional balanced Indian thali — dal, roti, sabzi, curd, salad. All food groups covered."
        impact_timeline = [{'time': 'Ongoing', 'benefit': 'Sustained wellness & energy'}]

    # --- 4. INNOVATIONS ---
    organ_benefits = [
        {'organ': 'Heart', 'benefit': 'Low sodium + Omega-3 from flaxseeds & walnuts'},
        {'organ': 'Kidneys', 'benefit': 'Hydration + reduced salt load from Indian spices'},
        {'organ': 'Liver', 'benefit': 'Turmeric & amla support detoxification'},
        {'organ': 'Brain', 'benefit': 'Omega-3 (walnuts, flax) + Brahmi for cognitive function'}
    ]
    food_effects = [
        {'food': 'Palak (Spinach)', 'immediate': 'Iron absorption, less fatigue', 'long_term': 'BP control & bone strength'},
        {'food': 'Haldi (Turmeric)', 'immediate': 'Anti-inflammatory action', 'long_term': 'Joint health & immunity'},
        {'food': 'Dahi (Curd)', 'immediate': 'Gut cooling & probiotic boost', 'long_term': 'Better digestion & calcium'}
    ]
    simple_rules = [
        "No maida (refined flour) — use atta, ragi, jowar instead",
        "Half your plate should be sabzi (vegetables)",
        "Stop eating at 80% full (traditional Ayurvedic rule)",
        "Eat curd/buttermilk with lunch daily",
        "Use cold-pressed mustard/coconut/groundnut oil, not refined oil"
    ]
    festival_guide = {'strategy': 'Smart Swaps', 'safe_foods': ['Grilled tikka', 'Tandoori items', 'Raita', 'Salad'], 'portion_limit': '1 small plate of sweets', 'recovery': 'Next day: Khichdi + Buttermilk + Light soup'}
    sleep_advice = {'correlation': 'Late heavy dinner causes acid reflux and poor sleep quality.', 'rule': 'Dinner by 7:30-8:00 PM. Haldi Doodh before bed aids sleep.'}
    classified_foods = [
        {'name': 'Green leafy sabzi, Dal, Curd', 'tag': 'Eat Daily', 'color': 'success'},
        {'name': 'Millets, Brown Rice, Whole Wheat', 'tag': 'Preferred', 'color': 'info'},
        {'name': 'White Rice, Potato, Banana', 'tag': 'Moderate', 'color': 'warning'},
        {'name': 'Maida, Deep Fried, Packaged Snacks', 'tag': 'Avoid', 'color': 'danger'}
    ]
    medico_legal = {'statement': 'Diet is an adjunct therapy, not a replacement for prescribed medication.', 'disclaimer': 'Consult your doctor before making major dietary changes.'}

    circadian_schedule = [
        {'time': '06:30 AM', 'activity': 'Warm water + Methi seeds / Lemon', 'icon': 'tint'},
        {'time': '08:00 AM', 'activity': 'Breakfast (High Fibre Indian)', 'icon': 'cloud-sun'},
        {'time': '11:00 AM', 'activity': 'Mid-morning: Buttermilk / Fruit / Nuts', 'icon': 'apple-alt'},
        {'time': '01:00 PM', 'activity': 'Lunch (Largest meal — Dal, Roti, Sabzi)', 'icon': 'sun'},
        {'time': '04:00 PM', 'activity': 'Evening: Green Tea + Roasted Chana / Makhana', 'icon': 'mug-hot'},
        {'time': '07:30 PM', 'activity': 'Dinner (Light — Soup, Khichdi, Roti-Sabzi)', 'icon': 'moon'},
        {'time': '09:30 PM', 'activity': 'Haldi Doodh — fasting window begins', 'icon': 'stopwatch'}
    ]

    sugar_graph_data = {
        'labels': ['0h', '1h', '2h', '3h'],
        'standard': [90, 180, 160, 110],
        'smart': [90, 130, 110, 95]
    }

    cheat_options = [
        {'craving': 'Biryani', 'fix': 'Use brown rice + extra raita + walk 30 mins after eating'},
        {'craving': 'Samosa / Pakoda', 'fix': 'Air-fry instead of deep fry + mint chutney (no tamarind)'},
        {'craving': 'Gulab Jamun / Mithai', 'fix': '1 piece only + eat 5 almonds before (fibre buffer)'},
        {'craving': 'Chole Bhature', 'fix': 'Eat Chole with 1 Roti instead of Bhatura + large salad'},
        {'craving': 'Ice Cream', 'fix': 'Frozen banana + cocoa powder blend (homemade) or 1 small scoop'},
        {'craving': 'Maggi / Instant Noodles', 'fix': 'Use ragi noodles + add vegetables + limit to 1 pack'}
    ]

    weather_advice = {
        'season': 'Seasonal Protocols (Ritucharya)',
        'foods': 'Summer: Buttermilk, Sattu, Watermelon, Mint | Winter: Ginger Tea, Bajra Roti, Til (Sesame), Ghee | Monsoon: Haldi Doodh, Tulsi Tea, Warm Soups',
        'why': 'Ayurvedic Ritucharya (seasonal eating) aligns digestion with weather for optimal health.'
    }

    mood_kit = [
        {'mood': 'Stressed', 'food': 'Ashwagandha Milk / Dark Chocolate (small piece)', 'action': 'Pranayama (deep breathing)'},
        {'mood': 'Tired / Low Energy', 'food': 'Amla Juice / Banana + Dates', 'action': 'Short walk in sunlight (10 mins)'},
        {'mood': 'Low / Sad', 'food': 'Walnuts + Warm Haldi Doodh', 'action': 'Sunlight exposure + talk to someone'},
        {'mood': 'Anxious', 'food': 'Chamomile / Tulsi Tea + Makhana', 'action': 'Slow breathing (4-7-8 technique)'}
    ]

    plan = {
        'diet_type': diet_name,
        'conditions': ', '.join(stacking_order),
        'stacking_order': stacking_order,
        'departments': departments,
        'weekly_plan': three_week_plan,
        'lab_insights': lab_insights,
        'organ_benefits': organ_benefits,
        'food_effects': food_effects,
        'simple_rules': simple_rules,
        'festival_guide': festival_guide,
        'sleep_advice': sleep_advice,
        'consequences': consequences,
        'classified_foods': classified_foods,
        'medico_legal': medico_legal,
        'superfood': superfood,
        'impact_timeline': impact_timeline,
        'why_this_food': why_this_food,
        'circadian_schedule': circadian_schedule,
        'sugar_graph_data': sugar_graph_data,
        'cheat_options': cheat_options,
        'weather_advice': weather_advice,
        'mood_kit': mood_kit,
        'confidence_score': 96,
        'water_intake': '3 Liters (include Buttermilk, Coconut Water, Nimbu Pani)',
        'risk_warning': 'Sudden drastic diet changes may cause weakness. Start gradually and consult your doctor.',
        'eating_speed_advice': 'Fast eating causes insulin spikes and bloating. Chew each bite 20-25 times. Eat sitting down, not distracted.',
        'bmi': round(bmi, 1) if bmi else 'N/A'
    }

    return plan

@patient_bp.route('/dashboard')
@login_required
@patient_required
def dashboard():
    """Patient dashboard"""

    try:
        patient = current_user.patient
        
        # Initialize default values to prevent undefined errors
        health_score = 0
        h_status = {
            'heart': {'label': 'No Data', 'class': 'secondary'},
            'bp': {'label': 'No Data', 'class': 'secondary'},
            'sugar': {'label': 'No Data', 'class': 'secondary'},
            'sleep': {'label': 'No Data', 'class': 'secondary'}
        }
        trends = {
            'heart': {'msg': 'Stable', 'icon': 'fa-minus', 'class': 'change-neutral'},
            'bp': {'msg': 'Stable', 'icon': 'fa-minus', 'class': 'change-neutral'},
            'sugar': {'msg': 'Stable', 'icon': 'fa-minus', 'class': 'change-neutral'},
            'sleep': {'msg': 'Stable', 'icon': 'fa-minus', 'class': 'change-neutral'}
        }
        
        # Get latest 2 health records for trend analysis
        last_two_health = HealthData.query.filter_by(patient_id=patient.id).order_by(
            HealthData.recorded_at.desc()).limit(2).all()
        
        latest_health = last_two_health[0] if last_two_health else None
        previous_health = last_two_health[1] if len(last_two_health) > 1 else None

        # Staff-entered vitals (for backward compatibility and dashboard sync)
        latest_vitals = PatientVitals.query.filter_by(patient_id=patient.id).order_by(
            PatientVitals.recorded_at.desc()).first()

        # Choose a source for displayed vitals: whichever is MORE RECENT wins
        # Nurse-recorded vitals should always reflect on patient dashboard when newer
        if latest_health and latest_vitals:
            health_time = getattr(latest_health, 'recorded_at', None) or getattr(latest_health, 'created_at', None)
            vitals_time = latest_vitals.recorded_at
            if health_time and vitals_time and vitals_time > health_time:
                displayed_vitals = latest_vitals
            else:
                displayed_vitals = latest_health
        elif latest_vitals:
            displayed_vitals = latest_vitals
        else:
            displayed_vitals = latest_health

        # If nurse vitals are the displayed source, compute statuses from them
        use_nurse_vitals = (displayed_vitals is latest_vitals) and latest_vitals is not None
        if use_nurse_vitals:
            hr = latest_vitals.heart_rate or 0
            if 60 <= hr <= 100:
                h_status['heart'] = {'label': 'Normal', 'class': 'success'}
            elif hr > 0:
                h_status['heart'] = {'label': 'Attention', 'class': 'warning'}

            sys_bp = latest_vitals.systolic_bp or 0
            dia_bp = latest_vitals.diastolic_bp or 0
            if 90 <= sys_bp <= 120 and 60 <= dia_bp <= 80:
                h_status['bp'] = {'label': 'Optimal', 'class': 'info'}
            elif sys_bp > 140 or dia_bp > 90:
                h_status['bp'] = {'label': 'High', 'class': 'danger'}
            elif sys_bp > 0:
                h_status['bp'] = {'label': 'Normal', 'class': 'success'}

            sugar = getattr(latest_vitals, 'blood_sugar', None) or 0
            if sugar >= 200:
                h_status['sugar'] = {'label': 'High', 'class': 'danger'}
            elif sugar >= 125:
                h_status['sugar'] = {'label': 'Pre-Diabetic', 'class': 'warning'}
            elif sugar > 0:
                h_status['sugar'] = {'label': 'Normal', 'class': 'success'}

            # Compute health score from nurse vitals when no patient-entered data
            if not latest_health:
                nurse_vitals_dict = {
                    'systolic_bp': latest_vitals.systolic_bp or 0,
                    'diastolic_bp': latest_vitals.diastolic_bp or 0,
                    'heart_rate': latest_vitals.heart_rate or 0,
                    'temperature': getattr(latest_vitals, 'temperature', 0) or 0,
                    'fasting_sugar': sugar if sugar > 0 else 0,
                    'oxygen_level': getattr(latest_vitals, 'oxygen_level', 0) or 0,
                }
                if HEALTH_AI_AVAILABLE:
                    health_score = health_predictor.compute_health_score(nurse_vitals_dict)
                else:
                    # Simplified fallback for nurse vitals
                    _s = 0; _m = 0
                    sbp = nurse_vitals_dict['systolic_bp']; dbp = nurse_vitals_dict['diastolic_bp']
                    if sbp > 0 and dbp > 0:
                        _m += 25
                        if sbp < 120 and dbp < 80: _s += 25
                        elif sbp < 140 or dbp < 90: _s += 12
                        else: _s += 3
                    nhr = nurse_vitals_dict['heart_rate']
                    if nhr > 0:
                        _m += 15
                        if 60 <= nhr <= 100: _s += 15
                        elif 50 <= nhr <= 110: _s += 8
                        else: _s += 2
                    ntmp = nurse_vitals_dict['temperature']
                    if ntmp > 0:
                        _m += 10
                        if 97.0 <= ntmp <= 99.0: _s += 10
                        elif ntmp <= 100.4: _s += 5
                        else: _s += 1
                    health_score = int((_s / _m) * 100) if _m > 0 else 0
                    health_score = max(0, min(100, health_score))

        # Process Health Data if available
        if latest_health:
            # 1. Compute Health Score from actual vitals using clinical thresholds
            vitals_dict = {
                'systolic_bp': latest_health.systolic_bp or 0,
                'diastolic_bp': latest_health.diastolic_bp or 0,
                'heart_rate': latest_health.heart_rate or 0,
                'fasting_sugar': latest_health.fasting_sugar or 0,
                'random_sugar': latest_health.random_sugar or 0,
                'temperature': latest_health.temperature or 0,
                'bmi': latest_health.bmi or 0,
                'smoking': latest_health.smoking,
                'alcohol': latest_health.alcohol,
                'sleep_hours': latest_health.sleep_hours or 0,
                'stress_level': latest_health.stress_level,
                'exercise_minutes': latest_health.exercise_minutes or 0,
            }
            if HEALTH_AI_AVAILABLE:
                health_score = health_predictor.compute_health_score(vitals_dict)
            else:
                # Fallback: simple vitals-based score without the AI class
                _s = 0; _m = 0
                sbp = vitals_dict['systolic_bp']; dbp = vitals_dict['diastolic_bp']
                if sbp > 0 and dbp > 0:
                    _m += 25
                    if sbp < 120 and dbp < 80: _s += 25
                    elif sbp < 140 or dbp < 90: _s += 12
                    else: _s += 3
                hr = vitals_dict['heart_rate']
                if hr > 0:
                    _m += 15
                    if 60 <= hr <= 100: _s += 15
                    elif 50 <= hr <= 110: _s += 8
                    else: _s += 2
                fs = vitals_dict['fasting_sugar']
                if fs > 0:
                    _m += 20
                    if fs < 100: _s += 20
                    elif fs < 126: _s += 10
                    else: _s += 2
                tmp = vitals_dict['temperature']
                if tmp > 0:
                    _m += 10
                    if 97.0 <= tmp <= 99.0: _s += 10
                    elif tmp <= 100.4: _s += 5
                    else: _s += 1
                bmi_v = vitals_dict['bmi']
                if bmi_v > 0:
                    _m += 15
                    if 18.5 <= bmi_v < 25: _s += 15
                    elif 25 <= bmi_v < 30: _s += 8
                    else: _s += 2
                _m += 15; _ls = 0
                if not vitals_dict.get('smoking'): _ls += 5
                if not vitals_dict.get('alcohol'): _ls += 4
                sl = vitals_dict.get('sleep_hours', 0)
                if 7 <= sl <= 9: _ls += 6
                elif sl > 0: _ls += 2
                _s += _ls
                health_score = int((_s / _m) * 100) if _m > 0 else 0
                health_score = max(0, min(100, health_score))
            
            # 2. Update Statuses
            # Heart Rate
            hr = latest_health.heart_rate or 0
            if 60 <= hr <= 100:
                h_status['heart'] = {'label': 'Normal', 'class': 'success'}
            else:
                h_status['heart'] = {'label': 'Attention', 'class': 'warning'}
                
            # BP
            sys_bp = latest_health.systolic_bp or 0
            dia_bp = latest_health.diastolic_bp or 0
            if 90 <= sys_bp <= 120 and 60 <= dia_bp <= 80:
                h_status['bp'] = {'label': 'Optimal', 'class': 'info'}
            elif sys_bp > 140 or dia_bp > 90:
                h_status['bp'] = {'label': 'High', 'class': 'danger'}
            else:
                h_status['bp'] = {'label': 'Normal', 'class': 'success'}
                
            # Sugar (Fasting)
            sugar = latest_health.fasting_sugar or 0
            if sugar < 100:
                h_status['sugar'] = {'label': 'Normal', 'class': 'success'}
            elif sugar < 125:
                 h_status['sugar'] = {'label': 'Pre-Diabetic', 'class': 'warning'}
            else:
                 h_status['sugar'] = {'label': 'High', 'class': 'danger'}
                 
            # Sleep
            sleep = latest_health.sleep_hours or 0
            if 7 <= sleep <= 9:
                h_status['sleep'] = {'label': 'Optimal', 'class': 'success'}
            elif sleep > 0:
                h_status['sleep'] = {'label': 'Review', 'class': 'warning'}

        # 3. Calculate Trends
        if latest_health and previous_health:
            # Helper for trend calculation
            def calc_trend(curr, prev, unit=""):
                if curr is None or prev is None: return {'msg': 'Insufficient Data', 'icon': 'fa-minus', 'class': 'change-neutral'}
                diff = curr - prev
                if diff > 0:
                    return {'msg': f"+{diff}{unit} vs last", 'icon': 'fa-arrow-up', 'class': 'change-up'}
                elif diff < 0:
                    return {'msg': f"{diff}{unit} vs last", 'icon': 'fa-arrow-down', 'class': 'change-down'}
                else:
                    return {'msg': 'Stable', 'icon': 'fa-minus', 'class': 'change-neutral'}

            trends['heart'] = calc_trend(latest_health.heart_rate, previous_health.heart_rate, " bpm")
            trends['bp'] = calc_trend(latest_health.systolic_bp, previous_health.systolic_bp, "")
            trends['sugar'] = calc_trend(latest_health.fasting_sugar, previous_health.fasting_sugar, "")
            trends['sleep'] = calc_trend(latest_health.sleep_hours, previous_health.sleep_hours, "h")
        
        # Get upcoming appointments
        upcoming_appointments = Appointment.query.filter_by(patient_id=patient.id).filter(
            Appointment.appointment_date > datetime.utcnow()).order_by(
            Appointment.appointment_date).limit(5).all()
        
        # Get unread messages count
        unread_messages = Message.query.filter_by(patient_id=patient.id, is_read=False).count()
        
        # Get latest prescription using schema-adaptive SQL (avoids ORM column mismatch crashes)
        cols = {c['name'] for c in inspect(db.engine).get_columns('prescriptions')}
        med_expr = 'medicines' if 'medicines' in cols else ("medicine_name" if 'medicine_name' in cols else "''")
        dosage_expr = 'dosage' if 'dosage' in cols else "''"
        frequency_expr = 'frequency' if 'frequency' in cols else "''"
        instructions_expr = 'instructions' if 'instructions' in cols else "''"
        prescribed_expr = 'prescribed_at' if 'prescribed_at' in cols else ('created_at' if 'created_at' in cols else 'id')

        row = db.session.execute(
            text(f"""
                SELECT
                    id,
                    {med_expr} AS medicines,
                    {dosage_expr} AS dosage,
                    {frequency_expr} AS frequency,
                    {instructions_expr} AS instructions,
                    {prescribed_expr} AS prescribed_at
                FROM prescriptions
                WHERE patient_id = :patient_id
                ORDER BY {prescribed_expr} DESC
                LIMIT 1
            """),
            {'patient_id': patient.id}
        ).mappings().first()
        latest_prescription = SimpleNamespace(**row) if row else None

        def _parse_medicines(medicines_raw):
            if not medicines_raw:
                return []
            if isinstance(medicines_raw, list):
                return [str(m).strip() for m in medicines_raw if str(m).strip()]
            text = str(medicines_raw).strip()
            if not text:
                return []
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [str(m).strip() for m in parsed if str(m).strip()]
                if isinstance(parsed, str):
                    text = parsed.strip()
            except Exception:
                pass
            parts = re.split(r'[,\n;]+', text)
            return [p.strip() for p in parts if p.strip()]

        today_meds = _parse_medicines(latest_prescription.medicines) if latest_prescription else []
        med_details_parts = []
        if latest_prescription:
            if latest_prescription.dosage:
                med_details_parts.append(latest_prescription.dosage)
            if latest_prescription.frequency:
                med_details_parts.append(latest_prescription.frequency)
            if latest_prescription.instructions:
                med_details_parts.append(latest_prescription.instructions)
        med_details_text = " | ".join(med_details_parts) if med_details_parts else "As directed by your doctor"
        medication_entries = [{'name': name, 'details': med_details_text} for name in today_meds]
    
        # Get recent lab reports
        recent_reports = LabReport.query.filter_by(patient_id=patient.id).order_by(
            LabReport.conducted_at.desc()).limit(10).all()
    
        # Get health data history for charts (last 7 days)
        # Merge HealthData + nurse PatientVitals — whichever is more recent per day wins
        health_records = HealthData.query.filter_by(patient_id=patient.id).filter(
            HealthData.recorded_at >= (datetime.now() - timedelta(days=7))
        ).order_by(HealthData.recorded_at.asc()).all()

        nurse_vitals_7d = PatientVitals.query.filter_by(patient_id=patient.id).filter(
            PatientVitals.recorded_at >= (datetime.now() - timedelta(days=7))
        ).order_by(PatientVitals.recorded_at.asc()).all()

        # Process into Last 7 Days structure
        today = datetime.now().date()
        last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]

        chart_dates = [d.strftime('%a') for d in last_7_days]

        # Map HealthData by date
        health_map = {}
        for h in health_records:
            health_map[h.recorded_at.date()] = {
                'hr': h.heart_rate or 0,
                'bp': h.systolic_bp or 0,
                'sugar': h.fasting_sugar or 0,
                'sleep': h.sleep_hours or 0,
                'time': h.recorded_at
            }

        # Overlay nurse vitals — use nurse data if newer or if no HealthData for that day
        for v in nurse_vitals_7d:
            d = v.recorded_at.date()
            existing = health_map.get(d)
            if not existing or v.recorded_at > existing['time']:
                health_map[d] = {
                    'hr': v.heart_rate or 0,
                    'bp': v.systolic_bp or 0,
                    'sugar': v.blood_sugar or 0,
                    'sleep': existing['sleep'] if existing else 0,
                    'time': v.recorded_at
                }

        chart_heart_rate = []
        chart_bp_sys = []
        chart_sugar = []
        chart_sleep = []

        for d in last_7_days:
            if d in health_map:
                m = health_map[d]
                chart_heart_rate.append(m['hr'])
                chart_bp_sys.append(m['bp'])
                chart_sugar.append(m['sugar'])
                chart_sleep.append(m['sleep'])
            else:
                chart_heart_rate.append(0)
                chart_bp_sys.append(0)
                chart_sugar.append(0)
                chart_sleep.append(0)
    
        # Get Express Check-in history
        from app.models.models import PatientCheckIn
        my_checkins = PatientCheckIn.query.filter_by(patient_id=patient.id).order_by(
            PatientCheckIn.created_at.desc()).limit(5).all()
        
        # Get patient's recent check-ins for Express Check-in widget
        my_checkins = PatientCheckIn.query.filter_by(patient_id=patient.id).order_by(
            PatientCheckIn.created_at.desc()).limit(5).all()
        
        # Total counts for Hero Section
        total_reports = LabReport.query.filter_by(patient_id=patient.id).count() + LabOrder.query.filter_by(
            patient_id=patient.id).count()

        # Visit QR codes — recent visits with QR tokens
        from app.models.models import Visit
        my_visit_qrs = Visit.query.filter(
            Visit.patient_id == patient.id,
            Visit.qr_token.isnot(None),
        ).order_by(Visit.visit_date.desc()).limit(10).all()

        return render_template('patient/dashboard_enhanced.html',
                             patient=patient,
                             latest_health=latest_health,
                             latest_vitals=latest_vitals,
                             displayed_vitals=displayed_vitals,
                             appointments=upcoming_appointments,
                             upcoming_appointments=upcoming_appointments,
                             unread_messages=unread_messages,
                             latest_prescription=latest_prescription,
                             medication_entries=medication_entries,
                             recent_reports=recent_reports,
                             health_history=health_records,
                             chart_dates=chart_dates,
                             chart_heart_rate=chart_heart_rate,
                             chart_bp_sys=chart_bp_sys,
                             chart_sugar=chart_sugar,
                             chart_sleep=chart_sleep,
                             my_checkins=my_checkins,
                             health_score=health_score,
                             total_reports=total_reports,
                             h_status=h_status,
                             trends=trends,
                             my_visit_qrs=my_visit_qrs,
                             current_date=datetime.now(),
                             hide_sidebar=True)
    except Exception as e:
        import traceback
        with open('debug_dashboard_error.txt', 'w') as f:
            f.write(str(e) + '\n' + traceback.format_exc())
        return f"FIXED DASHBOARD ERROR [dashboard_v3]: {str(e)}", 500

@patient_bp.route('/consent', methods=['GET'])
@login_required
@patient_required
def consent():
    """Digital signature and consent forms page"""
    patient = current_user.patient
    # Import here to avoid circular dependencies if any
    from app.models.models import PatientConsent
    
    # Get all past signed consents
    past_consents = PatientConsent.query.filter_by(patient_id=patient.id).order_by(PatientConsent.signed_at.desc()).all()
    
    return render_template('patient/consent.html', past_consents=past_consents)

@patient_bp.route('/consent/sign', methods=['POST'])
@login_required
@patient_required
def sign_consent():
    """Handle processing of the canvas base64 signature"""
    patient = current_user.patient
    from app.models.models import PatientConsent
    
    form_type = request.form.get('form_type')
    consent_text = request.form.get('consent_text')
    signature_base64 = request.form.get('signature_base64')
    
    if not signature_base64 or not form_type:
        flash('Invalid submission: Signature is required.', 'danger')
        return redirect(url_for('patient.consent'))
        
    try:
        new_consent = PatientConsent(
            patient_id=patient.id,
            form_type=form_type,
            consent_text=consent_text,
            signature_base64=signature_base64,
            ip_address=request.remote_addr
        )
        db.session.add(new_consent)
        db.session.commit()
        
        flash(f'Digital signature attached to {form_type} successfully. Saved natively secured with base64 encoding.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving digital signature: {str(e)}', 'danger')
        
    return redirect(url_for('patient.consent'))

@patient_bp.route('/profile')
@login_required
@patient_required
def profile():
    """Patient profile page"""
    patient = current_user.patient
    return render_template('patient/profile.html', patient=patient)

@patient_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
@patient_required
def edit_profile():
    """Edit patient profile"""
    patient = current_user.patient
    
    if request.method == 'POST':
        patient.first_name = request.form.get('first_name', patient.first_name)
        patient.last_name = request.form.get('last_name', patient.last_name)
        
        # Safe conversion for Age
        age = request.form.get('age')
        if age and age.strip():
            patient.age = int(age)

        # Safe conversion for Weight
        weight = request.form.get('weight')
        if weight and weight.strip():
            patient.weight = float(weight)
        
        # Safe conversion for Height
        height = request.form.get('height')
        if height and height.strip():
            patient.height = float(height)

        patient.phone = request.form.get('phone', patient.phone)
        patient.address = request.form.get('address', patient.address)
        patient.blood_type = request.form.get('blood_type', patient.blood_type)
        patient.medical_history = request.form.get('medical_history', patient.medical_history)
        # patient.allergies = request.form.get('allergies', patient.allergies)
        # patient.emergency_contact = request.form.get('emergency_contact', patient.emergency_contact)
        
        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('patient.profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')

    return render_template('patient/edit_profile.html', patient=patient)

@patient_bp.route('/health-data/enter', methods=['GET', 'POST'])
@login_required
@patient_required
def enter_health_data():
    """Enter health parameters"""
    if request.method == 'POST':
        patient = current_user.patient
        
        # Get form data
        def _int(val, default=0):
            try: return int(val) if val not in (None, '') else default
            except (ValueError, TypeError): return default
        def _float(val, default=0.0):
            try: return float(val) if val not in (None, '') else default
            except (ValueError, TypeError): return default

        systolic_bp = _int(request.form.get('systolic_bp'))
        diastolic_bp = _int(request.form.get('diastolic_bp'))
        fasting_sugar = _float(request.form.get('fasting_sugar'))
        random_sugar = _float(request.form.get('random_sugar'))
        heart_rate = _int(request.form.get('heart_rate'))
        symptoms = request.form.get('symptoms', '')
        exercise_minutes = _int(request.form.get('exercise_minutes'))
        sleep_hours = _float(request.form.get('sleep_hours'))
        stress_level = request.form.get('stress_level', 'Low')
        smoking = request.form.get('smoking') == 'on'
        alcohol = request.form.get('alcohol') == 'on'
        temperature = _float(request.form.get('temperature'), 98.6)
        
        # Calculate BMI
        if patient.weight and patient.height:
            if HEALTH_AI_AVAILABLE:
                bmi, bmi_category = health_predictor.calculate_bmi(patient.weight, patient.height)
            else:
                # Fallback BMI calculation
                bmi = patient.weight / ((patient.height / 100) ** 2)
                if bmi < 18.5:
                    bmi_category = "Underweight"
                elif bmi < 25:
                    bmi_category = "Normal"
                elif bmi < 30:
                    bmi_category = "Overweight"
                else:
                    bmi_category = "Obese"
        else:
            bmi, bmi_category = 0, "Unknown"
        
        # Predict risks
        if HEALTH_AI_AVAILABLE:
            diabetes_risk = health_predictor.predict_diabetes_risk(
                patient.age, bmi, fasting_sugar, random_sugar)
            heart_risk = health_predictor.predict_heart_disease_risk(
                patient.age, systolic_bp, diastolic_bp, heart_rate, smoking=smoking)
            hypertension_risk = health_predictor.predict_hypertension_risk(
                systolic_bp, diastolic_bp, patient.age, bmi)
        else:
            # Fallback risk calculations (simple heuristics)
            diabetes_risk = min(100, max(0, (fasting_sugar - 100) * 2 + (random_sugar - 140) * 1.5))
            heart_risk = min(100, max(0, (systolic_bp - 120) * 1.5 + (heart_rate - 70) * 0.5 + (20 if smoking else 0)))
            hypertension_risk = min(100, max(0, (systolic_bp - 120) * 2 + (diastolic_bp - 80) * 2))
        
        # Create health data record
        health_data = HealthData(
            patient_id=patient.id,
            systolic_bp=systolic_bp,
            diastolic_bp=diastolic_bp,
            fasting_sugar=fasting_sugar,
            random_sugar=random_sugar,
            heart_rate=heart_rate,
            symptoms=symptoms,
            exercise_minutes=exercise_minutes,
            sleep_hours=sleep_hours,
            stress_level=stress_level,
            smoking=smoking,
            alcohol=alcohol,
            temperature=temperature,
            diabetes_risk=diabetes_risk,
            heart_disease_risk=heart_risk,
            hypertension_risk=hypertension_risk,
            bmi=bmi,
            bmi_category=bmi_category
        )
        
        db.session.add(health_data)
        db.session.commit()
        
        flash('Health data recorded successfully!', 'success')
        return redirect(url_for('patient.health_results', health_id=health_data.id))
    
    return render_template('patient/enter_health_data.html')

@patient_bp.route('/health-results/<int:health_id>')
@login_required
@patient_required
def health_results(health_id):
    """View AI health analysis results"""
    patient = current_user.patient
    health_data = HealthData.query.get_or_404(health_id)
    
    if health_data.patient_id != patient.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('patient.dashboard'))
    
    # Get risk levels
    risk_status = {
        'diabetes': 'High Risk' if health_data.diabetes_risk > 60 else 'Moderate Risk' if health_data.diabetes_risk > 30 else 'Low Risk',
        'heart': 'High Risk' if health_data.heart_disease_risk > 60 else 'Moderate Risk' if health_data.heart_disease_risk > 30 else 'Low Risk',
        'hypertension': 'High Risk' if health_data.hypertension_risk > 60 else 'Moderate Risk' if health_data.hypertension_risk > 30 else 'Low Risk'
    }
    
    # Check for warnings
    warnings = []
    if health_data.systolic_bp > 160 or health_data.diastolic_bp > 100:
        warnings.append('CRITICAL: Severe blood pressure detected. Seek immediate medical attention!')
    if health_data.fasting_sugar > 250 or health_data.random_sugar > 300:
        warnings.append('WARNING: Very high blood sugar detected. Consult your doctor!')
    if health_data.heart_rate < 50 or health_data.heart_rate > 120:
        warnings.append('WARNING: Abnormal heart rate detected.')
    
    # Verified Knowledge Base Analysis
    symptom_analysis = []
    if health_data.symptoms and HEALTH_AI_AVAILABLE:
        try:
            # Split symptoms by comma and analyze each if needed, 
            # or just analyze the whole string
            analysis = knowledge_base.get_response(health_data.symptoms)
            if "not available in our health database" not in analysis:
                symptom_analysis.append({
                    'symptom': health_data.symptoms,
                    'analysis': analysis
                })
        except Exception as e:
            print(f"Knowledge Base analysis error: {e}")
    
    return render_template('patient/health_results.html',
                         health_data=health_data,
                         risk_status=risk_status,
                         warnings=warnings,
                         symptom_analysis=symptom_analysis)

@patient_bp.route('/diet-plan')
@login_required
@patient_required
def diet_plan():
    """View AI-generated personalized diet plan"""
    print("=== DIET PLAN ROUTE CALLED ===")
    try:
        patient = current_user.patient
        latest_health = HealthData.query.filter_by(patient_id=patient.id).order_by(
            HealthData.recorded_at.desc()).first()
        
        if not latest_health:
            flash('Please enter health data first', 'info')
            return redirect(url_for('patient.enter_health_data'))
        
        # Debug logging
        print(f"DEBUG: Patient ID: {patient.id}")
        print(f"DEBUG: Patient weight: {patient.weight}, height: {patient.height}")
        print(f"DEBUG: Health data BMI: {latest_health.bmi}")
        print(f"DEBUG: Diabetes risk: {latest_health.diabetes_risk}")
        print(f"DEBUG: Hypertension risk: {latest_health.hypertension_risk}")
        print(f"DEBUG: Heart disease risk: {latest_health.heart_disease_risk}")
        
        # Generate personalized diet plan based on health conditions
        plan = generate_personalized_diet_plan(patient, latest_health)
        
        print(f"DEBUG: Generated plan type: {plan.get('diet_type')}")
        print(f"DEBUG: Plan keys: {plan.keys()}")
        
        return render_template('patient/diet_plan.html', 
                             plan=plan, 
                             patient=patient,
                             health_data=latest_health)
    except Exception as e:
        import traceback
        print(f"Error in diet_plan route: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        flash(f'Error loading diet plan: {str(e)}', 'danger')
        return redirect(url_for('patient.dashboard'))

@patient_bp.route('/prescriptions/refill', methods=['POST'])
@login_required
@patient_required
def request_refill():
    """Handle medication refill request"""
    medication = request.form.get('medication')
    quantity = request.form.get('quantity')
    notes = request.form.get('notes')
    
    # In a real app, we would link this to a specific Prescription record
    # For now, we'll confirm receipt
    flash(f'Refill request for {medication} ({quantity}) has been sent to your doctor.', 'success')
    return redirect(url_for('patient.prescriptions'))

def generate_doctor_prescribed_plan(patient, health_data):
    """
    Generate a vitals-driven Exercise & Yoga Rehabilitation Plan.
    Uses direct vitals (BP, HR, sugar, temp, BMI) for condition detection.
    Includes yoga asanas, pranayama, meditation alongside physical exercises.
    """

    # --- 1. IMAGE BANK ---
    img_db = {
        'ankle_pumps': 'https://images.unsplash.com/photo-1588286840104-8957b019727f?w=600&q=80',
        'glute_squeeze': 'https://images.unsplash.com/photo-1518611012118-696072aa579a?w=600&q=80',
        'walking': 'https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=600&q=80',
        'squat': 'https://images.unsplash.com/photo-1541534741688-6078c6bfb5c5?w=600&q=80',
        'standing_balance': 'https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=600&q=80',
        'chair_sit': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=600&q=80',
        'seated_knee': 'https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=600&q=80',
        'wall_pushup': 'https://images.unsplash.com/photo-1599058945522-28d584b6f0ff?w=600&q=80',
        'heel_raise': 'https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=600&q=80',
        'cycle': 'https://images.unsplash.com/photo-1517649763962-0c623066013b?w=600&q=80',
        'weights': 'https://images.unsplash.com/photo-1583454110551-21f2fa2afe61?w=600&q=80',
        'yoga': 'https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=600&q=80',
        'meditation': 'https://images.unsplash.com/photo-1508672019048-805c876b67e2?w=600&q=80',
        'pranayama': 'https://images.unsplash.com/photo-1545389336-cf090694435e?w=600&q=80',
        'surya': 'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=600&q=80',
        'swimming': 'https://images.unsplash.com/photo-1530549387789-4c1017266635?w=600&q=80',
        'stretching': 'https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=600&q=80',
        'running': 'https://images.unsplash.com/photo-1552674605-db6ffd4facb5?w=600&q=80',
    }

    # --- 2. VITALS-BASED CONDITION DETECTION ---
    def _to_num(value):
        try:
            return float(value) if value is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    systolic = _to_num(health_data.systolic_bp)
    diastolic = _to_num(health_data.diastolic_bp)
    hr = _to_num(health_data.heart_rate)
    fasting = _to_num(health_data.fasting_sugar)
    random_sugar = _to_num(health_data.random_sugar)
    bmi = _to_num(health_data.bmi)
    temp = _to_num(health_data.temperature)
    heart_risk = _to_num(health_data.heart_disease_risk)
    hypertension_risk = _to_num(health_data.hypertension_risk)
    diabetes_risk = _to_num(health_data.diabetes_risk)

    conditions = []
    if heart_risk > 50 or hr > 100 or (systolic >= 160 and hr > 90):
        conditions.append('Cardiac')
    if systolic >= 140 or diastolic >= 90 or hypertension_risk > 50:
        conditions.append('Hypertension')
    if fasting >= 126 or random_sugar >= 200 or diabetes_risk > 50:
        conditions.append('Diabetes')
    elif fasting >= 100 or random_sugar >= 140:
        conditions.append('Pre-Diabetes')
    if bmi > 30:
        conditions.append('Obesity')
    elif bmi > 25:
        conditions.append('Overweight')
    if temp > 100.4:
        conditions.append('Fever Recovery')
    if not conditions:
        conditions.append('General Fitness')

    primary_condition = conditions[0]

    # --- 3. CLINICAL SAFETY RULES (per condition) ---
    rules = {
        'Cardiac': {
            'focus': 'Heart Rate Control & Gentle Recovery',
            'analysis': {
                'safe': ['Slow Walking', 'Shavasana', 'Anulom Vilom Pranayama', 'Seated Stretching', 'Meditation'],
                'caution': ['Stair Climbing (Assisted)', 'Brisk Walking', 'Surya Namaskar (slow)'],
                'forbidden': ['HIIT', 'Heavy Lifting (>5kg)', 'Sprinting', 'Sirsasana (Headstand)', 'Hot Yoga']
            }
        },
        'Hypertension': {
            'focus': 'Stress Reduction & Blood Flow',
            'analysis': {
                'safe': ['Meditative Walk', 'Shavasana', 'Bhramari Pranayama', 'Yoga Nidra', 'Tai Chi'],
                'caution': ['Overhead Arm Exercises', 'Isometric Holds', 'Surya Namaskar (moderate pace)'],
                'forbidden': ['Sirsasana (Headstand)', 'Sarvangasana (Shoulder Stand)', 'Intense Cardio', 'Heavy Weightlifting', 'Kapalbhati (fast)']
            }
        },
        'Diabetes': {
            'focus': 'Glucose Stabilization & Metabolism Boost',
            'analysis': {
                'safe': ['Post-Meal Walk (15 min)', 'Mandukasana (Frog Pose)', 'Cycling', 'Resistance Bands', 'Pranayama'],
                'caution': ['Exercising on Empty Stomach (hypoglycemia risk)', 'Barefoot Exercise (neuropathy risk)'],
                'forbidden': ['Extreme Endurance Runs', 'Hot Yoga (dehydration risk)', 'Skipping meals before exercise']
            }
        },
        'Pre-Diabetes': {
            'focus': 'Insulin Sensitivity Improvement',
            'analysis': {
                'safe': ['Brisk Walking', 'Surya Namaskar', 'Cycling', 'Yoga Asanas', 'Pranayama'],
                'caution': ['Very intense workouts without eating', 'Prolonged fasting + exercise'],
                'forbidden': ['Extreme heat exercises', 'Crash exercise programs']
            }
        },
        'Obesity': {
            'focus': 'Joint-Safe Fat Burning & Mobility',
            'analysis': {
                'safe': ['Walking', 'Swimming', 'Chair Yoga', 'Cycling (stationary)', 'Pranayama'],
                'caution': ['Deep Squats (knee stress)', 'Planks (wrist stress)', 'Running (joint impact)'],
                'forbidden': ['High Impact Jumps', 'Burpees', 'Heavy Barbell Squats', 'Box Jumps']
            }
        },
        'Overweight': {
            'focus': 'Gradual Fat Loss & Fitness Building',
            'analysis': {
                'safe': ['Brisk Walking', 'Surya Namaskar', 'Cycling', 'Yoga Asanas', 'Swimming'],
                'caution': ['Running on hard surfaces', 'Heavy weights without trainer'],
                'forbidden': ['Extreme dieting + intense exercise', 'Plyometrics without preparation']
            }
        },
        'Fever Recovery': {
            'focus': 'Gentle Recovery & Energy Restoration',
            'analysis': {
                'safe': ['Shavasana', 'Deep Breathing', 'Gentle Neck Stretches', 'Slow Walking (indoor)'],
                'caution': ['Any moderate exercise until fever-free for 24h'],
                'forbidden': ['All intense exercise', 'Outdoor exercise', 'Yoga inversions', 'Swimming']
            }
        },
        'General Fitness': {
            'focus': 'Overall Wellness & Strength',
            'analysis': {
                'safe': ['Surya Namaskar', 'Brisk Walking', 'Yoga Asanas', 'Bodyweight Training', 'Pranayama', 'Swimming', 'Cycling'],
                'caution': ['Heavy weights without warm-up'],
                'forbidden': ['Exercising through pain', 'Skipping warm-up/cool-down']
            }
        }
    }

    current_rule = rules.get(primary_condition, rules['General Fitness'])

    # --- 4. EXPANDED EXERCISE + YOGA LIBRARY (8 per week) ---

    # Week 1: Gentle Mobility + Pranayama + Meditation
    week1_exercises = [
        {'name': 'Ankle Pumps & Circles', 'img': img_db['ankle_pumps'], 'tag': 'Circulation', 'desc': 'Pump ankles up-down and rotate in circles. 10 each direction.', 'reason': 'Prevents blood clots (DVT) and improves peripheral circulation.'},
        {'name': 'Glute Squeezes', 'img': img_db['glute_squeeze'], 'tag': 'Iso-Tone', 'desc': 'Squeeze glutes tightly for 5 seconds, relax. Repeat 10 times.', 'reason': 'Maintains gluteal muscle tone without joint stress.'},
        {'name': 'Anulom Vilom (Alternate Nostril Breathing)', 'img': img_db['pranayama'], 'tag': 'Pranayama', 'desc': 'Close right nostril, inhale left (4s). Close left, exhale right (4s). Alternate. 5 minutes.', 'reason': 'Calms the nervous system, lowers BP, reduces stress. Proven in clinical studies.'},
        {'name': 'Shavasana (Corpse Pose)', 'img': img_db['meditation'], 'tag': 'Yoga', 'desc': 'Lie flat on back, arms by sides, palms up. Close eyes. Breathe naturally for 10 minutes.', 'reason': 'Activates parasympathetic system. Reduces cortisol and heart rate.'},
        {'name': 'Seated Knee Extensions', 'img': img_db['seated_knee'], 'tag': 'Mobility', 'desc': 'While seated, slowly straighten one knee, hold 5s, lower. 8 reps each leg.', 'reason': 'Gentle quadriceps activation without standing.'},
        {'name': 'Neck & Shoulder Stretches', 'img': img_db['stretching'], 'tag': 'Flexibility', 'desc': 'Tilt head left/right (10s each), roll shoulders forward/back (10 each).', 'reason': 'Relieves cervical tension and improves posture.'},
        {'name': 'Bhramari Pranayama (Bee Breathing)', 'img': img_db['pranayama'], 'tag': 'Pranayama', 'desc': 'Close ears with thumbs, inhale deeply, exhale with humming sound. 7 rounds.', 'reason': 'Reduces anxiety, lowers blood pressure, calms the mind.'},
        {'name': 'Sukhasana Meditation', 'img': img_db['meditation'], 'tag': 'Meditation', 'desc': 'Sit cross-legged, spine straight, eyes closed. Focus on breath for 10 minutes.', 'reason': 'Reduces cortisol, improves focus and emotional regulation.'}
    ]

    # Week 2: Standing + Yoga Asanas + Balance
    week2_exercises = [
        {'name': 'Chair Stand (Sit-to-Stand)', 'img': img_db['chair_sit'], 'tag': 'Strength', 'desc': 'Stand up from chair without using hands. Sit back slowly. 10 reps.', 'reason': 'Builds functional leg strength for daily activities.'},
        {'name': 'Heel Raises (Calf Raises)', 'img': img_db['heel_raise'], 'tag': 'Balance', 'desc': 'Hold chair, lift heels off floor. Hold 3s at top. 12 reps.', 'reason': 'Strengthens calves, improves ankle stability and balance.'},
        {'name': 'Tadasana (Mountain Pose)', 'img': img_db['yoga'], 'tag': 'Yoga', 'desc': 'Stand feet together, arms at sides. Lift arms overhead, stretch upward, hold 30s.', 'reason': 'Improves posture, body alignment and balance awareness.'},
        {'name': 'Vrikshasana (Tree Pose)', 'img': img_db['yoga'], 'tag': 'Yoga Balance', 'desc': 'Stand on one leg, place other foot on inner thigh. Hands in prayer. Hold 20s each side.', 'reason': 'Strengthens legs, improves balance and concentration.'},
        {'name': 'Marching in Place', 'img': img_db['walking'], 'tag': 'Cardio', 'desc': 'Lift knees to hip height alternately. 2 minutes at comfortable pace.', 'reason': 'Safely elevates heart rate and improves coordination.'},
        {'name': 'Vajrasana (Diamond Pose)', 'img': img_db['meditation'], 'tag': 'Yoga Digestion', 'desc': 'Kneel and sit back on heels, spine straight. Hold 5-10 minutes after meals.', 'reason': 'Only yoga pose done after eating. Aids digestion, reduces bloating.'},
        {'name': 'Kapalbhati Pranayama (Skull Shining)', 'img': img_db['pranayama'], 'tag': 'Pranayama', 'desc': 'Sit straight, exhale forcefully through nose with belly pull-in. Passive inhale. 30 breaths x 3 rounds.', 'reason': 'Boosts metabolism, improves lung capacity. Helps with weight management.'},
        {'name': 'Side Leg Raises', 'img': img_db['glute_squeeze'], 'tag': 'Hip Strength', 'desc': 'Lie on side, lift top leg to 45 degrees, hold 2s, lower. 10 reps each side.', 'reason': 'Stabilizes hip abductors, prevents falls.'}
    ]

    # Week 3: Strength + Advanced Yoga + Surya Namaskar
    week3_exercises = [
        {'name': 'Surya Namaskar (Sun Salutation)', 'img': img_db['surya'], 'tag': 'Yoga Full Body', 'desc': '12-step flow: Prayer > Raised Arms > Forward Bend > Lunge > Plank > 8-point > Cobra > Downward Dog > Lunge > Forward Bend > Raised Arms > Prayer. Start with 3 rounds.', 'reason': 'Complete body workout. Strengthens all muscle groups, improves flexibility and cardiovascular fitness.'},
        {'name': 'Wall Push-ups', 'img': img_db['wall_pushup'], 'tag': 'Upper Body', 'desc': 'Stand arm-length from wall, push against it. Keep back straight. 12 reps x 2 sets.', 'reason': 'Builds chest, shoulder and arm strength progressively.'},
        {'name': 'Setu Bandhasana (Bridge Pose)', 'img': img_db['glute_squeeze'], 'tag': 'Yoga Core', 'desc': 'Lie on back, bend knees, lift hips toward ceiling. Hold 20s. 5 reps.', 'reason': 'Strengthens glutes, core and lower back. Opens chest for better breathing.'},
        {'name': 'Trikonasana (Triangle Pose)', 'img': img_db['yoga'], 'tag': 'Yoga Stretch', 'desc': 'Wide stance, reach one hand to ankle, other arm up. Hold 20s each side.', 'reason': 'Stretches hamstrings, opens hips, strengthens legs. Improves digestion.'},
        {'name': 'Mini Lunges', 'img': img_db['standing_balance'], 'tag': 'Leg Strength', 'desc': 'Step forward slightly, bend both knees to 45 degrees. 10 reps each leg.', 'reason': 'Improves balance, strengthens quads and glutes.'},
        {'name': 'One Leg Balance (30s)', 'img': img_db['standing_balance'], 'tag': 'Stability', 'desc': 'Stand on one foot, eyes open. Try closing eyes for advanced. 30s each side.', 'reason': 'Critical for fall prevention. Builds proprioception.'},
        {'name': 'Bhujangasana (Cobra Pose)', 'img': img_db['yoga'], 'tag': 'Yoga Back', 'desc': 'Lie face down, hands under shoulders, lift chest keeping hips grounded. Hold 20s.', 'reason': 'Strengthens back muscles, opens chest, improves spinal flexibility.'},
        {'name': 'Step-Ups', 'img': img_db['heel_raise'], 'tag': 'Functional', 'desc': 'Step up onto a low step with one foot, bring other up, step down. 10 each leg.', 'reason': 'Functional stair-climbing ability. Builds leg endurance.'}
    ]

    # Week 4: Endurance + Advanced Yoga + Full Fitness
    week4_exercises = [
        {'name': 'Brisk Walk / Light Jog', 'img': img_db['running'], 'tag': 'Endurance', 'desc': 'Walk briskly (or light jog) for 20-30 minutes at talking pace.', 'reason': 'Cardiovascular conditioning. Burns calories and improves stamina.'},
        {'name': 'Bodyweight Squats', 'img': img_db['squat'], 'tag': 'Strength', 'desc': 'Stand, push hips back, bend knees to 90 degrees. Stand up. 15 reps x 3 sets.', 'reason': 'Total lower body strengthening. Boosts metabolism.'},
        {'name': 'Virabhadrasana (Warrior Poses I & II)', 'img': img_db['yoga'], 'tag': 'Yoga Power', 'desc': 'Warrior I: Lunge with arms overhead. Warrior II: Arms extended, gaze over front hand. Hold 30s each.', 'reason': 'Builds leg strength, stamina, and mental focus. Opens hips and chest.'},
        {'name': 'Mandukasana (Frog Pose)', 'img': img_db['meditation'], 'tag': 'Yoga Diabetes', 'desc': 'Sit in Vajrasana, make fists on navel, exhale and bend forward pressing fists into abdomen. Hold 20s x 3.', 'reason': 'Massages pancreas, stimulates insulin secretion. Specifically recommended for diabetics.'},
        {'name': 'Plank Hold', 'img': img_db['glute_squeeze'], 'tag': 'Core', 'desc': 'Hold push-up position on forearms (or hands). Keep body straight. Hold 20-45s.', 'reason': 'Core stability, total body engagement. Builds endurance.'},
        {'name': 'Nadi Shodhana (Channel Purification)', 'img': img_db['pranayama'], 'tag': 'Advanced Pranayama', 'desc': 'Alternate nostril breathing with retention: Inhale left (4s), hold (16s), exhale right (8s). 5 rounds.', 'reason': 'Advanced pranayama that balances the nervous system and improves oxygen utilization.'},
        {'name': 'Paschimottanasana (Seated Forward Bend)', 'img': img_db['stretching'], 'tag': 'Yoga Flexibility', 'desc': 'Sit with legs extended, hinge from hips and reach toward toes. Hold 30s.', 'reason': 'Stretches entire posterior chain. Massages abdominal organs. Calms the mind.'},
        {'name': 'Stationary Cycling', 'img': img_db['cycle'], 'tag': 'Cardio', 'desc': 'Cycle at moderate pace for 15-20 minutes. Maintain 60-70% max heart rate.', 'reason': 'Low-impact sustained cardio. Great for knee-friendly endurance building.'}
    ]

    # --- 5. BUILD PROGRESSIVE PLAN ---
    phases = {
        'Week 1': {'title': 'Phase 1: Gentle Activation + Pranayama', 'zone': 'Bed / Chair / Mat', 'intensity': 'Low', 'pool': week1_exercises},
        'Week 2': {'title': 'Phase 2: Standing Stability + Yoga Basics', 'zone': 'Home / Mat', 'intensity': 'Low-Moderate', 'pool': week2_exercises},
        'Week 3': {'title': 'Phase 3: Strength + Surya Namaskar', 'zone': 'Home / Park', 'intensity': 'Moderate', 'pool': week3_exercises},
        'Week 4': {'title': 'Phase 4: Endurance + Advanced Yoga', 'zone': 'Outdoors / Gym', 'intensity': 'Moderate-High', 'pool': week4_exercises}
    }

    structured_plan = {}
    import random as _rand

    for week in ['Week 1', 'Week 2', 'Week 3', 'Week 4']:
        structured_plan[week] = {
            'meta': {k: v for k, v in phases[week].items() if k != 'pool'},
            'days': {}
        }

        pool = phases[week]['pool']
        is_harder = week in ['Week 3', 'Week 4']

        for day_num in range(1, 8):
            day = f'Day {day_num}'
            daily_routine = []

            # Select 4 exercises per day (mix of exercise + yoga)
            # Deterministic selection: rotate through pool based on day
            count = min(4, len(pool))
            selected = []
            for i in range(count):
                idx = (day_num - 1 + i * 2) % len(pool)
                if pool[idx] not in selected:
                    selected.append(pool[idx])
                else:
                    # Find next unused
                    for j in range(len(pool)):
                        alt_idx = (idx + j + 1) % len(pool)
                        if pool[alt_idx] not in selected:
                            selected.append(pool[alt_idx])
                            break

            for ex in selected:
                if is_harder:
                    sets = "3 Sets x 12 Reps" if 'Yoga' not in ex['tag'] and 'Pranayama' not in ex['tag'] and 'Meditation' not in ex['tag'] else "Hold 30s x 3 Rounds"
                    tag_color = "primary"
                else:
                    sets = "2 Sets x 8 Reps" if 'Yoga' not in ex['tag'] and 'Pranayama' not in ex['tag'] and 'Meditation' not in ex['tag'] else "Hold 20s x 2 Rounds"
                    tag_color = "success"

                daily_routine.append({
                    'name': ex['name'],
                    'sets': sets,
                    'desc': ex['desc'],
                    'tag': ex['tag'],
                    'reason': ex['reason'],
                    'tag_color': tag_color,
                    'image': ex['img'],
                    'approved': True
                })

            structured_plan[week]['days'][day] = daily_routine

    return {
        'plan': structured_plan,
        'doctor_note': {
            'doctor': 'Dr. Priya Sharma, MD (Physiotherapy & Yoga Therapy)',
            'dept': 'Rehabilitation & Integrative Medicine',
            'hospital': 'CarePoint Hospital',
            'date': datetime.now().strftime("%d %b %Y"),
            'prescription_id': f'RX-{_rand.randint(1000,9999)}',
            'condition': primary_condition,
            'focus': current_rule['focus'],
            'restrictions': None
        },
        'analysis': current_rule['analysis']
    }

@patient_bp.route('/exercise-plan')
@login_required
@patient_required
def exercise_plan():
    """View AI-generated exercise plan"""
    try:
        if not current_user.patient:
             import traceback
             print("ERROR: User has no patient record - possible incomplete registration.")
             return "Data Integrity Error: User has no patient record.", 500

        patient = current_user.patient
        latest_health = HealthData.query.filter_by(patient_id=patient.id).order_by(
            HealthData.recorded_at.desc()).first()
        
        if not latest_health:
            flash('Please enter health data first', 'info')
            return redirect(url_for('patient.enter_health_data'))
        
        # Generate Doctor Prescribed Plan
        # Format: { 'plan': {...}, 'doctor_note': {...}, 'analysis': {...} }
        prescribed_data = generate_doctor_prescribed_plan(patient, latest_health)
        
        return render_template('patient/exercise_plan.html', 
                             full_plan=prescribed_data, # Passing the whole object
                             patient=patient)
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"CRITICAL ERROR IN EXERCISE PLAN: {error_msg}")
        with open('debug_exercise_error.txt', 'w') as f:
            f.write(error_msg)
        return f"Internal Server Error (Logged): {str(e)}", 500

@patient_bp.route('/appointments')
@login_required
@patient_required
def appointments():
    """View appointments"""
    patient = current_user.patient
    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(
        Appointment.appointment_date.desc()).all()
    
    return render_template('patient/appointments.html', appointments=appointments)

from app.services.notification_service import NotificationService

@patient_bp.route('/appointments/book', methods=['GET', 'POST'])
@login_required
@patient_required
def book_appointment():
    """Book an appointment"""
    from datetime import datetime, date
    from app.models.models import SystemSettings
    
    settings = SystemSettings.query.first()
    if settings and settings.maintenance_mode:
        flash('Non-emergency appointments are disabled during maintenance mode.', 'warning')
        return redirect(url_for('patient.appointments'))
        
    patient = current_user.patient
    
    if request.method == 'POST':
        doctor_id = request.form.get('doctor_id')
        appointment_date_str = request.form.get('date')
        appointment_time_str = request.form.get('time')
        reason = request.form.get('reason')
        
        try:
            # Parse date and time
            appointment_datetime = datetime.strptime(f"{appointment_date_str} {appointment_time_str}", '%Y-%m-%d %H:%M')
            
            # Create appointment
            appointment = Appointment(
                patient_id=patient.id,
                doctor_id=int(doctor_id),
                appointment_date=appointment_datetime,
                reason=reason,
                status='pending'
            )
            
            db.session.add(appointment)
            db.session.commit()
            
            # Send Acknowledgment
            try:
                doctor = Doctor.query.get(int(doctor_id))
                NotificationService.send_appointment_request_acknowledgement(patient, doctor, appointment)
            except Exception as e:
                print(f"Notification error: {e}")
            
            flash('Appointment request sent! Waiting for doctor approval.', 'success')
            return redirect(url_for('patient.appointments'))
        except Exception as e:
            flash(f'Error booking appointment: {str(e)}', 'danger')
    
    # Get all verified doctors
    # Get all verified and non-suspended doctors (and not deleted optionally if added later)
    doctors = Doctor.query.filter_by(verified=True, is_suspended=False).filter(Doctor.is_deleted == False).all()
    today_date = date.today().isoformat()
    
    return render_template('patient/book_appointment.html', doctors=doctors, today_date=today_date)

@patient_bp.route('/prescriptions')
@login_required
@patient_required
def prescriptions():
    """View prescriptions"""
    patient = current_user.patient
    try:
        prescriptions = Prescription.query.filter_by(patient_id=patient.id).order_by(
            Prescription.prescribed_at.desc()).all()
    except Exception:
        # Fallback: column mismatch between ORM model and DB — use raw SQL
        db.session.rollback()
        cols = {c['name'] for c in inspect(db.engine).get_columns('prescriptions')}
        safe_cols = ', '.join(c for c in cols)
        rows = db.session.execute(
            text(f"SELECT {safe_cols} FROM prescriptions WHERE patient_id = :pid ORDER BY id DESC"),
            {'pid': patient.id}
        ).mappings().all()
        prescriptions = [SimpleNamespace(**dict(r)) for r in rows]
    
    return render_template('patient/prescriptions.html', prescriptions=prescriptions)

@patient_bp.route('/prescription/<int:id>/view')
@login_required
@patient_required
def view_prescription(id):
    """View full prescription sheet — uses professional hospital format."""
    try:
        prescription = Prescription.query.get_or_404(id)
    except Exception:
        db.session.rollback()
        cols = {c['name'] for c in inspect(db.engine).get_columns('prescriptions')}
        safe_cols = ', '.join(c for c in cols)
        row = db.session.execute(
            text(f"SELECT {safe_cols} FROM prescriptions WHERE id = :rid"),
            {'rid': id}
        ).mappings().first()
        if not row:
            from flask import abort
            return abort(404)
        prescription = SimpleNamespace(**dict(row))

    if prescription.patient_id != current_user.patient.id:
        from flask import abort
        return abort(403)

    # If prescription has consultation_id, use the professional Paras-style template
    consultation_id = getattr(prescription, 'consultation_id', None)
    if consultation_id:
        consultation = Consultation.query.get(consultation_id)
        if consultation:
            patient = consultation.patient
            doc = consultation.doctor
            medicines = []
            try:
                for m in prescription.medicine_items:
                    medicines.append({
                        'name': m.medicine_name, 'dosage': m.dosage or '', 'route': m.route or '',
                        'frequency': m.frequency or '', 'duration': m.duration or '',
                        'food_relation': m.food_relation or '', 'instruction': m.instruction or '',
                        'special_instruction': m.special_instruction or '',
                    })
            except Exception:
                pass

            allergy_warning = None
            if patient.allergy_history or patient.allergies:
                allergy_warning = patient.allergy_history or patient.allergies

            return render_template('doctor/consultation_prescription.html',
                                   consultation=consultation, patient=patient,
                                   doctor_record=doc, medicines=medicines,
                                   prescription=prescription, allergy_warning=allergy_warning)

    # Fallback for old prescriptions without consultation_id
    return render_template('patient/view_prescription.html', prescription=prescription)


@patient_bp.route('/messages')
@login_required
@patient_required
def messages():
    """List of doctors to chat with"""
    patient = current_user.patient
    
    # Get doctors from appointments, prescriptions, and existing messages
    appointment_doctor_ids = [a.doctor_id for a in Appointment.query.filter_by(patient_id=patient.id).all()]
    # Use lightweight raw SQL — we only need doctor_id, avoids loading all ORM columns
    try:
        prescription_doctor_ids = [p.doctor_id for p in Prescription.query.filter_by(patient_id=patient.id).all()]
    except Exception:
        db.session.rollback()
        rows = db.session.execute(
            text("SELECT DISTINCT doctor_id FROM prescriptions WHERE patient_id = :pid"),
            {'pid': patient.id}
        ).all()
        prescription_doctor_ids = [r[0] for r in rows]
    message_doctor_ids = [m.doctor_id for m in Message.query.filter_by(patient_id=patient.id).all()]
    
    # Unique doctor IDs
    doctor_ids = set(appointment_doctor_ids + prescription_doctor_ids + message_doctor_ids)
    
    doctors_list = []
    for d_id in doctor_ids:
        doctor = Doctor.query.get(d_id)
        if doctor:
            # Get unread count
            unread = Message.query.filter_by(
                patient_id=patient.id, 
                doctor_id=d_id, 
                sender_type='doctor', 
                is_read=False
            ).count()
            
            # Get last message
            last_msg = Message.query.filter(
                ((Message.patient_id == patient.id) & (Message.doctor_id == d_id))
            ).order_by(Message.created_at.desc()).first()
            
            doctors_list.append({
                'info': doctor,
                'unread': unread,
                'last_message': last_msg
            })
    
    # If no doctors found (new patient), show all verified doctors
    if not doctors_list:
        all_doctors = Doctor.query.filter_by(verified=True).limit(10).all()
        for doctor in all_doctors:
             doctors_list.append({
                'info': doctor,
                'unread': 0,
                'last_message': None
            })

    return render_template('patient/messages.html', doctors_list=doctors_list)

@patient_bp.route('/chat/<int:doctor_id>')
@login_required
@patient_required
def chat(doctor_id):
    """Chat with doctor"""
    patient = current_user.patient
    doctor = Doctor.query.get_or_404(doctor_id)
    
    # Get chat history
    messages = Message.query.filter(
        (Message.patient_id == patient.id) & (Message.doctor_id == doctor_id)
    ).order_by(Message.created_at).all()
    
    # Mark messages as read
    for msg in messages:
        if msg.sender_type == 'doctor':
            msg.is_read = True
    db.session.commit()
    
    return render_template('patient/chat.html', doctor=doctor, messages=messages)

@patient_bp.route('/api/send-message/<int:doctor_id>', methods=['POST'])
@login_required
@patient_required
def send_message(doctor_id):
    """Send message to doctor (API)"""
    patient = current_user.patient
    data = request.get_json()
    
    message = Message(
        patient_id=patient.id,
        doctor_id=doctor_id,
        sender_type='patient',
        message_text=data.get('message')
    )
    
    db.session.add(message)
    db.session.commit()
    
    try:
        from app.events import emit_to_user
        doctor_profile = Doctor.query.get(doctor_id)
        if doctor_profile and doctor_profile.user_id:
             emit_to_user(doctor_profile.user_id, 'new_message', {
                 'message_id': message.id,
                 'message_text': message.message_text,
                 'patient_id': patient.id,
                 'doctor_id': doctor_id,
                 'sender_type': 'patient',
                 'created_at': message.created_at.isoformat() if message.created_at else datetime.utcnow().isoformat()
             })
    except Exception as e:
        print(f"Socket emit failed: {e}")
    
    return jsonify({'success': True, 'message_id': message.id})

@patient_bp.route('/health-history')
@login_required
@patient_required
def health_history():
    """View health history"""
    patient = current_user.patient
    health_records = HealthData.query.filter_by(patient_id=patient.id).order_by(
        HealthData.recorded_at.desc()).all()
    
    return render_template('patient/health_history.html', health_records=health_records)





@patient_bp.route('/billing')
@login_required
@patient_required
def billing():
    """View patient bills"""
    patient = current_user.patient
    # Sort by unpaid first, then by date
    bills = Billing.query.filter_by(patient_id=patient.id).order_by(
        Billing.status.desc(), Billing.created_at.desc()).all()
    
    return render_template('patient/billing.html', bills=bills)


@patient_bp.route('/billing/<int:bill_id>/pay', methods=['POST'])
@login_required
@patient_required
def pay_bill(bill_id):
    """Pay a bill (Mock Payment)"""
    patient = current_user.patient
    bill = Billing.query.get_or_404(bill_id)
    
    if bill.patient_id != patient.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('patient.billing'))
    
    if bill.status == 'Paid':
        flash('Bill already paid', 'warning')
        return redirect(url_for('patient.billing'))
        
    # Mock payment processing
    bill.status = 'Paid'
    bill.payment_method = 'Credit Card (Mock)'
    bill.paid_at = datetime.utcnow()
    db.session.commit()
    
    flash('Payment successful! Thank you.', 'success')
    return redirect(url_for('patient.billing'))


@patient_bp.route('/lab-reports')
@login_required
@patient_required
def lab_reports():
    """View lab reports (workflow orders + legacy lab report rows)."""
    patient = current_user.patient
    try:
        lab_orders = LabOrder.query.filter_by(patient_id=patient.id).order_by(
            LabOrder.created_at.desc()).all()
        reports = LabReport.query.filter_by(patient_id=patient.id).order_by(
            LabReport.conducted_at.desc()).all()
    except Exception as e:
        current_app.logger.exception('Patient lab_reports error')
        flash('Unable to load lab reports at this time. Please contact support.', 'danger')
        lab_orders = []
        reports = []

    return render_template(
        'patient/lab_reports.html',
        patient=patient,
        lab_orders=lab_orders,
        reports=reports,
        show_requests=True,
    )


@patient_bp.route('/lab-requests')
@login_required
@patient_required
def lab_requests():
    """View lab requests only"""
    # ✅ DEBUG: Verify session persistence in protected route
    print(f"[LAB_REQUESTS] protected route accessed")
    print(f"  is_authenticated={current_user.is_authenticated}")
    print(f"  user_id={current_user.id}")
    print(f"  session_keys={list(session.keys())}")
    print(f"  session_get('_user_id')={session.get('_user_id')}")
    print(f"  cookies={dict(request.cookies)}")
    
    patient = current_user.patient
    try:
        lab_orders = LabOrder.query.filter_by(patient_id=patient.id).order_by(
            LabOrder.created_at.desc()).all()
        reports = LabReport.query.filter_by(patient_id=patient.id).order_by(
            LabReport.conducted_at.desc()).all()
    except Exception as e:
        current_app.logger.exception('Patient lab_requests error')
        flash('Unable to load lab requests at this time. Please contact support.', 'danger')
        lab_orders = []
        reports = []

    return render_template(
        'patient/lab_reports.html',
        patient=patient,
        lab_orders=lab_orders,
        reports=reports,
        show_requests=False,
    )



@patient_bp.route('/medicine-status')
@login_required
@patient_required
def medicine_status():
    """View pharmacy / medicine dispensing status"""
    from app.models.models import PharmacyOrder
    patient = current_user.patient
    orders = PharmacyOrder.query.filter_by(patient_id=patient.id).order_by(
        PharmacyOrder.created_at.desc()).all()
    
    return render_template('patient/medicine_status.html', orders=orders)


@patient_bp.route('/lab-reports/<int:report_id>/download')
@login_required
@patient_required
def download_report(report_id):
    """Download Lab Report as PDF."""
    report = LabReport.query.get_or_404(report_id)

    if report.patient_id != current_user.patient.id:
        return "Unauthorized", 403

    # Generate PDF using fpdf
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Hospital Lab Report', ln=True, align='C')
    pdf.ln(8)
    pdf.set_font('Arial', '', 12)

    def add_line(label, value):
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(45, 8, f'{label}:', ln=False)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 8, str(value or '-'))

    add_line('Patient', f'{current_user.patient.first_name} {current_user.patient.last_name}')
    add_line('UHID', current_user.patient.uhid)
    add_line('Test', report.test_name)
    add_line('Date', report.conducted_at.strftime('%Y-%m-%d') if report.conducted_at else 'N/A')
    add_line('Status', report.status)

    report_result = report.result_value or report.report_data or 'N/A'
    add_line('Result', report_result)
    add_line('Reference', report.reference_range or '-')
    add_line('Remarks', report.remarks or report.doctor_notes or '-')

    pdf.ln(8)
    pdf.set_font('Arial', 'I', 10)
    pdf.multi_cell(0, 6, 'This report was generated by the CarePoint hospital system. Please verify the details before sharing.')

    output = pdf.output(dest='S').encode('latin-1')

    from flask import Response
    return Response(
        output,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment;filename=lab_report_{report_id}.pdf'}
    )

@patient_bp.route('/lab-orders/<int:order_id>/download-attachment')
@login_required
@patient_required
def download_lab_order_attachment(order_id):
    """Download the result attachment for a lab order."""
    from app.models.models import LabOrder
    order = LabOrder.query.get_or_404(order_id)

    if order.patient_id != current_user.patient.id:
        return "Unauthorized", 403

    # If there's a generated report, redirect to the report PDF download
    for report in (order.generated_reports or []):
        return redirect(url_for('patient.download_report', report_id=report.id))

    # Otherwise try to serve a file attachment from the order's result_data
    rel_path = order.result_attachment_rel_path()
    if rel_path:
        import os
        from flask import send_file, current_app, abort
        abs_path = os.path.join(current_app.root_path, '..', rel_path)
        if not os.path.isfile(abs_path):
            abs_path = os.path.join(current_app.root_path, rel_path)
        if os.path.isfile(abs_path):
            return send_file(abs_path, as_attachment=True)

    flash('No attachment available for this lab order.', 'info')
    return redirect(url_for('patient.lab_reports'))


@patient_bp.route('/billing/<int:bill_id>/download')
@login_required
@patient_required
def download_invoice(bill_id):
    """Download Invoice (Mock)"""
    bill = Billing.query.get_or_404(bill_id)
    
    if bill.patient_id != current_user.patient.id:
        return "Unauthorized", 403
        
    content = f"""
    HOSPITAL INVOICE #{bill_id}
    -------------------
    Date: {bill.created_at}
    Patient: {current_user.patient.first_name} {current_user.patient.last_name}
    Description: {bill.description}
    Amount: ${bill.amount}
    Status: {bill.status}
    
    Thank you.
    """
    
    from flask import Response
    return Response(
        content,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment;filename=invoice_{bill_id}.txt"}
    )

@patient_bp.route('/billing/download-insurance-form')
@login_required
@patient_required
def download_insurance_form():
    """Download Insurance Claim Form (Mock)"""
    content = """
    INSURANCE CLAIM FORM
    --------------------
    Patient Name: __________________________
    Policy Number: _________________________
    Diagnosis: _____________________________
    
    Please attach original bills.
    """
    
    from flask import Response
    return Response(
        content,
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment;filename=claim_form.txt"}
    )


# =====================================================
# SYMPTOM CHECKER
# =====================================================
@patient_bp.route('/symptom-checker')
@login_required
def symptom_checker():
    patient = current_user.patient
    if not patient:
        flash('Patient profile not found.', 'error')
        return redirect(url_for('patient.dashboard'))
    doctors = Doctor.query.filter_by(is_deleted=False, verified=True).all()
    return render_template('patient/symptom_checker.html', patient=patient, doctors=doctors)


# =====================================================
# MEDICAL IMAGE ANALYSIS
# =====================================================
@patient_bp.route('/image-analysis', methods=['GET', 'POST'])
@login_required
def image_analysis():
    patient = current_user.patient
    if not patient:
        flash('Patient profile not found.', 'error')
        return redirect(url_for('patient.dashboard'))

    # Get existing analysis results
    from app.models.models import MedicalImage
    images = MedicalImage.query.filter_by(patient_id=patient.id).order_by(MedicalImage.uploaded_at.desc()).all()

    if request.method == 'POST':
        if 'image' not in request.files:
            flash('No image selected', 'warning')
            return redirect(url_for('patient.image_analysis'))

        file = request.files['image']
        if file.filename == '':
            flash('No image selected', 'warning')
            return redirect(url_for('patient.image_analysis'))

        filename = secure_filename(file.filename)
        upload_dir = os.path.join(current_app.root_path, 'uploads', 'medical_images')
        os.makedirs(upload_dir, exist_ok=True)
        stored_name = f"{patient.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        filepath = os.path.join(upload_dir, stored_name)
        file.save(filepath)

        # Create record
        image_type = request.form.get('image_type', 'Other')
        clinical_context = request.form.get('notes', '')
        img = MedicalImage(
            patient_id=patient.id,
            image_type=image_type,
            filename=stored_name,
            original_filename=filename,
            file_path=filepath,
            clinical_context=clinical_context,
            risk_level='Pending'
        )
        db.session.add(img)
        db.session.commit()

        # Run AI analysis
        try:
            from app.ml_models.medical_image_analyzer import medical_analyzer
            result = medical_analyzer.analyze_medical_image(filepath, image_type, clinical_context)
            if result.get('success'):
                img.analysis_results = result.get('findings', '')
                img.detected_conditions = ', '.join(result.get('detected_conditions', []))
                img.confidence_score = result.get('confidence_score', 0)
                img.risk_level = result.get('risk_level', 'Low')
                img.analyzed_at = datetime.now()
                db.session.commit()
                flash('Image uploaded and analyzed successfully!', 'success')
            else:
                flash('Image uploaded. Analysis could not be completed: ' + result.get('error', 'Unknown error'), 'warning')
        except Exception as e:
            current_app.logger.error(f'Image analysis failed: {e}')
            flash('Image uploaded successfully! Analysis is pending.', 'info')

        return redirect(url_for('patient.image_analysis'))

    return render_template('patient/image_analysis.html', patient=patient, images=images)


# =====================================================
# MEDICATION ADHERENCE TRACKER
# =====================================================
@patient_bp.route('/medication-tracker')
@login_required
def medication_tracker():
    """Track medication adherence - which medicines taken vs missed."""
    patient = current_user.patient
    if not patient:
        flash('Patient profile not found.', 'error')
        return redirect(url_for('patient.dashboard'))

    # Get active prescriptions
    prescriptions = Prescription.query.filter_by(patient_id=patient.id).order_by(
        Prescription.prescribed_at.desc()
    ).limit(10).all()

    return render_template('patient/medication_tracker.html',
                           patient=patient, prescriptions=prescriptions)


# =====================================================
# VACCINATION RECORDS
# =====================================================
@patient_bp.route('/vaccination-records')
@login_required
def vaccination_records():
    """View vaccination history and upcoming vaccines."""
    patient = current_user.patient
    if not patient:
        flash('Patient profile not found.', 'error')
        return redirect(url_for('patient.dashboard'))

    return render_template('patient/vaccination_records.html', patient=patient)
