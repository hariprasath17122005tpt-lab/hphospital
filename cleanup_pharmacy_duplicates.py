import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from app import create_app
from app.models.models import db, Medicine
from sqlalchemy import func

app = create_app()

with app.app_context():
    print("Scanning pharmacy database for duplicate medicines...")
    medicines = Medicine.query.all()
    
    seen = {}
    duplicates_removed = 0
    
    for m in medicines:
        # Normalize name for comparison (lowercase, strip whitespace)
        name_key = m.name.lower().strip()
        
        if name_key in seen:
            # Duplicate found!
            original = seen[name_key]
            # Merge the stock
            original.stock += (m.stock or 0)
            print(f"Merging duplicate '{m.name}' -> added {m.stock} stock to original.")
            
            # Delete the duplicate row
            db.session.delete(m)
            duplicates_removed += 1
        else:
            # First time seeing this medicine
            seen[name_key] = m
            # We also normalize the actual saved name just in case it had trailing spaces
            m.name = m.name.strip()
            
    try:
        db.session.commit()
        print(f"\n✅ Cleanup Complete! Removed {duplicates_removed} duplicate entries and merged their stock levels.")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error during cleanup: {e}")
