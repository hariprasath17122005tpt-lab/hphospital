import numpy as np
import warnings
warnings.filterwarnings('ignore')

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    SKLEARN_AVAILABLE = False
    
import pickle
import os

class HealthRiskPredictor:
    """AI/ML Models for health risk predictions"""
    
    def __init__(self):
        self.diabetes_model = None
        self.heart_disease_model = None
        self.hypertension_model = None
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        if SKLEARN_AVAILABLE:
            self.load_models()
    
    def load_models(self):
        """Load pre-trained models or train new ones"""
        if not SKLEARN_AVAILABLE:
            return
        # For now, we'll create simple models
        # In production, these would be trained on real data
        self.diabetes_model = self._create_diabetes_model()
        self.heart_disease_model = self._create_heart_disease_model()
        self.hypertension_model = self._create_hypertension_model()
    
    def _create_diabetes_model(self):
        """Create a simple diabetes risk model"""
        # Placeholder - in real scenario, this would be trained
        return RandomForestClassifier(n_estimators=100, random_state=42)
    
    def _create_heart_disease_model(self):
        """Create heart disease risk model"""
        return RandomForestClassifier(n_estimators=100, random_state=42)
    
    def _create_hypertension_model(self):
        """Create hypertension risk model"""
        return LogisticRegression(random_state=42)
    
    def predict_diabetes_risk(self, age, bmi, fasting_sugar, random_sugar, family_history=0):
        """
        Predict diabetes risk (0-100%)
        Returns float between 0 and 100
        """
        try:
            # Simple rule-based system for now
            risk = 0
            
            # Sugar levels
            if fasting_sugar > 125:
                risk += 40
            elif fasting_sugar > 100:
                risk += 20
            
            if random_sugar > 200:
                risk += 30
            elif random_sugar > 140:
                risk += 15
            
            # BMI
            if bmi > 30:
                risk += 15
            elif bmi > 25:
                risk += 8
            
            # Age
            if age > 45:
                risk += 10
            
            # Family history
            if family_history:
                risk += 15
            
            # Normalize to 0-100
            return min(100, max(0, risk))
        except Exception as e:
            print(f"Error predicting diabetes risk: {e}")
            return 0
    
    def predict_heart_disease_risk(self, age, systolic_bp, diastolic_bp, heart_rate, 
                                   cholesterol=None, smoking=False):
        """
        Predict heart disease risk (0-100%)
        """
        try:
            risk = 0
            
            # Blood Pressure
            if systolic_bp > 140:
                risk += 35
            elif systolic_bp > 130:
                risk += 20
            
            if diastolic_bp > 90:
                risk += 20
            elif diastolic_bp > 80:
                risk += 10
            
            # Heart Rate
            if heart_rate > 100:
                risk += 15
            elif heart_rate < 60:
                risk += 10
            
            # Age
            if age > 55:
                risk += 20
            elif age > 45:
                risk += 10
            
            # Smoking
            if smoking:
                risk += 15
            
            return min(100, max(0, risk))
        except Exception as e:
            print(f"Error predicting heart disease risk: {e}")
            return 0
    
    def predict_hypertension_risk(self, systolic_bp, diastolic_bp, age, bmi):
        """
        Predict hypertension risk (0-100%)
        """
        try:
            risk = 0
            
            # Current BP levels
            if systolic_bp >= 140 or diastolic_bp >= 90:
                return 100  # Already hypertensive
            elif systolic_bp >= 130 or diastolic_bp >= 80:
                risk = 70
            elif systolic_bp >= 120 or diastolic_bp >= 80:
                risk = 40
            
            # BMI contribution
            if bmi > 30:
                risk += 15
            elif bmi > 25:
                risk += 8
            
            # Age contribution
            if age > 60:
                risk += 10
            
            return min(100, max(0, risk))
        except Exception as e:
            print(f"Error predicting hypertension risk: {e}")
            return 0
    
    def calculate_bmi(self, weight_kg, height_cm):
        """Calculate BMI and category"""
        try:
            height_m = height_cm / 100
            bmi = weight_kg / (height_m ** 2)
            
            if bmi < 18.5:
                category = "Underweight"
            elif bmi < 25:
                category = "Normal"
            elif bmi < 30:
                category = "Overweight"
            else:
                category = "Obese"
            
            return round(bmi, 2), category
        except Exception as e:
            print(f"Error calculating BMI: {e}")
            return 0, "Unknown"



class DietPlanGenerator:
    """AI-based diet plan generator"""
    
    def __init__(self):
        self.diet_database = self._initialize_diets()
    
    def _initialize_diets(self):
        """Initialize diet recommendations database"""
        return {
            'diabetic': {
                'breakfast': ['Oatmeal with berries', 'Whole grain toast with eggs', 'Greek yogurt with nuts'],
                'lunch': ['Grilled chicken with vegetables', 'Fish with brown rice', 'Lentil soup with salad'],
                'dinner': ['Steamed vegetables with tofu', 'Baked fish with sweet potato', 'Chicken stir-fry with brown rice'],
                'avoid': ['White bread', 'Sugary drinks', 'Refined carbs', 'Sweets'],
                'eat': ['Whole grains', 'Lean proteins', 'Fresh vegetables', 'Low-GI fruits'],
                'water': '3-4 liters daily'
            },
            'high_bp': {
                'breakfast': ['Oatmeal with banana', 'Whole wheat toast with avocado', 'Smoothie with spinach'],
                'lunch': ['Grilled fish with vegetables', 'Chicken salad with olive oil', 'Vegetable stew'],
                'dinner': ['Steamed vegetables with lean meat', 'Baked salmon', 'Chickpea curry'],
                'avoid': ['Salt', 'Processed foods', 'Canned foods', 'Fast food'],
                'eat': ['Potassium-rich foods', 'Garlic', 'Leafy greens', 'Berries'],
                'water': '2-3 liters daily'
            },
            'weight_loss': {
                'breakfast': ['Egg white omelet', 'Oatmeal with berries', 'Green smoothie'],
                'lunch': ['Grilled chicken breast with vegetables', 'Fish with salad', 'Vegetable soup'],
                'dinner': ['Steamed vegetables with tofu', 'Baked fish', 'Chicken breast with rice'],
                'avoid': ['Fried foods', 'Sugary drinks', 'Desserts', 'High-fat dairy'],
                'eat': ['Vegetables', 'Lean proteins', 'Whole grains', 'Fruits'],
                'water': '3-4 liters daily'
            },
            'general_health': {
                'breakfast': ['Balanced meal with protein', 'Whole grains', 'Fresh fruit'],
                'lunch': ['Mixed protein with vegetables', 'Whole grain carbs', 'Healthy fats'],
                'dinner': ['Lean protein', 'Vegetables', 'Whole grains'],
                'avoid': ['Excessive sugar', 'Too much salt', 'Processed foods'],
                'eat': ['All food groups in moderation', 'Variety of colors', 'Natural foods'],
                'water': '2-3 liters daily'
            }
        }
    
    def generate_diet_plan(self, bmi, diabetes_risk, bp_status, heart_risk):
        """Generate personalized diet plan based on health parameters"""
        try:
            diet_type = 'general_health'
            
            if diabetes_risk > 60:
                diet_type = 'diabetic'
            elif bp_status > 70:
                diet_type = 'high_bp'
            elif bmi > 28:
                diet_type = 'weight_loss'
            
            plan = self.diet_database.get(diet_type, self.diet_database['general_health'])
            
            return {
                'diet_type': diet_type,
                'breakfast': plan['breakfast'],
                'lunch': plan['lunch'],
                'dinner': plan['dinner'],
                'snacks': 'Nuts, fruits, yogurt, seeds',
                'avoid': ', '.join(plan['avoid']),
                'eat': ', '.join(plan['eat']),
                'water_intake': plan['water'],
                'tips': self._get_diet_tips(diet_type)
            }
        except Exception as e:
            print(f"Error generating diet plan: {e}")
            return {}
    
    def _get_diet_tips(self, diet_type):
        """Get diet tips based on type"""
        tips = {
            'diabetic': 'Eat at regular intervals, monitor portion sizes, check blood sugar regularly',
            'high_bp': 'Reduce sodium, increase potassium, manage stress, limit caffeine',
            'weight_loss': 'Create calorie deficit, increase physical activity, eat slowly, track intake',
            'general_health': 'Eat balanced meals, stay hydrated, exercise regularly, sleep well'
        }
        return tips.get(diet_type, '')


class ExercisePlanGenerator:
    """AI-based exercise plan generator"""
    
    def __init__(self):
        self.exercise_database = self._initialize_exercises()
    
    def _initialize_exercises(self):
        """Initialize exercise recommendations database"""
        return {
            'high_bp': {
                'exercises': 'Walking, swimming, cycling, yoga, stretching',
                'duration': 30,
                'frequency': '5 days a week',
                'intensity': 'Low to moderate',
                'precautions': 'Avoid sudden movements, stay hydrated, stop if dizzy'
            },
            'diabetes': {
                'exercises': 'Aerobic (brisk walking, jogging), strength training, flexibility exercises',
                'duration': 45,
                'frequency': '5 days a week',
                'intensity': 'Moderate',
                'precautions': 'Check blood sugar before exercise, carry glucose, wear proper shoes'
            },
            'weight_loss': {
                'exercises': 'Cardio, HIIT, strength training, walking, cycling',
                'duration': 60,
                'frequency': '5-6 days a week',
                'intensity': 'Moderate to high',
                'precautions': 'Start gradually, stay hydrated, warm up properly, cool down'
            },
            'heart_disease': {
                'exercises': 'Light walking, gentle yoga, tai chi, swimming',
                'duration': 20,
                'frequency': '3-4 days a week',
                'intensity': 'Very light',
                'precautions': 'Avoid sudden exertion, monitor heart rate, take prescribed medications'
            },
            'general_fitness': {
                'exercises': 'Mix of cardio, strength training, flexibility',
                'duration': 45,
                'frequency': '4-5 days a week',
                'intensity': 'Moderate',
                'precautions': 'Proper warm-up, proper form, gradual progression'
            }
        }
    
    def generate_exercise_plan(self, bmi, diabetes_risk, bp_status, heart_risk, age):
        """Generate personalized exercise plan based on health parameters"""
        try:
            exercise_type = 'general_fitness'
            
            if heart_risk > 70:
                exercise_type = 'heart_disease'
            elif bp_status > 70:
                exercise_type = 'high_bp'
            elif diabetes_risk > 60:
                exercise_type = 'diabetes'
            elif bmi > 28:
                exercise_type = 'weight_loss'
            
            plan = self.exercise_database.get(exercise_type, self.exercise_database['general_fitness'])
            
            return {
                'exercise_type': exercise_type,
                'exercises': plan['exercises'],
                'duration_minutes': plan['duration'],
                'frequency': plan['frequency'],
                'intensity': plan['intensity'],
                'precautions': plan['precautions'],
                'tips': self._get_exercise_tips(exercise_type, age)
            }
        except Exception as e:
            print(f"Error generating exercise plan: {e}")
            return {}
    
    def _get_exercise_tips(self, exercise_type, age):
        """Get exercise tips based on type and age"""
        base_tips = {
            'high_bp': 'Start slowly, gradually increase duration, monitor during exercise',
            'diabetes': 'Exercise 30 mins after meals, monitor blood sugar, keep glucose handy',
            'weight_loss': 'Combine cardio and strength training, track calories, stay consistent',
            'heart_disease': 'Always consult doctor first, wear ID, have phone nearby',
            'general_fitness': 'Balance all types of exercise, progressive overload, rest days'
        }
        tips = base_tips.get(exercise_type, '')
        
        if age > 50:
            tips += '. Special consideration: Warm up thoroughly, avoid sudden movements'
        
        return tips
