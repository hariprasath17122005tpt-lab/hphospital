#!/usr/bin/env python3
"""Seed medicines table with sample data"""

import sys
from datetime import datetime
from app import create_app, db
from app.models.models import Medicine

def seed_medicines():
    app = create_app()
    with app.app_context():
        # Sample medicines data
        medicines_data = [
            {'name': 'Paracetamol', 'brand': 'Calpol', 'category': 'Analgesic', 'price': 10.0, 'stock': 500, 'supplier': 'MediCare Inc', 'expiry_date': '2027-06'},
            {'name': 'Dolo 650', 'brand': 'Dolo', 'category': 'Analgesic', 'price': 12.0, 'stock': 450, 'supplier': 'MediCare Inc', 'expiry_date': '2027-08'},
            {'name': 'Crocin', 'brand': 'GlaxoSmithKline', 'category': 'Analgesic', 'price': 15.0, 'stock': 400, 'supplier': 'GSK', 'expiry_date': '2027-03'},
            {'name': 'Azithromycin', 'brand': 'Zithromax', 'category': 'Antibiotic', 'price': 85.0, 'stock': 300, 'supplier': 'Pfizer', 'expiry_date': '2027-12'},
            {'name': 'Amoxicillin', 'brand': 'Amoxil', 'category': 'Antibiotic', 'price': 45.0, 'stock': 350, 'supplier': 'MediCare Inc', 'expiry_date': '2027-09'},
            {'name': 'Ibuprofen', 'brand': 'Brufen', 'category': 'NSAID', 'price': 20.0, 'stock': 600, 'supplier': 'MediCare Inc', 'expiry_date': '2028-01'},
            {'name': 'Insulin', 'brand': 'Insulin Aspart', 'category': 'Antidiabetic', 'price': 350.0, 'stock': 150, 'supplier': 'Novo Nordisk', 'expiry_date': '2027-04'},
            {'name': 'Metformin', 'brand': 'Glucophage', 'category': 'Antidiabetic', 'price': 25.0, 'stock': 800, 'supplier': 'Bristol Myers', 'expiry_date': '2028-02'},
            {'name': 'Lisinopril', 'brand': 'Prinivil', 'category': 'Antihypertensive', 'price': 30.0, 'stock': 400, 'supplier': 'Merck', 'expiry_date': '2027-11'},
            {'name': 'Atorvastatin', 'brand': 'Lipitor', 'category': 'Statin', 'price': 45.0, 'stock': 500, 'supplier': 'Pfizer', 'expiry_date': '2028-05'},
            {'name': 'Omeprazole', 'brand': 'Prilosec', 'category': 'PPI', 'price': 18.0, 'stock': 550, 'supplier': 'AstraZeneca', 'expiry_date': '2027-07'},
            {'name': 'Ranitidine', 'brand': 'Zantac', 'category': 'H2 Blocker', 'price': 12.0, 'stock': 400, 'supplier': 'GSK', 'expiry_date': '2027-10'},
            {'name': 'Aspirin', 'brand': 'Ecosprin', 'category': 'Antiplatelet', 'price': 5.0, 'stock': 1000, 'supplier': 'USV Ltd', 'expiry_date': '2028-03'},
            {'name': 'Thiopental', 'brand': 'Sodium Pentothal', 'category': 'Anesthetic', 'price': 120.0, 'stock': 100, 'supplier': 'JB Chemicals', 'expiry_date': '2027-05'},
            {'name': 'Diclofenac', 'brand': 'Voltaren', 'category': 'NSAID', 'price': 22.0, 'stock': 350, 'supplier': 'Novartis', 'expiry_date': '2027-08'},
        ]

        print(f"Seeding {len(medicines_data)} medicines...")
        
        # Check existing medicines
        existing_count = Medicine.query.count()
        if existing_count > 0:
            print(f"⚠️  Database already has {existing_count} medicines. Updating/Adding missing ones...")

        for med_data in medicines_data:
            existing = Medicine.query.filter(
                Medicine.name == med_data['name'],
                Medicine.brand == med_data['brand']
            ).first()
            
            if existing:
                if not existing.expiry_date and med_data.get('expiry_date'):
                    existing.expiry_date = med_data['expiry_date']
                    print(f"  ✓ Updated expiry_date: {med_data['name']} - {med_data['brand']} -> {med_data['expiry_date']}")
                else:
                    print(f"  ✓ Already exists: {med_data['name']} - {med_data['brand']}")
            else:
                med = Medicine(
                    name=med_data['name'],
                    brand=med_data['brand'],
                    category=med_data['category'],
                    price=med_data['price'],
                    stock=med_data['stock'],
                    supplier=med_data['supplier'],
                    expiry_date=med_data.get('expiry_date'),
                    created_at=datetime.utcnow()
                )
                db.session.add(med)
                print(f"  ✅ Added: {med_data['name']} - {med_data['brand']}")

        db.session.commit()
        
        # Verify count
        final_count = Medicine.query.count()
        print(f"\n✅ Seeding complete! Total medicines in database: {final_count}")

if __name__ == '__main__':
    seed_medicines()
