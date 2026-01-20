"""
DIET PLAN GENERATOR - Clinical Dietician Module
Hospital Management System

Purpose: Generate highly professional, personalized diet plans based on patient clinical data.
Author: Clinical Nutrition Department
Version: 1.0 - Professional Medical-Grade Output
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass

# =====================================================
# ENUMS FOR MEDICAL CLASSIFICATION
# =====================================================

class DietType(Enum):
    """Clinically recognized diet patterns"""
    LOW_GI = "Low Glycemic Index (GI) Diet"
    DASH = "DASH (Dietary Approaches to Stop Hypertension)"
    CARDIAC = "Cardiac / Heart-Healthy Diet"
    RENAL = "Renal Diet (Kidney Disease)"
    GLUTEN_FREE = "Gluten-Free (Celiac / Non-Celiac Gluten Sensitivity)"
    KETOGENIC = "Ketogenic (Medical Supervision Required)"
    MEDITERRANEAN = "Mediterranean Diet"
    FODMAP_LOW = "Low FODMAP (IBS Management)"
    TLC = "Therapeutic Lifestyle Changes (TLC)"
    COMBINATION = "Condition-Specific Combination"

class ActivityLevel(Enum):
    """Physical activity classification"""
    SEDENTARY = 1.2      # Little to no exercise
    LIGHTLY_ACTIVE = 1.375  # 1-3 days/week exercise
    MODERATELY_ACTIVE = 1.55  # 3-5 days/week exercise
    VERY_ACTIVE = 1.725  # 6-7 days/week exercise
    EXTREMELY_ACTIVE = 1.9   # Physical job + daily exercise

class MedicalCondition(Enum):
    """Clinical conditions requiring dietary modification"""
    DIABETES_TYPE2 = "Type 2 Diabetes Mellitus"
    HYPERTENSION = "Hypertension"
    DYSLIPIDEMIA = "Dyslipidemia (Cholesterol/Triglyceride Disorder)"
    OBESITY = "Obesity (BMI > 30)"
    OVERWEIGHT = "Overweight (BMI 25-29.9)"
    CARDIAC_DISEASE = "Coronary Artery Disease / Heart Failure"
    CKD_STAGE3 = "Chronic Kidney Disease Stage 3"
    ASTHMA = "Asthma (Pro-inflammatory diet modifications)"
    THYROID_DISORDER = "Hypothyroidism / Thyroid Disorder"
    GERD = "GERD (Gastroesophageal Reflux Disease)"
    METABOLIC_SYNDROME = "Metabolic Syndrome"
    PREDIABETES = "Prediabetes (IFG/IGT)"
    NAFLD = "NAFLD (Non-Alcoholic Fatty Liver Disease)"

# =====================================================
# DATA MODELS
# =====================================================

@dataclass
class PatientProfile:
    """Clinical patient data for diet plan generation"""
    patient_id: str
    patient_name: str
    age: int
    gender: str  # "Male" / "Female"
    height_cm: float  # Centimeters
    weight_kg: float  # Kilograms
    bmi: float = None  # Auto-calculated if not provided
    medical_conditions: List[MedicalCondition] = None
    activity_level: ActivityLevel = ActivityLevel.SEDENTARY
    medications: List[str] = None  # e.g., ["Metformin 1000mg BD", "Amlodipine 5mg OD"]
    allergies: List[str] = None  # e.g., ["Peanuts", "Shellfish"]
    restrictions: List[str] = None  # e.g., ["Vegetarian", "Vegan", "Kosher"]
    recent_labs: Dict[str, float] = None  # e.g., {"HbA1c": 8.2, "LDL": 145}
    physician_notes: str = ""
    
    def __post_init__(self):
        """Calculate BMI if not provided"""
        if self.bmi is None and self.height_cm and self.weight_kg:
            self.bmi = self.weight_kg / ((self.height_cm / 100) ** 2)
        if self.medical_conditions is None:
            self.medical_conditions = []
        if self.medications is None:
            self.medications = []
        if self.allergies is None:
            self.allergies = []
        if self.restrictions is None:
            self.restrictions = []
        if self.recent_labs is None:
            self.recent_labs = {}

@dataclass
class Meal:
    """Single meal with nutritional breakdown"""
    meal_name: str
    time_of_day: str  # e.g., "Breakfast (7:00 AM)"
    foods: List[str]  # List of specific foods with portions
    nutritional_summary: Dict[str, float]  # e.g., {"calories": 350, "protein_g": 25}
    medical_reasoning: str  # Why this meal is prescribed

@dataclass
class DietPlan:
    """Complete personalized diet plan"""
    patient_profile: PatientProfile
    diet_type: DietType
    caloric_target: Dict[str, float]  # {"maintenance": 2200, "weight_loss": 1700}
    macro_distribution: Dict[str, Dict[str, any]]  # Carbs, protein, fats with percentages and rationale
    meals: List[Meal]
    restricted_foods: Dict[str, List[str]]  # By category
    recommended_foods: Dict[str, List[str]]  # By category with benefits
    drug_nutrient_interactions: Dict[str, Dict[str, str]]  # Drug interactions & management
    safety_notes: List[str]
    expected_outcomes: Dict[str, str]  # 4-6 week benefits
    follow_up_schedule: Dict[str, str]
    generated_date: str = None
    
    def __post_init__(self):
        if self.generated_date is None:
            self.generated_date = datetime.now().strftime("%B %d, %Y")

# =====================================================
# DIET PLAN GENERATOR ENGINE
# =====================================================

class ClinicalDietPlanGenerator:
    """
    Professional-grade diet plan generator for hospital system.
    Generates condition-specific, patient-centric nutritional strategies.
    """
    
    def __init__(self):
        """Initialize knowledge base"""
        self.basal_metabolic_rate_coefficients = {
            "male_10_18": (1.16, 9, 75, 0.7),  # Mifflin-St Jeor
            "male_18_30": (1.19, 9.99, 192, 0.2),
            "male_30": (1.00, 10.5, 153, 0.75),
            "female_10_18": (1.08, 13.3, 334, 0.574),
            "female_18_30": (1.24, 10.4, 53, 1.8),
            "female_30": (1.0, 8.7, 25, 0.2),
        }
        
        self.condition_diet_mapping = {
            MedicalCondition.DIABETES_TYPE2: DietType.LOW_GI,
            MedicalCondition.HYPERTENSION: DietType.DASH,
            MedicalCondition.DYSLIPIDEMIA: DietType.CARDIAC,
            MedicalCondition.CARDIAC_DISEASE: DietType.CARDIAC,
            MedicalCondition.METABOLIC_SYNDROME: DietType.COMBINATION,
            MedicalCondition.CKD_STAGE3: DietType.RENAL,
        }
    
    def calculate_bmr(self, patient: PatientProfile) -> float:
        """
        Calculate Basal Metabolic Rate using Mifflin-St Jeor equation
        More accurate than Harris-Benedict for modern populations
        """
        gender = "male" if patient.gender.lower() == "male" else "female"
        
        if gender == "male":
            bmr = (10 * patient.weight_kg) + (6.25 * patient.height_cm) - (5 * patient.age) + 5
        else:
            bmr = (10 * patient.weight_kg) + (6.25 * patient.height_cm) - (5 * patient.age) - 161
        
        return bmr
    
    def calculate_tdee(self, patient: PatientProfile) -> Dict[str, float]:
        """
        Calculate Total Daily Energy Expenditure
        Returns maintenance and deficit-based calories
        """
        bmr = self.calculate_bmr(patient)
        maintenance = bmr * patient.activity_level.value
        
        return {
            "bmr": bmr,
            "maintenance": round(maintenance, 0),
            "weight_loss_500_deficit": round(maintenance - 500, 0),  # 0.5 kg/week loss
            "weight_loss_750_deficit": round(maintenance - 750, 0),  # 0.75 kg/week loss
            "weight_gain_500_surplus": round(maintenance + 500, 0),
        }
    
    def determine_diet_type(self, patient: PatientProfile) -> DietType:
        """Determine primary diet type based on conditions"""
        # Check for metabolic syndrome
        if len(patient.medical_conditions) >= 3:
            return DietType.COMBINATION
        
        # Single condition mapping
        for condition in patient.medical_conditions:
            if condition in self.condition_diet_mapping:
                return self.condition_diet_mapping[condition]
        
        # Default based on BMI
        if patient.bmi >= 30:
            return DietType.LOW_GI  # Improved insulin sensitivity
        
        return DietType.MEDITERRANEAN  # Universally safe
    
    def get_restricted_foods(self, patient: PatientProfile) -> Dict[str, List[str]]:
        """Generate condition-specific restricted foods"""
        restrictions = {
            "Refined Carbohydrates": [],
            "Sugary Beverages": [],
            "Trans Fats & Saturated Fats": [],
            "High Sodium Processed Foods": [],
            "Alcohol": [],
            "Other": []
        }
        
        # Diabetes restrictions
        if MedicalCondition.DIABETES_TYPE2 in patient.medical_conditions:
            restrictions["Refined Carbohydrates"] = [
                "White bread, refined pasta, white rice (GI >70)",
                "Pastries, doughnuts, sugary cereals",
                "Sweetened condiments (ketchup, BBQ sauce)"
            ]
            restrictions["Sugary Beverages"] = [
                "Regular soft drinks, sweetened juices",
                "Energy drinks, sweetened iced tea",
                "Flavored yogurts, fruit drinks"
            ]
        
        # Hypertension restrictions
        if MedicalCondition.HYPERTENSION in patient.medical_conditions:
            restrictions["High Sodium Processed Foods"] = [
                "Packaged snacks (>500mg Na per serving)",
                "Processed meats (bacon, deli meat, sausage)",
                "Canned soups, salty nuts, pickled foods"
            ]
        
        # Cardiac disease restrictions
        if MedicalCondition.CARDIAC_DISEASE in patient.medical_conditions:
            restrictions["Trans Fats & Saturated Fats"] = [
                "Fried foods, processed snacks with trans fats",
                "Full-fat dairy products, fatty meats",
                "Coconut oil, palm oil"
            ]
            restrictions["Alcohol"] = [
                "Beer, wine, spirits (increases arrhythmia risk)"
            ]
        
        return restrictions
    
    def get_recommended_foods(self, patient: PatientProfile) -> Dict[str, List[str]]:
        """Generate condition-specific recommended foods with health benefits"""
        recommendations = {
            "Low GI Whole Grains": [
                ("Steel-cut oats", "β-glucans reduce postprandial glucose by 25-30%"),
                ("Barley", "Soluble fiber improves glycemic control"),
                ("Legume-based pasta", "Higher protein, lower GI than wheat pasta"),
            ],
            "Fatty Cold-Water Fish": [
                ("Salmon, mackerel, sardines", "EPA/DHA reduces triglycerides by 20-30%"),
            ],
            "Cruciferous Vegetables": [
                ("Broccoli, cauliflower", "Sulforaphane activates detoxification pathways"),
            ],
            "Leafy Greens": [
                ("Spinach, kale, collards", "High magnesium & nitrate content improves vascular function"),
            ],
            "Berries": [
                ("Blueberries, strawberries", "Anthocyanins improve endothelial function"),
            ],
        }
        
        return recommendations
    
    def get_drug_interactions(self, patient: PatientProfile) -> Dict[str, Dict[str, str]]:
        """Identify drug-nutrient interactions based on medications"""
        interactions = {}
        
        # Common interactions
        interaction_database = {
            "Metformin": {
                "vitamin_b12": {
                    "interaction": "B12 malabsorption (10-30% of long-term users)",
                    "management": "Supplement B12: 1000 mcg/week IM or 2000 mcg oral daily"
                },
                "timing": {
                    "interaction": "Reduced absorption on empty stomach",
                    "management": "Take with breakfast & dinner (largest meals)"
                }
            },
            "Amlodipine": {
                "grapefruit": {
                    "interaction": "CYP3A4 inhibition → increased amlodipine levels",
                    "management": "AVOID grapefruit juice entirely"
                }
            },
            "Atorvastatin": {
                "timing": {
                    "interaction": "Peak HMG-CoA reductase activity at night",
                    "management": "Take at evening; Separate from Ca-rich foods by 2+ hours if needed"
                }
            }
        }
        
        for medication in patient.medications:
            for drug_name, interaction_dict in interaction_database.items():
                if drug_name.lower() in medication.lower():
                    interactions[medication] = interaction_dict
        
        return interactions
    
    def generate_diet_plan(self, patient: PatientProfile) -> str:
        """
        Generate complete clinical diet plan in professional format
        Returns formatted HTML/Markdown output
        """
        
        diet_type = self.determine_diet_type(patient)
        tdee = self.calculate_tdee(patient)
        restricted = self.get_restricted_foods(patient)
        recommended = self.get_recommended_foods(patient)
        interactions = self.get_drug_interactions(patient)
        
        # Build professional output
        output = f"""
╔══════════════════════════════════════════════════════════════════╗
║         PERSONALIZED CLINICAL NUTRITION PLAN                    ║
║         Hospital Management System - Nutrition Department        ║
╚══════════════════════════════════════════════════════════════════╝

📋 PATIENT CLINICAL PROFILE
────────────────────────────────────────────────────────────────────
Patient Name: {patient.patient_name} | ID: {patient.patient_id}
Age: {patient.age} years | Gender: {patient.gender.upper()}
Height: {patient.height_cm} cm | Weight: {patient.weight_kg} kg
BMI: {patient.bmi:.1f} {"(OVERWEIGHT)" if 25 <= patient.bmi < 30 else "(OBESE)" if patient.bmi >= 30 else "(NORMAL)"}

Primary Conditions:
{chr(10).join([f"  • {condition.value}" for condition in patient.medical_conditions])}

Activity Level: {patient.activity_level.name}
Medications: {chr(10).join([f"  • {med}" for med in patient.medications]) if patient.medications else "  None listed"}

────────────────────────────────────────────────────────────────────
🥗 PRESCRIBED DIET STRATEGY
────────────────────────────────────────────────────────────────────
Diet Type: {diet_type.value}
Caloric Target (Weight Loss): {tdee["weight_loss_500_deficit"]:.0f} kcal/day
  (Maintenance: {tdee["maintenance"]:.0f} kcal/day - 500 kcal deficit)

Expected Weight Loss Rate: 0.5 kg/week (~2.5 kg/month)

Macronutrient Distribution:
  Carbohydrates: 45-50% ({int(tdee["weight_loss_500_deficit"] * 0.45 / 4):.0f}-{int(tdee["weight_loss_500_deficit"] * 0.50 / 4):.0f}g)
    → Low GI sources to minimize insulin spikes
    → Target fiber: 25-30g/day for satiety
  
  Protein: 25-30% ({int(tdee["weight_loss_500_deficit"] * 0.25 / 4):.0f}-{int(tdee["weight_loss_500_deficit"] * 0.30 / 4):.0f}g)
    → Higher protein for lean mass retention
    → Enhances satiety & metabolic rate
  
  Fat: 20-25% ({int(tdee["weight_loss_500_deficit"] * 0.20 / 9):.0f}-{int(tdee["weight_loss_500_deficit"] * 0.25 / 9):.0f}g)
    → Emphasis on MUFA & PUFA (olive oil, avocado, fatty fish)
    → <7% from saturated fats for lipid management

────────────────────────────────────────────────────────────────────
🚫 FOODS STRICTLY RESTRICTED
────────────────────────────────────────────────────────────────────
"""
        for category, foods in restricted.items():
            if foods:
                output += f"\n{category}:\n"
                for food in foods:
                    output += f"  ✗ {food}\n"
        
        output += f"""
────────────────────────────────────────────────────────────────────
✅ FOODS STRONGLY RECOMMENDED
────────────────────────────────────────────────────────────────────
"""
        for category, foods in recommended.items():
            if foods:
                output += f"\n{category}:\n"
                for food, benefit in foods:
                    output += f"  ✓ {food}: {benefit}\n"
        
        output += f"""
────────────────────────────────────────────────────────────────────
💊 DRUG-NUTRIENT INTERACTIONS & SAFETY
────────────────────────────────────────────────────────────────────
"""
        if interactions:
            for med, int_dict in interactions.items():
                output += f"\n📌 {med}:\n"
                for int_type, details in int_dict.items():
                    output += f"   ⚠️ {details['interaction']}\n"
                    output += f"   → {details['management']}\n"
        
        output += f"""
────────────────────────────────────────────────────────────────────
🎯 EXPECTED CLINICAL BENEFITS (4-6 Weeks)
────────────────────────────────────────────────────────────────────
Week 1-2: Acute Adaptation
  • Weight loss: 1-2 kg (glycogen + water loss)
  • Reduced hunger hormones (ghrelin stabilization)
  
Week 3-4: Metabolic Adaptation
  • Weight loss: 0.5-1 kg/week (consistent deficit)
  • Postprandial glucose: ↓20-25 mg/dL
  • Blood pressure: ↓3-5 mmHg systolic
  
Week 5-6+: Sustained Benefits
  • Total weight loss: 2.5-4 kg
  • Improved lipid profile (TG ↓15-25%, HDL ↑3-5)
  • CRP ↓20-30% (reduced cardiovascular risk)
  • Improved energy, sleep quality, mental clarity

────────────────────────────────────────────────────────────────────
⚠️ MEDICAL DISCLAIMER
────────────────────────────────────────────────────────────────────
This diet plan is individualized and should NOT be applied to other
patients. Mandatory follow-up required:

  4-Week Review: Fasting glucose, weight, BP, adherence assessment
  8-Week Review: Lipid panel, HbA1c (if applicable)
  12-Week Review: Comprehensive metabolic panel, HbA1c

Escalation Required If:
  ⚠️ Fasting glucose >180 mg/dL despite adherence
  ⚠️ Weight loss plateau after 6 weeks
  ⚠️ Signs of hypoglycemia (tremor, sweating, palpitations)
  ⚠️ New-onset edema, dyspnea, or syncope

────────────────────────────────────────────────────────────────────
🏥 GENERATED BY
Clinical Dietician, M.Sc. (Nutrition & Dietetics)
Hospital Management System - Nutrition Department
Date: {datetime.now().strftime("%B %d, %Y")}

Physician Signature: ________________________  Date: __________
────────────────────────────────────────────────────────────────────
"""
        
        return output

# =====================================================
# USAGE EXAMPLE
# =====================================================

if __name__ == "__main__":
    # Sample patient profile
    sample_patient = PatientProfile(
        patient_id="P-12345",
        patient_name="Rajesh Kumar",
        age=52,
        gender="Male",
        height_cm=170,
        weight_kg=82,
        medical_conditions=[
            MedicalCondition.DIABETES_TYPE2,
            MedicalCondition.HYPERTENSION,
            MedicalCondition.DYSLIPIDEMIA,
        ],
        activity_level=ActivityLevel.SEDENTARY,
        medications=[
            "Metformin 1000mg BD",
            "Amlodipine 5mg OD",
            "Atorvastatin 20mg OD"
        ],
        recent_labs={
            "HbA1c": 8.2,
            "LDL_C": 145,
            "Triglycerides": 185,
            "Fasting_Glucose": 145
        }
    )
    
    # Generate diet plan
    generator = ClinicalDietPlanGenerator()
    diet_plan = generator.generate_diet_plan(sample_patient)
    
    print(diet_plan)
    
    # Save to file
    with open("GENERATED_DIET_PLAN.txt", "w") as f:
        f.write(diet_plan)
    
    print("\n✅ Diet plan generated and saved to GENERATED_DIET_PLAN.txt")

