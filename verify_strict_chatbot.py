from app.ml_models.strict_medical_chatbot import StrictMedicalChatbot
import sys
import io

# Force UTF-8 for output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_chatbot():
    bot = StrictMedicalChatbot("medical_data.json")
    
    tests = [
        ("doctor i have a fever", True),
        ("fever", True),
        ("i have fever with asthma", True),
        ("unsupported query", False)
    ]
    
    for query, should_found in tests:
        response = bot.get_response(query)
        print(f"Query: {query}")
        print(f"Response:\n{response}")
        print("-" * 30)

if __name__ == "__main__":
    test_chatbot()
