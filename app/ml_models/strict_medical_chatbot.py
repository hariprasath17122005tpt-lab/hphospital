import json
import os
import re

class StrictMedicalChatbot:
    def __init__(self, dataset_path="medical_data.json"):
        self.dataset_path = dataset_path
        self.dataset = {}
        self.fallback_message = "💊 This medical query is not available in our health database. Please consult a qualified healthcare professional."
        self.load_dataset()

    def load_dataset(self):
        """Load the JSON dataset once at startup."""
        if not os.path.exists(self.dataset_path):
            print(f"Warning: Dataset file {self.dataset_path} not found.")
            return

        try:
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                self.dataset = json.load(f)
            print(f"Dataset loaded successfully with {len(self.dataset)} entries.")
        except Exception as e:
            print(f"Error loading dataset: {e}")

    def normalize_input(self, text):
        """
        Normalize user input:
        1. Lowercase
        2. Remove special characters
        3. Remove common conversational fillers (stop words)
        """
        if not text:
            return ""
            
        # Lowercase
        text = text.lower().strip()
        
        # Remove special characters
        text = re.sub(r'[^\w\s]', '', text)
        
        # Common fillers to ignore for better matching
        fillers = [
            "doctor", "please", "help", "me", "with", "i", "have", "a", "an", "the", 
            "tell", "me", "about", "what", "is", "can", "you", "give", "advice", "on"
        ]
        
        words = text.split()
        normalized_words = [w for w in words if w not in fillers]
        
        # Return both the full normalized text AND the keyword-only version for matching
        full_normalized = " ".join(words)
        keyword_version = " ".join(normalized_words)
        
        return full_normalized, keyword_version

    def get_response(self, user_input):
        """
        Strictly retrieves an answer from the dataset.
        No LLM or generation.
        """
        if not self.dataset:
            return self.fallback_message

        full_norm, keyword_norm = self.normalize_input(user_input)
        
        # 1. Try exact match on full normalized input
        if full_norm in self.dataset:
            return self.dataset[full_norm]["output"]
            
        # 2. Try match on keyword version
        if keyword_norm in self.dataset:
            return self.dataset[keyword_norm]["output"]
            
        # 3. Try to find if any key is contained in the normalized input (greedy match)
        # This helps if the user says "doctor i have a fever" and the key is just "fever"
        for key in sorted(self.dataset.keys(), key=len, reverse=True):
            if key in full_norm or key in keyword_norm:
                return self.dataset[key]["output"]

        return self.fallback_message

# Example Usage
if __name__ == "__main__":
    chatbot = StrictMedicalChatbot()
    
    test_inputs = [
        "fever",
        "doctor i have a fever",
        "i have fever with asthma",
        "can you help me with a headache",
        "something unknown"
    ]
    
    for inp in test_inputs:
        print(f"Input: {inp}")
        print(f"Output:\n{chatbot.get_response(inp)}")
        print("-" * 50)
