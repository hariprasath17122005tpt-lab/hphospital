"""
Diet Plan Routes for Flask Application

Provides endpoints for generating and displaying personalized diet plans
using the clinical-grade diet planning engine.
"""

from flask import Blueprint, render_template, request, jsonify, session
from app.modules.diet_plan_engine import DietPlanEngine, validate_patient_profile
import os

# Create Blueprint
diet_plan_bp = Blueprint('diet_plan', __name__, url_prefix='/diet')

# Initialize Diet Plan Engine
current_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(os.path.dirname(current_dir), 'data')
diet_engine = DietPlanEngine(data_dir=data_dir)


@diet_plan_bp.route('/generate', methods=['POST'])
def generate_diet_plan():
    """
    Generate a personalized diet plan based on patient profile.
    
    Expects JSON payload with patient profile data.
    Returns the generated diet plan as JSON or renders the diet plan template.
    """
    try:
        # Get patient profile from request
        patient_profile = request.get_json()
        
        if not patient_profile:
            return jsonify({'error': 'No patient profile provided'}), 400
        
        # Validate patient profile
        is_valid, errors = validate_patient_profile(patient_profile)
        if not is_valid:
            return jsonify({'error': 'Invalid patient profile', 'details': errors}), 400
        
        # Generate diet plan
        diet_plan = diet_engine.generate_diet_plan(patient_profile)
        
        # Store in session for rendering
        session['current_diet_plan'] = diet_plan
        
        # Return diet plan for rendering
        return render_template('patient/diet_plan_display.html', diet_plan=diet_plan)
    
    except Exception as e:
        return jsonify({'error': f'Error generating diet plan: {str(e)}'}), 500


@diet_plan_bp.route('/view', methods=['GET'])
def view_diet_plan():
    """View the current user's diet plan."""
    try:
        # Get diet plan from session
        diet_plan = session.get('current_diet_plan')
        
        if not diet_plan:
            return render_template('patient/diet_plan_display.html', 
                                 diet_plan={'error': 'No diet plan available'}), 404
        
        return render_template('patient/diet_plan_display.html', diet_plan=diet_plan)
    
    except Exception as e:
        return jsonify({'error': f'Error viewing diet plan: {str(e)}'}), 500


@diet_plan_bp.route('/api/generate', methods=['POST'])
def api_generate_diet_plan():
    """
    API endpoint to generate diet plan.
    Returns JSON response instead of HTML.
    """
    try:
        patient_profile = request.get_json()
        
        if not patient_profile:
            return jsonify({'error': 'No patient profile provided'}), 400
        
        is_valid, errors = validate_patient_profile(patient_profile)
        if not is_valid:
            return jsonify({'error': 'Invalid patient profile', 'details': errors}), 400
        
        diet_plan = diet_engine.generate_diet_plan(patient_profile)
        
        return jsonify({'success': True, 'diet_plan': diet_plan}), 200
    
    except Exception as e:
        return jsonify({'error': f'Error generating diet plan: {str(e)}'}), 500


@diet_plan_bp.route('/protocols', methods=['GET'])
def get_diet_protocols():
    """Get available diet protocols."""
    try:
        protocols = {}
        for name, protocol in diet_engine.diet_protocols.items():
            protocols[name] = {
                'name': protocol['name'],
                'target_conditions': protocol['target_conditions'],
                'primary_focus': protocol.get('primary_focus', '')
            }
        
        return jsonify({'success': True, 'protocols': protocols}), 200
    
    except Exception as e:
        return jsonify({'error': f'Error retrieving protocols: {str(e)}'}), 500


@diet_plan_bp.route('/conditions', methods=['GET'])
def get_medical_conditions():
    """Get available medical conditions."""
    try:
        conditions = set()
        for rule_key, rule in diet_engine.condition_rules.items():
            if 'name' in rule:
                conditions.add(rule['name'])
        
        # Also add from diet protocols
        for protocol in diet_engine.diet_protocols.values():
            conditions.update(protocol['target_conditions'])
        
        return jsonify({'success': True, 'conditions': sorted(list(conditions))}), 200
    
    except Exception as e:
        return jsonify({'error': f'Error retrieving conditions: {str(e)}'}), 500


@diet_plan_bp.route('/test', methods=['GET', 'POST'])
def test_diet_plan():
    """
    Test endpoint for diet plan generation.
    Can be used for demo/testing purposes.
    """
    if request.method == 'POST':
        try:
            patient_profile = request.get_json()
            diet_plan = diet_engine.generate_diet_plan(patient_profile)
            return render_template('patient/diet_plan_display.html', diet_plan=diet_plan)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # GET - show test form
    return render_template('patient/diet_plan_test.html')
