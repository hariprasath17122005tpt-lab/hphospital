import traceback
from app.models.models import HealthData, Patient
from app import create_app
from app.routes.patient import generate_personalized_diet_plan
from flask import Flask, render_template_string

app = create_app()

# Mock the template partially to test rendering
template_stub = """
{{ plan.diet_type }}
{% for week, days in plan.weekly_plan.items() %}
  {{ week }}
  {% for day, meals in days.items() %}
    {{ day }} - {{ meals.breakfast }}
  {% endfor %}
{% endfor %}
{{ plan.cheat_options | tojson }}
{{ plan.weather_advice.season }}
"""

with app.app_context():
    try:
        print("--- STARTING DEBUG ---")
        # Mock patient data
        class MockPatient:
            id = 1
            first_name = "Test"
            last_name = "User"
            age = 30
            weight = 80
            height = 175
            
        class MockHealthData:
            diabetes_risk = 70
            hypertension_risk = 20
            heart_disease_risk = 30
            bmi = 29
            fasting_sugar = 120
            random_sugar = 140
            systolic_bp = 130
            diastolic_bp = 85
            heart_rate = 72
            symptoms = "None"
            exercise_minutes = 30
            sleep_hours = 7
            stress_level = "Low"
            smoking = False
            alcohol = False
            
        p = MockPatient()
        h = MockHealthData()
        
        print("Calling generate_personalized_diet_plan...")
        plan = generate_personalized_diet_plan(p, h)
        print("Plan generated successfully.")
        
        print(f"Plan structure keys: {plan.keys()}")
        print(f"Weekly plan type: {type(plan.get('weekly_plan'))}")
        
        # Test if encoding cheat_options fails
        import json
        print("Testing JSON dumping of cheat_options...")
        json.dumps(plan.get('cheat_options'))
        print("JSON dump success.")

        # Test rendering (basic sanity check)
        # We can't easily use the real render_template without the actual file and environment, 
        # but we can check if keys exist.
        
        required_keys = [
            'diet_type', 'confidence_score', 'departments', 'circadian_schedule',
            'cheat_options', 'sugar_graph_data', 'mood_kit', 'superfood',
            'weekly_plan', 'impact_timeline', 'organ_benefits', 'lab_insights',
            'festival_guide', 'weather_advice', 'recipe_cards' # recipe_cards added?
        ]
        
        for k in required_keys:
            if k not in plan:
                print(f"MISSING KEY: {k}")
            else:
                 # Check nested for weather advice
                if k == 'weather_advice' and not isinstance(plan[k], dict):
                     print(f"weather_advice is not a dict: {plan[k]}")
        
        print("--- DEBUG COMPLETED WITHOUT CRITICAL ERRORS ---")
        
    except Exception:
        print("--- EXCEPTION OCCURRED ---")
        traceback.print_exc()
