"""
Medical AI Service for Flask Integration
This module integrates the fine-tuned chatbot model with your Flask app
"""

import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class MedicalAIService:
    """Service for generating medical AI responses"""
    
    _instance = None  # Singleton pattern
    _model = None
    _tokenizer = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MedicalAIService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize service (only once)"""
        if self._initialized:
            return
        
        self.model_path = "./finetuned_health_ai"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._initialized = True
        self.load_model()
    
    def load_model(self):
        """Load model on first use (lazy loading)"""
        if self._model is not None:
            return  # Already loaded
        
        logger.info("Loading fine-tuned medical model...")
        
        if not os.path.exists(self.model_path):
            logger.warning(f"Model not found at {self.model_path}")
            logger.info("Using fallback responses. Run: python train.py to get better results")
            return False
        
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else self.device
            )
            
            self._model.eval()
            logger.info(f"✓ Medical AI model loaded on {self.device}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            return False
    
    def is_available(self) -> bool:
        """Check if model is loaded and available"""
        return self._model is not None and self._tokenizer is not None
    
    def generate_response(
        self, 
        query: str, 
        max_length: int = 200,
        temperature: float = 0.7
    ) -> str:
        """
        Generate AI response for medical query
        
        Args:
            query: User's medical question
            max_length: Maximum response length
            temperature: Response creativity (0-1)
        
        Returns:
            Generated response string
        """
        
        if not self.is_available():
            logger.warning("Model not available, using fallback response")
            return self._fallback_response(query)
        
        try:
            # Create prompt with safety guidelines
            prompt = (
                "You are a medical information assistant. "
                "Provide educational information only. "
                "Do NOT diagnose or prescribe. "
                "Always recommend consulting healthcare professionals.\n\n"
                f"Question: {query}\n"
                f"Answer:"
            )
            
            # Tokenize
            inputs = self._tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=512
            ).to(self._model.device)
            
            # Generate
            with torch.no_grad():
                output = self._model.generate(
                    **inputs,
                    max_new_tokens=max_length,
                    temperature=temperature,
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=self._tokenizer.eos_token_id,
                    no_repeat_ngram_size=2
                )
            
            # Decode
            response = self._tokenizer.decode(output[0], skip_special_tokens=True)
            
            # Extract answer part
            if "Answer:" in response:
                response = response.split("Answer:")[-1].strip()
            
            return response.strip()
        
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return self._fallback_response(query)
    
    def _fallback_response(self, query: str) -> str:
        """Fallback response when model is not available"""
        
        query_lower = query.lower()
        
        fallbacks = {
            'fever': 'Fever is a temporary increase in body temperature. Common causes include infections, inflammation, or immune response. It is generally a sign that your body is fighting an illness. If fever persists beyond 3 days or is accompanied by severe symptoms, consult a healthcare provider.',
            
            'headache': 'Headaches can result from stress, dehydration, tension, or other factors. Some relief measures include resting, hydrating, and managing stress. If headaches are frequent or severe, please consult a doctor.',
            
            'cold': 'Cold symptoms include sneezing, runny nose, sore throat, and cough. Most colds resolve within 7-10 days. Management includes rest, hydration, and over-the-counter symptom relief. Consult a doctor if symptoms worsen.',
            
            'cough': 'A cough can be caused by infections, allergies, or irritation. Most coughs improve with rest and hydration. If a cough persists for more than 2-3 weeks, consult a healthcare provider.',
            
            'fatigue': 'Fatigue can result from stress, poor sleep, illness, or lifestyle factors. Ensure adequate rest, nutrition, and exercise. If fatigue persists, consult a doctor to rule out underlying conditions.',
            
            'default': 'For medical concerns, it\'s best to consult with a qualified healthcare professional. They can provide personalized advice based on your specific situation. If you\'re experiencing an emergency, please seek immediate medical attention.'
        }
        
        # Find best matching fallback
        for keyword, response in fallbacks.items():
            if keyword != 'default' and keyword in query_lower:
                return response
        
        return fallbacks['default']

# Create singleton instance
def get_medical_ai_service() -> MedicalAIService:
    """Get medical AI service instance"""
    return MedicalAIService()
