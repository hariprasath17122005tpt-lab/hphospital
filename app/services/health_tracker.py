"""
Health Metrics Tracking Service
Tracks patient vitals, symptoms, and wellness over time
"""

from datetime import datetime, timedelta
from app.models.models import db
from sqlalchemy import func

class HealthTracker:
    """Service for tracking and analyzing patient health metrics"""
    
    @staticmethod
    def log_symptom(patient_id, symptom_name, severity=None, notes=None):
        """
        Log a symptom reported by patient
        
        Args:
            patient_id: Patient ID
            symptom_name: Name of symptom
            severity: 1-10 scale (optional)
            notes: Additional notes
        """
        from app.models.models import SymptomLog
        
        symptom = SymptomLog(
            patient_id=patient_id,
            symptom_name=symptom_name,
            severity=severity,
            notes=notes,
            logged_at=datetime.utcnow()
        )
        db.session.add(symptom)
        db.session.commit()
        return symptom
    
    @staticmethod
    def get_recent_symptoms(patient_id, days=30):
        """Get symptoms logged in last N days"""
        from app.models.models import SymptomLog
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        symptoms = SymptomLog.query.filter(
            SymptomLog.patient_id == patient_id,
            SymptomLog.logged_at >= cutoff_date
        ).order_by(SymptomLog.logged_at.desc()).all()
        
        return symptoms
    
    @staticmethod
    def analyze_symptom_trends(patient_id):
        """
        Analyze symptom patterns for a patient
        
        Returns:
            Dictionary with analysis results
        """
        from app.models.models import SymptomLog
        
        # Get last 90 days
        cutoff = datetime.utcnow() - timedelta(days=90)
        symptoms = SymptomLog.query.filter(
            SymptomLog.patient_id == patient_id,
            SymptomLog.logged_at >= cutoff
        ).all()
        
        if not symptoms:
            return {
                'total_symptoms': 0,
                'most_common': None,
                'trend': 'stable',
                'alerts': []
            }
        
        # Count by symptom name
        symptom_counts = {}
        for s in symptoms:
            symptom_counts[s.symptom_name] = symptom_counts.get(s.symptom_name, 0) + 1
        
        most_common = max(symptom_counts, key=symptom_counts.get)
        
        # Check for concerning patterns
        alerts = []
        if symptom_counts.get('headache', 0) > 10:
            alerts.append('Frequent headaches - consider neurological consultation')
        if symptom_counts.get('chest pain', 0) > 0:
            alerts.append('Chest pain reported - cardiac evaluation recommended')
        
        return {
            'total_symptoms': len(symptoms),
            'most_common': most_common,
            'symptom_counts': symptom_counts,
            'alerts': alerts,
            'last_reported': symptoms[0].logged_at if symptoms else None
        }
    
    @staticmethod
    def get_wellness_score(patient_id):
        """
        Calculate overall wellness score (0-100)
        Based on recent vitals and symptom frequency
        """
        from app.models.models import HealthData, SymptomLog
        
        score = 100  # Start with perfect score
        
        # Check recent vitals
        latest_vitals = HealthData.query.filter_by(
            patient_id=patient_id
        ).order_by(HealthData.date.desc()).first()
        
        if latest_vitals:
            # Deduct points for abnormal vitals
            if latest_vitals.heart_rate > 100 or latest_vitals.heart_rate < 60:
                score -= 10
            if latest_vitals.systolic_bp > 140 or latest_vitals.systolic_bp < 90:
                score -= 15
            if latest_vitals.temperature and latest_vitals.temperature > 99.5:
                score -= 10
        
        # Check symptom frequency
        recent_symptoms = HealthTracker.get_recent_symptoms(patient_id, days=7)
        symptom_penalty = min(len(recent_symptoms) * 5, 30)  # Max 30 points for symptoms
        score -= symptom_penalty
        
        return max(0, min(100, score))  # Clamp between 0-100
