"""
Integration Module: Enhanced Diet Plan Engine
Connects EnhancedDietPlanEngine with existing Flask routes

This module provides helper functions to integrate the new 15-feature diet engine
with existing Flask application without breaking changes.
"""

from app.modules.diet_plan_engine_enhanced import EnhancedDietPlanEngine, validate_patient_profile
import os


class DietPlanIntegration:
    """Helper class to integrate enhanced diet engine with Flask app."""
    
    def __init__(self):
        """Initialize the enhanced diet plan engine."""
        # Determine data directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(os.path.dirname(current_dir), 'data')
        
        self.engine = EnhancedDietPlanEngine(data_dir=data_dir)
    
    def generate_plan(self, patient_data: dict) -> dict:
        """
        Generate a complete enhanced diet plan.
        
        Args:
            patient_data: Dictionary with patient information
                - age: int
                - gender: str
                - height_cm: float
                - weight_kg: float
                - primary_condition: str
                - secondary_conditions: list
                - medications: list
                - activity_level: str
                - recent_labs: dict (optional)
                - eating_speed: str (optional)
        
        Returns:
            Complete diet plan dictionary with all 15 features
        """
        try:
            # Validate patient data
            is_valid, errors = validate_patient_profile(patient_data)
            if not is_valid:
                return {
                    'success': False,
                    'error': f"Validation failed: {', '.join(errors)}"
                }
            
            # Generate plan using enhanced engine
            diet_plan = self.engine.generate_diet_plan(patient_data)
            
            return {
                'success': True,
                'diet_plan': diet_plan,
                'message': 'Diet plan generated successfully with 15 innovative features'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_organ_benefits(self, diet_protocol: str) -> list:
        """Get organ benefits for a specific diet protocol."""
        return self.engine._get_organ_benefits(
            {'primary_condition': 'General Health'},
            diet_protocol
        )
    
    def get_food_effects(self, diet_protocol: str, meal_plan: dict) -> list:
        """Get food effect classifications."""
        return self.engine._get_food_effect_classification(diet_protocol, meal_plan)
    
    def get_simple_rules(self, diet_protocol: str) -> list:
        """Get simplified 3-rule version of diet."""
        return self.engine._get_simple_rules(
            {'primary_condition': 'General Health'},
            diet_protocol
        )
    
    def get_lab_insights(self, labs: dict, diet_protocol: str) -> list:
        """Get lab-report linked justifications."""
        return self.engine._get_lab_linked_justification(
            labs,
            {'primary_condition': 'General Health'},
            diet_protocol
        )


# Singleton instance for use throughout the app
_diet_integration = None


def get_diet_integration() -> DietPlanIntegration:
    """Get or create singleton diet plan integration instance."""
    global _diet_integration
    if _diet_integration is None:
        _diet_integration = DietPlanIntegration()
    return _diet_integration
