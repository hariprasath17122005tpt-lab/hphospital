from app.ml_models.strict_medical_chatbot import StrictMedicalChatbot
import json

def test_chatbot():
    bot = StrictMedicalChatbot("medical_data.json")
    
    tests = [
        "doctor i have a fever",
        "fever",
        "i have fever with asthma",
        "unsupported query"
    ]
    
    results = []
    for query in tests:
        response = bot.get_response(query)
        results.append({
            "query": query,
            "response": response
        })
    
    with open("test_results_final.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("Test completed. Results in test_results_final.json")

if __name__ == "__main__":
    test_chatbot()
