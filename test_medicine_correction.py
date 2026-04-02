"""Quick test for the RapidFuzz medicine correction engine."""
import sys
sys.path.insert(0, r'c:\Users\harip\OneDrive\Desktop\hospital')

from app.services.voice_service import (
    correct_medicine_name, correct_full_text, 
    get_medicine_suggestions, parse_medicines_from_text,
    RAPIDFUZZ_AVAILABLE
)

print(f"RapidFuzz available: {RAPIDFUZZ_AVAILABLE}")
print("=" * 60)

# Test 1: Single word corrections
test_words = [
    "parasitamol",
    "paracitmol",  
    "amoxicilin",
    "ceptirizine",
    "ibuprofin",
    "azithromicin",
    "pantaprazole",
    "metformine",
    "atorvastatine",
    "omeprezole",
    "Paracetamol",
    "UnknownDrug123",
]

print("\nTest 1: Single Word Corrections")
print("-" * 50)
for word in test_words:
    result = correct_medicine_name(word)
    status = "CORRECTED" if result["corrected"] else ("EXACT" if result["confidence"] == "exact" else "NO MATCH")
    print(f"  {word:20s} -> {result['name']:20s} [{result['confidence']:8s}] {status}")

# Test 2: Full text correction
print("\nTest 2: Full Text Correction")
print("-" * 50)
test_texts = [
    "parasitamol 500 mg twice daily",
    "amoxicilin 250 mg after food and ceptirizine 10 mg once daily",
    "ibuprofin 400 mg thrice daily for 5 days",
]

for text in test_texts:
    result = correct_full_text(text)
    print(f"\n  Original:  {result['original']}")
    print(f"  Corrected: {result['corrected_text']}")
    if result['corrections']:
        for c in result['corrections']:
            print(f"    Fix: '{c['original']}' -> '{c['corrected']}' ({c['confidence']})")

# Test 3: Medicine suggestions
print("\n\nTest 3: Suggestions for 'parasitamol'")
print("-" * 50)
suggestions = get_medicine_suggestions("parasitamol", limit=5)
for s in suggestions:
    print(f"    -> {s['name']} ({s['score']}%)")

# Test 4: Full parsing
print("\n\nTest 4: Full Medicine Parsing")
print("-" * 50)
test_parse = "parasitamol 500 mg twice daily after food, amoxicilin 250 mg thrice daily for 7 days"
medicines = parse_medicines_from_text(test_parse)
print(f"  Input: {test_parse}")
print(f"  Parsed {len(medicines)} medicines:")
for m in medicines:
    corrected_flag = " (CORRECTED)" if m.get("corrected") else ""
    print(f"    Medicine: {m['name']}{corrected_flag}")
    print(f"    Dosage:   {m['dosage']}")
    print(f"    Freq:     {m['frequency']}")
    print(f"    Duration: {m['duration']}")
    print(f"    Inst:     {m['instructions']}")
    print()

print("\nAll tests completed!")
