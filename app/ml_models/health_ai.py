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
    """AI/ML Models for health risk predictions based on clinical guidelines
    (AHA, WHO, ADA thresholds)"""

    def __init__(self):
        self.diabetes_model = None
        self.heart_disease_model = None
        self.hypertension_model = None
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        if SKLEARN_AVAILABLE:
            self.load_models()

    def load_models(self):
        if not SKLEARN_AVAILABLE:
            return
        self.diabetes_model = self._create_diabetes_model()
        self.heart_disease_model = self._create_heart_disease_model()
        self.hypertension_model = self._create_hypertension_model()

    def _create_diabetes_model(self):
        return RandomForestClassifier(n_estimators=100, random_state=42)

    def _create_heart_disease_model(self):
        return RandomForestClassifier(n_estimators=100, random_state=42)

    def _create_hypertension_model(self):
        return LogisticRegression(random_state=42)

    # ── Comprehensive Health Score (0-100) ──────────────────────────
    # Based on clinical reference ranges from AHA, ADA, WHO
    # Breakdown: BP 25 | Heart Rate 15 | Blood Sugar 20 | Temp 10 | BMI 15 | Lifestyle 15
    def compute_health_score(self, vitals):
        """Compute a 0-100 health score from a dict of patient vitals.

        Expected keys (all optional, missing = not scored):
            systolic_bp, diastolic_bp, heart_rate, fasting_sugar,
            random_sugar, temperature (°F), bmi, smoking (bool),
            alcohol (bool), sleep_hours, stress_level ('Low'/'Medium'/'High'),
            exercise_minutes, oxygen_level
        """
        score = 0.0
        max_possible = 0.0

        # ── 1. Blood Pressure (25 pts) — AHA 2017 guidelines ──
        sys = vitals.get('systolic_bp')
        dia = vitals.get('diastolic_bp')
        if sys is not None and dia is not None and sys > 0 and dia > 0:
            max_possible += 25
            if sys < 120 and dia < 80:
                score += 25                     # Normal
            elif sys < 130 and dia < 80:
                score += 20                     # Elevated
            elif sys < 140 or dia < 90:
                score += 12                     # Stage 1 Hypertension
            elif sys < 180 and dia < 120:
                score += 5                      # Stage 2 Hypertension
            else:
                score += 0                      # Hypertensive crisis

            # Also penalise abnormally LOW BP (hypotension)
            if sys < 90 or dia < 60:
                score = score - 10 if score >= 10 else 0

        # ── 2. Heart Rate (15 pts) — resting adult 60-100 bpm ──
        hr = vitals.get('heart_rate')
        if hr is not None and hr > 0:
            max_possible += 15
            if 60 <= hr <= 100:
                score += 15                     # Normal
            elif 50 <= hr < 60 or 100 < hr <= 110:
                score += 10                     # Mild deviation
            elif 40 <= hr < 50 or 110 < hr <= 130:
                score += 5                      # Moderate deviation
            else:
                score += 0                      # Severe (bradycardia / tachycardia)

        # ── 3. Blood Sugar (20 pts) — ADA guidelines ──
        fasting = vitals.get('fasting_sugar')
        random_s = vitals.get('random_sugar')
        sugar_score = 0
        sugar_max = 0

        if fasting is not None and fasting > 0:
            sugar_max += 10
            if fasting < 100:
                sugar_score += 10               # Normal
            elif fasting < 126:
                sugar_score += 5                # Pre-diabetes
            else:
                sugar_score += 0                # Diabetes range

        if random_s is not None and random_s > 0:
            sugar_max += 10
            if random_s < 140:
                sugar_score += 10               # Normal
            elif random_s < 200:
                sugar_score += 5                # Impaired glucose tolerance
            else:
                sugar_score += 0                # Diabetes range

        # If only one sugar metric was provided, scale to full 20
        if sugar_max > 0:
            score += (sugar_score / sugar_max) * 20
            max_possible += 20

        # ── 4. Body Temperature (10 pts) — normal 97.0-99.5 °F ──
        temp = vitals.get('temperature')
        if temp is not None and temp > 0:
            max_possible += 10
            if 97.0 <= temp <= 99.0:
                score += 10                     # Normal
            elif 96.0 <= temp < 97.0 or 99.0 < temp <= 99.5:
                score += 8                      # Slight deviation
            elif 99.5 < temp <= 100.4:
                score += 5                      # Low-grade fever
            elif 100.4 < temp <= 103.0:
                score += 2                      # Fever
            else:
                score += 0                      # High fever / hypothermia

        # ── 5. BMI (15 pts) — WHO classification ──
        bmi = vitals.get('bmi')
        if bmi is not None and bmi > 0:
            max_possible += 15
            if 18.5 <= bmi < 25:
                score += 15                     # Normal
            elif 25 <= bmi < 27.5 or 17 <= bmi < 18.5:
                score += 10                     # Slightly overweight / underweight
            elif 27.5 <= bmi < 30 or 16 <= bmi < 17:
                score += 6                      # Overweight / underweight
            elif 30 <= bmi < 35:
                score += 3                      # Obese class I
            else:
                score += 0                      # Obese class II+ / severe underweight

        # ── 6. Oxygen Saturation bonus (absorb into heart section) ──
        spo2 = vitals.get('oxygen_level')
        if spo2 is not None and spo2 > 0:
            max_possible += 5
            if spo2 >= 95:
                score += 5
            elif spo2 >= 90:
                score += 2
            # < 90 → 0

        # ── 7. Lifestyle factors (15 pts) ──
        lifestyle_max = 0
        lifestyle_score = 0

        smoking = vitals.get('smoking')
        if smoking is not None:
            lifestyle_max += 3
            if not smoking:
                lifestyle_score += 3

        alcohol = vitals.get('alcohol')
        if alcohol is not None:
            lifestyle_max += 2
            if not alcohol:
                lifestyle_score += 2

        sleep = vitals.get('sleep_hours')
        if sleep is not None and sleep > 0:
            lifestyle_max += 4
            if 7 <= sleep <= 9:
                lifestyle_score += 4            # Optimal (NSF guideline)
            elif 6 <= sleep < 7 or 9 < sleep <= 10:
                lifestyle_score += 2
            else:
                lifestyle_score += 0

        stress = vitals.get('stress_level')
        if stress is not None:
            lifestyle_max += 3
            if stress == 'Low':
                lifestyle_score += 3
            elif stress == 'Medium':
                lifestyle_score += 2
            else:
                lifestyle_score += 0

        exercise = vitals.get('exercise_minutes')
        if exercise is not None:
            lifestyle_max += 3
            if exercise >= 30:
                lifestyle_score += 3            # WHO recommends 150 min/week
            elif exercise >= 15:
                lifestyle_score += 1
            else:
                lifestyle_score += 0

        if lifestyle_max > 0:
            score += (lifestyle_score / lifestyle_max) * 15
            max_possible += 15

        # ── Final score (normalise to 0-100) ──
        if max_possible == 0:
            return 0
        final = (score / max_possible) * 100
        return max(0, min(100, int(round(final))))

    # ── Risk Predictors ─────────────────────────────────────────────

    def predict_diabetes_risk(self, age, bmi, fasting_sugar, random_sugar, family_history=0):
        """Predict diabetes risk (0-100%) — ADA thresholds"""
        try:
            risk = 0

            # Fasting plasma glucose (ADA: normal <100, pre-diabetes 100-125, diabetes ≥126)
            if fasting_sugar >= 126:
                risk += 40
            elif fasting_sugar >= 100:
                risk += 20
            elif fasting_sugar >= 90:
                risk += 5

            # Random glucose (ADA: diabetes ≥200, impaired 140-199)
            if random_sugar >= 200:
                risk += 30
            elif random_sugar >= 140:
                risk += 15
            elif random_sugar >= 120:
                risk += 5

            # BMI (WHO: obese ≥30, overweight 25-29.9)
            if bmi and bmi > 35:
                risk += 20
            elif bmi and bmi > 30:
                risk += 15
            elif bmi and bmi > 25:
                risk += 8

            # Age (risk increases significantly after 45)
            if age and age > 65:
                risk += 15
            elif age and age > 45:
                risk += 10
            elif age and age > 35:
                risk += 5

            if family_history:
                risk += 15

            return min(100, max(0, risk))
        except Exception as e:
            print(f"Error predicting diabetes risk: {e}")
            return 0

    def predict_heart_disease_risk(self, age, systolic_bp, diastolic_bp, heart_rate,
                                   cholesterol=None, smoking=False):
        """Predict heart disease risk (0-100%) — AHA / Framingham factors"""
        try:
            risk = 0

            # Blood Pressure (AHA stages)
            if systolic_bp >= 180 or diastolic_bp >= 120:
                risk += 40                      # Hypertensive crisis
            elif systolic_bp >= 140 or diastolic_bp >= 90:
                risk += 30                      # Stage 2
            elif systolic_bp >= 130 or diastolic_bp >= 80:
                risk += 20                      # Stage 1
            elif systolic_bp >= 120:
                risk += 10                      # Elevated

            # Heart Rate
            if heart_rate > 120:
                risk += 20
            elif heart_rate > 100:
                risk += 15
            elif heart_rate < 50:
                risk += 12
            elif heart_rate < 60:
                risk += 5

            # Age
            if age and age > 65:
                risk += 20
            elif age and age > 55:
                risk += 15
            elif age and age > 45:
                risk += 10

            if smoking:
                risk += 15

            return min(100, max(0, risk))
        except Exception as e:
            print(f"Error predicting heart disease risk: {e}")
            return 0

    def predict_hypertension_risk(self, systolic_bp, diastolic_bp, age, bmi):
        """Predict hypertension risk (0-100%) — AHA 2017 BP categories"""
        try:
            risk = 0

            if systolic_bp >= 180 or diastolic_bp >= 120:
                return 100                      # Crisis
            elif systolic_bp >= 140 or diastolic_bp >= 90:
                risk = 90                       # Already hypertensive
            elif systolic_bp >= 130 or diastolic_bp >= 80:
                risk = 65
            elif systolic_bp >= 120:
                risk = 35

            if bmi and bmi > 35:
                risk += 15
            elif bmi and bmi > 30:
                risk += 10
            elif bmi and bmi > 25:
                risk += 5

            if age and age > 65:
                risk += 12
            elif age and age > 50:
                risk += 8

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
    """Indian diet plan generator based on vitals"""

    def __init__(self):
        self.diet_database = self._initialize_diets()

    def _initialize_diets(self):
        return {
            'diabetic': {
                'breakfast': ['Moong Dal Cheela + Pudina Chutney', 'Ragi Dosa + Coconut Chutney', 'Oats Idli + Sambar'],
                'lunch': ['Brown Rice + Methi Dal + Bhindi Sabzi', 'Bajra Roti + Palak Paneer (low oil)', 'Jowar Roti + Karela Sabzi + Dal'],
                'dinner': ['Moong Dal Khichdi + Kadhi', 'Palak Soup + Grilled Paneer', 'Vegetable Soup + Chapati (1)'],
                'avoid': ['Maida (refined flour)', 'White sugar', 'White rice (excess)', 'Packaged juices'],
                'eat': ['Millets (Ragi, Jowar, Bajra)', 'Methi seeds', 'Karela', 'Curd/Buttermilk'],
                'water': '3-4 liters daily (include Buttermilk, Nimbu Pani)'
            },
            'high_bp': {
                'breakfast': ['Vegetable Poha + Buttermilk', 'Ragi Idli + Coconut Chutney (low salt)', 'Oats Upma + Green Tea'],
                'lunch': ['Curd Rice + Beetroot Poriyal', 'Brown Rice + Lauki Dal + Salad', 'Chapati + Palak Dal + Raita'],
                'dinner': ['Vegetable Stew + Idiyappam', 'Pumpkin Soup + Roti (1)', 'Steamed Fish + Salad'],
                'avoid': ['Excess salt', 'Pickles', 'Papad (salted)', 'Processed/packaged foods'],
                'eat': ['Banana', 'Beetroot', 'Coconut water', 'Leafy greens', 'Garlic'],
                'water': '3 liters daily (include Coconut water)'
            },
            'weight_loss': {
                'breakfast': ['Green Tea + Boiled Eggs (2)', 'Sprouted Moong Chaat', 'Besan Cheela + Buttermilk'],
                'lunch': ['Roti (1) + Palak Paneer (no cream) + Salad', 'Jowar Roti + Mixed Veg + Dal', 'Brown Rice (small) + Rasam + Poriyal'],
                'dinner': ['Moong Dal Soup + Paneer Salad', 'Vegetable Soup + Tandoori Chicken', 'Cauliflower Rice + Buttermilk'],
                'avoid': ['Maida', 'Deep fried items', 'White rice (large)', 'Sweets/Mithai'],
                'eat': ['Sattu', 'Millets', 'High-protein dal', 'Vegetables', 'Green tea'],
                'water': '3-4 liters daily'
            },
            'general_health': {
                'breakfast': ['Idli + Sambar + Coconut Chutney', 'Aloo Paratha + Curd', 'Poha + Buttermilk'],
                'lunch': ['Rice + Sambar + Rasam + Poriyal + Curd', 'Chapati + Dal Fry + Sabzi + Raita', 'Jeera Rice + Rajma + Salad'],
                'dinner': ['Chapati + Dal Tadka + Gobhi Matar', 'Khichdi + Kadhi + Papad', 'Dosa + Sambar + Warm Milk'],
                'avoid': ['Excess processed food', 'Too much oil/ghee', 'Refined flour'],
                'eat': ['All food groups in balance', 'Seasonal fruits', 'Curd daily', 'Dal-Roti-Sabzi'],
                'water': '2-3 liters daily'
            }
        }

    def generate_diet_plan(self, bmi, diabetes_risk, bp_status, heart_risk):
        try:
            diet_type = 'general_health'
            if diabetes_risk > 50: diet_type = 'diabetic'
            elif bp_status > 50: diet_type = 'high_bp'
            elif bmi > 28: diet_type = 'weight_loss'

            plan = self.diet_database.get(diet_type, self.diet_database['general_health'])
            return {
                'diet_type': diet_type,
                'breakfast': plan['breakfast'],
                'lunch': plan['lunch'],
                'dinner': plan['dinner'],
                'snacks': 'Roasted Makhana, Dry Fruits, Buttermilk, Seasonal Fruits',
                'avoid': ', '.join(plan['avoid']),
                'eat': ', '.join(plan['eat']),
                'water_intake': plan['water'],
                'tips': self._get_diet_tips(diet_type)
            }
        except Exception as e:
            print(f"Error generating diet plan: {e}")
            return {}

    def _get_diet_tips(self, diet_type):
        tips = {
            'diabetic': 'Eat at regular intervals. Use millets instead of white rice. Soak methi seeds overnight and drink the water.',
            'high_bp': 'Reduce salt. Use rock salt (sendha namak) sparingly. Eat banana, beetroot & coconut water daily.',
            'weight_loss': 'Eat dinner by 7:30 PM. Replace white rice with millets. Drink buttermilk with lunch.',
            'general_health': 'Eat a balanced Indian thali. Include dal, roti, sabzi, curd and salad in every meal.'
        }
        return tips.get(diet_type, '')


class ExercisePlanGenerator:
    """Exercise + Yoga plan generator based on vitals"""

    def __init__(self):
        self.exercise_database = self._initialize_exercises()

    def _initialize_exercises(self):
        return {
            'high_bp': {
                'exercises': 'Walking, Shavasana, Anulom Vilom, Bhramari Pranayama, Swimming, Tai Chi',
                'yoga': 'Shavasana, Vajrasana, Sukhasana Meditation, Yoga Nidra',
                'duration': 30,
                'frequency': '5 days a week',
                'intensity': 'Low to moderate',
                'precautions': 'Avoid inversions (Sirsasana, Sarvangasana). No heavy weights. Stop if dizzy.'
            },
            'diabetes': {
                'exercises': 'Post-meal Walk (15 min), Cycling, Resistance Bands, Surya Namaskar',
                'yoga': 'Mandukasana (Frog Pose), Vajrasana, Paschimottanasana, Kapalbhati Pranayama',
                'duration': 45,
                'frequency': '5 days a week',
                'intensity': 'Moderate',
                'precautions': 'Never exercise on empty stomach. Carry glucose. Check sugar before & after.'
            },
            'weight_loss': {
                'exercises': 'Brisk Walking, Cycling, Bodyweight Squats, Surya Namaskar, Swimming',
                'yoga': 'Surya Namaskar (5 rounds), Virabhadrasana, Trikonasana, Kapalbhati (3 rounds)',
                'duration': 45,
                'frequency': '5-6 days a week',
                'intensity': 'Moderate to high',
                'precautions': 'Start gradually. Warm up properly. Stay hydrated. Cool down with Shavasana.'
            },
            'heart_disease': {
                'exercises': 'Slow Walking, Ankle Pumps, Gentle Stretching',
                'yoga': 'Shavasana, Anulom Vilom, Bhramari Pranayama, Sukhasana Meditation',
                'duration': 20,
                'frequency': '3-4 days a week',
                'intensity': 'Very light',
                'precautions': 'No sudden exertion. Monitor heart rate. Have phone nearby. No inversions.'
            },
            'general_fitness': {
                'exercises': 'Brisk Walking, Surya Namaskar, Bodyweight Training, Cycling, Swimming',
                'yoga': 'Surya Namaskar, Vrikshasana, Trikonasana, Virabhadrasana, Pranayama, Meditation',
                'duration': 45,
                'frequency': '4-5 days a week',
                'intensity': 'Moderate',
                'precautions': 'Proper warm-up. Correct form. Progressive overload. Rest days.'
            }
        }

    def generate_exercise_plan(self, bmi, diabetes_risk, bp_status, heart_risk, age):
        try:
            exercise_type = 'general_fitness'
            if heart_risk > 50: exercise_type = 'heart_disease'
            elif bp_status > 50: exercise_type = 'high_bp'
            elif diabetes_risk > 50: exercise_type = 'diabetes'
            elif bmi > 28: exercise_type = 'weight_loss'

            plan = self.exercise_database.get(exercise_type, self.exercise_database['general_fitness'])
            return {
                'exercise_type': exercise_type,
                'exercises': plan['exercises'],
                'yoga': plan.get('yoga', ''),
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
        base_tips = {
            'high_bp': 'Do Anulom Vilom daily (5 min). Walk after meals. Avoid holding breath during exercise.',
            'diabetes': 'Walk 15 min after every meal. Do Mandukasana daily. Surya Namaskar boosts metabolism.',
            'weight_loss': 'Surya Namaskar (5-10 rounds daily). Combine with brisk walking. Kapalbhati burns belly fat.',
            'heart_disease': 'Start with Shavasana and deep breathing. Walk slowly. Consult doctor before advancing.',
            'general_fitness': 'Do Surya Namaskar (5 rounds) + 20 min walk daily. Add Pranayama for stress relief.'
        }
        tips = base_tips.get(exercise_type, '')
        if age and age > 50:
            tips += ' Over 50: Warm up thoroughly. Prefer yoga over high-impact. Focus on balance exercises.'
        return tips
