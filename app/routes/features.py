from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.models.models import db, Medicine, BloodInventory, Bed, DoctorEvent, Staff, PatientCheckIn, Patient, Doctor
from app.routes.auth import patient_required
from sqlalchemy import or_, case, func
import warnings
warnings.filterwarnings('ignore')

features_bp = Blueprint('features', __name__, url_prefix='/features')

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

def _append_bulk_pharmacy_items(catalog, item_count=5000):
    """
    Expand fallback pharmacy catalog with a massive variety of realistic medicines.
    (Tablets, capsules, syrups, tonics, drops, ointments, injections, inhalers, etc.)
    """
    drug_profiles = [
        # Format: (Category, Base Name, [Brands], [Forms], [Strengths])
        ('Analgesic', 'Paracetamol', ['Dolo', 'Calpol', 'Crocin', 'Pacimol', 'Tylenol', 'P-500'], ['Tablet', 'Syrup', 'Drops', 'Injection', 'Infusion', 'Suspension'], ['500mg', '650mg', '125mg/5ml', '100mg/ml', '250mg/5ml']),
        ('Analgesic', 'Ibuprofen', ['Brufen', 'Advil', 'Ibugesic', 'Combiflam', 'Motrin'], ['Tablet', 'Capsule', 'Syrup', 'Gel', 'Suspension'], ['200mg', '400mg', '600mg', '100mg/5ml', '5%']),
        ('NSAID', 'Diclofenac', ['Voveran', 'Voltaren', 'Reactin', 'Fenak', 'Dynapar'], ['Tablet', 'Injection', 'Gel', 'Patch', 'Suppository'], ['50mg', '100mg', '75mg/ml', '1%', '100mg SR']),
        ('NSAID', 'Aceclofenac', ['Zerodol', 'Hifenac', 'Acenac', 'Dolokind'], ['Tablet', 'Gel', 'Injection'], ['100mg', '200mg SR', '1.5%']),
        ('NSAID', 'Naproxen', ['Naprosyn', 'Aleve', 'Xenobid', 'Naprox'], ['Tablet', 'Suspension', 'Gel'], ['250mg', '500mg', '10%']),

        ('Antibiotic', 'Amoxicillin', ['Novamox', 'Mox', 'Amoxil', 'Almox', 'Wymox'], ['Capsule', 'Tablet', 'Syrup', 'Drops', 'Dry Syrup'], ['250mg', '500mg', '125mg', '125mg/5ml']),
        ('Antibiotic', 'Amoxicillin + Clavulanate', ['Augmentin', 'Clavam', 'Moxikind-CV', 'Advent', 'Mega-CV'], ['Tablet', 'Syrup', 'Injection', 'Dry Syrup'], ['375mg', '625mg', '1.2g', '228.5mg']),
        ('Antibiotic', 'Azithromycin', ['Azee', 'Azithral', 'Zithromax', 'Zady', 'Azax'], ['Tablet', 'Suspension', 'Injection', 'Syrup'], ['250mg', '500mg', '100mg/5ml', '200mg/5ml']),
        ('Antibiotic', 'Cefpodoxime', ['Monocef-O', 'Cepodem', 'Gudcef', 'Macpod'], ['Tablet', 'Syrup', 'Drops', 'Dry Syrup'], ['50mg', '100mg', '200mg', '50mg/5ml']),
        ('Antibiotic', 'Cefixime', ['Zifi', 'Taxim-O', 'Mahacef', 'Cefolac', 'Omnicef'], ['Tablet', 'Syrup', 'Drops', 'Dry Suspension'], ['100mg', '200mg', '50mg/5ml']),
        ('Antibiotic', 'Doxycycline', ['Doxypal', 'Minocycline', 'Vibramycin', 'Dox', 'Doxy-1'], ['Tablet', 'Capsule', 'Injection'], ['100mg', '200mg']),

        ('Gastrointestinal', 'Pantoprazole', ['Pan', 'Pantop', 'Pantocid', 'Pentab', 'P20'], ['Tablet', 'Injection', 'Capsule'], ['20mg', '40mg']),
        ('Gastrointestinal', 'Omeprazole', ['Omez', 'Omecip', 'Omee', 'Nocid'], ['Capsule', 'Injection'], ['20mg', '40mg']),
        ('Gastrointestinal', 'Rabeprazole', ['Rablet', 'Rabicip', 'Cyra', 'Happi', 'Razo'], ['Tablet', 'Capsule', 'Injection'], ['20mg']),
        ('Gastrointestinal', 'Ondansetron', ['Emeset', 'Zofran', 'Vomistop', 'Periset'], ['Tablet', 'Syrup', 'Injection', 'Drops'], ['4mg', '8mg', '2mg/ml']),
        ('Gastrointestinal', 'Domperidone', ['Domstal', 'Motilium', 'Vomitrol'], ['Tablet', 'Syrup', 'Drops'], ['10mg', '1mg/ml']),
        ('Gastrointestinal', 'Lactulose', ['Duphalac', 'Looz', 'Lactifiber', 'Smuth'], ['Solution', 'Syrup', 'Granules'], ['10g/15ml', '150ml', '200ml']),
        ('Gastrointestinal', 'Antacid Gel', ['Digene', 'Gelusil', 'Mucaine', 'Polycrol'], ['Gel', 'Syrup', 'Tablet'], ['200ml', '110ml', 'Standard']),

        ('Antidiabetic', 'Metformin', ['Glycomet', 'Glucophage', 'Cetapin', 'Okamet'], ['Tablet'], ['500mg', '850mg', '1000mg', '500mg SR']),
        ('Antidiabetic', 'Glimepiride', ['Amaryl', 'Glimer', 'Zoryl', 'Glimy'], ['Tablet'], ['1mg', '2mg', '3mg', '4mg']),
        ('Antidiabetic', 'Teneligliptin', ['Zita', 'Tenefit', 'Teneza', 'Dynaglipt'], ['Tablet'], ['20mg']),
        ('Antidiabetic', 'Sitagliptin', ['Januvia', 'Istavel', 'Zita-D'], ['Tablet'], ['50mg', '100mg']),
        ('Antidiabetic', 'Insulin', ['Lantus', 'Novomix', 'Mixtard', 'Humalog'], ['Injection', 'Pen', 'Cartridge'], ['100 IU/ml', '300 IU/ml']),

        ('Antihypertensive', 'Amlodipine', ['Amlokind', 'Stamlo', 'Norvasc', 'Amlodac'], ['Tablet'], ['2.5mg', '5mg', '10mg']),
        ('Antihypertensive', 'Telmisartan', ['Telma', 'Tazloc', 'Micardis', 'Tsart', 'Telmikind'], ['Tablet'], ['20mg', '40mg', '80mg']),
        ('Antihypertensive', 'Losartan', ['Losar', 'Cozaar', 'Repace', 'Covance'], ['Tablet'], ['25mg', '50mg']),
        ('Antihypertensive', 'Metoprolol', ['Metolar', 'Seloken', 'Prolomet', 'Starpress'], ['Tablet', 'Injection'], ['25mg', '50mg', '12.5mg']),

        ('Cardiovascular', 'Atorvastatin', ['Atorva', 'Lipikind', 'Lipitor', 'Tonact', 'Storvas'], ['Tablet'], ['10mg', '20mg', '40mg', '80mg']),
        ('Cardiovascular', 'Rosuvastatin', ['Rosuvas', 'Rozavel', 'Crestor', 'Rozucor'], ['Tablet'], ['5mg', '10mg', '20mg', '40mg']),
        ('Cardiovascular', 'Clopidogrel', ['Deplatt', 'Clavix', 'Plavix', 'Clopilet'], ['Tablet'], ['75mg']),
        ('Cardiovascular', 'Aspirin', ['Ecosprin', 'Aspirin', 'Disprin', 'Loprin'], ['Tablet'], ['75mg', '150mg', '325mg']),

        ('Respiratory', 'Levosalbutamol + Ipratropium', ['Duolin'], ['Inhaler', 'Respules', 'Rotacaps', 'Turbuhaler'], ['50mcg/20mcg', '1.25mg/500mcg']),
        ('Respiratory', 'Budesonide', ['Budecort', 'Pulmicort'], ['Inhaler', 'Respules', 'Rotacaps', 'Nebulizer Suspension'], ['100mcg', '200mcg', '0.5mg', '1mg']),
        ('Respiratory', 'Fluticasone', ['Flomist', 'Flohale', 'Fluticone'], ['Nasal Spray', 'Inhaler'], ['50mcg', '125mcg']),
        ('Respiratory', 'Montelukast', ['Montair', 'Romilast', 'Telekast'], ['Tablet', 'Syrup', 'Chewable Tablet'], ['4mg', '5mg', '10mg']),
        ('Respiratory', 'Cetirizine', ['Zyrtec', 'Cetzine', 'Allerid', 'Okacet'], ['Tablet', 'Syrup', 'Drops'], ['10mg', '5mg/5ml']),
        ('Respiratory', 'Levocetirizine', ['Levocet', 'Teczine', '1-AL', 'Leczine'], ['Tablet', 'Syrup'], ['5mg', '2.5mg/5ml']),
        ('Respiratory', 'Dextromethorphan + CPM', ['Corex DX', 'Ascoril D', 'Grilinctus', 'Benadryl DR'], ['Syrup', 'Tonic', 'Cough Drop'], ['100ml', '50ml', '60ml', 'Standard']),
        ('Respiratory', 'Ambroxol', ['Mucolite', 'Ambrodil'], ['Syrup', 'Tablet', 'Drops'], ['30mg', '15mg/5ml']),

        ('Vitamins & Supplements', 'Multivitamin', ['A to Z', 'Zincovit', 'Supradyn', 'Becosules', 'Revital', 'Cobadex'], ['Tablet', 'Capsule', 'Syrup', 'Drops', 'Tonic'], ['Standard']),
        ('Vitamins & Supplements', 'Cholecalciferol (Vit D3)', ['Calcirol', 'Uprise D3', 'D3 Must', 'Arachitol'], ['Granules', 'Capsule', 'Drops', 'Syrup', 'Injection'], ['60000 IU', '800 IU/ml', '400 IU/ml']),
        ('Vitamins & Supplements', 'Iron + Folic Acid', ['Dexorange', 'Livogen', 'Autrin', 'Ferium', 'Orofer'], ['Syrup', 'Tablet', 'Tonic', 'Capsule', 'Injection'], ['Standard', '200ml']),
        ('Vitamins & Supplements', 'Calcium + Vit D3', ['Shelcal', 'Gemcal', 'Cipcal', 'Macalvit'], ['Tablet', 'Syrup', 'Suspension'], ['500mg', '250mg/5ml']),
        ('Vitamins & Supplements', 'B-Complex', ['Neurobion Forte', 'PolyBion', 'Optineuron', 'Nurokind'], ['Tablet', 'Syrup', 'Injection', 'Capsule'], ['Standard', '2ml']),
        ('Vitamins & Supplements', 'Protein Supplement', ['Protinex', 'B-Protin', 'Ensure'], ['Powder', 'Granules'], ['250g', '400g']),
        ('Vitamins & Supplements', 'Vitamin C', ['Limcee', 'Celin', 'Sukcee'], ['Chewable Tablet', 'Drops'], ['500mg']),

        ('Dermatological', 'Ketoconazole', ['Nizral', 'Ketomac', 'Abzorb', 'Phytoral', 'Sebizole'], ['Shampoo', 'Cream', 'Dusting Powder', 'Soap', 'Lotion'], ['2%', '1%', 'Standard', '50g']),
        ('Dermatological', 'Clotrimazole', ['Candid', 'SurfAZ', 'Canesten', 'Surfaz-SN'], ['Cream', 'Dusting Powder', 'Lotion', 'Ear Drops'], ['1%', 'Standard', '15g']),
        ('Dermatological', 'Mupirocin', ['T-Bact', 'Supirocin', 'Bactroban'], ['Ointment', 'Cream'], ['2%', '5g']),
        ('Dermatological', 'Permethrin', ['Perlice', 'Scaboma', 'Permite', 'Zeroscab'], ['Lotion', 'Cream', 'Soap'], ['5%', '1%']),
        ('Dermatological', 'Luliconazole', ['Lulifin', 'Lulimac', 'Lulican'], ['Cream', 'Lotion'], ['1%', '10g', '20g']),
        ('Dermatological', 'Diclofenac', ['Volini', 'Moov', 'Omnigel'], ['Gel', 'Spray', 'Ointment'], ['Standard', '30g', '50g']),
        ('Dermatological', 'Povidone Iodine', ['Betadine', 'Wokadine'], ['Ointment', 'Solution', 'Gargle', 'Powder'], ['5%', '10%', '2%']),

        ('Neurology / CNS', 'Pregabalin', ['Pregeb', 'Lyrica', 'Maxgalin', 'Pregalin'], ['Capsule', 'Tablet'], ['75mg', '150mg', '300mg']),
        ('Neurology / CNS', 'Gabapentin', ['Gabapin', 'Neurontin', 'Pentanevrin'], ['Tablet', 'Capsule', 'Syrup'], ['100mg', '300mg', '400mg']),
        ('Neurology / CNS', 'Escitalopram', ['Nexito', 'Lexapro', 'Stalopam', 'Cilentra'], ['Tablet'], ['5mg', '10mg', '20mg']),
        ('Neurology / CNS', 'Clonazepam', ['Clonotril', 'Zapiz', 'Lonazep', 'Petril'], ['Tablet', 'Mouth Dissolving Tablet'], ['0.25mg', '0.5mg', '1mg']),
        ('Neurology / CNS', 'Amitriptyline', ['Tryptomer', 'Eliwel', 'Amitone'], ['Tablet'], ['10mg', '25mg', '50mg']),

        ('Antiviral', 'Acyclovir', ['Zovirax', 'Herpex', 'Acivir'], ['Tablet', 'Cream', 'Ointment', 'Injection'], ['200mg', '400mg', '5%', '500mg']),
        ('Antiviral', 'Oseltamivir', ['Antiflu', 'Tamiflu', 'Fluvir'], ['Capsule', 'Suspension'], ['75mg']),
        
        ('Antimalarial', 'Hydroxychloroquine', ['HCQS', 'Zyq'], ['Tablet'], ['200mg', '400mg']),
        ('Antimalarial', 'Artemether + Lumefantrine', ['Lumerax', 'Arteether'], ['Tablet', 'Injection', 'Syrup'], ['80mg/480mg', '20mg/120mg']),

        ('Anthelmintic', 'Albendazole', ['Zentel', 'Bandy', 'Noworm'], ['Tablet', 'Suspension'], ['400mg', '200mg/5ml']),
        ('Anthelmintic', 'Ivermectin', ['Iver', 'Ivecop', 'Scaboma Plus'], ['Tablet'], ['6mg', '12mg']),
        
        ('Ophthalmic', 'Moxifloxacin', ['Vigamox', 'Moxicip', 'Milflox', 'MahaMox'], ['Eye Drops'], ['0.5%', '5ml']),
        ('Ophthalmic', 'Carboxymethylcellulose', ['Refresh Tears', 'EcoTears', 'Tear Drops', 'Lubistar'], ['Eye Drops', 'Gel Drops'], ['0.5%', '1%', '10ml']),
        ('Ophthalmic', 'Tobramycin', ['Toba', 'Tobacin'], ['Eye Drops', 'Eye Ointment'], ['0.3%']),
        
        ('Steroids', 'Prednisolone', ['Omnacortil', 'Wysolone'], ['Tablet', 'Drops', 'Syrup'], ['5mg', '10mg', '20mg', '1%']),
        ('Steroids', 'Dexamethasone', ['Dexona', 'Decadron'], ['Tablet', 'Injection', 'Drops'], ['0.5mg', '4mg/ml']),
        
        ('Gynaecology', 'Progesterone', ['Susten', 'Naturogest'], ['Capsule', 'Injection'], ['200mg', '300mg', '100mg']),
        ('Gynaecology', 'Drotaverine', ['Drotin', 'Drotikind'], ['Tablet', 'Injection', 'Syrup'], ['40mg', '80mg']),

        # MORE OTC, OINTMENTS, SOAPS, SURGICALS AND DEVICES
        ('Ointment & First Aid', 'Povidone Iodine', ['Betadine', 'Wokadine', 'Cipladine'], ['Ointment', 'Solution', 'Gargle', 'Powder'], ['5%', '10%', '2%']),
        ('Ointment & First Aid', 'Chlorhexidine Cetrimide', ['Savlon', 'Dettol', 'Suthol'], ['Liquid', 'Cream', 'Spray'], ['Standard', '200ml', '500ml']),
        ('Ointment & First Aid', 'Framycetin', ['Soframycin'], ['Skin Cream'], ['1%', '30g', '15g']),
        ('Ointment & First Aid', 'Neomycin + Bacitracin', ['Neosporin', 'Nebasulf'], ['Ointment', 'Powder'], ['10g', '20g']),
        ('Ointment & First Aid', 'Silver Sulfadiazine', ['Silverex', 'Burnol', 'Silvadene'], ['Cream', 'Ointment'], ['1%', '15g']),

        ('OTC Pain Relief', 'Diclofenac / Methyl Salicylate', ['Volini', 'Moov', 'Relispray', 'Iodex'], ['Spray', 'Gel', 'Balm', 'Ointment'], ['30g', '50g', 'Standard']),
        ('OTC Pain Relief', 'Ayurvedic Pain Balm', ['Zandu Balm', 'Amrutanjan', 'Tiger Balm'], ['Balm', 'Roll-on'], ['10g', '25g', 'Standard']),

        ('Medical Soaps & Washes', 'Ketoconazole Soap', ['Ketomac', 'Nizral', 'Phytoral Soap'], ['Soap'], ['75g', '100g']),
        ('Medical Soaps & Washes', 'Monosulfiram', ['Tetmosol'], ['Soap'], ['100g', 'Standard']),
        ('Medical Soaps & Washes', 'Antiseptic Soap', ['Dettol Original', 'Savlon Glycerin', 'Lifebuoy'], ['Soap', 'Handwash'], ['75g', '125g', '200ml']),
        ('Medical Soaps & Washes', 'Acne Care Soap', ['Acnesan', 'AcneStar', 'Klite'], ['Soap', 'Face Wash'], ['75g', '100g']),
        ('Medical Soaps & Washes', 'Intimate Wash', ['VWash Plus', 'Everteen', 'Clean & Dry'], ['Liquid Wash', 'Foam'], ['100ml', '200ml']),

        ('Powders & Dusting', 'Clotrimazole Dusting', ['Candid Powder', 'Clocip', 'SurfAZ'], ['Powder'], ['50g', '100g']),
        ('Powders & Dusting', 'Prickly Heat Powder', ['Nycil', 'DermiCool', 'Shower to Shower'], ['Powder'], ['150g', 'Standard']),

        ('Hydration & Energy', 'ORS', ['Electral', 'Walyte', 'Prolyte'], ['Powder', 'Liquid Solution'], ['4.4g', '21g', '200ml']),
        ('Hydration & Energy', 'Glucose', ['Glucon-D', 'Dabur Glucose', 'Glucose-C'], ['Powder'], ['100g', '200g', '500g']),

        ('Surgicals & Essentials', 'Cotton', ['Absorbent Cotton Roll', 'Sterile Cotton Swab'], ['Roll', 'Pack'], ['50g', '100g', '500g']),
        ('Surgicals & Essentials', 'Bandage', ['Crepe Bandage', 'Roller Bandage', 'Adhesive Tape'], ['Roll', 'Pack'], ['5cm', '10cm', 'Standard']),
        ('Surgicals & Essentials', 'Band-Aid', ['Band-Aid Washproof', 'Hansaplast', 'Medipore'], ['Strip', 'Patch', 'Box'], ['Standard', '100 Strips']),
        ('Surgicals & Essentials', 'Syringe & Needle', ['Dispovan 2ml', 'Dispovan 5ml', 'Insulin Syringe'], ['Piece', 'Box'], ['24G', '22G', 'Standard']),
        ('Surgicals & Essentials', 'Masks & Gloves', ['N95 Mask', 'Surgical Mask', 'Latex Gloves', 'Sterile Gloves'], ['Piece', 'Box of 50', 'Box of 100'], ['Standard', 'Medium', 'Large']),

        ('Medical Devices', 'Monitoring Device', ['Digital Thermometer', 'Omron BP Monitor', 'Accu-Chek Glucometer', 'Pulse Oximeter', 'Nebulizer Machine'], ['Device', 'Kit'], ['Standard']),
        ('Medical Devices', 'Device Accessories', ['Glucometer Strips', 'Lancets', 'Nebulizer Mask'], ['Pack of 25', 'Pack of 50'], ['Standard']),

        ('Baby Care', 'Baby Soap & Wash', ['Johnson Baby Soap', 'Himalaya Baby Wash', 'Sebamed Baby'], ['Soap', 'Body Wash', 'Shampoo'], ['75g', '100g', '200ml']),
        ('Baby Care', 'Diapers & Wipes', ['Pampers Active', 'MamyPoko Pants', 'Himalaya Wipes'], ['Pack', 'Jumbo Pack'], ['Small', 'Medium', 'Large']),
        ('Baby Care', 'Baby Food', ['Cerelac Stage 1', 'Lactogen 1', 'Nan Pro', 'Dexolac'], ['Powder Box'], ['400g']),
        ('Baby Care', 'Gripe Water', ['Woodwards Gripe Water', 'Dabur Gripe Water'], ['Syrup'], ['130ml', '200ml']),

        ('Nutrition & Drinks', 'Health Drink', ['Ensure', 'Protinex', 'Pediasure', 'Horlicks', 'Bournvita'], ['Powder Jar', 'Refill Pack'], ['200g', '400g', '500g']),

        ('Dental & Oral', 'Toothpaste', ['Sensodyne', 'Colgate Total', 'Meswak', 'Paradontax'], ['Tube'], ['50g', '100g', '150g']),
        ('Dental & Oral', 'Mouthwash', ['Listerine', 'Colgate Plax', 'Hexidine', 'Clohex'], ['Bottle'], ['100ml', '250ml', '500ml']),
        ('Dental & Oral', 'Oral Gear', ['Oral-B Toothbrush', 'Sensodyne Brush', 'Dental Floss'], ['Piece', 'Pack of 2'], ['Standard', 'Soft']),

        ('Ayurvedic / Herbal', 'Digestive', ['Liv.52', 'Hajmola', 'Pudin Hara', 'Eno Fruit Salt', 'Kayam Churna', 'Isabgol Husk'], ['Tablet', 'Syrup', 'Powder', 'Drops'], ['Standard', '100g', '200ml']),
        ('Ayurvedic / Herbal', 'Immunity & Tonic', ['Chyawanprash', 'Ashwagandha', 'Giloy Ghanvati', 'Revital H'], ['Paste', 'Tablet', 'Capsule'], ['500g', '1kg', 'Standard']),

        ('Specific Syrups / Tonics', 'Blood & Iron Tonic', ['Dexorange Tonic', 'Cinkara', 'LivoHills', 'Neeri Syrup'], ['Syrup', 'Tonic', 'Liquid'], ['200ml', '500ml']),
    ]

    manufacturers = ['Sun Pharma', 'Cipla', 'Abbott', 'Mankind', 'Lupin', 'Alkem', 'Torrent', 'Glenmark', 'Intas', 'Zydus', 'Micro Labs', 'Macleods', 'Aristo', 'Dr. Reddys', 'Pfizer', 'GSK', 'Sanofi', 'Novartis', 'Mylan', 'Aurobindo']

    import random
    rng = random.Random(42) # Fixed seed for predictable catalog list on restart
    generated_count = 0

    while generated_count < item_count:
        for cat, base, brands, forms, strengths in drug_profiles:
            if generated_count >= item_count:
                break
                
            brand = rng.choice(brands)
            form = rng.choice(forms)
            strength = rng.choice(strengths)
            manufacturer = rng.choice(manufacturers)
            
            # Make the brand name unique if we exceed 1000 items so we have diverse records
            suffix_num = rng.randint(1, 9) if generated_count > 1000 else ""
            prefix = rng.choice(['', 'Max', 'Plus', 'Forte', 'XR', 'SR']) if generated_count > 2000 else ""
            
            final_brand = brand
            if suffix_num or prefix:
                parts = [p for p in [brand, prefix, str(suffix_num)] if p]
                final_brand = "-".join(parts)
                
            # Formulate the final name
            if strength == 'Standard':
                name = f"{final_brand} {form}"
            else:
                name = f"{final_brand} {strength} {form}"

            stock = rng.randint(50, 6000)

            # Realistic price heuristic (in INR) based on form and category
            lower_name = name.lower()
            lower_cat = cat.lower()
            if 'device' in lower_cat or 'monitor' in lower_name or 'meter' in lower_name or 'nebulizer' in lower_name:
                price = round(rng.uniform(500.0, 2500.0), 2)
            elif 'nutrition' in lower_cat or 'supplement' in lower_cat or 'powder jar' in lower_name or 'cerelac' in lower_name:
                price = round(rng.uniform(250.0, 800.0), 2)
            elif 'diaper' in lower_name or 'wipes' in lower_name:
                price = round(rng.uniform(90.0, 450.0), 2)
            elif 'tablet' in lower_name or 'capsule' in lower_name:
                if 'paracetamol' in lower_name or 'ibuprofen' in lower_name or 'aspirin' in lower_name or 'diclofenac' in lower_name:
                    price = round(rng.uniform(10.0, 45.0), 2)
                elif 'antibiotic' in lower_cat or 'amoxicillin' in lower_name or 'azithromycin' in lower_name:
                    price = round(rng.uniform(40.0, 150.0), 2)
                else:
                    price = round(rng.uniform(30.0, 200.0), 2)
            elif 'syrup' in lower_name or 'suspension' in lower_name or 'liquid' in lower_name or 'drop' in lower_name or 'wash' in lower_name or 'shampoo' in lower_name:
                price = round(rng.uniform(40.0, 180.0), 2)
            elif 'ointment' in lower_name or 'cream' in lower_name or 'gel' in lower_name or 'soap' in lower_name or 'powder' in lower_name or 'paste' in lower_name:
                price = round(rng.uniform(50.0, 200.0), 2)
            elif 'injection' in lower_name or 'vaccine' in lower_name:
                price = round(rng.uniform(15.0, 500.0), 2)
            else:
                price = round(rng.uniform(20.0, 300.0), 2)
            
            catalog.append({
                'id': 0,
                'name': name,
                'brand': final_brand,
                'category': cat,
                'price': float(price),
                'stock': stock,
                'manufacturer': manufacturer
            })
            generated_count += 1

_append_bulk_pharmacy_items(_BUILTIN_MEDICINE_CATALOG, item_count=5000)

# ============================================================================
# STEP 8: NEW CORRECT CHATBOT - INTEGRATED WITH FLASK
# ============================================================================

from app.ml_models.strict_medical_chatbot import StrictMedicalChatbot
from app.services.ai_service import LocalAIService

chatbot_instance = None

def get_chatbot_instance():
    """Get or initialize the strict medical chatbot"""
    global chatbot_instance
    
    if chatbot_instance is None:
        try:
            chatbot_instance = StrictMedicalChatbot()
            print("[OK] Strict Medical Chatbot initialized for Flask")
        except Exception as e:
            print(f"[ERROR] Error initializing chatbot: {e}")
            return None
    
    return chatbot_instance



@features_bp.route('/api/ai-chat', methods=['POST'])
@login_required
@patient_required
def ai_chat():
    """
    API Endpoint for AI Chatbot - Uses Groq Cloud AI
    """
    print("=" * 60)
    print("[ALERT] FEATURES.AI_CHAT ENDPOINT HIT!")
    print("=" * 60)
    
    data = request.get_json()
    message = data.get('message', '')
    
    print(f"[NOTE] Received message: {message}")
    
    if not message:
        print("[ERROR] No message provided!")
        return jsonify({'error': 'No message provided'}), 400
    
    try:
        print(f"[AI] Calling LocalAIService.get_ai_response()")
        response = LocalAIService.get_ai_response(message)
        print(f"[OK] Got response: {response[:100]}...")
        return jsonify({'response': response})
    except Exception as e:
        print(f"[ERROR] Exception in ai_chat: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'response': f"Error: {str(e)}"}), 500


@features_bp.route('/api/symptom-chat', methods=['POST'])
@login_required
def symptom_chat():
    """Backward-compatible endpoint for legacy symptom checker template."""
    return ai_chat()

@features_bp.route('/ai-assistant')
@login_required
@patient_required
def ai_assistant():
    """Page for the Local AI Medical Assistant"""
    return render_template('features/ai_assistant.html')

from app.models.models import db, Medicine, BloodInventory, Bed
from sqlalchemy import func

@features_bp.route('/operations')
@login_required
def operations():
    """Operations Center - Bed & Ambulance Tracking"""
    from app.models.models import Bed, Ambulance, Patient
    
    beds = Bed.query.all()
    # Seed beds if none exist
    if not beds:
        seed_beds()
        beds = Bed.query.all()
        
    ambulances = Ambulance.query.all()
    # Seed ambulances if none exist
    if not ambulances:
        seed_ambulances()
        ambulances = Ambulance.query.all()

    bed_data = []
    for bed in beds:
        patient_name = 'Vacant'
        if bed.is_occupied and bed.patient_id:
            patient = Patient.query.get(bed.patient_id)
            if patient:
                patient_name = f"{patient.first_name} {patient.last_name}"

        bed_data.append({
            'id': bed.id,
            'number': bed.bed_number,
            'ward': bed.ward_type,
            'status': bed.status,
            'patient': patient_name
        })

    return render_template('features/operations.html', 
                         beds=bed_data, 
                         ambulances=ambulances)

def seed_beds():
    """Seed initial hospital beds"""
    from app.models.models import Bed
    wards = [
        ('ICU', 5),
        ('General Ward', 10),
        ('Emergency', 5),
        ('Pediatrics', 5)
    ]
    for ward_name, count in wards:
        for i in range(1, count + 1):
            bed_num = f"{ward_name[0]}{i:02d}"
            # Check if bed already exists by number and type
            if not Bed.query.filter_by(bed_number=bed_num, ward_type=ward_name).first():
                bed = Bed(ward_type=ward_name, bed_number=bed_num, is_occupied=False)
                db.session.add(bed)
    db.session.commit()

def seed_ambulances():
    """Seed initial ambulances"""
    from app.models.models import Ambulance
    initial_ambulances = [
        ('AMB-001', 'Advanced Life Support', 'Available', 'Hospital Base', 'John Doe', '555-0101'),
        ('AMB-002', 'Basic Life Support', 'On Mission', 'Downtown Medical', 'Jane Smith', '555-0102'),
        ('AMB-003', 'Basic Life Support', 'Available', 'Hospital Base', 'Mike Ross', '555-0103'),
        ('AMB-004', 'Advanced Life Support', 'Maintenance', 'Service Center', 'Harvey Specter', '555-0104')
    ]
    for num, vtype, status, loc, driver, phone in initial_ambulances:
        if not Ambulance.query.filter_by(vehicle_number=num).first():
            amb = Ambulance(
                vehicle_number=num,
                vehicle_type=vtype,
                status=status,
                current_location=loc,
                driver_name=driver,
                driver_phone=phone
            )
            db.session.add(amb)
    db.session.commit()

@features_bp.route('/pharmacy')
@login_required
def pharmacy():
    """Pharmacy & Inventory Management"""
    search_query = request.args.get('search', '').strip()
    
    # Base query
    query = Medicine.query
    
    if search_query:
        query = query.filter(Medicine.name.ilike(f'%{search_query}%'))
        
    inventory = query.all()
    
    # Calculate Stats
    all_inventory = Medicine.query.all()
    
    low_stock = sum(1 for m in all_inventory if m.stock < 50)
    total_value = sum((m.stock * (m.unit_price or 0)) for m in all_inventory)
    
    import datetime
    current_year = str(datetime.datetime.now().year)
    expiring_soon = sum(1 for m in all_inventory if m.expiry_date and m.expiry_date.startswith(current_year))
    
    stats = {
        'low_stock': low_stock,
        'total_value': f"${total_value:,.2f}",
        'expiring_soon': expiring_soon,
        'daily_sales': 156 
    }
    
    return render_template('features/pharmacy.html', inventory=inventory, stats=stats, search_query=search_query)

@features_bp.route('/api/pharmacy/search', methods=['GET'])
@login_required
def search_pharmacy_medicines():
    """Autocomplete endpoint for the /features/pharmacy modal."""
    q = (request.args.get('q') or '').strip()
    if len(q) < 2:
        return jsonify([])

    prefix = f"{q}%"
    contains = f"%{q}%"

    try:
        matches = (
            Medicine.query
            .filter(
                or_(
                    Medicine.name.ilike(contains),
                    Medicine.brand.ilike(contains),
                    Medicine.category.ilike(contains),
                    Medicine.manufacturer.ilike(contains),
                )
            )
            .order_by(
                case((Medicine.name.ilike(prefix), 0), else_=1),
                func.length(Medicine.name),
                Medicine.name.asc()
            )
            .limit(12)
            .all()
        )

        if matches:
            return jsonify([
                {
                    'id': med.id,
                    'name': med.name,
                    'brand': med.brand or '',
                    'price': float(med.unit_price) if med.unit_price else 0,
                    'stock': int(med.stock) if med.stock else 0,
                    'manufacturer': med.manufacturer or '',
                }
                for med in matches
            ])
    except Exception as e:
        print(f"[Pharmacy Search] DB query error: {e}")

    # ---------- Fallback: built-in medicine catalog ----------
    q_lower = q.lower()
    fallback_results = [
        m for m in _BUILTIN_MEDICINE_CATALOG
        if q_lower in m['name'].lower()
           or q_lower in m.get('brand', '').lower()
           or q_lower in m.get('category', '').lower()
    ]
    # Prioritise prefix matches, then sort by name length
    fallback_results.sort(key=lambda m: (
        0 if m['name'].lower().startswith(q_lower) else 1,
        len(m['name']),
        m['name']
    ))
    return jsonify(fallback_results[:12])

@features_bp.route('/api/pharmacy/restock', methods=['POST'])
@login_required
def restock_pharmacy():
    """API to Restock Medicine"""
    data = request.get_json()
    
    try:
        med_id = int(data.get('id'))
        amount = int(data.get('amount'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Invalid format'})
        
    if not med_id or amount <= 0:
        return jsonify({'success': False, 'error': 'Invalid data'})
        
    medicine = Medicine.query.get(med_id)
    if not medicine:
        return jsonify({'success': False, 'error': 'Medicine not found'})
        
    medicine.stock += amount
    db.session.commit()
    
    return jsonify({'success': True})

@features_bp.route('/api/pharmacy/add', methods=['POST'])
@login_required
def add_medicine():
    """API to Add New Medicine or update existing"""
    from sqlalchemy.exc import IntegrityError
    
    data = request.get_json()
    
    try:
        med_name = data['name'].strip() if data.get('name') else None
        med_brand = data.get('brand', '').strip() if data.get('brand') else None
        
        if not med_name:
            return jsonify({'success': False, 'error': 'Medicine name is required'}), 400
            
        # Robust duplicate check: find by BOTH name and brand (case-insensitive, trimmed)
        query = Medicine.query.filter(
            func.lower(func.trim(Medicine.name)) == med_name.lower()
        )
        
        if med_brand:
            # Brand is provided - match exactly
            query = query.filter(
                func.lower(func.trim(func.coalesce(Medicine.brand, ''))) == med_brand.lower()
            )
        else:
            # No brand - match medicines with NULL or empty brand
            query = query.filter(
                or_(
                    Medicine.brand.is_(None),
                    func.trim(Medicine.brand) == ''
                )
            )
        
        existing_med = query.first()
        
        try:
            stock_to_add = int(data['stock']) if data.get('stock') else 0
            unit_price = float(data['unit_price']) if data.get('unit_price') else 0
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Invalid stock or price value'}), 400
        
        if existing_med:
            # If medicine already exists, just update stock and relevant details
            old_stock = existing_med.stock or 0
            existing_med.stock = old_stock + stock_to_add
            if unit_price > 0:
                existing_med.unit_price = unit_price
            if data.get('expiry_date'):
                existing_med.expiry_date = data['expiry_date']
            if data.get('batch_number'):
                existing_med.batch_number = data['batch_number']
            if data.get('manufacturer'):
                existing_med.manufacturer = data['manufacturer']
            db.session.commit()
            return jsonify({
                'success': True, 
                'message': f'[OK] Updated: added {stock_to_add} units to "{existing_med.name}" (total: {existing_med.stock} units)',
                'medicine': {
                    'id': existing_med.id,
                    'name': existing_med.name,
                    'stock': existing_med.stock
                }
            }), 200
        else:
            new_med = Medicine(
                name=med_name,
                brand=med_brand or None,
                stock=max(stock_to_add, 0),
                unit_price=unit_price,
                expiry_date=data.get('expiry_date'),
                batch_number=data.get('batch_number', 'N/A'),
                manufacturer=data.get('manufacturer', 'N/A')
            )
            db.session.add(new_med)
            db.session.commit()
            return jsonify({
                'success': True, 
                'message': f'[OK] New medicine "{new_med.name}" added with {new_med.stock} units',
                'medicine': {
                    'id': new_med.id,
                    'name': new_med.name,
                    'stock': new_med.stock
                }
            }), 201
    except IntegrityError as e:
        db.session.rollback()
        # Handle unique constraint violation on (name, brand) pair
        if 'unique' in str(e).lower():
            # Try to find and update the existing medicine
            try:
                med_name = data['name'].strip() if data.get('name') else None
                med_brand = data.get('brand', '').strip() if data.get('brand') else None
                
                query = Medicine.query.filter(
                    func.lower(func.trim(Medicine.name)) == med_name.lower()
                )
                if med_brand:
                    query = query.filter(
                        func.lower(func.trim(func.coalesce(Medicine.brand, ''))) == med_brand.lower()
                    )
                else:
                    query = query.filter(
                        or_(
                            Medicine.brand.is_(None),
                            func.trim(Medicine.brand) == ''
                        )
                    )
                
                existing_med = query.first()
                if existing_med:
                    stock_to_add = int(data['stock']) if data.get('stock') else 0
                    existing_med.stock = (existing_med.stock or 0) + stock_to_add
                    db.session.commit()
                    return jsonify({
                        'success': True,
                        'message': f'[OK] Updated: added {stock_to_add} units to "{existing_med.name}"'
                    }), 200
            except Exception:
                db.session.rollback()
                pass
            return jsonify({'success': False, 'error': 'This medicine with this brand already exists. Please add stock instead.'}), 409
        return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error processing medicine: {str(e)}'}), 500

@features_bp.route('/features/pharmacy/export')
@login_required
def export_pharmacy_report():
    """Export Inventory as CSV"""
    import csv
    import io
    from flask import Response
    
    inventory = Medicine.query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['ID', 'Name', 'Stock', 'Unit Price', 'Expiry Date', 'Batch', 'Manufacturer', 'Status'])
    
    # Rows
    for m in inventory:
        writer.writerow([m.id, m.name, m.stock, m.unit_price, m.expiry_date, m.batch_number, m.manufacturer, m.status])
        
    output.seek(0)
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=pharmacy_inventory.csv"}
    )

@features_bp.route('/education')
@login_required
def education():
    """Personalized Health Education"""
    videos = [
        # Diabetes Management (Verified)
        {'id': 'wZAjVQWbMlE', 'title': 'What is Diabetes? (CDC Verified)', 'category': 'Diabetes', 'duration': '02:30'},
        {'id': 'X9ivR4y03DE', 'title': 'Understanding Diabetes', 'category': 'Diabetes', 'duration': '05:15'},
        {'id': 'JAjJoFj5-DA', 'title': 'Reverse Type 2 Diabetes', 'category': 'Diabetes', 'duration': '15:30'},
        {'id': 'sV2dtA74Yx0', 'title': 'What is Type 2 Diabetes?', 'category': 'Diabetes', 'duration': '03:45'},

        # Hypertension & Heart (Verified)
        {'id': 'diG519dFVNs', 'title': 'High Blood Pressure Explained', 'category': 'Hypertension', 'duration': '02:50'},
        {'id': 'H04d3rJCLCE', 'title': 'How the Heart Works (Mayo Clinic)', 'category': 'Heart Health', 'duration': '03:10'},
        {'id': '50lFZHOyPzI', 'title': 'How the Heart Pumps Blood', 'category': 'Heart Health', 'duration': '04:45'},
        
        # Mental Health & Wellness (TED-Ed Verified)
        {'id': 'WuyPuH9ojCE', 'title': 'How Stress Affects Your Brain', 'category': 'Mental Health', 'duration': '04:15'},
        {'id': 'gedoSfZvBgE', 'title': 'Benefits of Good Sleep', 'category': 'Wellness', 'duration': '05:10'},
        {'id': 'z-IR48Mb3W0', 'title': 'What is Depression?', 'category': 'Mental Health', 'duration': '04:50'},
        {'id': 'PSRJfaAYkW4', 'title': 'How Your Immune System Works', 'category': 'Immunity', 'duration': '05:20'},
        {'id': 'OyK0oE5rwFY', 'title': 'Benefits of Good Posture', 'category': 'Wellness', 'duration': '04:30'},
        {'id': 'lEXBxijQREo', 'title': 'Sugar and the Brain', 'category': 'Nutrition', 'duration': '04:55'},
        {'id': 'wUEl8KrMz14', 'title': 'Why Sitting is Bad', 'category': 'Wellness', 'duration': '05:05'}
    ]
    return render_template('patient/health_videos.html', videos=videos)

@features_bp.route('/digital-checkin', methods=['GET', 'POST'])
@login_required
def digital_checkin():
    """Digital Check-in & Queue Management - Express Check-in System"""
    # Fetch all available doctors for the selection dropdown
    doctors = Doctor.query.all()

    if request.method == 'POST':
        # Get form data
        check_in_reason = request.form.get('reason', 'General check-up')
        visit_type = request.form.get('visit_type', 'follow-up')
        symptoms = request.form.get('symptoms', '')
        severity = request.form.get('severity', 'normal')
        # Vital signs
        temperature = request.form.get('temperature')
        blood_pressure = request.form.get('blood_pressure')
        heart_rate = request.form.get('heart_rate')

        # Get patient details
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        
        if patient:
            # Determine appropriate doctor
            doctor_id = None
            selected_doctor_id = request.form.get('doctor_id')
            if selected_doctor_id:
                doctor_id = int(selected_doctor_id)
            else:
                # Fallback: Get first available doctor if none selected (though form should require it)
                first_doctor = Doctor.query.first()
                doctor_id = first_doctor.id if first_doctor else None

            if not doctor_id:
                flash('[ERROR] Error: No doctor selected or available.', 'danger')
                return redirect(url_for('features.digital_checkin'))

            # Create check-in record
            checkin = PatientCheckIn(
                patient_id=patient.id,
                doctor_id=doctor_id,
                check_in_reason=check_in_reason,
                visit_type=visit_type,
                symptoms=symptoms,
                severity=severity,
                temperature=float(temperature) if temperature else None,
                blood_pressure=blood_pressure if blood_pressure else None,
                heart_rate=int(heart_rate) if heart_rate else None,
                status='pending',
                priority='normal' if severity == 'normal' else 'urgent'
            )
            
            db.session.add(checkin)
            db.session.commit()
            
            # Fetch content for success message
            assigned_doctor = Doctor.query.get(doctor_id)
            doctor_name = f"Dr. {assigned_doctor.first_name} {assigned_doctor.last_name}" if assigned_doctor else "the doctor"

            flash(f'[OK] Express Check-in Successful! Your request has been sent to {doctor_name}.', 'success')
            return redirect(url_for('patient.dashboard'))
        else:
            flash('[ERROR] Error: Patient profile not found.', 'danger')
            return redirect(url_for('patient.dashboard'))
    
    return render_template('patient/check_in.html', doctors=doctors)

@features_bp.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    """Patient Feedback System"""
    if request.method == 'POST':
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('patient.dashboard'))
    return render_template('features/feedback.html')

@features_bp.route('/emergency-sos')
@login_required
@patient_required
def emergency_sos():
    """Emergency SOS Handler - Now Hospital Finder"""
    import json
    import os
    
    search_query = request.args.get('search', '').strip().lower()
    
    # Construct path to data file
    # features.py is in app/routes/, so we go up one level to app/
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_dir, 'data', 'hospitals.json')
    
    all_districts = []
    try:
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                all_districts = json.load(f)
    except Exception as e:
        print(f"Error loading hospital data: {e}")
    
    results = []
    
    if search_query:
        # Flat list of matching hospitals
        for district_data in all_districts:
            district_name = district_data.get('district', '')
            
            for hospital in district_data.get('hospitals', []):
                h_name = hospital.get('hospital_name', '').lower()
                h_loc = hospital.get('location', '').lower()
                h_type = hospital.get('type', '').lower()
                d_name = district_name.lower()
                
                if (search_query in h_name or 
                    search_query in h_loc or 
                    search_query in h_type or 
                    search_query in d_name):
                    
                    hospital_entry = hospital.copy()
                    hospital_entry['district'] = district_name
                    results.append(hospital_entry)
    else:
        # Prepare data for "all hospitals" view if needed, 
        # or just pass the structured data to iterate by district
        results = all_districts

    return render_template('features/emergency.html', 
                         results=results, 
                         search_query=search_query,
                         is_search=bool(search_query))

@features_bp.route('/schedule')
@login_required
def schedule():
    """Doctor Smart Schedule & Calendar"""
    # Fetch events from DB
    db_events = DoctorEvent.query.all()
    events = []
    for event in db_events:
        events.append({
            'title': event.title,
            'start': event.start_time.strftime('%H:%M'),
            'end': event.end_time.strftime('%H:%M'),
            'type': event.event_type
        })
    return render_template('features/schedule.html', events=events)

@features_bp.route('/blood-bank')
@login_required
def blood_bank():
    """Blood Bank Management"""
    inventory_items = BloodInventory.query.all()
    stock = {}
    for item in inventory_items:
        stock[item.blood_group] = {
            'units': item.units,
            'status': item.status
        }
    return render_template('features/blood_bank.html', stock=stock)

@features_bp.route('/blood-bank/donate', methods=['POST'])
@login_required
def donate_blood():
    """Register a new blood donation"""
    blood_group = request.form.get('blood_group')
    units = int(request.form.get('units', 1))
    donor_name = request.form.get('donor_name')
    
    inventory = BloodInventory.query.filter_by(blood_group=blood_group).first()
    if inventory:
        inventory.units += units
        inventory.last_updated = datetime.now()
    else:
        new_inv = BloodInventory(blood_group=blood_group, units=units)
        db.session.add(new_inv)
        
    db.session.commit()
    flash('[OK] Donation registered successfully!', 'success')
    return redirect(url_for('features.blood_bank'))


@features_bp.route('/hr-payroll')
@login_required
def hr_payroll():
    """HR & Staff Payroll Dashboard"""
    total_staff = Staff.query.count()
    present_today = Staff.query.filter_by(status='Present').count()
    on_leave = Staff.query.filter_by(status='On Leave').count()
    
    stats = {
        'total_staff': total_staff,
        'present_today': present_today,
        'on_leave': on_leave,
        'payroll_due': '5 Days'
    }
    return render_template('features/hr_dashboard.html', stats=stats)


# ============================================================================
# DOCTOR CHECK-IN MANAGEMENT ROUTES
# ============================================================================

@features_bp.route('/doctor/pending-checkins')
@login_required
def doctor_pending_checkins():
    """Doctor view all pending patient check-ins"""
    from app.routes.auth import doctor_required
    
    # Get current doctor
    doctor = current_user.doctor if hasattr(current_user, 'doctor') else None
    
    if not doctor:
        flash('[ERROR] Access denied. Doctor profile not found.', 'danger')
        return redirect(url_for('main.index'))
    
    # Get all pending check-ins for this doctor
    pending_checkins = PatientCheckIn.query.filter_by(
        doctor_id=doctor.id, 
        status='pending'
    ).order_by(PatientCheckIn.created_at.desc()).all()
    
    # Get accepted check-ins
    accepted_checkins = PatientCheckIn.query.filter_by(
        doctor_id=doctor.id,
        status='accepted'
    ).order_by(PatientCheckIn.acceptance_time.desc()).limit(10).all()
    
    # Statistics
    stats = {
        'pending_count': len(pending_checkins),
        'accepted_count': PatientCheckIn.query.filter_by(doctor_id=doctor.id, status='accepted').count(),
        'rejected_count': PatientCheckIn.query.filter_by(doctor_id=doctor.id, status='rejected').count(),
        'completed_count': PatientCheckIn.query.filter_by(doctor_id=doctor.id, status='completed').count()
    }
    
    return render_template('doctor/pending_checkins.html',
                         pending_checkins=pending_checkins,
                         accepted_checkins=accepted_checkins,
                         stats=stats)


@features_bp.route('/doctor/checkin/<int:checkin_id>/accept', methods=['POST'])
@login_required
def accept_checkin(checkin_id):
    """Doctor accepts a patient check-in"""
    from datetime import datetime
    
    checkin = PatientCheckIn.query.get(checkin_id)
    
    if not checkin:
        return jsonify({'success': False, 'error': 'Check-in not found'}), 404
    
    doctor = current_user.doctor if hasattr(current_user, 'doctor') else None
    
    if not doctor:
        return jsonify({'success': False, 'error': 'Doctor profile not found'}), 403
    
    # Allow doctor to accept if assigned OR no doctor assigned yet
    if checkin.doctor_id is not None and checkin.doctor_id != doctor.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    # Get doctor notes safely (request.json can be None with FormData)
    notes = request.form.get('notes', '')
    if not notes and request.json:
        notes = request.json.get('notes', '')
    
    # Update check-in
    checkin.status = 'accepted'
    checkin.acceptance_time = datetime.utcnow()
    checkin.doctor_notes = notes
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'[OK] Check-in from {checkin.patient.user.username} accepted!',
        'checkin_id': checkin.id
    })


@features_bp.route('/doctor/checkin/<int:checkin_id>/reject', methods=['POST'])
@login_required
def reject_checkin(checkin_id):
    """Doctor rejects a patient check-in"""
    
    checkin = PatientCheckIn.query.get(checkin_id)
    
    if not checkin:
        return jsonify({'success': False, 'error': 'Check-in not found'}), 404
    
    doctor = current_user.doctor if hasattr(current_user, 'doctor') else None
    
    if not doctor:
        return jsonify({'success': False, 'error': 'Doctor profile not found'}), 403
    
    if checkin.doctor_id is not None and checkin.doctor_id != doctor.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    # Get rejection reason safely
    reason = request.form.get('reason', '')
    if not reason and request.json:
        reason = request.json.get('reason', '')
    
    # Update check-in
    checkin.status = 'rejected'
    checkin.doctor_notes = f'Rejected: {reason}'
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'[ERROR] Check-in from {checkin.patient.user.username} rejected.',
        'checkin_id': checkin.id
    })


@features_bp.route('/doctor/checkin/<int:checkin_id>/complete', methods=['POST'])
@login_required
def complete_checkin(checkin_id):
    """Doctor marks a check-in as completed"""
    
    checkin = PatientCheckIn.query.get(checkin_id)
    
    if not checkin:
        return jsonify({'success': False, 'error': 'Check-in not found'}), 404
    
    doctor = current_user.doctor if hasattr(current_user, 'doctor') else None
    
    if not doctor:
        return jsonify({'success': False, 'error': 'Doctor profile not found'}), 403
    
    if checkin.doctor_id is not None and checkin.doctor_id != doctor.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    # Get completion notes safely
    notes = request.form.get('notes', '')
    if not notes and request.json:
        notes = request.json.get('notes', '')
    
    # Update check-in
    checkin.status = 'completed'
    if notes:
        checkin.doctor_notes = notes
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'[OK] Check-in marked as completed!',
        'checkin_id': checkin.id
    })


@features_bp.route('/doctor/checkin/<int:checkin_id>', methods=['GET'])
@login_required
def view_checkin_detail(checkin_id):
    """View detailed check-in information"""
    
    checkin = PatientCheckIn.query.get(checkin_id)
    
    if not checkin:
        return jsonify({'error': 'Check-in not found'}), 404
    
    doctor = current_user.doctor if hasattr(current_user, 'doctor') else None
    
    if not doctor or checkin.doctor_id != doctor.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Prepare check-in data
    checkin_data = {
        'id': checkin.id,
        'patient_name': checkin.patient.user.full_name if checkin.patient.user else 'Unknown',
        'patient_id': checkin.patient_id,
        'reason': checkin.check_in_reason,
        'visit_type': checkin.visit_type,
        'symptoms': checkin.symptoms,
        'severity': checkin.severity,
        'status': checkin.status,
        'priority': checkin.priority,
        'temperature': checkin.temperature,
        'blood_pressure': checkin.blood_pressure,
        'heart_rate': checkin.heart_rate,
        'doctor_notes': checkin.doctor_notes,
        'created_at': checkin.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'acceptance_time': checkin.acceptance_time.strftime('%Y-%m-%d %H:%M:%S') if checkin.acceptance_time else None
    }
    
    return jsonify(checkin_data)

@features_bp.route('/api/operations/bed/update', methods=['POST'])
@login_required
def update_bed_status():
    """API to Update Bed Status"""
    data = request.get_json()
    bed_id = data.get('bed_id')
    status = data.get('status') # 'Occupied' or 'Vacant'
    patient_name = data.get('patient_name')
    
    if not bed_id or not status:
        return jsonify({'success': False, 'error': 'Invalid data'})
        
    bed = Bed.query.get(bed_id)
    if not bed:
        return jsonify({'success': False, 'error': 'Bed not found'})
        
    bed.is_occupied = (status == 'Occupied')
    
    # In a real app, we would link to a patient ID. 
    # For this dashboard demo, we might just store the name in a temporary way 
    # or find a patient with that name.
    # Since Bed model links to patient_id, let's try to find the patient or create a dummy one if we really had to.
    # But strictly, the Bed model has `patient_id`. 
    # If the user enters a name, we can try to search for a patient.
    
    if status == 'Occupied' and patient_name:
        # Try to find patient by name
        parts = patient_name.split()
        if len(parts) >= 2:
            fname, lname = parts[0], parts[1]
            patient = Patient.query.filter_by(first_name=fname, last_name=lname).first()
            if patient:
                bed.patient_id = patient.id
    else:
        bed.patient_id = None
        
    db.session.commit()
    
    return jsonify({'success': True})

@features_bp.route('/api/operations/ambulance/dispatch', methods=['POST'])
@login_required
def dispatch_ambulance():
    """API to Dispatch Ambulance"""
    from app.models.models import Ambulance
    data = request.get_json()
    ambulance_id = data.get('ambulance_id')
    location = data.get('location')
    
    if not ambulance_id:
        return jsonify({'success': False, 'error': 'Invalid data'})
        
    ambulance = Ambulance.query.get(ambulance_id)
    if not ambulance:
        return jsonify({'success': False, 'error': 'Ambulance not found'})
        
    ambulance.status = 'On Mission'
    if location:
        ambulance.current_location = location
        
    db.session.commit()
    return jsonify({'success': True})
