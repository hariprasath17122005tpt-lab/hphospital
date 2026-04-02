import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from app import create_app
from app.models.models import db, Medicine
import random

app = create_app()

with app.app_context():
    print("Fixing prices for existing medicines in database...")
    medicines = Medicine.query.all()
    rng = random.Random(42)
    
    updated_count = 0
    for med in medicines:
        name = med.name.lower()
        cat = (med.category or "").lower()
        
        # Realistic price heuristic (in INR) based on form and category
        if 'device' in cat or 'monitor' in name or 'meter' in name or 'nebulizer' in name:
            price = round(rng.uniform(500.0, 2500.0), 2)
        elif 'nutrition' in cat or 'supplement' in cat or 'powder jar' in name or 'cerelac' in name:
            price = round(rng.uniform(250.0, 800.0), 2)
        elif 'diaper' in name or 'wipes' in name:
            price = round(rng.uniform(90.0, 450.0), 2)
        elif 'tablet' in name or 'capsule' in name:
            if 'paracetamol' in name or 'ibuprofen' in name or 'aspirin' in name or 'diclofenac' in name or 'dolo' in name:
                price = round(rng.uniform(10.0, 45.0), 2)
            elif 'antibiotic' in cat or 'amoxicillin' in name or 'azithromycin' in name:
                price = round(rng.uniform(40.0, 150.0), 2)
            else:
                price = round(rng.uniform(30.0, 200.0), 2)
        elif 'syrup' in name or 'suspension' in name or 'liquid' in name or 'drop' in name or 'wash' in name or 'shampoo' in name:
            price = round(rng.uniform(40.0, 180.0), 2)
        elif 'ointment' in name or 'cream' in name or 'gel' in name or 'soap' in name or 'powder' in name or 'paste' in name:
            price = round(rng.uniform(50.0, 200.0), 2)
        elif 'injection' in name or 'vaccine' in name:
            price = round(rng.uniform(15.0, 500.0), 2)
        else:
            price = round(rng.uniform(20.0, 300.0), 2)
            
        # Only update if current price seems randomly high or if we explicitly want to fix all of them to be safe
        med.unit_price = price
        updated_count += 1
            
    db.session.commit()
    print(f"✅ Fixed prices for {updated_count} medicines in the database.")
