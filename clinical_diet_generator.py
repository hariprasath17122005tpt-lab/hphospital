"""
Professional Clinical Diet Plan Generator
Generates condition-specific, patient-personalized nutrition reports
for hospital patient portals.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json

class ClinicalDietPlanGenerator:
    """
    Generates professional medical-grade diet plans based on patient
    clinical profile. Each plan is unique to patient's conditions,
    medications, and metabolic status.
    """
    
    # Condition to Diet Classification Mapping
    CONDITION_DIET_MAP = {
        'diabetes': {
            'classification': 'Therapeutic Low-Glycemic Index Diet (TLC + GI Management)',
            'rationale': 'Optimized for glycemic control with emphasis on soluble fiber intake and refined carbohydrate restriction to improve insulin sensitivity and reduce HbA1c levels.',
        },
        'hypertension': {
            'classification': 'DASH Diet Protocol (Dietary Approaches to Stop Hypertension)',
            'rationale': 'Sodium-restricted, potassium-rich intervention designed to reduce systolic BP by 8-14 mmHg through mineral optimization and cardiovascular risk reduction.',
        },
        'cardiac': {
            'classification': 'Cardiac-Protective Diet (TLC + AHA Guidelines)',
            'rationale': 'Modified lipid profile targeting plan with emphasis on omega-3 PUFA, soluble fiber, and saturated fat restriction to reduce cardiovascular event risk.',
        },
        'thyroid': {
            'classification': 'Thyroid-Supportive Iodine & Selenium Protocol',
            'rationale': 'Iodine-optimized plan avoiding goitrogens while supporting thyroid hormone metabolism and hormonal equilibrium.',
        },
        'kidney': {
            'classification': 'Renal-Protective KDIGO Protocol',
            'rationale': 'Protein-restricted, phosphorus-managed nutrition therapy designed to slow nephron loss progression and preserve renal function.',
        },
        'liver': {
            'classification': 'Hepatic-Supportive Antioxidant Protocol',
            'rationale': 'Nutrient-dense plan optimized for liver regeneration with emphasis on antioxidants, reduced ammonia precursors, and micronutrient density.',
        },
        'gerd': {
            'classification': 'Reflux-Minimizing Gastroprotective Diet',
            'rationale': 'Modified viscosity and pH-optimized plan eliminating acid-triggering foods while maintaining nutritional adequacy.',
        },
        'asthma': {
            'classification': 'Inflammation-Reducing Anti-Inflammatory Protocol',
            'rationale': 'Antioxidant and omega-3 rich intervention designed to reduce airway inflammation markers and improve pulmonary function.',
        },
    }
    
    # Meal Plans Database (Condition-Specific)
    CONDITION_MEALS = {
        'diabetes': {
            'breakfast': [
                {
                    'items': [
                        ('Steel-cut oatmeal with cinnamon', '½ cup cooked'),
                        ('Almonds (chopped)', '1 oz / 23 nuts'),
                        ('Fresh blueberries', '¾ cup'),
                        ('Greek yogurt, unsweetened', '¼ cup'),
                    ],
                    'kcal': 320, 'carb': 38, 'protein': 12, 'fat': 10,
                    'rationale': 'High-soluble-fiber oatmeal reduces postprandial glucose spikes by 15-20%. Blueberries contain anthocyanins with proven insulin-sensitizing effects. Almonds provide α-tocopherol reducing inflammation markers.'
                }
            ],
            'lunch': [
                {
                    'items': [
                        ('Grilled salmon (Atlantic)', '4 oz / 112g'),
                        ('Steamed broccoli', '1.5 cups'),
                        ('Brown rice', '⅔ cup cooked'),
                        ('Olive oil (EVOO)', '1 tsp'),
                    ],
                    'kcal': 420, 'carb': 35, 'protein': 38, 'fat': 12,
                    'rationale': 'Salmon provides EPA/DHA (2.2g/4oz) reducing triglycerides and inflammatory markers. Broccoli sulforaphane supports detoxification. Brown rice GI=68 (vs white GI=89) minimizes glycemic stress.'
                }
            ],
            'dinner': [
                {
                    'items': [
                        ('Baked chicken breast (skinless)', '4.5 oz'),
                        ('Roasted sweet potato', '1 medium'),
                        ('Mixed green salad', '2 cups'),
                        ('Balsamic vinaigrette (homemade)', '2 tbsp'),
                    ],
                    'kcal': 385, 'carb': 32, 'protein': 42, 'fat': 8,
                    'rationale': 'Lean poultry minimizes saturated fat. Sweet potato β-carotene supports glycemic control. Vinegar acetic acid reduces postprandial glucose excursion by ~25%. Salad increases micronutrient density.'
                }
            ],
            'snacks': [
                ('Raw almonds', '1 oz'),
                ('Apple with almond butter', '1 medium apple + 1 tbsp'),
            ]
        },
        'hypertension': {
            'breakfast': [
                {
                    'items': [
                        ('Plain non-fat Greek yogurt', '1 cup'),
                        ('Granola (low-sodium)', '¼ cup'),
                        ('Fresh raspberries', '¾ cup'),
                        ('Honey', '1 tsp'),
                    ],
                    'kcal': 280, 'carb': 42, 'protein': 18, 'fat': 2,
                    'rationale': 'High potassium (yogurt: 200mg/cup) offsets sodium. Raspberries contain polyphenols reducing arterial stiffness. Zero added sodium maintains blood pressure targets.'
                }
            ],
            'lunch': [
                {
                    'items': [
                        ('Turkey breast (no salt)', '4 oz'),
                        ('Whole wheat bread', '2 slices'),
                        ('Avocado', '¼ medium'),
                        ('Leafy greens (spinach)', '2 oz'),
                    ],
                    'kcal': 340, 'carb': 35, 'protein': 26, 'fat': 11,
                    'rationale': 'Potassium content 450+mg supports vasodilation. Magnesium from greens (8mg/oz) enhances smooth muscle relaxation. Whole grain fiber reduces LDL cholesterol by 10-15%.'
                }
            ],
            'dinner': [
                {
                    'items': [
                        ('Baked cod (sodium-free seasoning)', '4.5 oz'),
                        ('Steamed carrots', '1.5 cups'),
                        ('Quinoa (unsalted)', '⅔ cup cooked'),
                        ('Fresh lemon juice', '2 tbsp'),
                    ],
                    'kcal': 360, 'carb': 38, 'protein': 32, 'fat': 5,
                    'rationale': 'White fish rich in potassium (400+mg). Carrots lycopene acts as ACE-inhibitor alternative. Quinoa complete amino acid profile without sodium. Lemon enhances palatability without salt.'
                }
            ],
            'snacks': [
                ('Unsalted walnuts', '1 oz'),
                ('Banana (medium)', '1 medium'),
            ]
        },
        'cardiac': {
            'breakfast': [
                {
                    'items': [
                        ('Rolled oats (old-fashioned)', '½ cup dry'),
                        ('Ground flaxseed', '2 tbsp'),
                        ('Skim milk', '1 cup'),
                        ('Strawberries (fresh)', '¾ cup'),
                    ],
                    'kcal': 310, 'carb': 48, 'protein': 10, 'fat': 6,
                    'rationale': 'Oat β-glucan reduces LDL 3-5% per 2g soluble fiber. Flax ALA (2.3g/tbsp) converts to EPA via hepatic β-oxidation. Zero trans fat preserves endothelial function.'
                }
            ],
            'lunch': [
                {
                    'items': [
                        ('Grilled sardines', '3.5 oz'),
                        ('Whole grain crackers', '6 small'),
                        ('Tomato & basil salad', '2 cups'),
                        ('Olive oil', '1 tsp'),
                    ],
                    'kcal': 380, 'carb': 28, 'protein': 32, 'fat': 14,
                    'rationale': 'Sardines EPA/DHA 1.5g/3.5oz reduces arrhythmia risk by 25%. Tomato lycopene prevents LDL oxidation. Whole grain fiber improves lipid profiles. MUFA from olive oil supports HDL.'
                }
            ],
            'dinner': [
                {
                    'items': [
                        ('Skinless chicken breast', '4 oz'),
                        ('Steamed brussels sprouts', '1.5 cups'),
                        ('Sweet potato (mashed, no butter)', '1 medium'),
                        ('Herb seasoning (no salt)', '1 tsp'),
                    ],
                    'kcal': 350, 'carb': 35, 'protein': 40, 'fat': 4,
                    'rationale': 'Lean poultry supports LDL targets. Brussels sprouts sulforaphane activates antioxidant pathways reducing oxidative stress. Sweet potato potassium supports cardiac electrolytes. Zero sodium maintains blood pressure.'
                }
            ],
            'snacks': [
                ('Raw almonds', '1 oz'),
                ('Pear (medium)', '1 medium'),
            ]
        }
    }
    
    # Restriction Library (Condition-Specific)
    CONDITION_RESTRICTIONS = {
        'diabetes': {
            'Sugary & Refined Foods': [
                ('Refined white bread', 'High GI (95) causes acute hyperglycemic spikes; increases HbA1c 0.3-0.5% per 50g/day consumption'),
                ('Candy, pastries, desserts', 'Rapid glucose absorption (GI 80-100) triggers compensatory hyperinsulinemia and insulin resistance progression'),
                ('Soft drinks & juice', 'Fructose 55% bypasses normal glycemic regulation, promoting hepatic steatosis and triglyceride elevation'),
                ('Sweetened cereals', 'Refined carbs reduce insulin secretion capacity by 15-20%; worsens β-cell exhaustion'),
            ],
            'High-Glycemic Fruits': [
                ('Watermelon, cantaloupe', 'GI >70 produces rapid glucose surges equivalent to 3-4 tsp pure sugar per serving'),
                ('Dried fruits (raisins, dates)', 'Concentrated sugars (70% carbohydrate) cause 2-3x larger glucose excursions vs fresh fruit'),
                ('Fruit juices (all types)', 'No fiber; complete sugar absorption within 15 minutes spike'),
            ],
            'Certain Grains': [
                ('White rice, instant rice', 'Amylose depletion GI=89; causes postprandial glucose peak of 150-180 mg/dL in type-2'),
                ('Instant oatmeal', 'Processing removes β-glucan fiber reducing soluble fiber content 60%'),
            ]
        },
        'hypertension': {
            'High-Sodium Foods': [
                ('Processed meats (bacon, sausage)', 'Sodium 300-400mg per serving; salt sensitivity increases BP 3-5 mmHg per 1000mg Na+/day'),
                ('Canned soups & broths', 'Sodium 700-1200mg per serving (>50% daily allowance); promotes fluid retention and sympathetic activation'),
                ('Deli meats & cheese', 'Sodium 200-400mg per oz; high saturated fat worsens vascular stiffness'),
                ('Soy sauce, condiments', 'Sodium 800-1000mg per tablespoon; complete daily sodium in single serving'),
            ],
            'High-Saturated Fat': [
                ('Fatty red meat', 'Saturated fat increases arterial stiffness; raises SBP 2-3 mmHg per 3% caloric increase'),
                ('Full-fat dairy', 'Cholesterol increases LDL; indirectly elevates BP via endothelial dysfunction'),
                ('Tropical oils (coconut, palm)', 'Saturated fat composition exceeds animal fats; impairs vasodilation'),
            ],
        },
        'cardiac': {
            'Trans Fats & Saturated Fat Sources': [
                ('Fried foods & fast food', 'Trans fats (0.5g serving) increase Lp(a) by 20-25%; elevates cardiac event risk 25%'),
                ('Butter, cream, fatty meats', 'Saturated fat LDL elevation promotes atherosclerotic plaque progression 0.5-1mm/year per 2% calories'),
                ('Processed baked goods', 'Contains 30-40% trans fats; acute endothelial dysfunction within 4 hours of consumption'),
            ],
            'High-Cholesterol Foods': [
                ('Organ meats, egg yolks (>3/week)', 'Dietary cholesterol increases LDL 20-30mg/dL in responsive individuals (30% population)'),
                ('Full-fat dairy products', 'Cholesterol 24mg/cup increases atherosclerotic burden'),
            ],
        },
        'thyroid': {
            'Goitrogenic Foods (if hypothyroid)': [
                ('Raw cruciferous vegetables in excess', 'Thiocyanates inhibit iodine uptake 30-50%; impair thyroid hormone synthesis'),
                ('Soy products (unfermented)', 'Isoflavones reduce thyroxine absorption; lower free T4 by 15-20%'),
            ],
        }
    }
    
    # Recommended Foods Library (Condition-Specific Benefits)
    CONDITION_RECOMMENDATIONS = {
        'diabetes': {
            'High-Fiber Vegetables': [
                ('Broccoli, spinach, kale', 'Α-lipoic acid improves insulin sensitivity 20-25%; insoluble fiber slows glucose absorption'),
                ('Brussels sprouts, cauliflower', 'Sulforaphane activates SIRT1 pathway; enhances mitochondrial oxidative capacity'),
                ('Bell peppers, zucchini, cucumber', 'Vitamin C enhances insulin secretion; chromium improves glucose metabolism 15-20%'),
            ],
            'Legumes & Whole Grains': [
                ('Lentils, chickpeas, beans', 'Resistant starch produces 20-25% lower glucose response; increases GLP-1 secretion'),
                ('Barley, steel-cut oats', 'β-glucan soluble fiber reduces postprandial glucose 15-20%; improves lipid panels 5-10%'),
            ],
            'Nuts & Seeds': [
                ('Walnuts, flaxseeds', 'Magnesium improves insulin sensitivity; polyphenols reduce oxidative stress markers 25-30%'),
                ('Chia seeds, almonds', 'Fiber-to-carb ratio <1:2; minimal glycemic impact with sustained satiety'),
            ],
        },
        'hypertension': {
            'Potassium-Rich Foods': [
                ('Spinach, Swiss chard, beet greens', 'Potassium 850-1000mg/cup; reduces SBP 8-10 mmHg through vasodilation'),
                ('Bananas, cantaloupe, avocado', 'Potassium-sodium ratio >10:1 activates Na-K-ATPase; lowers BP 3-5 mmHg'),
                ('Sweet potato, winter squash', 'Potassium 350-450mg + fiber prebiotic effects improve vascular endothelial function'),
            ],
            'Magnesium Sources': [
                ('Pumpkin seeds, almonds, spinach', 'Magnesium 100-200mg per serving; reduces arterial stiffness 10-15%; enhances vasodilation'),
                ('Whole grains, legumes', 'Magnesium activates Na-K-ATPase; improves SBP 5-8 mmHg in deficient individuals'),
            ],
            'Calcium & Vitamin D Foods': [
                ('Fortified low-fat milk, yogurt', 'Calcium 200-300mg/serving + vitamin D enhances calcium absorption; reduces SBP 3-5 mmHg'),
                ('Salmon, sardines with bones', 'Bioavailable calcium + omega-3 PUFAs; synergistic cardiovascular protection'),
            ],
        },
        'cardiac': {
            'Omega-3 PUFA Sources': [
                ('Fatty fish (salmon, mackerel, sardines)', 'EPA 500mg + DHA 1200mg/3.5oz; reduces triglycerides 25-30%; decreases sudden cardiac death 25%'),
                ('Walnuts, flaxseeds, chia seeds', 'ALA 2.3g/tbsp (walnuts); converts to EPA 8-12% providing modest anti-inflammatory effects'),
            ],
            'Antioxidant-Rich Foods': [
                ('Blueberries, strawberries, blackberries', 'Anthocyanins reduce arterial stiffness; improve endothelial function markers 15-20%'),
                ('Dark chocolate (70%+ cocoa)', 'Flavonols 10-12mg/oz; improve vasodilation 10-15%; reduce platelet aggregation'),
                ('Tomatoes, red peppers', 'Lycopene prevents LDL oxidation; reduces atherosclerotic plaque 30-40% in prospective studies'),
            ],
            'Soluble Fiber': [
                ('Oats, barley, beans', 'β-glucan 2g daily reduces LDL 3-5%; improves lipid ratios Total:HDL by 0.5 units'),
                ('Apples, pears, citrus', 'Pectin fiber slows LDL oxidation; improves hs-CRP inflammatory marker 20-25%'),
            ],
        }
    }
    
    # Drug-Nutrient Interactions Database
    DRUG_INTERACTIONS = {
        'metformin': {
            'medication': 'Metformin (Diabetes)',
            'risk': 'Vitamin B12 malabsorption (~10% patients); decreased intrinsic factor binding leads to 10-year cumulative B12 deficiency in 20-30% long-term users',
            'management': 'Supplement B12 500-1000mcg weekly or 2000mcg daily; monitor serum B12 annually. Add B12-fortified foods (dairy, fortified cereals) minimum 2-3 servings daily.',
            'timing': 'Take B12 supplement separately from metformin (2+ hours apart) to maximize absorption. Evening supplementation preferred due to improved mucosal contact time.'
        },
        'lisinopril': {
            'medication': 'Lisinopril (Hypertension/Cardiac)',
            'risk': 'Hyperkalemia risk from elevated potassium retention (~8-12% patients); ACE inhibition reduces aldosterone, impairing renal K+ excretion',
            'management': 'Monitor serum K+ baseline and every 6 months. Restrict potassium to 2000-2500mg/day (avoid K+ supplementation). Moderate intake of high-K+ foods.',
            'timing': 'Take lisinopril consistently with or without food; potassium content fluctuates with meal timing so consistency crucial.'
        },
        'warfarin': {
            'medication': 'Warfarin (Anticoagulation)',
            'risk': 'Vitamin K antagonism; inconsistent dietary K intake causes INR fluctuation (therapeutic range ±0.5 critical); increased bleeding/clotting risk',
            'management': 'MAINTAIN CONSTANT DAILY VITAMIN K INTAKE (90-120mcg/day). Eat consistent amount of dark leafy greens daily. Avoid sudden dietary changes.',
            'timing': 'Take warfarin consistently at same time daily. Allow 4-6 hour separation between warfarin and high-K foods for predictable INR.'
        },
        'statin': {
            'medication': 'Statins (Cholesterol)',
            'risk': 'Possible CoQ10 depletion (~40% reduction); impairs mitochondrial ATP production; myalgia in 5-10% patients',
            'management': 'Supplement CoQ10 100-200mg daily (or ubiquinol 50-100mg). Increase dietary sources: fatty fish, organ meats, whole grains.',
            'timing': 'Take statin with evening meal (increased absorption); CoQ10 fat-soluble so take with dietary fat for enhanced bioavailability.'
        },
        'thyroid': {
            'medication': 'Levothyroxine (Thyroid)',
            'risk': 'Food/supplement interference reduces absorption 20-40%; calcium, iron, fiber, soy impair L-thyroxine bioavailability',
            'management': 'Take levothyroxine on empty stomach (30-60min before breakfast). Avoid calcium/iron supplements 4+ hours after dose. Space soy products >4 hours.',
            'timing': 'CRITICAL: Take levothyroxine 30-60 minutes before ANY food, supplements, or medications. Consistent timing ensures stable TSH levels (±0.5 mIU/L target).'
        }
    }
    
    def __init__(self, patient_data: Dict):
        """Initialize with patient clinical profile"""
        self.patient_data = patient_data
        self.age = patient_data.get('age')
        self.gender = patient_data.get('gender')
        self.bmi = patient_data.get('bmi')
        self.conditions = patient_data.get('medical_conditions', [])
        self.medications = patient_data.get('medications', [])
        self.activity_level = patient_data.get('activity_level', 'moderate')
    
    def calculate_tdee(self) -> Tuple[int, int]:
        """
        Calculate Basal Metabolic Rate (BMR) and Total Daily Energy Expenditure (TDEE)
        Returns: (bmr, tdee)
        """
        weight = self.patient_data.get('weight', 70)  # kg
        height = self.patient_data.get('height', 170)  # cm
        
        # Mifflin-St Jeor equation (more accurate than Harris-Benedict)
        if self.gender.lower() == 'male':
            bmr = (10 * weight) + (6.25 * height) - (5 * self.age) + 5
        else:
            bmr = (10 * weight) + (6.25 * height) - (5 * self.age) - 161
        
        # Activity multiplier
        activity_multipliers = {
            'sedentary': 1.2,
            'light': 1.375,
            'moderate': 1.55,
            'active': 1.725,
            'very_active': 1.9
        }
        
        multiplier = activity_multipliers.get(self.activity_level, 1.55)
        tdee = int(bmr * multiplier)
        
        # Adjust based on conditions
        if 'diabetes' in self.conditions or 'weight_management' in self.conditions:
            tdee = int(tdee * 0.85)  # 15% deficit for weight loss
        
        return int(bmr), tdee
    
    def get_diet_classification(self) -> Tuple[str, str]:
        """Get primary diet classification based on conditions"""
        # Prioritize conditions by clinical severity
        priority_order = ['diabetes', 'cardiac', 'kidney', 'hypertension', 'thyroid', 'liver', 'gerd', 'asthma']
        
        for condition in priority_order:
            if condition in [c.lower() for c in self.conditions]:
                data = self.CONDITION_DIET_MAP.get(condition)
                return data['classification'], data['rationale']
        
        return 'Balanced Therapeutic Diet', 'General wellness optimization based on patient profile.'
    
    def get_macronutrient_targets(self, tdee: int) -> Dict:
        """Calculate condition-specific macronutrient targets"""
        targets = {}
        
        if 'diabetes' in [c.lower() for c in self.conditions]:
            # Diabetes: 40% carb, 30% protein, 30% fat
            targets['carb_percent'] = 40
            targets['protein_percent'] = 30
            targets['fat_percent'] = 30
            targets['carb_rationale'] = 'Moderate carbohydrate with emphasis on low-glycemic index foods to maintain steady blood glucose. Soluble fiber target 15-20g/day.'
            targets['protein_rationale'] = 'Elevated protein (1.2-1.3g/kg) supports satiety and preserves lean mass while improving insulin sensitivity through metabolic cost of protein.'
            targets['fat_rationale'] = 'MUFA-rich (olive oil, avocado) with limited saturated fat <7% calories. Omega-3 PUFA emphasis for anti-inflammatory protection.'
        
        elif 'hypertension' in [c.lower() for c in self.conditions]:
            # Hypertension: 50% carb, 20% protein, 30% fat
            targets['carb_percent'] = 50
            targets['protein_percent'] = 20
            targets['fat_percent'] = 30
            targets['carb_rationale'] = 'Emphasis on whole grains and vegetable carbohydrates providing fiber and micronutrients without excess sodium. Target 25-30g fiber/day.'
            targets['protein_rationale'] = 'Moderate protein (0.8-1.0g/kg) emphasis on plant-based and white fish sources. Red meat limited to 1-2x weekly maximum.'
            targets['fat_rationale'] = 'DASH-aligned MUFA focus with minimal saturated fat (<6% calories) and zero trans fats. Potassium-rich foods prioritized over sodium.'
        
        elif 'cardiac' in [c.lower() for c in self.conditions]:
            # Cardiac: 45% carb, 25% protein, 30% fat
            targets['carb_percent'] = 45
            targets['protein_percent'] = 25
            targets['fat_percent'] = 30
            targets['carb_rationale'] = 'Mediterranean-style carbohydrates (whole grains, legumes) with high antioxidant food emphasis. Refined carbohydrate complete elimination.'
            targets['protein_rationale'] = 'Lean protein (1.0-1.1g/kg) prioritizing fatty fish (EPA/DHA >2g/day), plant proteins, and poultry without skin. Red meat <once weekly.'
            targets['fat_rationale'] = 'MUFA 15% + PUFA 8% with saturated fat restricted to <5% calories. Emphasis on omega-3 sources: fish, walnuts, flaxseed.'
        
        else:
            # Default balanced
            targets['carb_percent'] = 45
            targets['protein_percent'] = 25
            targets['fat_percent'] = 30
            targets['carb_rationale'] = 'Balanced carbohydrate intake emphasizing whole grains, vegetables, and legumes for sustained energy and micronutrient optimization.'
            targets['protein_rationale'] = 'Adequate protein (0.8-1.0g/kg) from diverse sources supporting lean mass preservation and metabolic stability.'
            targets['fat_rationale'] = 'Moderate fat intake emphasizing unsaturated fats and limiting saturated fat for cardiovascular health maintenance.'
        
        # Calculate gram amounts
        carb_kcal = int(tdee * targets['carb_percent'] / 100)
        protein_kcal = int(tdee * targets['protein_percent'] / 100)
        fat_kcal = int(tdee * targets['fat_percent'] / 100)
        
        targets['carb_grams'] = int(carb_kcal / 4)
        targets['protein_grams'] = int(protein_kcal / 4)
        targets['fat_grams'] = int(fat_kcal / 9)
        
        return targets
    
    def get_drug_interactions(self) -> List[Dict]:
        """Extract drug-nutrient interactions based on patient medications"""
        interactions = []
        
        medication_keywords = [med.lower() for med in self.medications]
        
        for med_name, interaction_data in self.DRUG_INTERACTIONS.items():
            if any(med_name in med for med in medication_keywords):
                interactions.append(interaction_data)
        
        return interactions
    
    def get_restricted_foods(self) -> Dict[str, List]:
        """Get condition-specific restricted foods"""
        restricted = {}
        
        for condition in [c.lower() for c in self.conditions]:
            if condition in self.CONDITION_RESTRICTIONS:
                restricted.update(self.CONDITION_RESTRICTIONS[condition])
        
        return restricted if restricted else {'General Restrictions': [
            ('Processed foods with added sugars', 'High calories, low nutrients, promotes weight gain and metabolic dysfunction'),
            ('Trans fats & fried foods', 'Increase inflammation markers; elevate cardiovascular disease risk 25-30%'),
            ('Excessive sodium', 'Promotes fluid retention and increases hypertension risk; limit <2300mg/day'),
        ]}
    
    def get_recommended_foods(self) -> Dict[str, List]:
        """Get condition-specific recommended foods"""
        recommended = {}
        
        for condition in [c.lower() for c in self.conditions]:
            if condition in self.CONDITION_RECOMMENDATIONS:
                recommended.update(self.CONDITION_RECOMMENDATIONS[condition])
        
        if not recommended:
            recommended = {
                'Antioxidant-Rich Vegetables': [
                    ('Spinach, kale, broccoli', 'High in vitamins C, K and polyphenols; support detoxification and reduce oxidative stress'),
                    ('Bell peppers, tomatoes, carrots', 'Rich in carotenoids and vitamin C; improve immune function and cellular protection'),
                ],
                'High-Protein Lean Sources': [
                    ('Fish, poultry, legumes', 'Complete amino acids supporting lean mass maintenance and metabolic function'),
                    ('Low-fat dairy, nuts, seeds', 'Micronutrient-dense protein sources providing calcium, magnesium, and healthy fats'),
                ]
            }
        
        return recommended
    
    def get_expected_benefits(self) -> Dict[str, List]:
        """Clinical benefits timeline based on condition"""
        benefits = {
            'week1-2': [],
            'week3-4': [],
            'week5-6': []
        }
        
        if 'diabetes' in [c.lower() for c in self.conditions]:
            benefits['week1-2'] = [
                'Blood glucose stabilization with 20-30% reduction in postprandial spikes',
                'Improved energy levels and reduced mid-afternoon fatigue (due to stable glucose)',
                'Reduced food cravings and improved satiety (high-protein, fiber-rich foods)',
            ]
            benefits['week3-4'] = [
                'Initial weight loss 2-4 lbs (water weight + early fat mobilization)',
                'Fasting glucose trending downward 5-15 mg/dL reduction',
                'Improved sleep quality from glycemic stability',
            ]
            benefits['week5-6'] = [
                'Expected HbA1c improvement 0.5-1.0% over 3 months (with consistent adherence)',
                'Improved insulin sensitivity measured at lab review',
                'Sustained weight loss 4-8 lbs total with improved energy',
            ]
        
        elif 'hypertension' in [c.lower() for c in self.conditions]:
            benefits['week1-2'] = [
                'Blood pressure reduction 5-8 mmHg SBP within 7-14 days',
                'Reduced sodium-induced water retention (1-2 lbs weight loss)',
                'Improved urinary sodium excretion and renal function',
            ]
            benefits['week3-4'] = [
                'Further BP reduction 3-5 mmHg (additional potassium accumulation effect)',
                'Improved vascular endothelial function markers',
                'Reduced morning blood pressure surges',
            ]
            benefits['week5-6'] = [
                'Total expected SBP reduction 8-12 mmHg by 6 weeks',
                'Improved 24-hour ambulatory BP readings',
                'Sustained normalization with medication adjustment potential',
            ]
        
        elif 'cardiac' in [c.lower() for c in self.conditions]:
            benefits['week1-2'] = [
                'Triglyceride reduction 10-15% (rapid response to omega-3 PUFA)',
                'Improved exercise tolerance and reduced dyspnea',
                'Reduced inflammatory markers (hs-CRP trending downward)',
            ]
            benefits['week3-4'] = [
                'LDL cholesterol reduction 5-10% with dietary changes alone',
                'Improved endothelial function (better nitric oxide production)',
                'Enhanced vasodilation capacity (improved exercise performance)',
            ]
            benefits['week5-6'] = [
                'Total cholesterol improvement 10-15% expected by 8 weeks',
                'HDL cholesterol increase 5-10% (especially with regular activity)',
                'Risk profile improvement with potential medication adjustment',
            ]
        
        else:
            benefits['week1-2'] = [
                'Improved energy and mental clarity from nutritional optimization',
                'Better digestion and reduced GI distress',
                'Initial weight stabilization',
            ]
            benefits['week3-4'] = [
                'Improved sleep quality and recovery',
                'Enhanced athletic performance if applicable',
                'Sustained energy without mid-day crashes',
            ]
            benefits['week5-6'] = [
                'Visible improvements in body composition',
                'Laboratory markers trending toward healthy ranges',
                'Sustainable healthy habits established',
            ]
        
        return {
            'Weeks 1-2: Acute Metabolic Phase': benefits['week1-2'],
            'Weeks 3-4: Adaptation Phase': benefits['week3-4'],
            'Weeks 5-6: Stabilization Phase': benefits['week5-6'],
        }
    
    def get_safety_protocols(self) -> List[str]:
        """Condition-specific monitoring and safety protocols"""
        protocols = [
            'Weekly self-monitoring with food/symptom diary to identify triggers and adherence patterns',
            'Biweekly weight monitoring at consistent time (morning post-void for accuracy)',
            'Monthly blood pressure home monitoring (morning & evening readings)',
        ]
        
        if 'diabetes' in [c.lower() for c in self.conditions]:
            protocols.extend([
                'Blood glucose monitoring as directed by endocrinologist (frequency dependent on treatment)',
                'Watch for hypoglycemic symptoms (tremors, sweating, confusion) - carry fast-acting carbohydrate',
                'Report any signs of diabetic neuropathy or vision changes immediately',
            ])
        
        if 'cardiac' in [c.lower() for c in self.conditions]:
            protocols.extend([
                'Immediate evaluation if chest pain, dyspnea, or palpitations occur during meals',
                'Monitor salt retention (weight gain >2 lbs/day = fluid accumulation concern)',
            ])
        
        if 'hypertension' in [c.lower() for c in self.conditions]:
            protocols.extend([
                'Home blood pressure monitoring 2x weekly minimum; report SBP >160 mmHg immediately',
                'Monitor for signs of hypertensive crisis (severe headache, chest pain, vision changes)',
            ])
        
        return protocols
    
    def get_escalation_symptoms(self) -> List[str]:
        """Symptoms requiring immediate medical evaluation"""
        symptoms = []
        
        if 'cardiac' in [c.lower() for c in self.conditions]:
            symptoms.extend([
                'Chest pain, pressure, or tightness at rest or with exertion',
                'Shortness of breath at rest or with minimal activity',
                'Palpitations, irregular heartbeat, or syncope (fainting)',
                'Severe swelling of legs/ankles or rapid weight gain (>2-3 lbs/day)',
            ])
        
        if 'diabetes' in [c.lower() for c in self.conditions]:
            symptoms.extend([
                'Blood glucose <70 mg/dL (hypoglycemia) unresponsive to fast carbohydrates',
                'Diabetic ketoacidosis signs (fruity breath, nausea, severe fatigue)',
                'Vision changes, numbness in feet, or signs of infection',
            ])
        
        if 'hypertension' in [c.lower() for c in self.conditions]:
            symptoms.extend([
                'Severe headache accompanied by vision changes or chest pain',
                'Blood pressure >180/120 mmHg on home monitor',
                'Signs of stroke (facial droop, arm weakness, speech difficulty)',
            ])
        
        if not symptoms:
            symptoms = [
                'Severe abdominal pain or persistent nausea/vomiting',
                'Signs of allergic reaction (swelling, difficulty breathing, rash)',
                'Unexplained fever >101°F or signs of infection',
                'Severe dizziness, fainting, or confusion',
            ]
        
        return symptoms
    
    def generate_report_data(self) -> Dict:
        """Generate all data needed to render the professional diet plan template"""
        bmr, tdee = self.calculate_tdee()
        diet_class, diet_rationale = self.get_diet_classification()
        macros = self.get_macronutrient_targets(tdee)
        drug_interactions = self.get_drug_interactions()
        restricted_foods = self.get_restricted_foods()
        recommended_foods = self.get_recommended_foods()
        expected_benefits = self.get_expected_benefits()
        safety_protocols = self.get_safety_protocols()
        escalation_symptoms = self.get_escalation_symptoms()
        
        report_data = {
            # Header info
            'patient_id': self.patient_data.get('id', 'N/A'),
            'generated_date': datetime.now().strftime('%B %d, %Y'),
            'valid_until': (datetime.now() + timedelta(days=90)).strftime('%B %d, %Y'),
            'physician_name': self.patient_data.get('physician_name', 'Primary Care Physician'),
            
            # Clinical summary
            'status': f'{self.age}-year-old {self.gender.title()}',
            'priority': 'Therapeutic Intervention Required' if len(self.conditions) > 1 else 'Preventive Optimization',
            'intervention': 'Medical Nutrition Therapy (MNT)',
            
            # Diet strategy
            'diet_classification': diet_class,
            'diet_rationale': diet_rationale,
            'maintenance_kcal': bmr,
            'therapeutic_kcal': tdee,
            'caloric_justification': f'Calculated from Mifflin-St Jeor equation (BMR {bmr} kcal) × {self.activity_level.title()} activity factor (1.55). Adjusted for therapeutic targets.',
            
            # Macronutrients
            **macros,  # Unpacks carb_percent, protein_percent, fat_percent, etc.
            
            # Meal planning (simplified example - would be pulled from condition-specific data)
            # These would be populated from CONDITION_MEALS database
            
            # Restrictions
            'restriction_category1': list(restricted_foods.keys())[0] if restricted_foods else 'Restricted Foods',
            'restriction_category2': list(restricted_foods.keys())[1] if len(restricted_foods) > 1 else 'High-Sodium Items',
            'restriction_category3': list(restricted_foods.keys())[2] if len(restricted_foods) > 2 else None,
            
            # Recommendations
            'recommendation_category1': list(recommended_foods.keys())[0] if recommended_foods else 'Antioxidant Foods',
            'recommendation_category2': list(recommended_foods.keys())[1] if len(recommended_foods) > 1 else 'High-Protein Sources',
            'recommendation_category3': list(recommended_foods.keys())[2] if len(recommended_foods) > 2 else 'Healthy Fats',
            
            # Drug interactions
            'drug_interactions': drug_interactions,
            
            # Safety
            'safety_protocol1': safety_protocols[0] if len(safety_protocols) > 0 else 'Weekly monitoring required',
            'safety_protocol2': safety_protocols[1] if len(safety_protocols) > 1 else 'Maintain food diary',
            'safety_protocol3': safety_protocols[2] if len(safety_protocols) > 2 else 'Monthly lab review',
            'safety_protocol4': safety_protocols[3] if len(safety_protocols) > 3 else 'Follow-up appointments',
            
            # Benefits timeline
            'benefit_week1_1': expected_benefits.get('Weeks 1-2: Acute Metabolic Phase', [])[0] if expected_benefits else 'Improved energy',
            'benefit_week1_2': expected_benefits.get('Weeks 1-2: Acute Metabolic Phase', [])[1] if len(expected_benefits.get('Weeks 1-2: Acute Metabolic Phase', [])) > 1 else 'Better digestion',
            'benefit_week1_3': expected_benefits.get('Weeks 1-2: Acute Metabolic Phase', [])[2] if len(expected_benefits.get('Weeks 1-2: Acute Metabolic Phase', [])) > 2 else 'Stable mood',
            
            'benefit_week3_1': expected_benefits.get('Weeks 3-4: Adaptation Phase', [])[0] if expected_benefits else 'Continued improvement',
            'benefit_week3_2': expected_benefits.get('Weeks 3-4: Adaptation Phase', [])[1] if len(expected_benefits.get('Weeks 3-4: Adaptation Phase', [])) > 1 else 'Enhanced performance',
            'benefit_week3_3': expected_benefits.get('Weeks 3-4: Adaptation Phase', [])[2] if len(expected_benefits.get('Weeks 3-4: Adaptation Phase', [])) > 2 else 'Sustained energy',
            
            'benefit_week5_1': expected_benefits.get('Weeks 5-6: Stabilization Phase', [])[0] if expected_benefits else 'Health stabilization',
            'benefit_week5_2': expected_benefits.get('Weeks 5-6: Stabilization Phase', [])[1] if len(expected_benefits.get('Weeks 5-6: Stabilization Phase', [])) > 1 else 'Improved markers',
            'benefit_week5_3': expected_benefits.get('Weeks 5-6: Stabilization Phase', [])[2] if len(expected_benefits.get('Weeks 5-6: Stabilization Phase', [])) > 2 else 'Long-term success',
            
            # Escalation
            'escalation_symptom1': escalation_symptoms[0] if len(escalation_symptoms) > 0 else 'Severe symptoms',
            'escalation_symptom2': escalation_symptoms[1] if len(escalation_symptoms) > 1 else 'Dangerous vitals',
            'escalation_symptom3': escalation_symptoms[2] if len(escalation_symptoms) > 2 else 'Warning signs',
            'escalation_symptom4': escalation_symptoms[3] if len(escalation_symptoms) > 3 else 'Acute changes',
        }
        
        return report_data

# Example usage
if __name__ == '__main__':
    sample_patient = {
        'id': 'P00123',
        'age': 55,
        'gender': 'male',
        'weight': 85,
        'height': 175,
        'bmi': 27.7,
        'activity_level': 'moderate',
        'medical_conditions': ['diabetes', 'hypertension'],
        'medications': ['Metformin 500mg', 'Lisinopril 10mg'],
        'physician_name': 'Dr. Rajesh Kumar, MD',
    }
    
    generator = ClinicalDietPlanGenerator(sample_patient)
    report_data = generator.generate_report_data()
    
    print("✓ Professional Clinical Diet Plan Generator Ready")
    print(f"Patient: {report_data['status']}")
    print(f"Diet Classification: {report_data['diet_classification']}")
    print(f"Therapeutic Calories: {report_data['therapeutic_kcal']} kcal/day")
    print(f"Generated: {report_data['generated_date']}")
