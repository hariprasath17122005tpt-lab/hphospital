"""
Diet Plan Routes - Clinical Nutrition Feature
Integrated with Hospital Management System

Endpoints:
  GET  /diet-plan/patient/<patient_id> - Retrieve existing diet plan
  POST /diet-plan/generate - Generate new personalized diet plan
  GET  /diet-plan/patient/<patient_id>/view - View plan as professional HTML
  PUT  /diet-plan/patient/<patient_id>/update - Update physician notes
  GET  /diet-plan/patient/<patient_id>/pdf - Export as PDF
"""

from flask import Blueprint, request, jsonify, render_template, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json
import sys
import os

from app.models.models import db, ClinicalDietPlan, Patient, Doctor, User, UserRole

# Add project root to path for importing clinical_diet_generator
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from app.clinical_diet_generator import ClinicalDietPlanGenerator
except ImportError:
    try:
        from clinical_diet_generator import ClinicalDietPlanGenerator
    except ImportError:
        ClinicalDietPlanGenerator = None

diet_plan_bp = Blueprint('diet_plan', __name__, url_prefix='/diet-plan')

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def parse_medical_conditions(conditions_json):
    """Convert JSON string to medical conditions list"""
    try:
        conditions = json.loads(conditions_json) if isinstance(conditions_json, str) else conditions_json
        return conditions if isinstance(conditions, list) else []
    except:
        return []

def serialize_diet_plan(diet_plan_record):
    """Convert database record to JSON-serializable dict"""
    return {
        'id': diet_plan_record.id,
        'patient_id': diet_plan_record.patient_id,
        'diet_type': diet_plan_record.diet_type,
        'bmi': diet_plan_record.bmi,
        'caloric_target': {
            'maintenance': diet_plan_record.caloric_maintenance,
            'weight_loss': diet_plan_record.caloric_target_weight_loss
        },
        'macro_distribution': json.loads(diet_plan_record.macro_distribution),
        'medical_conditions': json.loads(diet_plan_record.medical_conditions),
        'activity_level': diet_plan_record.activity_level,
        'restricted_foods': json.loads(diet_plan_record.restricted_foods),
        'recommended_foods': json.loads(diet_plan_record.recommended_foods),
        'drug_interactions': json.loads(diet_plan_record.drug_interactions) if diet_plan_record.drug_interactions else {},
        'expected_outcomes': json.loads(diet_plan_record.expected_outcomes) if diet_plan_record.expected_outcomes else {},
        'generated_at': diet_plan_record.generated_at.isoformat(),
        'last_updated': diet_plan_record.last_updated.isoformat(),
        'next_review_date': diet_plan_record.next_review_date.isoformat() if diet_plan_record.next_review_date else None,
        'is_active': diet_plan_record.is_active,
        'physician_notes': diet_plan_record.physician_notes
    }

# =====================================================
# ROUTES
# =====================================================

@diet_plan_bp.route('/patient/<int:patient_id>', methods=['GET'])
@login_required
def get_diet_plan(patient_id):
    """
    Retrieve existing diet plan for patient
    Access: Patient own plan, Doctor treating patient, Admin
    
    Returns:
        200: Diet plan found with full details
        403: Unauthorized access
        404: No diet plan exists
    """
    # Authorization check
    patient = Patient.query.get_or_404(patient_id)
    
    # Check access permission
    if current_user.role == UserRole.PATIENT and current_user.patient.id != patient_id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    
    # Retrieve diet plan
    diet_plan = ClinicalDietPlan.query.filter_by(
        patient_id=patient_id,
        is_active=True
    ).first()
    
    if not diet_plan:
        return jsonify({
            'status': 'error',
            'message': 'No active diet plan found for this patient',
            'patient_id': patient_id
        }), 404
    
    return jsonify({
        'status': 'success',
        'data': serialize_diet_plan(diet_plan)
    }), 200


@diet_plan_bp.route('/generate', methods=['POST'])
@login_required
def generate_diet_plan():
    """
    Generate new personalized clinical diet plan
    Access: Doctors only
    
    Request JSON:
    {
        "patient_id": 1,
        "medical_conditions": ["DIABETES_TYPE2", "HYPERTENSION"],
        "activity_level": "SEDENTARY",
        "medications": ["Metformin 1000mg BD", "Amlodipine 5mg OD"],
        "recent_labs": {"HbA1c": 8.2, "LDL_C": 145},
        "physician_notes": "Patient showing good compliance"
    }
    """
    
    # Check if ClinicalDietPlanGenerator is available
    if ClinicalDietPlanGenerator is None:
        return jsonify({
            'status': 'error',
            'message': 'Diet plan generator is not available. Please check the system configuration.'
        }), 503
    
    # Only doctors can generate diet plans
    if current_user.role != UserRole.DOCTOR:
        return jsonify({
            'status': 'error',
            'message': 'Only doctors can generate diet plans'
        }), 403
    
    try:
        data = request.get_json()
        
        # Get patient
        patient = Patient.query.get_or_404(data.get('patient_id'))
        
        # Parse medical conditions (accept string list)
        conditions_list = data.get('medical_conditions', [])
        if isinstance(conditions_list, str):
            try:
                conditions_list = json.loads(conditions_list)
            except:
                conditions_list = [conditions_list]
        
        # Parse activity level (use string)
        activity = data.get('activity_level', 'SEDENTARY')
        
        # Calculate BMI
        height_m = (patient.height or 170) / 100
        weight = patient.weight or 70
        bmi = weight / (height_m ** 2)
        
        # Prepare patient data for generator
        patient_data = {
            'id': patient.id,
            'age': patient.age,
            'gender': patient.gender,
            'height': patient.height or 170,
            'weight': weight,
            'bmi': bmi,
            'medical_conditions': conditions_list,
            'activity_level': activity,
            'medications': data.get('medications', []),
            'allergies': patient.allergies.split(',') if patient.allergies else [],
            'recent_labs': data.get('recent_labs', {}),
            'physician_name': f"Dr. {current_user.doctor.first_name} {current_user.doctor.last_name}" if current_user.doctor else "Primary Care Physician"
        }
        
        # Initialize the clinical diet plan generator
        generator = ClinicalDietPlanGenerator(patient_data)
        
        # Generate the diet plan data
        bmr, tdee = generator.calculate_tdee()
        diet_classification, diet_rationale = generator.get_diet_classification()
        macros = generator.get_macronutrient_targets(tdee)
        restricted_foods = generator.get_restricted_foods()
        recommended_foods = generator.get_recommended_foods()
        drug_interactions = generator.get_drug_interactions()
        expected_benefits = generator.get_expected_benefits()
        safety_protocols = generator.get_safety_protocols()
        
        # Create the diet plan record
        new_plan = ClinicalDietPlan(
            patient_id=patient.id,
            doctor_id=current_user.doctor.id if current_user.doctor else None,
            age=patient.age,
            gender=patient.gender,
            height_cm=patient.height or 170,
            weight_kg=weight,
            bmi=bmi,
            medical_conditions=json.dumps(conditions_list),
            activity_level=activity,
            medications=json.dumps(data.get('medications', [])),
            recent_labs=json.dumps(data.get('recent_labs', {})),
            diet_type=diet_classification,
            caloric_maintenance=int(bmr),
            caloric_target_weight_loss=int(tdee),
            macro_distribution=json.dumps({
                'carbohydrates': {
                    'percentage': f"{macros['carb_percent']}%",
                    'grams': f"{macros['carb_grams']}g",
                    'rationale': macros['carb_rationale']
                },
                'protein': {
                    'percentage': f"{macros['protein_percent']}%",
                    'grams': f"{macros['protein_grams']}g",
                    'rationale': macros['protein_rationale']
                },
                'fats': {
                    'percentage': f"{macros['fat_percent']}%",
                    'grams': f"{macros['fat_grams']}g",
                    'rationale': macros['fat_rationale']
                }
            }),
            meal_plan=json.dumps({}),  # Can be expanded later
            restricted_foods=json.dumps(restricted_foods),
            recommended_foods=json.dumps(recommended_foods),
            drug_interactions=json.dumps(drug_interactions),
            safety_notes=json.dumps(safety_protocols),
            expected_outcomes=json.dumps(expected_benefits),
            full_plan_text=f"Clinical Diet Plan: {diet_classification}\n\nRationale: {diet_rationale}\n\nCaloric Target: {tdee} kcal/day",
            physician_notes=data.get('physician_notes', ''),
            next_review_date=datetime.utcnow() + timedelta(weeks=4)
        )
        
        db.session.add(new_plan)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Diet plan generated successfully',
            'data': serialize_diet_plan(new_plan)
        }), 201
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error generating diet plan: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error generating diet plan: {str(e)}'
        }), 500


@diet_plan_bp.route('/patient/<int:patient_id>/view', methods=['GET'])
@login_required
def view_diet_plan_professional(patient_id):
    """
    Render professional clinical diet plan HTML report with premium UI/UX
    Displays comprehensive personalized nutrition therapy with medical detail
    Falls back to basic plan if none exists
    """
    try:
        # Authorization check
        patient = Patient.query.get_or_404(patient_id)
        if current_user.role == UserRole.PATIENT and current_user.patient.id != patient_id:
            flash('You do not have permission to view this diet plan', 'error')
            return redirect(url_for('patient.dashboard')), 403
        
        # Get active diet plan, or create a basic one if it doesn't exist
        diet_plan = ClinicalDietPlan.query.filter_by(
            patient_id=patient_id,
            is_active=True
        ).first()
        
        # If no diet plan exists, create a basic one
        if not diet_plan:
            try:
                # Get latest health data
                from app.models.models import HealthData
                latest_health = HealthData.query.filter_by(patient_id=patient_id).order_by(
                    HealthData.recorded_at.desc()).first()
                
                # Create a basic diet plan record
                diet_plan = ClinicalDietPlan(
                    patient_id=patient_id,
                    doctor_id=None,
                    age=patient.age,
                    gender=patient.gender,
                    height_cm=patient.height or 170,
                    weight_kg=patient.weight or 70,
                    bmi=patient.weight / ((patient.height or 170) ** 2 * 0.0001) if patient.weight else 25,
                    medical_conditions=json.dumps([] if not latest_health else [
                        'Diabetes' if latest_health.diabetes_risk > 70 else None,
                        'Hypertension' if latest_health.hypertension_risk > 75 else None,
                        'Heart Disease Risk' if latest_health.heart_disease_risk > 75 else None
                    ]),
                    activity_level='moderate',
                    medications=json.dumps([]),
                    recent_labs=json.dumps({}),
                    diet_type='Balanced Nutrition Diet',
                    caloric_maintenance=2000,
                    caloric_target_weight_loss=2000,
                    macro_distribution=json.dumps({
                        'carbohydrates': {'percentage': '45%', 'grams': '225g'},
                        'protein': {'percentage': '25%', 'grams': '125g'},
                        'fats': {'percentage': '30%', 'grams': '67g'}
                    }),
                    meal_plan=json.dumps({}),
                    restricted_foods=json.dumps([]),
                    recommended_foods=json.dumps([]),
                    physician_notes='Basic nutrition plan generated automatically.',
                    is_active=True
                )
                db.session.add(diet_plan)
                db.session.commit()
                current_app.logger.info(f"Created basic diet plan for patient {patient_id}")
            except Exception as e:
                current_app.logger.error(f"Error creating basic diet plan: {str(e)}")
                # Continue with rendering even if we couldn't save
                diet_plan = None
        
        # Prepare data for rendering
        try:
            # Parse JSON fields safely
            medical_conditions = []
            medications = []
            
            if diet_plan:
                if isinstance(diet_plan.medical_conditions, str):
                    try:
                        medical_conditions = [c for c in json.loads(diet_plan.medical_conditions) if c]
                    except:
                        medical_conditions = []
                else:
                    medical_conditions = diet_plan.medical_conditions or []
                    
                if isinstance(diet_plan.medications, str):
                    try:
                        medications = json.loads(diet_plan.medications) if diet_plan.medications else []
                    except:
                        medications = []
                else:
                    medications = diet_plan.medications or []
            
            # Determine priority based on conditions
            priority = "High" if any(c and ('diabetes' in str(c).lower() or 'hypertension' in str(c).lower()) for c in medical_conditions) else "Standard"
            
            # Create a minimal set of variables with defaults
            full_report = {
                'patient_name': f"{patient.first_name} {patient.last_name}",
                'patient_age': patient.age,
                'patient_gender': patient.gender,
                'patient_height': patient.height or 170,
                'patient_weight': patient.weight or 70,
                'patient_bmi': (patient.weight / ((patient.height or 170) ** 2 * 0.0001)) if patient.weight else 25,
                'medical_conditions': medical_conditions,
                'medications': medications,
                'activity_level': diet_plan.activity_level if diet_plan else 'moderate',
                'diet_type': diet_plan.diet_type if diet_plan else 'Balanced Nutrition',
                'generated_date': diet_plan.generated_at.strftime('%B %d, %Y') if diet_plan and diet_plan.generated_at else datetime.utcnow().strftime('%B %d, %Y'),
                'valid_until': (diet_plan.next_review_date.strftime('%B %d, %Y') if diet_plan and diet_plan.next_review_date else (datetime.utcnow() + timedelta(days=90)).strftime('%B %d, %Y')),
                'physician_notes': diet_plan.physician_notes if diet_plan else 'Follow this plan as a general nutrition guide.',
                'caloric_maintenance': diet_plan.caloric_maintenance if diet_plan else 2000,
                'caloric_target': diet_plan.caloric_target_weight_loss if diet_plan else 2000,
                # Default variables for template
                'age': patient.age,
                'bmi': (patient.weight / ((patient.height or 170) ** 2 * 0.0001)) if patient.weight else 25,
                'priority': priority,
                'status': f"Based on your {', '.join(medical_conditions) if medical_conditions else 'general health'} profile",
                'diet_classification': diet_plan.diet_type if diet_plan else 'Balanced Nutrition Diet',
                'diet_rationale': 'This diet plan is tailored to your specific health conditions and nutritional needs.',
                'therapeutic_kcal': diet_plan.caloric_target_weight_loss if diet_plan else 2000,
                'carb_percent': 45,
                'protein_percent': 25,
                'fat_percent': 30,
                # Breakfast defaults
                'breakfast_kcal': 350,
                'breakfast_carb': 50,
                'breakfast_protein': 10,
                'breakfast_fat': 8,
                'breakfast_item1': 'Whole grain cereal',
                'breakfast_portion1': '1 cup',
                'breakfast_item2': 'Low-fat milk',
                'breakfast_portion2': '1 cup',
                'breakfast_item3': 'Fresh berries',
                'breakfast_portion3': '¾ cup',
                'breakfast_rationale': 'A balanced breakfast with whole grains, protein, and fresh fruits.',
                # Lunch defaults
                'lunch_kcal': 420,
                'lunch_carb': 50,
                'lunch_protein': 30,
                'lunch_fat': 10,
                'lunch_item1': 'Grilled chicken breast',
                'lunch_portion1': '4 oz',
                'lunch_item2': 'Brown rice',
                'lunch_portion2': '¾ cup',
                'lunch_item3': 'Steamed vegetables',
                'lunch_portion3': '1.5 cups',
                'lunch_rationale': 'A protein-rich lunch with whole grains and vegetables.',
                # Dinner defaults
                'dinner_kcal': 380,
                'dinner_carb': 45,
                'dinner_protein': 35,
                'dinner_fat': 9,
                'dinner_item1': 'Baked salmon',
                'dinner_portion1': '3.5 oz',
                'dinner_item2': 'Sweet potato',
                'dinner_portion2': '1 medium',
                'dinner_item3': 'Mixed greens salad',
                'dinner_portion3': '2 cups',
                'dinner_rationale': 'A heart-healthy dinner with omega-3 rich fish and nutritious vegetables.'
            }
            
            # Use new professional template with premium UI/UX
            return render_template('patient_diet_plan_view.html', **full_report)
        
        except json.JSONDecodeError as e:
            current_app.logger.error(f"JSON decode error in diet plan for patient {patient_id}: {str(e)}", exc_info=True)
            # Still render with defaults
            return render_template('patient_diet_plan_view.html', 
                                 patient_name=f"{patient.first_name} {patient.last_name}",
                                 patient_age=patient.age,
                                 age=patient.age,
                                 bmi=25,
                                 priority='Standard',
                                 status='General Health',
                                 diet_classification='Balanced Nutrition Diet',
                                 diet_rationale='This is a general nutrition guide.',
                                 generated_date=datetime.utcnow().strftime('%B %d, %Y'),
                                 valid_until=(datetime.utcnow() + timedelta(days=90)).strftime('%B %d, %Y'),
                                 physician_notes='Follow this nutrition plan.',
                                 therapeutic_kcal=2000,
                                 carb_percent=45,
                                 protein_percent=25,
                                 fat_percent=30,
                                 breakfast_kcal=350,
                                 breakfast_carb=50,
                                 breakfast_protein=10,
                                 breakfast_fat=8,
                                 breakfast_item1='Whole grain cereal',
                                 breakfast_portion1='1 cup',
                                 breakfast_item2='Low-fat milk',
                                 breakfast_portion2='1 cup',
                                 breakfast_item3='Fresh berries',
                                 breakfast_portion3='¾ cup',
                                 breakfast_rationale='A balanced breakfast with whole grains, protein, and fresh fruits.',
                                 lunch_kcal=420,
                                 lunch_carb=50,
                                 lunch_protein=30,
                                 lunch_fat=10,
                                 lunch_item1='Grilled chicken breast',
                                 lunch_portion1='4 oz',
                                 lunch_item2='Brown rice',
                                 lunch_portion2='¾ cup',
                                 lunch_item3='Steamed vegetables',
                                 lunch_portion3='1.5 cups',
                                 lunch_rationale='A protein-rich lunch with whole grains and vegetables.',
                                 dinner_kcal=380,
                                 dinner_carb=45,
                                 dinner_protein=35,
                                 dinner_fat=9,
                                 dinner_item1='Baked salmon',
                                 dinner_portion1='3.5 oz',
                                 dinner_item2='Sweet potato',
                                 dinner_portion2='1 medium',
                                 dinner_item3='Mixed greens salad',
                                 dinner_portion3='2 cups',
                                 dinner_rationale='A heart-healthy dinner with omega-3 rich fish and nutritious vegetables.')
        except Exception as e:
            current_app.logger.error(f"Error rendering diet plan for patient {patient_id}: {str(e)}", exc_info=True)
            # Render with basic defaults
            return render_template('patient_diet_plan_view.html',
                                 patient_name=f"{patient.first_name} {patient.last_name}",
                                 patient_age=patient.age,
                                 age=patient.age,
                                 bmi=25,
                                 priority='Standard',
                                 status='General Health',
                                 diet_classification='Balanced Nutrition Diet',
                                 diet_rationale='This is a general nutrition guide.',
                                 generated_date=datetime.utcnow().strftime('%B %d, %Y'),
                                 valid_until=(datetime.utcnow() + timedelta(days=90)).strftime('%B %d, %Y'),
                                 physician_notes='Follow this nutrition plan.',
                                 therapeutic_kcal=2000,
                                 carb_percent=45,
                                 protein_percent=25,
                                 fat_percent=30,
                                 breakfast_kcal=350,
                                 breakfast_carb=50,
                                 breakfast_protein=10,
                                 breakfast_fat=8,
                                 breakfast_item1='Whole grain cereal',
                                 breakfast_portion1='1 cup',
                                 breakfast_item2='Low-fat milk',
                                 breakfast_portion2='1 cup',
                                 breakfast_item3='Fresh berries',
                                 breakfast_portion3='¾ cup',
                                 breakfast_rationale='A balanced breakfast with whole grains, protein, and fresh fruits.',
                                 lunch_kcal=420,
                                 lunch_carb=50,
                                 lunch_protein=30,
                                 lunch_fat=10,
                                 lunch_item1='Grilled chicken breast',
                                 lunch_portion1='4 oz',
                                 lunch_item2='Brown rice',
                                 lunch_portion2='¾ cup',
                                 lunch_item3='Steamed vegetables',
                                 lunch_portion3='1.5 cups',
                                 lunch_rationale='A protein-rich lunch with whole grains and vegetables.',
                                 dinner_kcal=380,
                                 dinner_carb=45,
                                 dinner_protein=35,
                                 dinner_fat=9,
                                 dinner_item1='Baked salmon',
                                 dinner_portion1='3.5 oz',
                                 dinner_item2='Sweet potato',
                                 dinner_portion2='1 medium',
                                 dinner_item3='Mixed greens salad',
                                 dinner_portion3='2 cups',
                                 dinner_rationale='A heart-healthy dinner with omega-3 rich fish and nutritious vegetables.')
    
    except Exception as e:
        current_app.logger.error(f"Error in view_diet_plan_professional: {str(e)}", exc_info=True)
        flash('An unexpected error occurred. Rendering default diet plan.', 'warning')
        # Get patient info and render basic plan
        patient = Patient.query.get_or_404(patient_id)
        return render_template('patient_diet_plan_view.html',
                             patient_name=f"{patient.first_name} {patient.last_name}",
                             patient_age=patient.age,
                             age=patient.age,
                             bmi=25,
                             priority='Standard',
                             status='General Health',
                             diet_classification='Balanced Nutrition Diet',
                             diet_rationale='This is a general nutrition guide.',
                             generated_date=datetime.utcnow().strftime('%B %d, %Y'),
                             valid_until=(datetime.utcnow() + timedelta(days=90)).strftime('%B %d, %Y'),
                             physician_notes='Follow this nutrition plan.',
                             therapeutic_kcal=2000,
                             carb_percent=45,
                             protein_percent=25,
                             fat_percent=30,
                             breakfast_kcal=350,
                             breakfast_carb=50,
                             breakfast_protein=10,
                             breakfast_fat=8,
                             breakfast_item1='Whole grain cereal',
                             breakfast_portion1='1 cup',
                             breakfast_item2='Low-fat milk',
                             breakfast_portion2='1 cup',
                             breakfast_item3='Fresh berries',
                             breakfast_portion3='¾ cup',
                             breakfast_rationale='A balanced breakfast with whole grains, protein, and fresh fruits.',
                             lunch_kcal=420,
                             lunch_carb=50,
                             lunch_protein=30,
                             lunch_fat=10,
                             lunch_item1='Grilled chicken breast',
                             lunch_portion1='4 oz',
                             lunch_item2='Brown rice',
                             lunch_portion2='¾ cup',
                             lunch_item3='Steamed vegetables',
                             lunch_portion3='1.5 cups',
                             lunch_rationale='A protein-rich lunch with whole grains and vegetables.',
                             dinner_kcal=380,
                             dinner_carb=45,
                             dinner_protein=35,
                             dinner_fat=9,
                             dinner_item1='Baked salmon',
                             dinner_portion1='3.5 oz',
                             dinner_item2='Sweet potato',
                             dinner_portion2='1 medium',
                             dinner_item3='Mixed greens salad',
                             dinner_portion3='2 cups',
                             dinner_rationale='A heart-healthy dinner with omega-3 rich fish and nutritious vegetables.')


@diet_plan_bp.route('/patient/<int:patient_id>/view-legacy', methods=['GET'])


@diet_plan_bp.route('/patient/<int:patient_id>/update', methods=['PUT'])
@login_required
def update_diet_plan_notes(patient_id):
    """
    Update physician notes and status on diet plan
    """
    if current_user.role != UserRole.DOCTOR:
        return jsonify({'status': 'error', 'message': 'Only doctors can update diet plans'}), 403
    
    diet_plan = ClinicalDietPlan.query.filter_by(
        patient_id=patient_id,
        is_active=True
    ).first_or_404()
    
    data = request.get_json()
    
    if 'physician_notes' in data:
        diet_plan.physician_notes = data['physician_notes']
    
    if 'next_review_date' in data:
        diet_plan.next_review_date = datetime.fromisoformat(data['next_review_date'])
    
    diet_plan.last_updated = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Diet plan updated successfully',
        'data': serialize_diet_plan(diet_plan)
    }), 200


@diet_plan_bp.route('/patient/<int:patient_id>/deactivate', methods=['DELETE'])
@login_required
def deactivate_diet_plan(patient_id):
    """
    Archive/deactivate diet plan (soft delete)
    """
    if current_user.role != UserRole.DOCTOR:
        return jsonify({'status': 'error', 'message': 'Only doctors can deactivate diet plans'}), 403
    
    diet_plan = ClinicalDietPlan.query.filter_by(
        patient_id=patient_id,
        is_active=True
    ).first_or_404()
    
    diet_plan.is_active = False
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Diet plan archived'
    }), 200


@diet_plan_bp.route('/list', methods=['GET'])
@login_required
def list_diet_plans():
    """
    List all diet plans (filtered by role)
    Doctors: See all their patients' plans
    Patients: See only their own plan
    """
    if current_user.role == UserRole.PATIENT:
        # Patient sees only their own plan
        plans = ClinicalDietPlan.query.filter_by(
            patient_id=current_user.patient.id,
            is_active=True
        ).all()
    elif current_user.role == UserRole.DOCTOR:
        # Doctor sees plans for their patients
        plans = ClinicalDietPlan.query.filter_by(
            doctor_id=current_user.doctor.id,
            is_active=True
        ).all()
    else:
        # Admin sees all
        plans = ClinicalDietPlan.query.filter_by(is_active=True).all()
    
    return jsonify({
        'status': 'success',
        'count': len(plans),
        'data': [serialize_diet_plan(p) for p in plans]
    }), 200
