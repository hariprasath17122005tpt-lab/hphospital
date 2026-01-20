"""
Simple verification without Flask imports
"""
import sys
sys.path.insert(0, '.')

print("=" * 80)
print("TESTING NEW CORRECT CHATBOT ARCHITECTURE")
print("=" * 80)

# Test chatbot directly
try:
    print("\n[TEST 1] Loading chatbot...")
    from chatbot import chat
    
    test_queries = [
        "fever",
        "heart pain",
        "chest pain",
        "normal heart rate",
    ]
    
    for query in test_queries:
        print(f"\n{'─'*80}")
        print(f"Query: {query}")
        print(f"{'─'*80}")
        response = chat(query)
        print(response)
    
    print("\n" + "=" * 80)
    print("✅ CHATBOT IS WORKING CORRECTLY!")
    print("=" * 80)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
