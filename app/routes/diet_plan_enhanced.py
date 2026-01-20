"""
Enhanced Diet Plan Routes - Smart Diet Plan with 15 Innovative Features
Integrated with Hospital Management System

This module adds enhanced routes that use the new 15-feature diet engine.
It maintains backward compatibility with existing routes while providing
significantly improved functionality.

Endpoints:
  GET  /diet-plan/enhanced/<patient_id> - Retrieve enhanced diet plan
  POST /diet-plan/enhanced/generate - Generate enhanced diet plan
  GET  /diet-plan/enhanced/test - Test form for diet plan generation
"""

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
import json

from app.models.models import db, ClinicalDietPlan, Patient, Doctor, User, UserRole
from app.modules.diet_plan_integration import get_diet_integration

diet_plan_enhanced_bp = Blueprint('diet_plan_enhanced', __name__, url_prefix='/diet-plan/enhanced')


@diet_plan_enhanced_bp.route('/test', methods=['GET'])
def test_form():
    """Display test form for diet plan generation."""
    return render_template('patient/diet_plan_test_enhanced.html')


@diet_plan_enhanced_bp.route('/generate', methods=['POST'])
@login_required
def generate_enhanced_plan():
    """
    Generate enhanced personalized clinical diet plan with 15 features.
    
    Request JSON:
    {
        "age": 58,
        "gender": "Male",
        "height_cm": 175,
        "weight_kg": 92,
        "primary_condition": "Hypertension",
        "secondary_conditions": ["Obesity"],
        "medications": ["Lisinopril"],
        "activity_level": "Moderate",
        "recent_labs": {"BP": "150/95", "Sodium": "145"},
        "eating_speed": "Moderate",
        "patient_id": 1
    }
    """
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        
        # Convert string values to appropriate types
        patient_data = {
            'age': int(data.get('age', 50)),
            'gender': data.get('gender', 'Male'),
            'height_cm': float(data.get('height_cm', 170)),
            'weight_kg': float(data.get('weight_kg', 70)),
            'primary_condition': data.get('primary_condition', 'General Health'),
            'secondary_conditions': json.loads(data.get('secondary_conditions', '[]')) if isinstance(data.get('secondary_conditions'), str) else data.get('secondary_conditions', []),
            'medications': json.loads(data.get('medications', '[]')) if isinstance(data.get('medications'), str) else data.get('medications', []),
            'activity_level': data.get('activity_level', 'Moderate'),
            'recent_labs': json.loads(data.get('recent_labs', '{}')) if isinstance(data.get('recent_labs'), str) else data.get('recent_labs', {}),
            'eating_speed': data.get('eating_speed', 'Moderate')
        }
        
        # Generate diet plan using enhanced engine
        integration = get_diet_integration()
        result = integration.generate_plan(patient_data)
        
        if not result['success']:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to generate diet plan')
            }), 400
        
        diet_plan = result['diet_plan']
        
        # If patient_id provided, save to database
        patient_id = data.get('patient_id')
        if patient_id:
            try:
                patient = Patient.query.get(patient_id)
                if patient:
                    # Save enhanced plan to database
                    db_plan = ClinicalDietPlan(
                        patient_id=patient_id,
                        doctor_id=current_user.doctor.id if hasattr(current_user, 'doctor') and current_user.doctor else None,
                        age=patient_data['age'],
                        gender=patient_data['gender'],
                        height_cm=patient_data['height_cm'],
                        weight_kg=patient_data['weight_kg'],
                        bmi=diet_plan.get('patient_bmi', 0),
                        activity_level=patient_data['activity_level'],
                        medical_conditions=json.dumps(patient_data.get('secondary_conditions', [])),
                        medications=json.dumps(patient_data.get('medications', [])),
                        diet_type=diet_plan.get('protocol_name', 'Enhanced Diet Plan'),
                        macro_distribution=json.dumps({}),  # Can be enhanced later
                        restricted_foods=json.dumps(diet_plan.get('foods_to_avoid', [])),
                        recommended_foods=json.dumps(list(diet_plan.get('food_explanations', {}).keys())),
                        drug_interactions=json.dumps(diet_plan.get('medication_safety_notes', [])),
                        expected_outcomes=json.dumps(diet_plan.get('health_benefits', {})),
                        is_active=True,
                        generated_at=datetime.utcnow(),
                        next_review_date=datetime.utcnow() + timedelta(days=30),
                        physician_notes=f"Enhanced diet plan generated with 15 innovative features. Confidence: {diet_plan.get('14_confidence_score', 85)}%"
                    )
                    db.session.add(db_plan)
                    db.session.commit()
            except Exception as e:
                print(f"Error saving to database: {e}")
                # Continue even if database save fails
        
        return jsonify({
            'success': True,
            'diet_plan': diet_plan,
            'message': 'Enhanced diet plan generated successfully'
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Server error: {str(e)}"
        }), 500


@diet_plan_enhanced_bp.route('/patient/<int:patient_id>/view', methods=['GET'])
@login_required
def view_enhanced_plan(patient_id):
    """View enhanced diet plan for a patient."""
    
    # Authorization
    patient = Patient.query.get_or_404(patient_id)
    
    # Check permissions
    if current_user.role == UserRole.PATIENT and current_user.patient.id != patient_id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('patient.dashboard'))
    
    # Get the active diet plan
    diet_plan_record = ClinicalDietPlan.query.filter_by(
        patient_id=patient_id,
        is_active=True
    ).first()
    
    if not diet_plan_record:
        flash('No active diet plan found for this patient', 'warning')
        return redirect(url_for('patient.dashboard'))
    
    # Reconstruct patient data for template
    patient_data = {
        'age': diet_plan_record.age,
        'gender': diet_plan_record.gender,
        'height_cm': diet_plan_record.height_cm,
        'weight_kg': diet_plan_record.weight_kg,
        'primary_condition': 'General Health',  # Get from patient history if available
        'secondary_conditions': json.loads(diet_plan_record.medical_conditions or '[]'),
        'medications': json.loads(diet_plan_record.medications or '[]'),
        'activity_level': diet_plan_record.activity_level,
        'recent_labs': {}
    }
    
    # Generate fresh plan data for display
    integration = get_diet_integration()
    result = integration.generate_plan(patient_data)
    
    if result['success']:
        plan = result['diet_plan']
        return render_template('patient/diet_plan_enhanced.html', 
                             plan=plan, 
                             patient=patient)
    else:
        flash('Error generating diet plan display', 'danger')
        return redirect(url_for('patient.dashboard'))


@diet_plan_enhanced_bp.route('/api/protocols', methods=['GET'])
def get_available_protocols():
    """Get list of available diet protocols."""
    protocols = {
        'DASH': {
            'name': 'DASH Diet (Dietary Approaches to Stop Hypertension)',
            'description': 'Best for hypertension, heart disease prevention',
            'duration': '8+ weeks for best results'
        },
        'MEDITERRANEAN': {
            'name': 'Mediterranean Diet',
            'description': 'Best for cardiovascular health, longevity',
            'duration': '12+ weeks for benefits'
        },
        'LOW_GLYCEMIC': {
            'name': 'Low Glycemic Index Diet',
            'description': 'Best for diabetes, blood sugar control',
            'duration': '4+ weeks for HbA1c improvement'
        },
        'RENAL_FRIENDLY': {
            'name': 'Renal-Friendly Diet',
            'description': 'Best for chronic kidney disease management',
            'duration': 'Lifelong management'
        },
        'CELIAC_FRIENDLY': {
            'name': 'Gluten-Free Diet',
            'description': 'Best for celiac disease and gluten sensitivity',
            'duration': 'Lifelong requirement'
        }
    }
    
    return jsonify({
        'success': True,
        'protocols': protocols
    }), 200


@diet_plan_enhanced_bp.route('/api/conditions', methods=['GET'])
def get_supported_conditions():
    """Get list of supported medical conditions."""
    conditions = {
        'primary': [
            'Hypertension',
            'Heart Disease',
            'Diabetes Type 2',
            'Chronic Kidney Disease',
            'Celiac Disease',
            'High Cholesterol',
            'Obesity',
            'GERD'
        ],
        'secondary': [
            'Prediabetes',
            'High Blood Pressure',
            'Hyperlipidemia',
            'CKD',
            'Gluten Sensitivity',
            'Overweight',
            'Metabolic Syndrome',
            'Thyroid Disorder'
        ]
    }
    
    return jsonify({
        'success': True,
        'conditions': conditions
    }), 200


@diet_plan_enhanced_bp.route('/api/labs-reference', methods=['GET'])
def get_lab_reference_ranges():
    """Get reference lab ranges for diet interpretation."""
    ranges = {
        'BP': {
            'unit': 'mmHg',
            'normal': '< 120/80',
            'elevated': '120-129 / < 80',
            'stage1': '130-139 / 80-89',
            'stage2': '>= 140/90'
        },
        'HbA1c': {
            'unit': '%',
            'normal': '< 5.7',
            'prediabetic': '5.7-6.4',
            'diabetic': '>= 6.5',
            'target_diabetic': '< 7'
        },
        'Total_Cholesterol': {
            'unit': 'mg/dL',
            'desirable': '< 200',
            'borderline': '200-239',
            'high': '>= 240'
        },
        'LDL': {
            'unit': 'mg/dL',
            'optimal': '< 100',
            'near_optimal': '100-129',
            'borderline': '130-159',
            'high': '160-189',
            'very_high': '>= 190'
        }
    }
    
    return jsonify({
        'success': True,
        'lab_ranges': ranges
    }), 200


from datetime import timedelta

# Register error handlers
@diet_plan_enhanced_bp.errorhandler(404)
def not_found_error(error):
    return jsonify({'success': False, 'error': 'Resource not found'}), 404


@diet_plan_enhanced_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500
