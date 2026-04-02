"""
Enhanced Chatbot Features for Hospital Management System
- Symptom tracking across conversations
- Medical history context
- Appointment suggestions
- Emergency detection
"""

import re
from datetime import datetime
from app.services.ai_service import LocalAIService

class EnhancedChatbot:
    """Enhanced medical chatbot with context awareness"""
    
    # Emergency keywords that trigger immediate action
    EMERGENCY_KEYWORDS = [
        'chest pain', 'heart attack', 'stroke', 'can\'t breathe', 
        'difficulty breathing', 'severe bleeding', 'unconscious',
        'suicide', 'overdose', 'poisoning', 'severe burn',
        'head injury', 'broken bone', 'severe pain'
    ]
    
    # Symptoms that might require appointments
    APPOINTMENT_TRIGGERS = [
        'persistent', 'chronic', 'recurring', 'weeks', 'months',
        'getting worse', 'not improving', 'need to see doctor'
    ]
    
    @staticmethod
    def detect_emergency(message):
        """Detect if message contains emergency keywords"""
        message_lower = message.lower()
        for keyword in EnhancedChatbot.EMERGENCY_KEYWORDS:
            if keyword in message_lower:
                return True
        return False
    
    @staticmethod
    def should_suggest_appointment(message):
        """Check if user should be suggested to book appointment"""
        message_lower = message.lower()
        for trigger in EnhancedChatbot.APPOINTMENT_TRIGGERS:
            if trigger in message_lower:
                return True
        return False
    
    @staticmethod
    def get_enhanced_response(user_message, user_history=None):
        """
        Get AI response with additional context and suggestions
        
        Args:
            user_message: Current user message
            user_history: Optional list of previous messages from this user
        
        Returns:
            Enhanced response with suggestions
        """
        # Check for emergency
        if EnhancedChatbot.detect_emergency(user_message):
            return {
                'response': "🚨 **EMERGENCY ALERT** 🚨\n\nBased on your symptoms, this could be a medical emergency. Please:\n\n1. Call emergency services (911) immediately\n2. Do NOT wait for an appointment\n3. Go to the nearest Emergency Room\n\nYour health and safety are the top priority. Act now!",
                'type': 'emergency',
                'suggestion': 'emergency_services'
            }
        
        # Get AI response
        ai_response = LocalAIService.get_ai_response(user_message)
        
        # Add context if user has history
        context_note = ""
        if user_history and len(user_history) > 0:
            context_note = "\n\n💡 *I see you've asked about similar symptoms before. Tracking your health over time is important.*"
        
        # Check if should suggest appointment
        suggestion = None
        if EnhancedChatbot.should_suggest_appointment(user_message):
            suggestion = 'book_appointment'
            context_note += "\n\n📅 **Suggestion:** Your symptoms seem persistent. Consider booking an appointment with a doctor for a thorough evaluation."
        
        return {
            'response': ai_response + context_note,
            'type': 'normal',
            'suggestion': suggestion,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def extract_symptoms(message):
        """Extract potential symptoms from user message"""
        # Common symptom patterns
        symptom_patterns = [
            r'(?:have|experiencing|feeling)\s+(?:a\s+)?(\w+(?:\s+\w+)?)',
            r'my\s+(\w+(?:\s+\w+)?)\s+(?:hurts|aches|is\s+painful)',
            r'(\w+)\s+pain',
        ]
        
        symptoms = []
        for pattern in symptom_patterns:
            matches = re.findall(pattern, message.lower())
            symptoms.extend(matches)
        
        return list(set(symptoms))  # Remove duplicates
