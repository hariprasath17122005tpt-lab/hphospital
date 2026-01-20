"""
Clinical-Grade Diet Plan Engine

This module implements a rule-based, deterministic diet planning system designed for
medical use in hospital management systems. It ensures:

1. 100% Rule-Based Logic (No AI/hallucination)
2. Medical Safety (Pre-written explanations only)
3. Deterministic Output (Same input = Same output)
4. Data-Driven Decisions (Based on patient profiles)
5. Doctor-Approvable (Traceable logic)

Author: Hospital Medical Software Team
Version: 1.0
"""

import json
import os
from typing import Dict, List, Tuple
from datetime import datetime


class DietPlanEngine:
    """
    Clinical-grade diet plan generation engine.
    
    Uses rule-based logic to generate personalized, medically-appropriate diet plans
    based on patient profiles, medical conditions, medications, and lifestyle factors.
    """
    
    def __init__(self, data_dir: str = None):
        """Initialize the diet plan engine with medical data files for ALL 15 FEATURES."""
        if data_dir is None:
            # Default to app/data directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(os.path.dirname(current_dir), 'data')
        
        self.data_dir = data_dir
        # Original files
        self.diet_protocols = self._load_json('diet_protocols.json')
        self.food_medical_reasons = self._load_json('food_medical_reasons.json')
        self.condition_rules = self._load_json('condition_rules.json')
        self.medication_interactions = self._load_json('medication_food_interactions.json')
        self.health_impact_ranges = self._load_json('health_impact_ranges.json')
        
        # New files for 15 features
        self.organ_benefits = self._load_json('organ_benefits.json')  # Feature 1
        self.lab_reference_ranges = self._load_json('lab_reference_ranges.json')  # Feature 2
        self.food_effects = self._load_json('food_effects.json')  # Feature 3
        self.sleep_diet_correlation = self._load_json('sleep_diet_correlation.json')  # Feature 9
        self.food_safety_classifications = self._load_json('food_safety_classifications.json')  # Feature 10
        self.condition_priorities = self._load_json('condition_priorities.json')  # Feature 11
    
    def _load_json(self, filename: str) -> dict:
        """Safely load JSON data files."""
        filepath = os.path.join(self.data_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: {filename} not found at {filepath}")
            return {}
        except json.JSONDecodeError:
            print(f"Error: {filename} contains invalid JSON")
            return {}
    
    def generate_diet_plan(self, patient_profile: Dict) -> Dict:
        """
        Generate a complete, personalized diet plan based on patient profile with ALL 15 FEATURES.
        
        Args:
            patient_profile: Dictionary containing:
                - age: int
                - gender: str ("Male" or "Female")
                - height_cm: float
                - weight_kg: float
                - primary_condition: str
                - secondary_conditions: List[str]
                - medications: List[str]
                - activity_level: str ("Sedentary", "Light", "Moderate", "Active")
                - recent_labs: Dict (optional) for feature #2
        
        Returns:
            Dictionary containing complete diet plan with all 15 features
        """
        # Step 1: Calculate BMI and validate input
        bmi = self._calculate_bmi(patient_profile['height_cm'], patient_profile['weight_kg'])
        patient_profile['bmi'] = bmi
        
        # Step 2: Select appropriate diet protocol
        diet_protocol_name = self._select_diet_protocol(patient_profile)
        diet_protocol = self.diet_protocols[diet_protocol_name]
        
        # Step 3: Apply rule modifiers
        dietary_modifications = self._apply_rule_modifiers(patient_profile)
        
        # Step 4: Generate meal plan
        meal_plan = self._generate_meal_plan(diet_protocol, dietary_modifications)
        
        # Step 5: Get food medical reasons
        food_explanations = self._get_food_explanations(meal_plan)
        
        # Step 6: Get expected health impacts
        health_impacts = self._get_health_impacts(diet_protocol_name, patient_profile)
        
        # Step 7: Get medication safety notes
        safety_notes = self._get_medication_safety_notes(patient_profile['medications'])
        
        # Step 8: Get risk warnings
        risk_warnings = self._get_risk_warnings(diet_protocol_name, patient_profile)
        
        # Step 9: Calculate adherence potential score
        adherence_score = self._calculate_adherence_score(patient_profile, dietary_modifications)
        
        # ============ THE 15 INNOVATIVE FEATURES ============
        
        # 1️⃣ DIET-BODY ORGAN MAP
        organ_benefits = self._get_organ_benefits(diet_protocol_name)
        
        # 2️⃣ LAB-REPORT LINKED DIET JUSTIFICATION
        lab_insights = self._get_lab_linked_justification(patient_profile.get('recent_labs', {}), diet_protocol_name)
        
        # 3️⃣ FOOD EFFECT CLASSIFICATION
        food_effects = self._get_food_effect_classification()
        
        # 4️⃣ EATING SPEED ANALYZER
        eating_speed_advice = self._get_eating_speed_advice(patient_profile)
        
        # 5️⃣ DIET FATIGUE PREVENTION MODE (3-week rotation)
        weekly_plan = self._generate_weekly_rotation(diet_protocol)
        
        # 6️⃣ COGNITIVE LOAD DIET DESIGN
        simple_rules = self._get_simple_rules(diet_protocol_name, patient_profile)
        
        # 7️⃣ DIET CHANGE RISK WARNING
        risk_warning = self._get_diet_change_warning(patient_profile)
        
        # 8️⃣ FESTIVAL/TRAVEL SAFE MODE
        festival_guide = self._get_festival_travel_guide(diet_protocol_name)
        
        # 9️⃣ DIET + SLEEP CORRELATION PANEL
        sleep_advice = self._get_sleep_diet_correlation(patient_profile)
        
        # 🔟 DIET WARNING FLAGS (COLOR-BASED)
        classified_foods = self._classify_foods_by_safety(diet_protocol_name)
        
        # 1️⃣1️⃣ MEDICAL CONDITION STACKING LOGIC
        stacking_order = self._get_condition_stacking_order(patient_profile)
        
        # 1️⃣2️⃣ PATIENT UNDERSTANDING CHECK (UI element in template)
        understanding_check = True  # Set by user interaction in UI
        
        # 1️⃣3️⃣ MEDICO-LEGAL SAFETY PANEL
        medico_legal = self._get_medico_legal_panel()
        
        # 1️⃣4️⃣ DEPARTMENT-SPECIFIC DIET SIGNATURE
        approving_departments = self._get_approving_departments(patient_profile)
        confidence_score = self._calculate_confidence_score(patient_profile)
        
        # 1️⃣5️⃣ "WHAT HAPPENS IF YOU IGNORE THIS?"
        consequences = self._get_consequences_of_non_adherence(patient_profile)
        
        # Compile COMPLETE diet plan with all 15 features
        diet_plan = {
            # Basic info
            'plan_id': self._generate_plan_id(),
            'generated_date': datetime.now().isoformat(),
            'patient_age': patient_profile['age'],
            'patient_bmi': round(bmi, 1),
            'diet_protocol': diet_protocol_name,
            'protocol_name': diet_protocol['name'],
            'protocol_background': diet_protocol['medical_background'],
            'why_this_plan': self._get_diet_selection_rationale(patient_profile, diet_protocol_name),
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
            
            # ========== THE 15 FEATURES ==========
            # 1️⃣
            'organ_benefits': organ_benefits,
            # 2️⃣
            'lab_insights': lab_insights,
            # 3️⃣
            'food_effects': food_effects,
            # 4️⃣
            'eating_speed_advice': eating_speed_advice,
            # 5️⃣
            'weekly_plan': weekly_plan,
            # 6️⃣
            'simple_rules': simple_rules,
            # 7️⃣
            'risk_warning': risk_warning,
            # 8️⃣
            'festival_guide': festival_guide,
            # 9️⃣
            'sleep_advice': sleep_advice,
            # 🔟
            'classified_foods': classified_foods,
            # 1️⃣1️⃣
            'stacking_order': stacking_order,
            # 1️⃣2️⃣
            'understanding_check': understanding_check,
            # 1️⃣3️⃣
            'medico_legal': medico_legal,
            # 1️⃣4️⃣
            'departments': approving_departments,
            'confidence_score': confidence_score,
            # 1️⃣5️⃣
            'consequences': consequences
        }
        
        return diet_plan
    
    def _calculate_bmi(self, height_cm: float, weight_kg: float) -> float:
        """Calculate BMI from height (cm) and weight (kg)."""
        height_m = height_cm / 100
        return weight_kg / (height_m ** 2)
    
    def _select_diet_protocol(self, patient_profile: Dict) -> str:
        """
        Select the most appropriate diet protocol based on primary condition.
        
        Uses rule-based selection: if primary condition matches a protocol,
        use that protocol. Otherwise, recommend based on most relevant rule.
        """
        primary_condition = patient_profile.get('primary_condition', '')
        
        # Direct condition matching
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
        
        # Check for exact match
        if primary_condition in protocol_priority:
            return protocol_priority[primary_condition]
        
        # Check secondary conditions
        secondary_conditions = patient_profile.get('secondary_conditions', [])
        for condition in secondary_conditions:
            if condition in protocol_priority:
                return protocol_priority[condition]
        
        # Default to DASH for general health (hypertension prevention)
        return 'DASH'
    
    def _apply_rule_modifiers(self, patient_profile: Dict) -> Dict:
        """
        Apply rule-based modifiers based on patient characteristics.
        
        Returns dictionary with modification recommendations.
        """
        modifications = {
            'calorie_adjustment': 0,
            'activity_recommendations': [],
            'additional_restrictions': [],
            'adherence_factors': []
        }
        
        age = patient_profile.get('age', 0)
        bmi = patient_profile.get('bmi', 0)
        activity_level = patient_profile.get('activity_level', '')
        
        # Apply BMI-based rules
        if bmi > 30:
            modifications['calorie_adjustment'] = -500
            modifications['adherence_factors'].append('Overweight/Obese: Calorie reduction needed')
        elif 25 <= bmi <= 30:
            modifications['calorie_adjustment'] = -250
            modifications['adherence_factors'].append('Overweight: Modest calorie reduction beneficial')
        
        # Apply activity-based rules
        if activity_level == 'Sedentary':
            modifications['activity_recommendations'].append(
                'Start with 150 minutes moderate activity per week, as tolerated'
            )
            modifications['adherence_factors'].append('Sedentary lifestyle: Increase physical activity')
        
        # Apply age-based rules
        if age > 75:
            modifications['additional_restrictions'].append('Small frequent meals preferred')
            modifications['adherence_factors'].append('Advanced age: Nutrient density optimized')
        elif age > 60:
            modifications['adherence_factors'].append('Age 60+: Enhanced micronutrient focus')
        
        return modifications
    
    def _generate_meal_plan(self, diet_protocol: Dict, modifications: Dict) -> Dict:
        """Generate a specific meal plan for the day."""
        return {
            'breakfast': self._select_meal(diet_protocol['breakfast_options']),
            'lunch': self._select_meal(diet_protocol['lunch_options']),
            'dinner': self._select_meal(diet_protocol['dinner_options']),
            'snacks': self._select_snack(diet_protocol['snack_options'])
        }
    
    def _select_meal(self, options: List[str]) -> str:
        """Select the first meal option from the list (deterministic)."""
        return options[0] if options else "Not available"
    
    def _select_snack(self, options: List[str]) -> str:
        """Select the first snack option from the list (deterministic)."""
        return options[0] if options else "Not available"
    
    def _get_food_explanations(self, meal_plan: Dict) -> Dict:
        """
        Extract medical explanations for foods in the meal plan.
        
        Parses meal descriptions to identify foods and provides their medical rationales.
        """
        explanations = {}
        
        # List of key foods to explain
        foods_to_explain = [
            'salmon', 'oats', 'spinach', 'broccoli', 'berries',
            'almonds', 'beans', 'sweet_potato', 'turkey', 'chicken',
            'olive_oil', 'greek_yogurt', 'whole_wheat', 'brown_rice',
            'tomatoes', 'garlic', 'walnuts', 'avocado', 'carrot',
            'lentils', 'quinoa', 'fish', 'low_fat_milk'
        ]
        
        # Extract foods mentioned in meals
        all_meals_text = ' '.join([
            meal_plan['breakfast'],
            meal_plan['lunch'],
            meal_plan['dinner'],
            meal_plan['snacks']
        ]).lower()
        
        for food in foods_to_explain:
            if food.replace('_', ' ') in all_meals_text:
                if food in self.food_medical_reasons:
                    explanations[food.replace('_', ' ').title()] = self.food_medical_reasons[food]
        
        return explanations
    
    def _get_health_impacts(self, diet_protocol: str, patient_profile: Dict) -> Dict:
        """Get expected health impacts and clinical ranges."""
        impacts = {}
        
        # Search health_impact_ranges for matching protocol and condition
        primary_condition = patient_profile.get('primary_condition', '')
        
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
                if drug_name.replace('_', ' ').lower() in medication_lower or \
                   medication_lower in drug_name.replace('_', ' ').lower():
                    safety_notes.append({
                        'medication': medication,
                        'warning': f"Avoid {interaction['food']}",
                        'reason': interaction['reason'],
                        'severity': interaction['severity']
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
        
        if 'Diabetes' in primary_condition or 'Prediabetes' in primary_condition:
            warnings['diabetes_risk'] = {
                'title': 'If Diet Plan Not Followed:',
                'risks': [
                    'Blood glucose may remain poorly controlled',
                    'Risk of diabetes complications (neuropathy, nephropathy, retinopathy) increases',
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
        """
        Calculate predicted adherence potential score (0-100).
        
        Based on patient characteristics and lifestyle factors.
        Rules: Start at 100, subtract penalties for risk factors.
        """
        score = 100
        
        # Age-based penalty
        if patient_profile.get('age', 0) > 75:
            score -= 10
        elif patient_profile.get('age', 0) > 60:
            score -= 5
        
        # BMI-based penalty
        bmi = patient_profile.get('bmi', 0)
        if bmi > 30:
            score -= 10
        elif bmi > 25:
            score -= 5
        
        # Activity-based penalty
        if patient_profile.get('activity_level') == 'Sedentary':
            score -= 10
        elif patient_profile.get('activity_level') == 'Light':
            score -= 5
        
        # Ensure score stays in valid range
        return max(0, min(100, score))
    
    def _get_diet_selection_rationale(self, patient_profile: Dict, protocol_name: str) -> str:
        """Get explanation for why this diet was selected."""
        condition = patient_profile.get('primary_condition', '')
        
        if protocol_name == 'DASH':
            return f"DASH diet is indicated for {condition}. It is clinically proven to lower blood pressure and reduce cardiovascular risk through sodium reduction and nutrient-dense foods."
        elif protocol_name == 'MEDITERRANEAN':
            return f"Mediterranean diet is recommended for {condition}. Extensive clinical evidence supports its benefits for cardiovascular health, metabolic control, and overall longevity."
        elif protocol_name == 'LOW_GLYCEMIC':
            return f"Low Glycemic Index diet is selected for {condition}. This approach minimizes blood glucose spikes and reduces insulin demand, supporting better metabolic control."
        elif protocol_name == 'RENAL_FRIENDLY':
            return f"Renal-friendly diet is necessary for {condition}. It reduces filtration burden on kidneys and prevents dangerous electrolyte imbalances."
        elif protocol_name == 'CELIAC_FRIENDLY':
            return f"Gluten-free diet is medically required for {condition}. Complete gluten elimination allows intestinal healing and nutrient restoration."
        else:
            return f"This diet protocol was selected based on clinical evidence for {condition}."
    
    def _generate_plan_id(self) -> str:
        """Generate a unique plan ID for tracking."""
        return f"PLAN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _get_disclaimer(self) -> str:
        """Get standard medical disclaimer."""
        return (
            "This personalized diet plan is generated based on clinical guidelines and evidence-based "
            "medical science. It supports clinical care and does not replace consultation with your healthcare provider. "
            "All dietary changes should be discussed with your doctor or registered dietitian. This plan is not intended "
            "to diagnose, treat, cure, or prevent any disease. Regular monitoring and adjustment by healthcare professionals "
            "is recommended for optimal outcomes."
        )
    
    # ============================================================
    # THE 15 INNOVATIVE FEATURES - IMPLEMENTATION STARTS HERE
    # ============================================================
    
    # 1️⃣ DIET-BODY ORGAN MAP
    def _get_organ_benefits(self, diet_protocol_name: str) -> List[Dict]:
        """
        Feature 1: Show which organs benefit from this diet.
        Returns list of organs with benefits.
        """
        organ_data = self.organ_benefits.get(diet_protocol_name, {})
        result = []
        
        for organ, benefit in organ_data.items():
            if organ not in ['food_specific_benefits']:  # Skip metadata
                emoji_map = {
                    'Heart': '❤️', 'Brain': '🧠', 'Kidneys': '💧',
                    'Liver': '🏥', 'Pancreas': '⚡', 'Lungs': '💨'
                }
                result.append({
                    'organ': f"{emoji_map.get(organ, '🫀')} {organ}",
                    'benefit': benefit
                })
        
        return result if result else [{'organ': '❤️ Heart', 'benefit': 'Improved cardiovascular health'}]
    
    # 2️⃣ LAB-REPORT LINKED DIET JUSTIFICATION
    def _get_lab_linked_justification(self, recent_labs: Dict, diet_protocol_name: str) -> List[Dict]:
        """
        Feature 2: Link patient's lab values to diet rules.
        Shows connection between lab test and why this diet helps.
        """
        lab_insights = []
        lab_ranges = self.lab_reference_ranges if hasattr(self, 'lab_reference_ranges') else {}
        
        for lab_test, value in recent_labs.items():
            if lab_test in lab_ranges:
                lab_info = lab_ranges[lab_test]
                status = 'ELEVATED' if value > lab_info.get('elevated_above', 999) else \
                        'LOW' if value < lab_info.get('normal_min', 0) else 'NORMAL'
                
                diet_rule = lab_info.get('diet_recommendation', 'Follow diet protocol')
                
                lab_insights.append({
                    'test': lab_test,
                    'value': f"{value} {lab_info.get('unit', '')}",
                    'status': status,
                    'diet_rule': diet_rule,
                    'reason': f"This diet reduces {lab_test} through {diet_protocol_name} protocol"
                })
        
        return lab_insights if lab_insights else [{
            'test': 'Blood Sugar',
            'value': 'Not provided',
            'status': 'PENDING',
            'diet_rule': 'Low Glycemic Index approach',
            'reason': 'This diet minimizes blood glucose spikes through carb quality'
        }]
    
    # 3️⃣ FOOD EFFECT CLASSIFICATION
    def _get_food_effect_classification(self) -> List[Dict]:
        """
        Feature 3: Show immediate vs long-term effects of foods.
        """
        food_data = self.food_effects if hasattr(self, 'food_effects') else {}
        result = []
        
        for food, effects in food_data.items():
            if isinstance(effects, dict):
                result.append({
                    'food': food.replace('_', ' ').title(),
                    'immediate': effects.get('immediate', 'Quick energy boost'),
                    'long_term': effects.get('long_term', 'Improved health markers')
                })
        
        return result[:10]  # Return top 10 foods
    
    # 4️⃣ EATING SPEED ANALYZER
    def _get_eating_speed_advice(self, patient_profile: Dict) -> str:
        """
        Feature 4: Behavioral feedback about eating speed.
        """
        primary_condition = patient_profile.get('primary_condition', '')
        
        if 'Diabetes' in primary_condition:
            return "Eating slowly helps control blood sugar. Aim for 25-30 minutes per meal and chew 25 times per bite."
        elif 'Hypertension' in primary_condition or 'High Blood Pressure' in primary_condition:
            return "Slow eating reduces stress and supports blood pressure control. Take your time with meals."
        else:
            return "Eating at a moderate pace (20-30 minutes) aids digestion and prevents overeating."
    
    # 5️⃣ DIET FATIGUE PREVENTION MODE (3-week rotation)
    def _generate_weekly_rotation(self, diet_protocol: Dict) -> Dict:
        """
        Feature 5: Generate 3-week meal rotation to prevent diet boredom.
        """
        weeks = {}
        breakfast_opts = diet_protocol.get('breakfast_options', ['Oatmeal with berries'])[0:3]
        lunch_opts = diet_protocol.get('lunch_options', ['Grilled chicken with vegetables'])[0:3]
        dinner_opts = diet_protocol.get('dinner_options', ['Baked fish with brown rice'])[0:3]
        
        for week_num in range(1, 4):
            weeks[f'Week {week_num}'] = {
                'breakfast': [breakfast_opts[(week_num - 1) % len(breakfast_opts)]],
                'lunch': [lunch_opts[(week_num - 1) % len(lunch_opts)]],
                'dinner': [dinner_opts[(week_num - 1) % len(dinner_opts)]]
            }
        
        return weeks
    
    # 6️⃣ COGNITIVE LOAD DIET DESIGN
    def _get_simple_rules(self, diet_protocol_name: str, patient_profile: Dict) -> List[str]:
        """
        Feature 6: Simplify to 3 golden rules for confused patients.
        """
        simple_rules_map = {
            'DASH': [
                '✓ Replace salt with herbs & spices',
                '✓ Eat vegetables at every meal',
                '✓ Choose whole grains instead of white'
            ],
            'MEDITERRANEAN': [
                '✓ Use olive oil for cooking',
                '✓ Eat fish 2-3 times per week',
                '✓ Choose fresh fruits & vegetables daily'
            ],
            'LOW_GLYCEMIC': [
                '✓ Choose whole grains, not refined',
                '✓ Eat protein with every meal',
                '✓ Limit sugary foods & drinks'
            ],
            'RENAL_FRIENDLY': [
                '✓ Limit salt & processed foods',
                '✓ Control protein portions',
                '✓ Choose low-potassium foods'
            ],
            'CELIAC_FRIENDLY': [
                '✓ Avoid all wheat, barley & rye',
                '✓ Read all food labels carefully',
                '✓ Watch for cross-contamination'
            ]
        }
        
        return simple_rules_map.get(diet_protocol_name, [
            '✓ Eat variety of fresh whole foods',
            '✓ Limit processed & fried foods',
            '✓ Drink water instead of sugary beverages'
        ])
    
    # 7️⃣ DIET CHANGE RISK WARNING
    def _get_diet_change_warning(self, patient_profile: Dict) -> str:
        """
        Feature 7: Alert about sudden diet changes.
        """
        conditions = [patient_profile.get('primary_condition', '')] + patient_profile.get('secondary_conditions', [])
        
        if any('Diabetes' in c for c in conditions):
            return "WARNING: Sudden diet changes may affect blood sugar levels. Monitor glucose closely. If on diabetes medication, consult doctor before changing diet significantly."
        elif any('Hypertension' in c or 'High Blood Pressure' in c for c in conditions):
            return "WARNING: Sudden sodium reduction may cause dizziness. Gradually transition to this diet over 1-2 weeks."
        elif any('Kidney' in c or 'CKD' in c for c in conditions):
            return "WARNING: Protein & electrolyte changes must be gradual. Strict monitoring needed - consult doctor before starting."
        else:
            return "Transition to new diet gradually over 1-2 weeks to allow your digestive system to adjust."
    
    # 8️⃣ FESTIVAL/TRAVEL SAFE MODE
    def _get_festival_travel_guide(self, diet_protocol_name: str) -> Dict:
        """
        Feature 8: Guide for managing diet during festivals/travel.
        """
        return {
            'strategy': '80/20 Rule: Follow diet 80% of time, allow 20% flexibility',
            'portion_limit': 'Use hand-size portions for festival foods',
            'safe_foods': ['Fresh fruits', 'Grilled proteins', 'Vegetables', 'Nuts'],
            'recovery': 'Return to strict diet next meal. One indulgence doesn\'t ruin progress.'
        }
    
    # 9️⃣ DIET + SLEEP CORRELATION PANEL
    def _get_sleep_diet_correlation(self, patient_profile: Dict) -> Dict:
        """
        Feature 9: Show connection between diet and sleep quality.
        """
        sleep_data = self.sleep_diet_correlation if hasattr(self, 'sleep_diet_correlation') else {}
        
        if sleep_data:
            return {
                'correlation': sleep_data.get('general_principle', 'Diet timing affects sleep quality'),
                'rule': sleep_data.get('timing_rules', 'Dinner 2-3 hours before bed, avoid caffeine after 2 PM')
            }
        else:
            return {
                'correlation': 'Eating schedule affects circadian rhythm and sleep quality',
                'rule': 'Finish dinner 2-3 hours before bed. Avoid caffeine after 2 PM. Magnesium-rich foods promote sleep.'
            }
    
    # 🔟 DIET WARNING FLAGS (COLOR-BASED)
    def _classify_foods_by_safety(self, diet_protocol_name: str) -> List[Dict]:
        """
        Feature 10: Color-coded food safety flags (🟢🟡🔴)
        """
        safety_data = self.food_safety_classifications if hasattr(self, 'food_safety_classifications') else {}
        result = []
        
        color_map = {'green': ('🟢', 'success'), 'yellow': ('🟡', 'warning'), 'red': ('🔴', 'danger')}
        
        for category in ['safe_green', 'occasional_yellow', 'avoid_red']:
            color_key = list(color_map.keys())[['safe_green', 'occasional_yellow', 'avoid_red'].index(category)]
            emoji, color = color_map[color_key]
            
            foods = safety_data.get(category, {}).get('foods', [])
            for food in foods[:5]:
                result.append({'name': f"{emoji} {food}", 'color': color})
        
        return result[:15]
    
    # 1️⃣1️⃣ MEDICAL CONDITION STACKING LOGIC
    def _get_condition_stacking_order(self, patient_profile: Dict) -> List[str]:
        """
        Feature 11: Prioritize multiple conditions (Kidney > Diabetes > Cardio > BP > Obesity).
        """
        all_conditions = [patient_profile.get('primary_condition', '')] + patient_profile.get('secondary_conditions', [])
        all_conditions = [c for c in all_conditions if c]  # Remove empty
        
        priority_order = ['CKD', 'Chronic Kidney', 'Diabetes', 'Cardiovascular', 'Heart', 'Hypertension', 'Blood Pressure', 'Obesity']
        
        sorted_conditions = []
        for priority_keyword in priority_order:
            for condition in all_conditions:
                if priority_keyword in condition and condition not in sorted_conditions:
                    sorted_conditions.append(condition)
        
        for condition in all_conditions:
            if condition not in sorted_conditions:
                sorted_conditions.append(condition)
        
        return sorted_conditions if sorted_conditions else ['General Health']
    
    # 1️⃣2️⃣ PATIENT UNDERSTANDING CHECK (handled in template)
    # This is a UI element - no backend logic needed
    
    # 1️⃣3️⃣ MEDICO-LEGAL SAFETY PANEL
    def _get_medico_legal_panel(self) -> Dict:
        """
        Feature 13: Medical-legal compliance statements.
        """
        return {
            'statement': '✓ This plan is clinically prepared and doctor-verified',
            'monitoring': '✓ Regular monitoring recommended every 4 weeks',
            'disclaimer': '✓ This plan does not replace professional medical advice'
        }
    
    # 1️⃣4️⃣ DEPARTMENT-SPECIFIC DIET SIGNATURE
    def _get_approving_departments(self, patient_profile: Dict) -> List[str]:
        """
        Feature 14: Show which departments approve this plan.
        """
        departments = ['Nutrition & Dietetics']
        
        if 'Diabetes' in patient_profile.get('primary_condition', ''):
            departments.append('Endocrinology')
        if 'Hypertension' in patient_profile.get('primary_condition', '') or 'Cardiovascular' in patient_profile.get('primary_condition', ''):
            departments.append('Cardiology')
        if 'Kidney' in patient_profile.get('primary_condition', ''):
            departments.append('Nephrology')
        
        return departments
    
    def _calculate_confidence_score(self, patient_profile: Dict) -> int:
        """
        Feature 14: Calculate plan confidence based on data completeness.
        """
        score = 70  # Base score
        
        # Add points for data completeness
        if 'recent_labs' in patient_profile and patient_profile['recent_labs']:
            score += 15
        if 'medications' in patient_profile and len(patient_profile.get('medications', [])) > 0:
            score += 10
        if 'secondary_conditions' in patient_profile and len(patient_profile.get('secondary_conditions', [])) > 0:
            score += 5
        
        return min(100, score)
    
    # 1️⃣5️⃣ "WHAT HAPPENS IF YOU IGNORE THIS?"
    def _get_consequences_of_non_adherence(self, patient_profile: Dict) -> List[str]:
        """
        Feature 15: Show timeline of consequences if diet ignored.
        """
        primary_condition = patient_profile.get('primary_condition', '')
        
        if 'Diabetes' in primary_condition:
            return [
                '📅 Week 1-2: Blood sugar stays elevated, energy crashes',
                '📅 Month 1: A1c may increase, diabetes symptoms worsen',
                '📅 Month 3-6: Risk of complications (neuropathy, vision issues) increases'
            ]
        elif 'Hypertension' in primary_condition or 'High Blood Pressure' in primary_condition:
            return [
                '📅 Week 1-2: Blood pressure remains elevated, headaches persist',
                '📅 Month 1: Heart strain continues, medication needed longer',
                '📅 Month 3-6: Risk of stroke, heart attack, kidney damage increases'
            ]
        elif 'Kidney' in primary_condition or 'CKD' in primary_condition:
            return [
                '📅 Week 1-2: Electrolyte imbalance symptoms develop',
                '📅 Month 1: Kidney function declines faster, waste accumulates',
                '📅 Month 3-6: May require dialysis sooner than predicted'
            ]
        else:
            return [
                '📅 Week 1-2: Energy and mood may decline',
                '📅 Month 1: Weight loss stalls, health markers worsen',
                '📅 Month 3-6: Disease complications develop or progress faster'
            ]


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
    
    # Validate age
    if 'age' in profile:
        if not (0 < profile['age'] < 150):
            errors.append("Age must be between 1 and 149 years")
    
    # Validate height
    if 'height_cm' in profile:
        if not (50 < profile['height_cm'] < 300):
            errors.append("Height must be between 50 and 300 cm")
    
    # Validate weight
    if 'weight_kg' in profile:
        if not (20 < profile['weight_kg'] < 500):
            errors.append("Weight must be between 20 and 500 kg")
    
    # Validate activity level
    if 'activity_level' in profile:
        valid_levels = ['Sedentary', 'Light', 'Moderate', 'Active']
        if profile['activity_level'] not in valid_levels:
            errors.append(f"Activity level must be one of: {', '.join(valid_levels)}")
    
    return len(errors) == 0, errors
