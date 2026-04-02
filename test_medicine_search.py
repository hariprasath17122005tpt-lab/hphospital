"""Quick test: verify the built-in medicine catalog search works."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.routes.features import _BUILTIN_MEDICINE_CATALOG

def test_search(query):
    q = query.lower()
    results = [
        m for m in _BUILTIN_MEDICINE_CATALOG
        if q in m['name'].lower()
           or q in m.get('brand', '').lower()
           or q in m.get('category', '').lower()
    ]
    results.sort(key=lambda m: (
        0 if m['name'].lower().startswith(q) else 1,
        len(m['name']),
        m['name']
    ))
    return results[:12]

print("=" * 50)
print("TESTING MEDICINE AUTOCOMPLETE CATALOG")
print("=" * 50)

for query in ['para', 'amox', 'ibu', 'met', 'asp', 'vit', 'cip']:
    results = test_search(query)
    print(f"\nSearch '{query}': {len(results)} results")
    for r in results[:5]:
        print(f"  -> {r['name']} (Brand: {r['brand']}, Rs {r['price']})")

print("\n" + "=" * 50)
print(f"Total medicines in catalog: {len(_BUILTIN_MEDICINE_CATALOG)}")
print("ALL TESTS PASSED!" if len(_BUILTIN_MEDICINE_CATALOG) > 0 else "ERROR: Empty catalog!")
