#!/usr/bin/env python3
"""Patch features.py to add built-in medicine catalog for autocomplete fallback."""

import os

FEATURES_PATH = os.path.join(os.path.dirname(__file__), 'app', 'routes', 'features.py')

CATALOG_BLOCK = '''
# ---------------------------------------------------------------------------
# Built-in medicine catalog - autocomplete fallback when DB is empty.
# Each entry mirrors the JSON shape returned by the search endpoint.
# ---------------------------------------------------------------------------
_BUILTIN_MEDICINE_CATALOG = [
    # --- Analgesics / Antipyretics ---
    {'id': 0, 'name': 'Paracetamol 500mg', 'brand': 'Calpol', 'category': 'Analgesic', 'price': 10, 'stock': 0, 'manufacturer': 'GlaxoSmithKline'},
    {'id': 0, 'name': 'Paracetamol 650mg', 'brand': 'Dolo 650', 'category': 'Analgesic', 'price': 12, 'stock': 0, 'manufacturer': 'Micro Labs'},
    {'id': 0, 'name': 'Paracetamol Syrup', 'brand': 'Crocin Syrup', 'category': 'Analgesic', 'price': 45, 'stock': 0, 'manufacturer': 'GlaxoSmithKline'},
    {'id': 0, 'name': 'Ibuprofen 400mg', 'brand': 'Brufen', 'category': 'NSAID', 'price': 20, 'stock': 0, 'manufacturer': 'Abbott'},
    {'id': 0, 'name': 'Diclofenac 50mg', 'brand': 'Voltaren', 'category': 'NSAID', 'price': 22, 'stock': 0, 'manufacturer': 'Novartis'},
    {'id': 0, 'name': 'Aspirin 75mg', 'brand': 'Ecosprin', 'category': 'Antiplatelet', 'price': 5, 'stock': 0, 'manufacturer': 'USV Ltd'},
    {'id': 0, 'name': 'Aspirin 150mg', 'brand': 'Ecosprin', 'category': 'Antiplatelet', 'price': 8, 'stock': 0, 'manufacturer': 'USV Ltd'},
    {'id': 0, 'name': 'Naproxen 250mg', 'brand': 'Naprosyn', 'category': 'NSAID', 'price': 18, 'stock': 0, 'manufacturer': 'Roche'},
    {'id': 0, 'name': 'Tramadol 50mg', 'brand': 'Ultram', 'category': 'Opioid Analgesic', 'price': 30, 'stock': 0, 'manufacturer': 'Johnson and Johnson'},
    # --- Antibiotics ---
    {'id': 0, 'name': 'Amoxicillin 500mg', 'brand': 'Amoxil', 'category': 'Antibiotic', 'price': 45, 'stock': 0, 'manufacturer': 'Pfizer'},
    {'id': 0, 'name': 'Amoxicillin + Clavulanate', 'brand': 'Augmentin', 'category': 'Antibiotic', 'price': 95, 'stock': 0, 'manufacturer': 'GlaxoSmithKline'},
    {'id': 0, 'name': 'Azithromycin 500mg', 'brand': 'Zithromax', 'category': 'Antibiotic', 'price': 85, 'stock': 0, 'manufacturer': 'Pfizer'},
    {'id': 0, 'name': 'Azithromycin 250mg', 'brand': 'Azee', 'category': 'Antibiotic', 'price': 65, 'stock': 0, 'manufacturer': 'Cipla'},
    {'id': 0, 'name': 'Ciprofloxacin 500mg', 'brand': 'Cipro', 'category': 'Antibiotic', 'price': 35, 'stock': 0, 'manufacturer': 'Bayer'},
    {'id': 0, 'name': 'Cephalexin 500mg', 'brand': 'Keflex', 'category': 'Antibiotic', 'price': 55, 'stock': 0, 'manufacturer': 'Eli Lilly'},
    {'id': 0, 'name': 'Cefixime 200mg', 'brand': 'Suprax', 'category': 'Antibiotic', 'price': 70, 'stock': 0, 'manufacturer': 'Lupin'},
    {'id': 0, 'name': 'Doxycycline 100mg', 'brand': 'Vibramycin', 'category': 'Antibiotic', 'price': 40, 'stock': 0, 'manufacturer': 'Pfizer'},
    {'id': 0, 'name': 'Metronidazole 400mg', 'brand': 'Flagyl', 'category': 'Antibiotic', 'price': 15, 'stock': 0, 'manufacturer': 'Sanofi'},
    {'id': 0, 'name': 'Levofloxacin 500mg', 'brand': 'Levaquin', 'category': 'Antibiotic', 'price': 65, 'stock': 0, 'manufacturer': 'Johnson and Johnson'},
    {'id': 0, 'name': 'Clindamycin 300mg', 'brand': 'Cleocin', 'category': 'Antibiotic', 'price': 50, 'stock': 0, 'manufacturer': 'Pfizer'},
    # --- Antidiabetics ---
    {'id': 0, 'name': 'Metformin 500mg', 'brand': 'Glucophage', 'category': 'Antidiabetic', 'price': 25, 'stock': 0, 'manufacturer': 'Bristol-Myers Squibb'},
    {'id': 0, 'name': 'Metformin 1000mg', 'brand': 'Glucophage XR', 'category': 'Antidiabetic', 'price': 40, 'stock': 0, 'manufacturer': 'Bristol-Myers Squibb'},
    {'id': 0, 'name': 'Glimepiride 2mg', 'brand': 'Amaryl', 'category': 'Antidiabetic', 'price': 35, 'stock': 0, 'manufacturer': 'Sanofi'},
    {'id': 0, 'name': 'Glipizide 5mg', 'brand': 'Glucotrol', 'category': 'Antidiabetic', 'price': 28, 'stock': 0, 'manufacturer': 'Pfizer'},
    {'id': 0, 'name': 'Insulin Aspart', 'brand': 'NovoRapid', 'category': 'Antidiabetic', 'price': 350, 'stock': 0, 'manufacturer': 'Novo Nordisk'},
    {'id': 0, 'name': 'Insulin Glargine', 'brand': 'Lantus', 'category': 'Antidiabetic', 'price': 450, 'stock': 0, 'manufacturer': 'Sanofi'},
    {'id': 0, 'name': 'Sitagliptin 100mg', 'brand': 'Januvia', 'category': 'Antidiabetic', 'price': 120, 'stock': 0, 'manufacturer': 'Merck'},
    # --- Cardiovascular / Antihypertensives ---
    {'id': 0, 'name': 'Amlodipine 5mg', 'brand': 'Norvasc', 'category': 'Antihypertensive', 'price': 20, 'stock': 0, 'manufacturer': 'Pfizer'},
    {'id': 0, 'name': 'Amlodipine 10mg', 'brand': 'Norvasc', 'category': 'Antihypertensive', 'price': 30, 'stock': 0, 'manufacturer': 'Pfizer'},
    {'id': 0, 'name': 'Atenolol 50mg', 'brand': 'Tenormin', 'category': 'Beta Blocker', 'price': 15, 'stock': 0, 'manufacturer': 'AstraZeneca'},
    {'id': 0, 'name': 'Atorvastatin 10mg', 'brand': 'Lipitor', 'category': 'Statin', 'price': 35, 'stock': 0, 'manufacturer': 'Pfizer'},
    {'id': 0, 'name': 'Atorvastatin 20mg', 'brand': 'Lipitor', 'category': 'Statin', 'price': 45, 'stock': 0, 'manufacturer': 'Pfizer'},
    {'id': 0, 'name': 'Losartan 50mg', 'brand': 'Cozaar', 'category': 'ARB', 'price': 25, 'stock': 0, 'manufacturer': 'Merck'},
    {'id': 0, 'name': 'Telmisartan 40mg', 'brand': 'Micardis', 'category': 'ARB', 'price': 30, 'stock': 0, 'manufacturer': 'Boehringer Ingelheim'},
    {'id': 0, 'name': 'Lisinopril 10mg', 'brand': 'Prinivil', 'category': 'ACE Inhibitor', 'price': 30, 'stock': 0, 'manufacturer': 'Merck'},
    {'id': 0, 'name': 'Enalapril 5mg', 'brand': 'Vasotec', 'category': 'ACE Inhibitor', 'price': 22, 'stock': 0, 'manufacturer': 'Merck'},
    {'id': 0, 'name': 'Rosuvastatin 10mg', 'brand': 'Crestor', 'category': 'Statin', 'price': 55, 'stock': 0, 'manufacturer': 'AstraZeneca'},
    {'id': 0, 'name': 'Clopidogrel 75mg', 'brand': 'Plavix', 'category': 'Antiplatelet', 'price': 40, 'stock': 0, 'manufacturer': 'Sanofi'},
    {'id': 0, 'name': 'Warfarin 5mg', 'brand': 'Coumadin', 'category': 'Anticoagulant', 'price': 18, 'stock': 0, 'manufacturer': 'Bristol-Myers Squibb'},
    {'id': 0, 'name': 'Furosemide 40mg', 'brand': 'Lasix', 'category': 'Diuretic', 'price': 12, 'stock': 0, 'manufacturer': 'Sanofi'},
    {'id': 0, 'name': 'Hydrochlorothiazide 25mg', 'brand': 'HydroDiuril', 'category': 'Diuretic', 'price': 10, 'stock': 0, 'manufacturer': 'Merck'},
    # --- Gastrointestinal ---
    {'id': 0, 'name': 'Omeprazole 20mg', 'brand': 'Prilosec', 'category': 'PPI', 'price': 18, 'stock': 0, 'manufacturer': 'AstraZeneca'},
    {'id': 0, 'name': 'Pantoprazole 40mg', 'brand': 'Pantop', 'category': 'PPI', 'price': 22, 'stock': 0, 'manufacturer': 'Sun Pharma'},
    {'id': 0, 'name': 'Ranitidine 150mg', 'brand': 'Zantac', 'category': 'H2 Blocker', 'price': 12, 'stock': 0, 'manufacturer': 'GlaxoSmithKline'},
    {'id': 0, 'name': 'Domperidone 10mg', 'brand': 'Motilium', 'category': 'Antiemetic', 'price': 15, 'stock': 0, 'manufacturer': 'Johnson and Johnson'},
    {'id': 0, 'name': 'Ondansetron 4mg', 'brand': 'Zofran', 'category': 'Antiemetic', 'price': 25, 'stock': 0, 'manufacturer': 'GlaxoSmithKline'},
    {'id': 0, 'name': 'Loperamide 2mg', 'brand': 'Imodium', 'category': 'Antidiarrheal', 'price': 8, 'stock': 0, 'manufacturer': 'Johnson and Johnson'},
    {'id': 0, 'name': 'ORS Powder', 'brand': 'Electral', 'category': 'Rehydration', 'price': 12, 'stock': 0, 'manufacturer': 'FDC Ltd'},
    # --- Respiratory ---
    {'id': 0, 'name': 'Salbutamol Inhaler', 'brand': 'Asthalin', 'category': 'Bronchodilator', 'price': 120, 'stock': 0, 'manufacturer': 'Cipla'},
    {'id': 0, 'name': 'Montelukast 10mg', 'brand': 'Singulair', 'category': 'Leukotriene Inhibitor', 'price': 35, 'stock': 0, 'manufacturer': 'Merck'},
    {'id': 0, 'name': 'Cetirizine 10mg', 'brand': 'Zyrtec', 'category': 'Antihistamine', 'price': 8, 'stock': 0, 'manufacturer': 'Johnson and Johnson'},
    {'id': 0, 'name': 'Levocetirizine 5mg', 'brand': 'Xyzal', 'category': 'Antihistamine', 'price': 10, 'stock': 0, 'manufacturer': 'Sanofi'},
    {'id': 0, 'name': 'Fexofenadine 120mg', 'brand': 'Allegra', 'category': 'Antihistamine', 'price': 15, 'stock': 0, 'manufacturer': 'Sanofi'},
    {'id': 0, 'name': 'Loratadine 10mg', 'brand': 'Claritin', 'category': 'Antihistamine', 'price': 12, 'stock': 0, 'manufacturer': 'Bayer'},
    {'id': 0, 'name': 'Dextromethorphan Syrup', 'brand': 'Benadryl-DR', 'category': 'Antitussive', 'price': 55, 'stock': 0, 'manufacturer': 'Johnson and Johnson'},
    {'id': 0, 'name': 'Ambroxol 30mg', 'brand': 'Mucolite', 'category': 'Mucolytic', 'price': 18, 'stock': 0, 'manufacturer': 'Sun Pharma'},
    # --- Vitamins / Supplements ---
    {'id': 0, 'name': 'Vitamin D3 60000 IU', 'brand': 'D3 Must', 'category': 'Supplement', 'price': 30, 'stock': 0, 'manufacturer': 'Mankind'},
    {'id': 0, 'name': 'Vitamin B12', 'brand': 'Methylcobalamin', 'category': 'Supplement', 'price': 25, 'stock': 0, 'manufacturer': 'Abbott'},
    {'id': 0, 'name': 'Vitamin C 500mg', 'brand': 'Limcee', 'category': 'Supplement', 'price': 15, 'stock': 0, 'manufacturer': 'Abbott'},
    {'id': 0, 'name': 'Iron + Folic Acid', 'brand': 'Autrin', 'category': 'Supplement', 'price': 35, 'stock': 0, 'manufacturer': 'GlaxoSmithKline'},
    {'id': 0, 'name': 'Calcium + Vitamin D3', 'brand': 'Shelcal', 'category': 'Supplement', 'price': 40, 'stock': 0, 'manufacturer': 'Torrent'},
    {'id': 0, 'name': 'Multivitamin Tablet', 'brand': 'Zincovit', 'category': 'Supplement', 'price': 50, 'stock': 0, 'manufacturer': 'Apex Labs'},
    # --- Dermatology ---
    {'id': 0, 'name': 'Fluconazole 150mg', 'brand': 'Diflucan', 'category': 'Antifungal', 'price': 25, 'stock': 0, 'manufacturer': 'Pfizer'},
    {'id': 0, 'name': 'Clotrimazole Cream', 'brand': 'Candid', 'category': 'Antifungal', 'price': 35, 'stock': 0, 'manufacturer': 'Glenmark'},
    {'id': 0, 'name': 'Betamethasone Cream', 'brand': 'Betnovate', 'category': 'Corticosteroid', 'price': 40, 'stock': 0, 'manufacturer': 'GlaxoSmithKline'},
    {'id': 0, 'name': 'Mupirocin Ointment', 'brand': 'T-Bact', 'category': 'Topical Antibiotic', 'price': 80, 'stock': 0, 'manufacturer': 'GlaxoSmithKline'},
    # --- CNS / Neurology ---
    {'id': 0, 'name': 'Gabapentin 300mg', 'brand': 'Neurontin', 'category': 'Anticonvulsant', 'price': 45, 'stock': 0, 'manufacturer': 'Pfizer'},
    {'id': 0, 'name': 'Pregabalin 75mg', 'brand': 'Lyrica', 'category': 'Neuropathic', 'price': 55, 'stock': 0, 'manufacturer': 'Pfizer'},
    {'id': 0, 'name': 'Alprazolam 0.5mg', 'brand': 'Xanax', 'category': 'Anxiolytic', 'price': 15, 'stock': 0, 'manufacturer': 'Pfizer'},
    {'id': 0, 'name': 'Sertraline 50mg', 'brand': 'Zoloft', 'category': 'SSRI', 'price': 35, 'stock': 0, 'manufacturer': 'Pfizer'},
    {'id': 0, 'name': 'Escitalopram 10mg', 'brand': 'Lexapro', 'category': 'SSRI', 'price': 40, 'stock': 0, 'manufacturer': 'Lundbeck'},
    # --- Endocrine ---
    {'id': 0, 'name': 'Levothyroxine 50mcg', 'brand': 'Thyronorm', 'category': 'Thyroid', 'price': 20, 'stock': 0, 'manufacturer': 'Abbott'},
    {'id': 0, 'name': 'Levothyroxine 100mcg', 'brand': 'Thyronorm', 'category': 'Thyroid', 'price': 25, 'stock': 0, 'manufacturer': 'Abbott'},
    {'id': 0, 'name': 'Prednisolone 5mg', 'brand': 'Omnacortil', 'category': 'Corticosteroid', 'price': 12, 'stock': 0, 'manufacturer': 'Macleods'},
    {'id': 0, 'name': 'Dexamethasone 0.5mg', 'brand': 'Decadron', 'category': 'Corticosteroid', 'price': 10, 'stock': 0, 'manufacturer': 'Merck'},
    # --- Muscle Relaxants ---
    {'id': 0, 'name': 'Cyclobenzaprine 10mg', 'brand': 'Flexeril', 'category': 'Muscle Relaxant', 'price': 25, 'stock': 0, 'manufacturer': 'Johnson and Johnson'},
    {'id': 0, 'name': 'Thiocolchicoside 4mg', 'brand': 'Myoril', 'category': 'Muscle Relaxant', 'price': 30, 'stock': 0, 'manufacturer': 'Sanofi'},
    # --- Ophthalmology ---
    {'id': 0, 'name': 'Ciprofloxacin Eye Drops', 'brand': 'Ciplox Eye', 'category': 'Ophthalmic', 'price': 25, 'stock': 0, 'manufacturer': 'Cipla'},
    {'id': 0, 'name': 'Artificial Tears', 'brand': 'Refresh Tears', 'category': 'Ophthalmic', 'price': 60, 'stock': 0, 'manufacturer': 'Allergan'},
    # --- Other Common ---
    {'id': 0, 'name': 'Acyclovir 400mg', 'brand': 'Zovirax', 'category': 'Antiviral', 'price': 35, 'stock': 0, 'manufacturer': 'GlaxoSmithKline'},
    {'id': 0, 'name': 'Hydroxychloroquine 200mg', 'brand': 'HCQS', 'category': 'Antimalarial', 'price': 20, 'stock': 0, 'manufacturer': 'Ipca Labs'},
    {'id': 0, 'name': 'Tamsulosin 0.4mg', 'brand': 'Flomax', 'category': 'Alpha Blocker', 'price': 30, 'stock': 0, 'manufacturer': 'Boehringer Ingelheim'},
]
'''

def patch():
    with open(FEATURES_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if already patched
    if '_BUILTIN_MEDICINE_CATALOG = [' in content:
        print("Already patched! _BUILTIN_MEDICINE_CATALOG exists.")
        return

    # Find the insertion point: right after the blueprint declaration line
    marker = "features_bp = Blueprint('features', __name__, url_prefix='/features')"
    idx = content.find(marker)
    if idx < 0:
        print("ERROR: Could not find features_bp Blueprint line!")
        return

    # Insert after the marker line (find end of that line)
    end_of_line = content.index('\n', idx)
    before = content[:end_of_line + 1]
    after = content[end_of_line + 1:]

    new_content = before + CATALOG_BLOCK + after

    with open(FEATURES_PATH, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("SUCCESS: Inserted _BUILTIN_MEDICINE_CATALOG into features.py")
    count = CATALOG_BLOCK.count("'id': 0")
    print(f"Catalog has {count} medicines")


if __name__ == '__main__':
    patch()
