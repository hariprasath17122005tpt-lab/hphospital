import random
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_required, current_user
from app.models.models import (db, Patient, HealthData, PatientVitals, Appointment, Prescription,
                               Message, DietPlan, ExercisePlan, Doctor, MedicalImage,
                               Billing, LabReport, LabOrder)
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
    Generate an ULTRA-ADVANCED Diet Plan (Personal Project Level).
    Total Features: 22+
    
    NEW UNIQUE INNOVATIONS:
    16. 🕒 Circadian Metabolic Clock (Best times to eat)
    17. 📉 Sugar Spike Simulator (Visual Graph Data)
    18. 🛒 Smart Grocery List & Budget
    19. ⚖️ Cheat Meal Negotiator
    20. 🌦️ Weather-Adaptive Foods
    21. 🎭 Mood-Food Repair Kit
    22. 👨‍🍳 AI Chef (Recipe Cards)
    """
    
    # --- 1. HEALTH DATA & RISK ANALYSIS (Existing Logic) ---
    diabetes_risk = health_data.diabetes_risk or 0
    hypertension_risk = health_data.hypertension_risk or 0
    heart_risk = health_data.heart_disease_risk or 0
    bmi = health_data.bmi or 0
    
    active_conditions = []
    if diabetes_risk > 60: active_conditions.append({'name': 'Diabetes', 'priority': 2, 'dept': 'Endocrinology'})
    if hypertension_risk > 60: active_conditions.append({'name': 'Hypertension', 'priority': 3, 'dept': 'Cardiology'})
    if heart_risk > 60: active_conditions.append({'name': 'Heart Disease', 'priority': 1, 'dept': 'Cardiology'})
    if bmi > 28: active_conditions.append({'name': 'Obesity', 'priority': 4, 'dept': 'Nutrition'})
    
    active_conditions.sort(key=lambda x: x['priority'])
    
    if not active_conditions:
        active_conditions.append({'name': 'General Wellness', 'priority': 10, 'dept': 'Preventive Medicine'})
    
    primary_condition = active_conditions[0]
    stacking_order = [c['name'] for c in active_conditions]
    departments = list(set([c['dept'] for c in active_conditions]))
    departments.append('Nutrition & Dietetics')
    
    # --- 2. DIET STRATEGY & 3-WEEK DAILY PLAN ---
    diet_name = "Balanced Health Protocol"
    three_week_plan = {}
    
    # Database of variety meals
    meal_db = {
        'Diabetes': {
            'breakfast': [
                "Steel-cut Oats with Chia Seeds & Berries", "Moong Dal Cheela with Mint Chutney", "Ragi Malt with 5 Almonds",
                "Scrambled Eggs (2) with Spinach & Mushroom", "Vegetable Dalia (Broken Wheat) Upma", "Greek Yogurt with Walnuts & Flaxseeds",
                "Besan Chilla with Paneer Filling"
            ],
            'lunch': [
                "Brown Rice + Methi Dal + Cucumber Salad", "Quinoa Bowl with Grilled Chicken & Veggies", "Bajra Roti + Palak Paneer (Low Fat)",
                "Grilled Fish with Steamed Broccoli & Sweet Potato", "Chickpea (Chana) Salad with Olive Oil Dressing", "Multi-grain Chapati + Bhindi Masala + Dal",
                "Tofu Stir-fry with Bell Peppers & Brown Rice"
            ],
            'dinner': [
                "Grilled Fish + Clear Soup", "Soya Chunks Curry + 1 Roti", "Lentil Soup with Steamed Vegetables",
                "Grilled Chicken Breast + Zucchini Noodles", "Paneer Tikka (Grilled) + Green Salad", "Boiled Egg Salad with Avocado",
                "Mushroom Soup + 1 Multigrain Toast"
            ]
        },
        'Hypertension': {
            'breakfast': [
                "Spinach & Tomato Omelet + Whole Wheat Toast", "Banana & Flaxseed Smoothie (Almond Milk)", "Oats Porridge with Apple & Cinnamon",
                "Upma with lots of Vegetables (Low Salt)", "Yogurt Parfait with Berries & Granola", "Poached Eggs on Avocado Toast",
                "Papaya Bowl with Sunflower Seeds"
            ],
            'lunch': [
                "Curd Rice with Pomegranate (Low Salt) + Beetroot Poriyal", "Lemon Rice (Brown) + Grilled Fish", "Whole Wheat Pasta with Marinara & Veggies",
                "Lentil Soup + Baked Sweet Potato Wedges", "Grilled Mackeral + Quinoa Salad", "Kidney Bean (Rajma) Salad with Peppers",
                "Vegetable Stew with Appam (1)"
            ],
            'dinner': [
                "Baked Sweet Potato + Green Salad", "Vegetable Stew + Idiyappam", "Grilled Chicken with Roasted Asparagus",
                "Tomato Basil Soup + 1 Slice Toast", "Steamed Fish with Lemon & Herbs", "Spinach & Corn Sandwich (Whole Wheat)",
                "Pumpkin Soup with Roasted Seeds"
            ]
        },
        'Heart Disease': {
            'breakfast': [
                "Walnut & Apple Oatmeal Bowl", "Egg White Scramble with Spinach & Avocado", "Chia Pudding with Almond Milk",
                "Whole Grain Toast with Peanut Butter & Banana", "Berry Smoothie with Spinach & Flaxseeds", "Vegetable Poha (Red Rice)",
                "Cottage Cheese (Paneer) Sandwich (Grill)"
            ],
            'lunch': [
                "Grilled Mackerel with Sautéed Greens", "Lentil Soup + Multi-grain Toast", "Salmon Salad with Vinaigrette",
                "Soya Bean Curry + Brown Rice", "Chicken Stir-fry with Broccoli & Garlic", "Chickpea & Quinoa Bowl",
                "Tuna Salad Lettuce Wraps"
            ],
            'dinner': [
                "Boiled Veggies with Lemon Dressing + Tofu", "Roasted Pumpkin Soup + Grilled Chicken", "Steamed Cod with Green Beans",
                "Clear Vegetable Soup + Hummus Dip", "Baked Eggplant with Tomato Sauce", "Zucchini Boats with Ground Chicken",
                "Beetroot & Carrot Salad with Walnuts"
            ]
        },
        'Obesity': {
            'breakfast': [
                "Green Tea + 2 Boiled Eggs", "Protein Smoothie (Berry & Spinach)", "Oat Bran Pancake (Sugar-free)",
                "Mushroom & Pepper Omelet", "Apple Slices with Almond Butter", "Greek Yogurt with Chia Seeds",
                "Sprouted Moong Salad"
            ],
            'lunch': [
                "Grilled Chicken Salad with Vinaigrette (No Mayo)", "Tuna Salad Lettuce Wrap", "Grilled Tofu with Steamed Broccoli",
                "Lentil Soup + Cucumber Sticks", "Palak Paneer (No Cream) + 1 Roti", "Quinoa Salad with Black Beans",
                "Egg Salad with Celery & Mustard"
            ],
            'dinner': [
                "Clear Chicken Soup +  Zucchini Noodles", "Sauteed Mushrooms + Grilled Fish", "Cauliflower Rice Stir-fry",
                "Baked Salmon with Asparagus", "Broccoli Soup + 5 Almonds", "Stir-fried Tofu with Bok Choy",
                "Cabbage Soup (Detox Style)"
            ]
        }
    }

    # Helper to generate days with rotation
    def generate_days(week_num, condition):
        days = {}
        # Get the meal list for the condition, fallback to Obesity if not found
        c_meals = meal_db.get(condition, meal_db['Obesity'])
        
        # Calculate rotation offset based on week number (Week 1 = 0, Week 2 = 2, Week 3 = 4)
        # This ensures Week 1 Day 1 is Meal 0, Week 2 Day 1 is Meal 2, etc.
        offset = (week_num - 1) * 2
        
        for d in range(1, 8):
            day_num = f"Day {d}"
            # Use modulo to cycle through the 7 meals
            b_idx = (d - 1 + offset) % 7
            l_idx = (d - 1 + offset + 1) % 7 # Lunch offset by 1 for variety within day
            d_idx = (d - 1 + offset + 2) % 7 # Dinner offset by 2
            
            days[day_num] = {
                'breakfast': c_meals['breakfast'][b_idx],
                'lunch': c_meals['lunch'][l_idx],
                'dinner': c_meals['dinner'][d_idx]
            }
        return days

    # Defaults
    lab_insights = []
    consequences = []
    superfood = {}
    impact_timeline = []
    why_this_food = ""
    
    if primary_condition['name'] == 'Diabetes':
        diet_name = "Metabolic Control (Low-GI) Protocol"
        three_week_plan = {
            'Week 1 (Stabilize)': generate_days(1, 'Diabetes'),
            'Week 2 (Variety)': generate_days(2, 'Diabetes'),
            'Week 3 (Boost)': generate_days(3, 'Diabetes')
        }
        lab_insights.append({'test': 'Fasting Sugar', 'value': f"{health_data.fasting_sugar} mg/dL",'status': 'High' if (health_data.fasting_sugar or 0) > 100 else 'Normal','diet_rule': 'Complex Carbs Only', 'reason': 'Prevents insulin spikes.'})
        consequences = ['Persistent hyperglycemia', 'Nerve damage risk', 'Kidney strain']
        superfood = {'name': 'Bitter Melon (Karela)', 'benefit': 'Contains compounds that act like insulin.'}
        why_this_food = "Focuses on complex carbs to prevent spikes."
        impact_timeline = [{'time': 'Week 1', 'benefit': 'Stable Energy'}, {'time': 'Month 1', 'benefit': 'Lower Fasting Sugar'}]
        
    elif primary_condition['name'] == 'Heart Disease':
        diet_name = "Cardiac Protective (TLC) Protocol"
        three_week_plan = {
            'Week 1 (Detox)': generate_days(1, 'Heart Disease'),
            'Week 2 (Strengthen)': generate_days(2, 'Heart Disease'),
            'Week 3 (Maintain)': generate_days(3, 'Heart Disease')
        }
        lab_insights.append({'test': 'Heart Risk', 'value': f"{int(heart_risk)}%",'status': 'Elevated','diet_rule': 'Zero Trans Fat', 'reason': 'Reduces arterial plaque.'})
        consequences = ['Arterial hardening', 'Stroke risk', 'Reduced efficiency']
        superfood = {'name': 'Avocado', 'benefit': 'Monounsaturated fats lower bad cholesterol.'}
        why_this_food = "Lipid-lowering foods to clear arteries."
        impact_timeline = [{'time': 'Week 2', 'benefit': 'Better Circulation'}, {'time': 'Month 1', 'benefit': 'Lower LDL'}]

    elif primary_condition['name'] == 'Hypertension':
        diet_name = "DASH Advanced (Low-Sodium) Protocol"
        three_week_plan = {
            'Week 1 (Sodium Detox)': generate_days(1, 'Hypertension'),
            'Week 2 (Balance)': generate_days(2, 'Hypertension'),
            'Week 3 (Sustain)': generate_days(3, 'Hypertension')
        }
        lab_insights.append({'test': 'BP', 'value': f"{health_data.systolic_bp}/{health_data.diastolic_bp}",'status': 'High','diet_rule': 'Potassium Boost', 'reason': 'Counteracts sodium.'})
        consequences = ['Kidney strain', 'Vision issues', 'Headaches']
        superfood = {'name': 'Beetroot', 'benefit': 'Nitrates convert to nitric oxide, dilating vessels.'}
        why_this_food = "High Potassium diet to relax blood vessels."
        impact_timeline = [{'time': 'Day 3', 'benefit': 'Less Bloating'}, {'time': 'Week 2', 'benefit': 'Lower BP'}]
        
    else: # Obesity / General
        diet_name = "Caloric Deficit Protocol"
        three_week_plan = {
            'Week 1': generate_days(1, 'Obesity'),
            'Week 2': generate_days(2, 'Obesity'),
            'Week 3': generate_days(3, 'Obesity')
        }
        lab_insights.append({'test': 'BMI', 'value': f"{round(bmi, 1)}",'status': 'Overweight','diet_rule': 'High Protein', 'reason': 'Boosts metabolism.'})
        consequences = ['Joint pain', 'Metabolic syndrome', 'Sleep apnea']
        superfood = {'name': 'Green Tea (Matcha)', 'benefit': 'EGCG Catechins drive metabolic burn.'}
        why_this_food = "Caloric deficit with protein retention."
        impact_timeline = [{'time': 'Week 1', 'benefit': 'Water Weight Loss'}, {'time': 'Month 1', 'benefit': 'Fat Loss'}]

    # --- 3. INNOVATIONS ---
    organ_benefits = [{'organ': '❤️ Heart', 'benefit': 'Low sodium protection'}, {'organ': '🧠 Brain', 'benefit': 'Omega-3 boost'}]
    food_effects = [{'food': 'Spinach', 'immediate': 'Less bloating', 'long_term': 'BP Control'}]
    simple_rules = ["No white sugar", "Half plate veggies", "Stop at 80% full"]
    festival_guide = {'strategy': 'Damage Control', 'safe_foods': ['Grills', 'Salads'], 'portion_limit': '1 Plate', 'recovery': 'Fast 14h'}
    sleep_advice = {'correlation': 'Late dinner disrupts deep sleep.', 'rule': 'Finish by 8 PM.'}
    classified_foods = [{'name': 'Greens', 'tag': 'Safe', 'color': 'success'}, {'name': 'Fried', 'tag': 'Avoid', 'color': 'danger'}]
    medico_legal = {'statement': 'Adjunct therapy only.', 'disclaimer': 'Consult specialist.'}

    # 16. Circadian Clock
    circadian_schedule = [
        {'time': '07:00 AM', 'activity': 'Hydration (500ml)', 'icon': 'tint'},
        {'time': '08:30 AM', 'activity': 'Breakfast (High Fiber)', 'icon': 'cloud-sun'},
        {'time': '01:00 PM', 'activity': 'Lunch (Max Calories)', 'icon': 'sun'},
        {'time': '07:30 PM', 'activity': 'Dinner (Lightest Meal)', 'icon': 'moon'},
        {'time': '10:00 PM', 'activity': 'Fasting Window Begins', 'icon': 'stopwatch'}
    ]

    # 17. Sugar Spike Simulator
    sugar_graph_data = {
        'labels': ['0h', '1h', '2h', '3h'],
        'standard': [90, 180, 160, 110], 
        'smart': [90, 130, 110, 95]       
    }

    # 19. Cheat Meal Negotiator
    cheat_options = [
        {'craving': 'Pizza 🍕', 'fix': 'Eat 2 slices max + Large Salad + 20 min Walk'},
        {'craving': 'Ice Cream 🍦', 'fix': '1 Scoop only + Eat 5 Almonds before (Fiber buffer)'},
        {'craving': 'Biryani 🍛', 'fix': 'Double the Raita + Reduce Rice + Walk 30 mins'},
        {'craving': 'Burger 🍔', 'fix': 'Remove top bun (Open faced) + No Fries'}
    ]

    # 20. Weather Adaptive
    weather_advice = {
        'season': '❄️ Winter Protocols',
        'foods': 'Ginger Tea, Garlic Soups, Root Vegetables',
        'why': 'Boosts immunity against seasonal flu and keeps body warm.'
    }

    # 21. Mood Repair Kit
    mood_kit = [
        {'mood': '🤯 Stressed', 'food': 'Dark Chocolate (Magnesium)', 'action': 'Deep Breathe'},
        {'mood': '😴 Tired', 'food': 'Citrus Fruit (Vitamin C)', 'action': 'Hydrate'},
        {'mood': '😔 Low/Sad', 'food': 'Walnuts (Omega-3)', 'action': 'Sunlight Exposure'}
    ]

    # --- COMPILE ---
    plan = {
        'diet_type': diet_name,
        'conditions': ', '.join(stacking_order),
        'stacking_order': stacking_order,
        'departments': departments,
        'weekly_plan': three_week_plan, # Now contains nested Days
        'lab_insights': lab_insights,
        'organ_benefits': organ_benefits,
        'food_effects': food_effects,
        'simple_rules': simple_rules,
        'festival_guide': festival_guide,
        'sleep_advice': sleep_advice,
        'consequences': consequences,
        'classified_foods': classified_foods,
        'medico_legal': medico_legal,
        
        # RESTORED / NEW
        'superfood': superfood,
        'impact_timeline': impact_timeline,
        'why_this_food': why_this_food,
        'circadian_schedule': circadian_schedule,
        'sugar_graph_data': sugar_graph_data,
        'cheat_options': cheat_options,
        'weather_advice': weather_advice,
        'mood_kit': mood_kit,

        'confidence_score': 96,
        'water_intake': '3 Liters',
        'risk_warning': '⚠️ Sudden drastic diet changes may cause electrolyte imbalance or weakness. Start gradually.',
        'eating_speed_advice': 'Fast eating creates insulin spikes. Chew each bite 20-25 times.',
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

        # Choose a source for displayed vitals: prefer HealthData for AI metrics, fallback to nurse vitals
        displayed_vitals = latest_health if latest_health else latest_vitals

        # Process Health Data if available
        if latest_health:
            # 1. Update Health Score
            d_risk = latest_health.diabetes_risk or 0
            h_risk = latest_health.heart_disease_risk or 0
            hy_risk = latest_health.hypertension_risk or 0
             
            avg_risk = (d_risk + h_risk + hy_risk) / 3
            lifestyle_bonus = 0
            if latest_health.smoking is False: lifestyle_bonus += 5
            if latest_health.alcohol is False: lifestyle_bonus += 5
            if (latest_health.exercise_minutes or 0) > 30: lifestyle_bonus += 5
             
            health_score = int(100 - avg_risk + lifestyle_bonus)
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
    
        # Get health data history for charts (last 7 entries)
        health_records = HealthData.query.filter_by(patient_id=patient.id).filter(
            HealthData.recorded_at >= (datetime.now() - timedelta(days=7))
        ).order_by(HealthData.recorded_at.asc()).all()
    
        # Process into Last 7 Days structure
        today = datetime.now().date()
        last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        
        chart_dates = [d.strftime('%a') for d in last_7_days] # e.g. "Mon", "Tue"
        
        # Map data by date (key: date object)
        health_map = {h.recorded_at.date(): h for h in health_records}
        
        chart_heart_rate = []
        chart_bp_sys = []
        chart_sugar = []
        chart_sleep = []
        
        for d in last_7_days:
            if d in health_map:
                h = health_map[d]
                chart_heart_rate.append(h.heart_rate or 0)
                chart_bp_sys.append(h.systolic_bp or 0)
                chart_sugar.append(h.fasting_sugar or 0)
                chart_sleep.append(h.sleep_hours or 0)
            else:
                # No data for this day -> 0 (Flat line)
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
        
        return render_template('patient/dashboard_enhanced.html',
                             patient=patient,
                             latest_health=latest_health,
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
        systolic_bp = int(request.form.get('systolic_bp', 0))
        diastolic_bp = int(request.form.get('diastolic_bp', 0))
        fasting_sugar = float(request.form.get('fasting_sugar', 0))
        random_sugar = float(request.form.get('random_sugar', 0))
        heart_rate = int(request.form.get('heart_rate', 0))
        symptoms = request.form.get('symptoms', '')
        exercise_minutes = int(request.form.get('exercise_minutes', 0))
        sleep_hours = float(request.form.get('sleep_hours', 0))
        stress_level = request.form.get('stress_level', 'Low')
        smoking = request.form.get('smoking') == 'on'
        alcohol = request.form.get('alcohol') == 'on'
        temperature = float(request.form.get('temperature', 98.6))
        
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
    Generate a 'Doctor Prescribed' Rehabilitation Plan
    Crucial for Clinical Realism.
    """
    
    # --- 1. ROBUST IMAGE BANK (Unsplash Source IDs - Verified) ---
    img_db = {
        # Verified & Relevant - UPDATED for Accuracy
        'ankle_pumps': 'https://images.unsplash.com/photo-1588286840104-8957b019727f?w=600&q=80', # Barefoot/Yoga Studio (Active Feet)
        'glute_squeeze': 'https://images.unsplash.com/photo-1518611012118-696072aa579a?w=600&q=80', # Mat exercise
        'walking': 'https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=600&q=80', # Walking
        
        # Specific Fixes
        'squat': 'https://images.unsplash.com/photo-1541534741688-6078c6bfb5c5?w=600&q=80', # Real squat action
        'standing_balance': 'https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=600&q=80', # Active Lunge/Balance Pose
        
        # Valid replacements
        'chair_sit': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=600&q=80',
        'seated_knee': 'https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=600&q=80',
        'wall_pushup': 'https://images.unsplash.com/photo-1599058945522-28d584b6f0ff?w=600&q=80',
        'heel_raise': 'https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=600&q=80',
        
        'cycle': 'https://images.unsplash.com/photo-1517649763962-0c623066013b?w=600&q=80',
        'weights': 'https://images.unsplash.com/photo-1583454110551-21f2fa2afe61?w=600&q=80',
        'yoga': 'https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=600&q=80',
        
        # Fallbacks
        'generic_stretch': 'https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=600&q=80'
    }

    # --- 2. PATIENT PROFILING ---
    def _to_num(value):
        try:
            if value is None:
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    conditions = []
    # Guard against missing or non-numeric health metrics
    heart_risk = _to_num(health_data.heart_disease_risk)
    bmi = _to_num(health_data.bmi)
    hypertension_risk = _to_num(health_data.hypertension_risk)
    diabetes_risk = _to_num(health_data.diabetes_risk)

    if heart_risk > 60: conditions.append('Cardiac')
    if bmi > 30: conditions.append('Obesity')
    if hypertension_risk > 60: conditions.append('Hypertension')
    if diabetes_risk > 60: conditions.append('Diabetes')
    
    if not conditions: conditions.append('General Recovery')
    
    primary_condition = conditions[0]
    
    # --- 3. CLINICAL RULES ---
    rules = {
        'Cardiac': {
            'focus': 'Heart Rate Control',
            'analysis': {
                'safe': ['Slow Walk', 'Seated Stretching', 'Breathing Exercises'],
                'caution': ['Stair Climbing (Assisted)', 'Brisk Walking'],
                'forbidden': ['HIIT', 'Heavy Lifting (>5kg)', 'Sprinting']
            }
        },
        'Obesity': {
            'focus': 'Joint Protection & Mobility',
            'analysis': {
                'safe': ['Water Aerobics', 'Chair Exercises', 'Walking'],
                'caution': ['Deep Squats', 'Planks'],
                'forbidden': ['High Impact Jumps', 'Burpees', 'Running']
            }
        },
        'Hypertension': {
            'focus': 'Stress Reduction & Flow',
            'analysis': {
                'safe': ['Meditative Walk', 'Yoga', 'Tai Chi'],
                'caution': ['Overhead Press', 'Isometric Holds'],
                'forbidden': ['Inversion Poses', 'Intense Cardio', 'Heavy Weightlifting']
            }
        },
        'Diabetes': {
            'focus': 'Glucose Stabilization',
            'analysis': {
                'safe': ['Post-Meal Walk', 'Resistance Bands', 'Cycling'],
                'caution': ['Exercising on Empty Stomach', 'Barefoot Exercise'],
                'forbidden': ['Extreme Endurance', 'High Heat Yoga']
            }
        },
        'General Recovery': {
            'focus': 'Mobility Restoration',
            'analysis': {
                'safe': ['Bed Mobility', 'Ankle Rotation', 'Glute Squeezes'],
                'caution': ['Standing Unassisted'],
                'forbidden': ['Lifting > 10kg', 'Twisting']
            }
        }
    }
    
    current_rule = rules.get(primary_condition, rules['General Recovery'])
    
    # --- 4. EXERCISE LIBRARY (Weekly Progression) ---
    
    # Week 1: Bed/Chair Mobility (Low Impact)
    week1_exercises = [
        {'name': 'Ankle Pumps', 'img': img_db['ankle_pumps'], 'tag': 'Circulation', 'desc': 'Pump ankles up and down slowly.', 'reason': 'Prevents DVT & improves flow.'},
        {'name': 'Glute Squeezes', 'img': img_db['glute_squeeze'], 'tag': 'Iso-Tone', 'desc': 'Squeeze glutes for 5s, relax.', 'reason': 'Maintains muscle tone safely.'},
        {'name': 'Deep Breathing', 'img': img_db['yoga'], 'tag': 'Lung Health', 'desc': 'Inhale 4s, hold 2s, exhale 6s.', 'reason': 'Improves oxygen saturation.'},
        {'name': 'Seated Knee Ext', 'img': img_db['seated_knee'], 'tag': 'Mobility', 'desc': 'Straighten knee while seated.', 'reason': 'Gentle quad strengthening.'},
        {'name': 'Neck Stretches', 'img': img_db['generic_stretch'], 'tag': 'Flexibility', 'desc': 'Gently tilt head side to side.', 'reason': 'Reduces cervical tension.'}
    ]

    # Week 2: Standing Stability (Moderate)
    week2_exercises = [
        {'name': 'Chair Stand', 'img': img_db['chair_sit'], 'tag': 'Strength', 'desc': 'Stand up from chair without hands.', 'reason': 'Builds functional leg strength.'},
        {'name': 'Heel Raises', 'img': img_db['heel_raise'], 'tag': 'Balance', 'desc': 'Lift heels while holding chair.', 'reason': 'Strengthens calves & ankles.'},
        {'name': 'Side Leg Raise', 'img': img_db['glute_squeeze'], 'tag': 'Hip Strength', 'desc': 'Lie on side, lift top leg.', 'reason': 'Stabilizes hip abductors.'},
        {'name': 'Marching in Place', 'img': img_db['walking'], 'tag': 'Cardio', 'desc': 'Lift knees high while standing.', 'reason': 'Increases heart rate safely.'},
        {'name': 'Torso Twists', 'img': img_db['generic_stretch'], 'tag': 'Mobility', 'desc': 'Gentle rotation of upper body.', 'reason': 'Improves spinal mobility.'}
    ]

    # Week 3: Strength Building (Active)
    week3_exercises = [
        {'name': 'Wall Push-ups', 'img': img_db['wall_pushup'], 'tag': 'Upper Body', 'desc': 'Push against wall, keep back straight.', 'reason': 'Builds chest & arm strength.'},
        {'name': 'Mini Lunges', 'img': img_db['standing_balance'], 'tag': 'Leg Strength', 'desc': 'Small step forward, slight bend.', 'reason': 'Improves balance & quads.'},
        {'name': 'One Leg Balance', 'img': img_db['standing_balance'], 'tag': 'Stability', 'desc': 'Stand on one foot for 10s.', 'reason': 'Critical for fall prevention.'},
        {'name': 'Step-Ups', 'img': img_db['heel_raise'], 'tag': 'Functional', 'desc': 'Step up onto a low step.', 'reason': 'Functional stair climbing.'},
        {'name': 'Arm Circles', 'img': img_db['seated_knee'], 'tag': 'Mobility', 'desc': 'Large circles with arms.', 'reason': 'Shoulder joint range of motion.'}
    ]

    # Week 4: Functional & Endurance (Advanced)
    week4_exercises = [
        {'name': 'Brisk Walk', 'img': img_db['walking'], 'tag': 'Endurance', 'desc': 'Walk at a talking pace for 15m.', 'reason': 'Cardiovascular conditioning.'},
        {'name': 'Bodyweight Squats', 'img': img_db['squat'] if 'squat' in img_db else img_db['chair_sit'], 'tag': 'Strength', 'desc': 'Sit back as if into a chair.', 'reason': 'Total body strengthening.'},
        {'name': 'Plank Hold', 'img': img_db['glute_squeeze'], 'tag': 'Core', 'desc': 'Hold pushup position on knees/toes.', 'reason': 'Core stability.'},
        {'name': 'Light Weights', 'img': img_db['weights'], 'tag': 'Resistance', 'desc': 'Bicep curls with light objects.', 'reason': 'Arm strength definition.'},
        {'name': 'Stationary Cycle', 'img': img_db['cycle'], 'tag': 'Cardio', 'desc': 'Cycling at moderate pace.', 'reason': 'Low impact sustained cardio.'}
    ]

    # --- 5. PROGRESSIVE TIMELINE GENERATION ---
    phases = {
        'Week 1': {'title': 'Phase 1: Activation', 'zone': 'Bed/Chair', 'intensity': 'Low', 'pool': week1_exercises},
        'Week 2': {'title': 'Phase 2: Stability', 'zone': 'Home Active', 'intensity': 'Low-Mod', 'pool': week2_exercises},
        'Week 3': {'title': 'Phase 3: Strengthening', 'zone': 'Gym/Home', 'intensity': 'Moderate', 'pool': week3_exercises},
        'Week 4': {'title': 'Phase 4: Endurance', 'zone': 'Outdoors', 'intensity': 'High', 'pool': week4_exercises}
    }
    
    structured_plan = {}
    
    import random
    
    for week in ['Week 1', 'Week 2', 'Week 3', 'Week 4']:
        structured_plan[week] = {
            'meta': {k:v for k,v in phases[week].items() if k != 'pool'},
            'days': {}
        }
        
        pool = phases[week]['pool']
        # Difficulty Multiplier
        is_harder = week in ['Week 3', 'Week 4']
        
        for day in ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7']:
            daily_routine = []
            
            # Select 3 distinct exercises from the weekly pool
            # Use random.sample to ensure uniqueness per day
            day_seed = week + day + str(random.randint(1, 1000))
            random.seed(day_seed) 
            selected_ex = random.sample(pool, 3)
            
            for ex in selected_ex:
                # Custom sets based on week
                if is_harder:
                    sets = "3 Sets x 12 Reps"
                    tag_color = "primary"
                else:
                    sets = "2 Sets x 8 Reps"
                    tag_color = "success"
                
                # Check formatting
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
            'doctor': 'Dr. Sarah Smith, MD (Physiotherapy)',
            'dept': 'Orthopedics & Rehab Dept',
            'hospital': 'City General Hospital',
            'date': datetime.now().strftime("%d %b %Y"),
            'prescription_id': f'RX-{random.randint(1000,9999)}',
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
    """View full prescription sheet"""
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


