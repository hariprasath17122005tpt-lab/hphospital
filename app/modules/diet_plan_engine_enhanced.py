"""
Enhanced Clinical-Grade Diet Plan Engine with 15 Innovative Features

This module implements a rule-based, deterministic diet planning system with:
1. Diet-Body Organ Map
2. Lab-Report Linked Diet Justification
3. Food Effect Classification (Immediate vs Long-Term)
4. Eating Speed Analyzer
5. Diet Fatigue Prevention Mode (3-week rotation)
6. Cognitive Load Diet Design (Simple vs Detailed)
7. Diet Change Risk Warning
8. Festival/Travel Safe Mode
9. Diet + Sleep Correlation Panel
10. Diet Warning Flags (Color-Based)
11. Medical Condition Stacking Logic
12. Patient Understanding Check
13. Medico-Legal Safety Panel
14. Department-Specific Diet Signature
15. What Happens If You Ignore This? (Consequences)

Author: Hospital Medical Software Team
Version: 2.0 (Enhanced with 15 innovative features)
"""

import json
import os
from typing import Dict, List, Tuple
from datetime import datetime


class EnhancedDietPlanEngine:
    """
    Enhanced clinical-grade diet plan generation engine with 15 innovative features.
    
    Uses rule-based logic to generate personalized, medically-appropriate diet plans
    based on patient profiles, medical conditions, medications, and lifestyle factors.
    """
    
    def __init__(self, data_dir: str = None):
        """Initialize the diet plan engine with medical data files."""
        if data_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(os.path.dirname(current_dir), 'data')
        
        self.data_dir = data_dir
        self.diet_protocols = self._load_json('diet_protocols.json')
        self.food_medical_reasons = self._load_json('food_medical_reasons.json')
        self.condition_rules = self._load_json('condition_rules.json')
        self.medication_interactions = self._load_json('medication_food_interactions.json')
        self.health_impact_ranges = self._load_json('health_impact_ranges.json')
        
        # Load enhanced data files for 15 features
        self.organ_benefits_data = self._load_json('organ_benefits.json')
        self.food_effects_data = self._load_json('food_effects.json')
        self.lab_ranges_data = self._load_json('lab_reference_ranges.json')
        self.sleep_correlation_data = self._load_json('sleep_diet_correlation.json')
        self.food_classifications = self._load_json('food_safety_classifications.json')
        self.condition_priorities = self._load_json('condition_priorities.json')
    
    def _load_json(self, filename: str) -> dict:
        """Safely load JSON data files."""
        filepath = os.path.join(self.data_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def generate_diet_plan(self, patient_profile: Dict) -> Dict:
        """
        Generate a complete, personalized diet plan with all 15 innovative features.
        
        Args:
            patient_profile: Dictionary containing patient information
        
        Returns:
            Dictionary containing comprehensive diet plan
        """
        # Validation
        is_valid, errors = validate_patient_profile(patient_profile)
        if not is_valid:
            raise ValueError(f"Invalid patient profile: {', '.join(errors)}")
        
        # Core calculations
        bmi = self._calculate_bmi(patient_profile['height_cm'], patient_profile['weight_kg'])
        patient_profile['bmi'] = bmi
        
        diet_protocol_name = self._select_diet_protocol(patient_profile)
        diet_protocol = self.diet_protocols.get(diet_protocol_name, {})
        
        dietary_modifications = self._apply_rule_modifiers(patient_profile)
        meal_plan = self._generate_meal_plan(diet_protocol, dietary_modifications)
        food_explanations = self._get_food_explanations(meal_plan)
        health_impacts = self._get_health_impacts(diet_protocol_name, patient_profile)
        safety_notes = self._get_medication_safety_notes(patient_profile.get('medications', []))
        risk_warnings = self._get_risk_warnings(diet_protocol_name, patient_profile)
        adherence_score = self._calculate_adherence_score(patient_profile, dietary_modifications)
        
        # ===== 15 INNOVATIVE FEATURES =====
        
        # 1️⃣ DIET-BODY ORGAN MAP
        organ_benefits = self._get_organ_benefits(patient_profile, diet_protocol_name)
        
        # 2️⃣ LAB-REPORT LINKED DIET JUSTIFICATION
        lab_insights = self._get_lab_linked_justification(
            patient_profile.get('recent_labs', {}),
            patient_profile,
            diet_protocol_name
        )
        
        # 3️⃣ FOOD EFFECT CLASSIFICATION
        food_effects = self._get_food_effect_classification(diet_protocol_name, meal_plan)
        
        # 4️⃣ EATING SPEED ANALYZER
        eating_speed_advice = self._get_eating_speed_advice(
            patient_profile.get('eating_speed', 'Moderate'),
            patient_profile
        )
        
        # 5️⃣ DIET FATIGUE PREVENTION MODE (3-Week Rotation)
        weekly_plan = self._generate_weekly_rotation(diet_protocol, meal_plan)
        
        # 6️⃣ COGNITIVE LOAD DIET DESIGN
        simple_rules = self._get_simple_rules(patient_profile, diet_protocol_name)
        
        # 7️⃣ DIET CHANGE RISK WARNING
        risk_warning = self._get_diet_change_warning(patient_profile)
        
        # 8️⃣ FESTIVAL/TRAVEL SAFE MODE
        festival_guide = self._get_festival_travel_guide(diet_protocol_name, meal_plan)
        
        # 9️⃣ DIET + SLEEP CORRELATION PANEL
        sleep_advice = self._get_sleep_diet_correlation(diet_protocol_name)
        
        # 🔟 DIET WARNING FLAGS (Color-Based)
        classified_foods = self._classify_foods_by_safety(diet_protocol, patient_profile)
        
        # 1️⃣1️⃣ MEDICAL CONDITION STACKING LOGIC
        stacking_order = self._get_condition_stacking_order(patient_profile)
        
        # 1️⃣2️⃣ PATIENT UNDERSTANDING CHECK
        understanding_prompt = "Did you understand this clinically prepared diet?"
        
        # 1️⃣3️⃣ MEDICO-LEGAL SAFETY PANEL
        medico_legal = self._get_medico_legal_panel()
        
        # 1️⃣4️⃣ DEPARTMENT-SPECIFIC DIET SIGNATURE
        departments = self._get_approving_departments(patient_profile)
        confidence_score = self._calculate_confidence_score(patient_profile, diet_protocol_name)
        
        # 1️⃣5️⃣ WHAT HAPPENS IF YOU IGNORE THIS?
        consequences = self._get_consequences_of_non_adherence(patient_profile, diet_protocol_name)
        
        # Compile complete diet plan
        return {
            # Basic Information
            'plan_id': self._generate_plan_id(),
            'generated_date': datetime.now().isoformat(),
            'patient_age': patient_profile['age'],
            'patient_gender': patient_profile.get('gender', 'Not specified'),
            'patient_bmi': round(bmi, 1),
            'diet_protocol': diet_protocol_name,
            'protocol_name': diet_protocol.get('name', diet_protocol_name),
            'protocol_background': diet_protocol.get('medical_background', ''),
            'why_this_plan': self._get_diet_selection_rationale(patient_profile, diet_protocol_name),
            
            # Clinical Content
            'daily_meal_plan': meal_plan,
            'meal_guidelines': diet_protocol.get('daily_servings', {}),
            'food_explanations': food_explanations,
            'health_benefits': health_impacts,
            'medication_safety_notes': safety_notes,
            'risk_warnings': risk_warnings,
            'foods_to_avoid': diet_protocol.get('foods_to_avoid', []),
            'adherence_score': adherence_score,
            'adherence_factors': dietary_modifications.get('adherence_factors', []),
            'disclaimer': self._get_disclaimer(),
            
            # ===== 15 INNOVATIVE FEATURES =====
            '1_organ_benefits': organ_benefits,
            '2_lab_insights': lab_insights,
            '3_food_effects': food_effects,
            '4_eating_speed_advice': eating_speed_advice,
            '5_weekly_plan': weekly_plan,
            '6_simple_rules': simple_rules,
            '7_risk_warning': risk_warning,
            '8_festival_guide': festival_guide,
            '9_sleep_advice': sleep_advice,
            '10_classified_foods': classified_foods,
            '11_stacking_order': stacking_order,
            '12_understanding_prompt': understanding_prompt,
            '13_medico_legal': medico_legal,
            '14_departments': departments,
            '14_confidence_score': confidence_score,
            '15_consequences': consequences
        }
    
    # ===== BASIC CALCULATIONS =====
    
    def _calculate_bmi(self, height_cm: float, weight_kg: float) -> float:
        """Calculate BMI from height (cm) and weight (kg)."""
        height_m = height_cm / 100
        return weight_kg / (height_m ** 2)
    
    def _select_diet_protocol(self, patient_profile: Dict) -> str:
        """Select the most appropriate diet protocol based on primary condition."""
        primary_condition = patient_profile.get('primary_condition', '')
        
        protocol_priority = {
            'Hypertension': 'DASH',
            'High Blood Pressure': 'DASH',
            'Cardiovascular Disease': 'MEDITERRANEAN',
            'Heart Disease': 'MEDITERRANEAN',
            'Diabetes Type 2': 'LOW_GLYCEMIC',
            'Prediabetes': 'LOW_GLYCEMIC',
            'High Cholesterol': 'MEDITERRANEAN',
            'Hyperlipidemia': 'MEDITERRANEAN',
            'Chronic Kidney Disease': 'RENAL_FRIENDLY',
            'CKD': 'RENAL_FRIENDLY',
            'Celiac Disease': 'CELIAC_FRIENDLY',
            'Gluten Sensitivity': 'CELIAC_FRIENDLY'
        }
        
        if primary_condition in protocol_priority:
            return protocol_priority[primary_condition]
        
        for condition in patient_profile.get('secondary_conditions', []):
            if condition in protocol_priority:
                return protocol_priority[condition]
        
        return 'DASH'
    
    def _apply_rule_modifiers(self, patient_profile: Dict) -> Dict:
        """Apply rule-based modifiers based on patient characteristics."""
        modifications = {
            'calorie_adjustment': 0,
            'activity_recommendations': [],
            'additional_restrictions': [],
            'adherence_factors': []
        }
        
        age = patient_profile.get('age', 0)
        bmi = patient_profile.get('bmi', 0)
        activity_level = patient_profile.get('activity_level', '')
        
        if bmi > 30:
            modifications['calorie_adjustment'] = -500
            modifications['adherence_factors'].append('Overweight/Obese (BMI 25-30): modest calorie reduction beneficial')
        elif 25 <= bmi <= 30:
            modifications['calorie_adjustment'] = -250
            modifications['adherence_factors'].append('Overweight: Modest calorie reduction beneficial')
        
        if activity_level == 'Sedentary':
            modifications['activity_recommendations'].append('Start with 150 minutes moderate activity per week')
            modifications['adherence_factors'].append('Sedentary lifestyle: Increase physical activity')
        
        if age > 75:
            modifications['additional_restrictions'].append('Small frequent meals preferred')
            modifications['adherence_factors'].append('Advanced age: Nutrient density optimized')
        elif age > 60:
            modifications['adherence_factors'].append('Age 60+: Enhanced micronutrient focus')
        
        return modifications
    
    def _generate_meal_plan(self, diet_protocol: Dict, modifications: Dict) -> Dict:
        """Generate a specific meal plan for the day."""
        return {
            'breakfast': self._select_meal(diet_protocol.get('breakfast_options', [])),
            'lunch': self._select_meal(diet_protocol.get('lunch_options', [])),
            'dinner': self._select_meal(diet_protocol.get('dinner_options', [])),
            'snacks': self._select_snack(diet_protocol.get('snack_options', []))
        }
    
    def _select_meal(self, options: List[str]) -> str:
        """Select the first meal option from the list (deterministic)."""
        return options[0] if options else "Not available"
    
    def _select_snack(self, options: List[str]) -> str:
        """Select the first snack option from the list (deterministic)."""
        return options[0] if options else "Not available"
    
    def _get_food_explanations(self, meal_plan: Dict) -> Dict:
        """Extract medical explanations for foods in the meal plan."""
        explanations = {}
        
        foods_to_explain = [
            'salmon', 'oats', 'spinach', 'broccoli', 'berries', 'almonds',
            'beans', 'sweet potato', 'turkey', 'chicken', 'olive oil',
            'greek yogurt', 'whole wheat', 'brown rice', 'tomatoes', 'garlic',
            'walnuts', 'avocado', 'carrot', 'lentils', 'quinoa', 'fish',
            'low fat milk', 'herring', 'mackerel', 'sardines'
        ]
        
        all_meals_text = ' '.join([
            meal_plan.get('breakfast', ''),
            meal_plan.get('lunch', ''),
            meal_plan.get('dinner', ''),
            meal_plan.get('snacks', '')
        ]).lower()
        
        for food in foods_to_explain:
            if food in all_meals_text:
                if food in self.food_medical_reasons:
                    explanations[food.replace('_', ' ').title()] = self.food_medical_reasons[food]
        
        return explanations
    
    def _get_health_impacts(self, diet_protocol: str, patient_profile: Dict) -> Dict:
        """Get expected health impacts and clinical ranges."""
        impacts = {}
        
        for impact_key, impact_data in self.health_impact_ranges.items():
            if diet_protocol.lower() in impact_key.lower():
                impacts = impact_data.get('expected_outcomes', {})
                break
        
        return impacts if impacts else {
            'general_benefit': 'Improved metabolic markers and health status expected',
            'timeline': 'Benefits typically observed within 2-4 weeks of consistent adherence'
        }
    
    def _get_medication_safety_notes(self, medications: List[str]) -> List[Dict]:
        """Get drug-food interaction warnings for patient's medications."""
        safety_notes = []
        
        for medication in medications:
            medication_lower = medication.lower()
            for drug_name, interaction in self.medication_interactions.items():
                if drug_name.replace('_', ' ').lower() in medication_lower:
                    safety_notes.append({
                        'medication': medication,
                        'warning': f"Avoid {interaction.get('food', 'certain foods')}",
                        'reason': interaction.get('reason', ''),
                        'severity': interaction.get('severity', 'MODERATE')
                    })
        
        return safety_notes
    
    def _get_risk_warnings(self, diet_protocol: str, patient_profile: Dict) -> Dict:
        """Get risk information for non-adherence."""
        bmi = patient_profile.get('bmi', 0)
        primary_condition = patient_profile.get('primary_condition', '')
        
        warnings = {}
        
        if 'Hypertension' in primary_condition or 'High Blood Pressure' in primary_condition:
            warnings['hypertension_risk'] = {
                'title': 'If Diet Plan Not Followed:',
                'risks': [
                    'Blood pressure may remain elevated, increasing stroke and heart attack risk',
                    'Continued sodium intake raises hypertensive complications',
                    'Medication effectiveness may be reduced'
                ]
            }
        
        if 'Diabetes' in primary_condition:
            warnings['diabetes_risk'] = {
                'title': 'If Diet Plan Not Followed:',
                'risks': [
                    'Blood glucose may remain poorly controlled',
                    'Risk of complications (neuropathy, nephropathy, retinopathy) increases',
                    'Weight gain may accelerate disease progression'
                ]
            }
        
        if bmi > 30:
            warnings['obesity_risk'] = {
                'title': 'If Weight Loss Plan Not Followed:',
                'risks': [
                    'Obesity-related complications may worsen',
                    'Cardiovascular and metabolic risks remain elevated',
                    'Future health outcomes may deteriorate'
                ]
            }
        
        return warnings
    
    def _calculate_adherence_score(self, patient_profile: Dict, modifications: Dict) -> int:
        """Calculate predicted adherence potential score (0-100)."""
        score = 100
        
        if patient_profile.get('age', 0) > 75:
            score -= 10
        elif patient_profile.get('age', 0) > 60:
            score -= 5
        
        bmi = patient_profile.get('bmi', 0)
        if bmi > 30:
            score -= 10
        elif bmi > 25:
            score -= 5
        
        if patient_profile.get('activity_level') == 'Sedentary':
            score -= 10
        elif patient_profile.get('activity_level') == 'Light':
            score -= 5
        
        return max(0, min(100, score))
    
    # ===== 15 INNOVATIVE FEATURES =====
    
    # 1️⃣ DIET-BODY ORGAN MAP
    def _get_organ_benefits(self, patient_profile: Dict, diet_protocol: str) -> List[Dict]:
        """Map diet benefits to specific body organs."""
        organ_mapping = {
            'DASH': [
                {'organ': '❤️ Heart', 'benefit': 'Reduced sodium → Lower BP & better cardiovascular function'},
                {'organ': '🧠 Brain', 'benefit': 'Potassium-rich foods → Improved cognitive function & stroke prevention'},
                {'organ': '🩸 Kidneys', 'benefit': 'Controlled sodium → Reduced filtration burden'},
                {'organ': '🦠 Gut', 'benefit': 'High fiber → Better digestion & microbiome health'}
            ],
            'MEDITERRANEAN': [
                {'organ': '❤️ Heart', 'benefit': 'Omega-3 rich → Reduced inflammation & better cholesterol'},
                {'organ': '🧠 Brain', 'benefit': 'Olive oil & nuts → Enhanced memory & neuroprotection'},
                {'organ': '🫀 Arteries', 'benefit': 'Antioxidants → Reduced arterial plaque formation'},
                {'organ': '🦠 Gut', 'benefit': 'Polyphenols → Improved bacterial diversity'}
            ],
            'LOW_GLYCEMIC': [
                {'organ': '🧬 Pancreas', 'benefit': 'Low GI foods → Reduced insulin demand & beta-cell protection'},
                {'organ': '❤️ Heart', 'benefit': 'Better glucose control → Reduced cardiovascular risk'},
                {'organ': '🧠 Brain', 'benefit': 'Stable blood sugar → Better focus & mood regulation'},
                {'organ': '🫀 Vessels', 'benefit': 'Reduced inflammation → Better endothelial function'}
            ]
        }
        
        return organ_mapping.get(diet_protocol, organ_mapping['DASH'])
    
    # 2️⃣ LAB-REPORT LINKED DIET JUSTIFICATION
    def _get_lab_linked_justification(self, recent_labs: Dict, patient_profile: Dict, diet_protocol: str) -> List[Dict]:
        """Link diet recommendations to specific lab values."""
        insights = []
        
        # Standard lab interpretations
        lab_to_diet = {
            'BP': {
                'high': 'Low sodium diet recommended - DASH protocol addresses this',
                'value_key': 'Blood Pressure',
                'target': '< 130/80 mmHg'
            },
            'HbA1c': {
                'high': 'Low GI diet recommended - Controls blood glucose spikes',
                'value_key': 'HbA1c',
                'target': '< 7%'
            },
            'Cholesterol': {
                'high': 'Mediterranean diet rich in unsaturated fats recommended',
                'value_key': 'Total Cholesterol',
                'target': '< 200 mg/dL'
            },
            'Sodium': {
                'high': 'Sodium restriction essential - Limit to < 2300mg daily',
                'value_key': 'Serum Sodium',
                'target': '135-145 mEq/L'
            },
            'Potassium': {
                'low': 'Increase potassium-rich foods - Important for cardiac health',
                'value_key': 'Serum Potassium',
                'target': '3.5-5.0 mEq/L'
            },
            'GFR': {
                'low': 'Renal-friendly diet with protein restriction recommended',
                'value_key': 'GFR (Glomerular Filtration Rate)',
                'target': '> 60 mL/min/1.73m2'
            }
        }
        
        # Create insights for labs provided
        for lab, values in recent_labs.items():
            if lab in lab_to_diet:
                insights.append({
                    'test': lab_to_diet[lab].get('value_key', lab),
                    'value': str(values),
                    'status': 'Abnormal' if isinstance(values, (int, float)) else 'Review Needed',
                    'diet_rule': f"Restrict foods increasing {lab}",
                    'reason': lab_to_diet[lab].get('high', lab_to_diet[lab].get('low', 'Monitor closely'))
                })
        
        return insights if insights else [
            {
                'test': 'Blood Pressure',
                'value': 'Pending lab work',
                'status': 'Recommended',
                'diet_rule': 'Low sodium diet protocol',
                'reason': 'Baseline measurement needed for diet optimization'
            }
        ]
    
    # 3️⃣ FOOD EFFECT CLASSIFICATION
    def _get_food_effect_classification(self, diet_protocol: str, meal_plan: Dict) -> List[Dict]:
        """Classify foods by immediate vs long-term effects."""
        food_effects_data = {
            'Spinach': {
                'immediate': 'Reduced bloating & improved digestion',
                'long_term': 'BP control through nitrate absorption'
            },
            'Salmon': {
                'immediate': 'Satiety & mood elevation from omega-3s',
                'long_term': 'Reduced arterial inflammation & plaque formation'
            },
            'Oats': {
                'immediate': 'Stable energy & reduced hunger spikes',
                'long_term': 'Reduced LDL cholesterol by 3-5%'
            },
            'Broccoli': {
                'immediate': 'Improved digestion & detoxification',
                'long_term': 'Cancer prevention & antioxidant buildup'
            },
            'Berries': {
                'immediate': 'Antioxidant burst & improved cognition',
                'long_term': 'Neurodegeneration prevention & brain aging reversal'
            },
            'Almonds': {
                'immediate': 'Stable blood glucose & sustained energy',
                'long_term': 'Cardiovascular risk reduction & weight management'
            },
            'Whole Wheat': {
                'immediate': 'Better satiety & improved digestion',
                'long_term': 'Reduced diabetes risk & gut health improvement'
            }
        }
        
        return [
            {
                'food': 'Spinach/Greens',
                'immediate': food_effects_data['Spinach']['immediate'],
                'long_term': food_effects_data['Spinach']['long_term']
            },
            {
                'food': 'Fatty Fish',
                'immediate': food_effects_data['Salmon']['immediate'],
                'long_term': food_effects_data['Salmon']['long_term']
            },
            {
                'food': 'Whole Grains',
                'immediate': food_effects_data['Oats']['immediate'],
                'long_term': food_effects_data['Oats']['long_term']
            },
            {
                'food': 'Cruciferous Vegetables',
                'immediate': food_effects_data['Broccoli']['immediate'],
                'long_term': food_effects_data['Broccoli']['long_term']
            }
        ]
    
    # 4️⃣ EATING SPEED ANALYZER
    def _get_eating_speed_advice(self, eating_speed: str, patient_profile: Dict) -> str:
        """Provide personalized advice based on eating speed."""
        advice_map = {
            'Slow': 'Excellent! Slow eating aids digestion and nutrient absorption. Your BPwill remain stable.',
            'Moderate': 'Good pace! Continue eating mindfully. Aim to finish meals in 20-25 minutes.',
            'Fast': 'WARNING: Fast eating spikes insulin & BP! Recommendation: Chew 25-30 times per bite, use smaller utensils, put fork down between bites.'
        }
        
        return advice_map.get(eating_speed, advice_map['Moderate'])
    
    # 5️⃣ DIET FATIGUE PREVENTION MODE (3-Week Rotation)
    def _generate_weekly_rotation(self, diet_protocol: Dict, meal_plan: Dict) -> Dict:
        """Generate 3-week rotation to prevent diet fatigue."""
        # Week rotation with different meal variations
        return {
            'Week 1 (Sodium Detox)': {
                'breakfast': 'Oatmeal with berries & almonds',
                'lunch': 'Grilled salmon with steamed broccoli',
                'dinner': 'Lean turkey with sweet potato & greens'
            },
            'Week 2 (Balance)': {
                'breakfast': 'Whole wheat toast with avocado & egg whites',
                'lunch': 'Mediterranean quinoa salad with chickpeas',
                'dinner': 'Baked white fish with roasted vegetables'
            },
            'Week 3 (Sustain)': {
                'breakfast': 'Greek yogurt parfait with walnuts & berries',
                'lunch': 'Vegetable soup with lean chicken breast',
                'dinner': 'Brown rice & beans with roasted root vegetables'
            }
        }
    
    # 6️⃣ COGNITIVE LOAD DIET DESIGN
    def _get_simple_rules(self, patient_profile: Dict, diet_protocol: str) -> List[str]:
        """Simplify diet to 3 golden rules for easy memorization."""
        simple_rules_map = {
            'DASH': [
                '1. No added salt - Cook at home, read labels carefully',
                '2. Eat colorful vegetables daily - At least 4-5 servings',
                '3. Choose lean proteins - Fish, chicken breast, legumes'
            ],
            'MEDITERRANEAN': [
                '1. Use olive oil for cooking & dressing - Primary fat source',
                '2. Eat fish 2-3 times weekly - Sardines, salmon, mackerel',
                '3. Loads of vegetables, nuts, whole grains - Every meal'
            ],
            'LOW_GLYCEMIC': [
                '1. No sugary foods or refined carbs - Read nutrition labels',
                '2. Pair carbs with protein & fiber - Every meal',
                '3. Choose whole grains only - Brown rice, oats, quinoa'
            ]
        }
        
        return simple_rules_map.get(diet_protocol, simple_rules_map['DASH'])
    
    # 7️⃣ DIET CHANGE RISK WARNING
    def _get_diet_change_warning(self, patient_profile: Dict) -> str:
        """Warn about risks of sudden diet changes."""
        warnings = {
            'Hypertension': 'Sudden diet changes may cause electrolyte imbalance → weakness, dizziness',
            'Diabetes': 'Rapid carb reduction may cause hypoglycemia → dizziness, confusion',
            'CKD': 'Sudden protein changes may stress kidneys → worsen kidney function'
        }
        
        condition = patient_profile.get('primary_condition', '')
        return warnings.get(condition,
            'Sudden diet changes may cause temporary weakness & fatigue. Transition gradually over 5-7 days.'
        )
    
    # 8️⃣ FESTIVAL/TRAVEL SAFE MODE
    def _get_festival_travel_guide(self, diet_protocol: str, meal_plan: Dict) -> Dict:
        """Provide damage control strategy for festivals/travel."""
        return {
            'strategy': '80% adherence rule - Follow diet 80% of time, allow 20% flexibility',
            'portion_limit': 'Limit cheat meals to 1-2 per week, keep portions to ½ usual size',
            'safe_foods': ['Grilled protein', 'Salads with oil & vinegar', 'Fresh fruits', 'Nuts', 'Water', 'Tea'],
            'recovery': 'After festival meal, return to strict diet immediately - No "all-in" mentality'
        }
    
    # 9️⃣ DIET + SLEEP CORRELATION PANEL
    def _get_sleep_diet_correlation(self, diet_protocol: str) -> Dict:
        """Explain diet-sleep correlation."""
        return {
            'correlation': 'Late heavy meals → Poor sleep → Higher BP & glucose spikes in morning',
            'rule': 'Finish dinner by 8:00 PM - Light meals after 7 PM only',
            'timing': {
                'breakfast': '7:00 AM',
                'lunch': '12:30 PM',
                'dinner': '7:00 PM'
            },
            'sleep_benefit': '7-8 hours sleep improves diet adherence by 40%'
        }
    
    # 🔟 DIET WARNING FLAGS (Color-Based)
    def _classify_foods_by_safety(self, diet_protocol: Dict, patient_profile: Dict) -> List[Dict]:
        """Classify foods by safety level with color coding."""
        return [
            {'name': 'Leafy Greens', 'color': 'success'},  # 🟢 Safe
            {'name': 'Whole Grains', 'color': 'success'},  # 🟢 Safe
            {'name': 'Lean Protein', 'color': 'success'},  # 🟢 Safe
            {'name': 'Low-Fat Dairy', 'color': 'success'}, # 🟢 Safe
            {'name': 'Nuts & Seeds', 'color': 'success'},  # 🟢 Safe
            {'name': 'Red Meat', 'color': 'warning'},      # 🟡 Occasional
            {'name': 'Processed Foods', 'color': 'warning'}, # 🟡 Occasional
            {'name': 'Fried Foods', 'color': 'danger'},    # 🔴 Avoid
            {'name': 'High-Sodium Foods', 'color': 'danger'}, # 🔴 Avoid
            {'name': 'Sugary Drinks', 'color': 'danger'}   # 🔴 Avoid
        ]
    
    # 1️⃣1️⃣ MEDICAL CONDITION STACKING LOGIC
    def _get_condition_stacking_order(self, patient_profile: Dict) -> List[str]:
        """Priority order for managing multiple conditions."""
        conditions = [patient_profile.get('primary_condition', '')] + patient_profile.get('secondary_conditions', [])
        
        # Priority: Kidney > Diabetes > Hypertension > Obesity
        priority_order = {
            'Chronic Kidney Disease': 1,
            'CKD': 1,
            'Diabetes Type 2': 2,
            'Prediabetes': 3,
            'Hypertension': 4,
            'High Blood Pressure': 4,
            'Obesity': 5,
            'Heart Disease': 2,
            'Cardiovascular Disease': 2
        }
        
        sorted_conditions = sorted(
            conditions,
            key=lambda x: priority_order.get(x, 99)
        )
        
        return [c for c in sorted_conditions if c]
    
    # 1️⃣2️⃣ PATIENT UNDERSTANDING CHECK
    def _get_understanding_prompt(self) -> str:
        """Interactive understanding check."""
        return "Did you understand this clinically prepared diet?"
    
    # 1️⃣3️⃣ MEDICO-LEGAL SAFETY PANEL
    def _get_medico_legal_panel(self) -> Dict:
        """Medical-legal compliance panel."""
        return {
            'statement': '✔ This diet supports clinical care and does not replace professional medical consultation',
            'monitoring': '✔ Requires regular monitoring by healthcare professionals',
            'disclaimer': 'Consult your doctor before making significant dietary changes. This plan is not intended to diagnose, treat, cure, or prevent any disease.'
        }
    
    # 1️⃣4️⃣ DEPARTMENT-SPECIFIC DIET SIGNATURE
    def _get_approving_departments(self, patient_profile: Dict) -> List[str]:
        """Get list of approving departments."""
        condition = patient_profile.get('primary_condition', '')
        
        departments_map = {
            'Hypertension': ['Cardiology', 'Internal Medicine', 'Nutrition'],
            'Diabetes Type 2': ['Endocrinology', 'Internal Medicine', 'Nutrition'],
            'Heart Disease': ['Cardiology', 'Nutrition', 'Internal Medicine'],
            'Chronic Kidney Disease': ['Nephrology', 'Internal Medicine', 'Nutrition'],
            'Celiac Disease': ['Gastroenterology', 'Nutrition', 'Internal Medicine']
        }
        
        return departments_map.get(condition, ['Internal Medicine', 'Nutrition', 'Clinical Care'])
    
    def _calculate_confidence_score(self, patient_profile: Dict, diet_protocol: str) -> int:
        """Calculate confidence score for diet plan (0-100)."""
        score = 85  # Base score
        
        # Adjust based on data completeness
        if patient_profile.get('recent_labs'):
            score += 5
        if patient_profile.get('medications'):
            score += 5
        if patient_profile.get('activity_level'):
            score += 3
        
        return min(100, score)
    
    # 1️⃣5️⃣ WHAT HAPPENS IF YOU IGNORE THIS?
    def _get_consequences_of_non_adherence(self, patient_profile: Dict, diet_protocol: str) -> List[str]:
        """Realistic consequences of diet non-adherence."""
        condition = patient_profile.get('primary_condition', '')
        
        consequences_map = {
            'Hypertension': [
                'Week 1-2: BP remains elevated',
                'Month 1-3: Increased stroke & heart attack risk',
                'Year 1+: End-organ damage (kidneys, heart, brain)'
            ],
            'Diabetes Type 2': [
                'Week 1-2: Blood sugar becomes uncontrolled',
                'Month 1-3: Increased neuropathy & vision problems',
                'Year 1+: Kidney disease, amputation risk increases'
            ],
            'Heart Disease': [
                'Week 1-2: Cholesterol levels worsen',
                'Month 1-3: Arterial plaque accumulation accelerates',
                'Year 1+: Sudden heart attack & death risk increases'
            ],
            'Chronic Kidney Disease': [
                'Week 1-2: Electrolyte imbalance develops',
                'Month 1-3: Kidney function declines faster',
                'Year 1+: Dialysis need may occur sooner'
            ]
        }
        
        return consequences_map.get(condition, [
            'Health status deteriorates gradually',
            'Medical complications increase in frequency',
            'Long-term life expectancy may decrease significantly'
        ])
    
    # ===== UTILITY METHODS =====
    
    def _get_diet_selection_rationale(self, patient_profile: Dict, protocol_name: str) -> str:
        """Get explanation for why this diet was selected."""
        condition = patient_profile.get('primary_condition', '')
        
        rationale_map = {
            'DASH': f'DASH diet is indicated for {condition}. It is clinically proven to lower blood pressure and reduce cardiovascular risk through sodium reduction and nutrient-dense foods.',
            'MEDITERRANEAN': f'Mediterranean diet is recommended for {condition}. Extensive clinical evidence supports its benefits for cardiovascular health, metabolic control, and overall longevity.',
            'LOW_GLYCEMIC': f'Low Glycemic Index diet is selected for {condition}. This approach minimizes blood glucose spikes and reduces insulin demand.',
            'RENAL_FRIENDLY': f'Renal-friendly diet is necessary for {condition}. It reduces filtration burden on kidneys and prevents dangerous electrolyte imbalances.',
            'CELIAC_FRIENDLY': f'Gluten-free diet is medically required for {condition}. Complete gluten elimination allows intestinal healing.'
        }
        
        return rationale_map.get(protocol_name, f'This diet protocol was selected based on clinical evidence for {condition}.')
    
    def _generate_plan_id(self) -> str:
        """Generate a unique plan ID for tracking."""
        return f"PLAN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _get_disclaimer(self) -> str:
        """Get standard medical disclaimer."""
        return (
            'This personalized diet plan is generated based on clinical guidelines and evidence-based '
            'medical science. It supports clinical care and does not replace consultation with your healthcare provider. '
            'All dietary changes should be discussed with your doctor or registered dietitian. This plan is not intended '
            'to diagnose, treat, cure, or prevent any disease. Regular monitoring and adjustment by healthcare professionals '
            'is recommended for optimal outcomes.'
        )


def validate_patient_profile(profile: Dict) -> Tuple[bool, List[str]]:
    """
    Validate patient profile data before generating diet plan.
    
    Returns: (is_valid, error_messages)
    """
    errors = []
    
    required_fields = ['age', 'gender', 'height_cm', 'weight_kg', 'primary_condition', 'activity_level']
    for field in required_fields:
        if field not in profile:
            errors.append(f"Missing required field: {field}")
    
    if 'age' in profile:
        if not (0 < profile['age'] < 150):
            errors.append("Age must be between 1 and 149 years")
    
    if 'height_cm' in profile:
        if not (50 < profile['height_cm'] < 300):
            errors.append("Height must be between 50 and 300 cm")
    
    if 'weight_kg' in profile:
        if not (20 < profile['weight_kg'] < 500):
            errors.append("Weight must be between 20 and 500 kg")
    
    if 'activity_level' in profile:
        valid_levels = ['Sedentary', 'Light', 'Moderate', 'Active']
        if profile['activity_level'] not in valid_levels:
            errors.append(f"Activity level must be one of: {', '.join(valid_levels)}")
    
    return len(errors) == 0, errors
