"""
STEP 7: Test locally (Interactive testing)
"""

from chatbot import chat

print("=" * 80)
print("MEDICAL CHATBOT TEST")
print("=" * 80)
print("\nTesting dataset retrieval and AI expansion...")
print("\nType 'exit' to quit\n")

# Pre-defined test queries to show correct behavior
test_queries = [
    "normal heart rate",
    "fever",
    "chest pain",
    "heart pain",
    "stroke symptoms",
]

print("🧪 RUNNING PREDEFINED TEST QUERIES:\n")

for query in test_queries:
    print(f"\n{'─'*80}")
    response = chat(query)
    print(f"\n{response}\n")
    print(f"{'─'*80}")

print("\n\n🔄 INTERACTIVE MODE - Ask your own questions:\n")

while True:
    try:
        user_input = input("You: ").strip()
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        if not user_input:
            continue
        
        response = chat(user_input)
        print(f"\nChatbot:\n{response}\n")
    
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        break
    except Exception as e:
        print(f"❌ Error: {e}\n")
