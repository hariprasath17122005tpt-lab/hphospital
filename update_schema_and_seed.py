
from app import create_app, db
from app.models.models import Medicine, BloodInventory, Bed, DoctorEvent, NurseTask, Staff
from datetime import datetime, timedelta

app = create_app()

with app.app_context():
    # Create tables if they don't exist
    db.create_all()
    print("Database schema updated.")

    # --- Seed Pharmacy ---
    if not Medicine.query.first():
        print("Seeding Medicines...")
        medicines = [
            {'name': 'Paracetamol 500mg', 'stock': 450, 'expiry_date': '2025-12', 'batch_number': 'PCM-001', 'manufacturer': 'PharmaCorp', 'unit_price': 2.50},
            {'name': 'Amoxicillin 250mg', 'stock': 45, 'expiry_date': '2024-10', 'batch_number': 'AMX-992', 'manufacturer': 'MediLife', 'unit_price': 15.00},
            {'name': 'Ibuprofen 400mg', 'stock': 120, 'expiry_date': '2025-01', 'batch_number': 'IBU-443', 'manufacturer': 'WellHealth', 'unit_price': 5.00},
            {'name': 'Cetirizine 10mg', 'stock': 0, 'expiry_date': '2024-08', 'batch_number': 'CET-112', 'manufacturer': 'AllergyFix', 'unit_price': 3.00},
            {'name': 'Metformin 500mg', 'stock': 300, 'expiry_date': '2026-05', 'batch_number': 'MET-551', 'manufacturer': 'DiabetCare', 'unit_price': 8.50},
        ]
        for data in medicines:
            med = Medicine(**data)
            db.session.add(med)

    # --- Seed Blood Bank ---
    if not BloodInventory.query.first():
        print("Seeding Blood Inventory...")
        blood_stock = [
            {'blood_group': 'A+', 'units': 12},
            {'blood_group': 'A-', 'units': 4},
            {'blood_group': 'B+', 'units': 15},
            {'blood_group': 'B-', 'units': 2},
            {'blood_group': 'AB+', 'units': 8},
            {'blood_group': 'AB-', 'units': 1},
            {'blood_group': 'O+', 'units': 20},
            {'blood_group': 'O-', 'units': 5},
        ]
        for data in blood_stock:
            inv = BloodInventory(**data)
            db.session.add(inv)

    # --- Seed Beds (Hospital Operations) ---
    if not Bed.query.first():
        print("Seeding Beds...")
        # ICU
        for i in range(1, 21):
            db.session.add(Bed(ward_type='ICU', bed_number=f'ICU-{i:02d}', is_occupied=(i <= 15)))
        # General Ward
        for i in range(1, 51):
            db.session.add(Bed(ward_type='General Ward', bed_number=f'GEN-{i:02d}', is_occupied=(i <= 42)))
        # Emergency
        for i in range(1, 11):
            db.session.add(Bed(ward_type='Emergency', bed_number=f'EMG-{i:02d}', is_occupied=(i <= 2)))

    # --- Seed Doctor Events ---
    if not DoctorEvent.query.first():
        print("Seeding Doctor Events...")
        now = datetime.utcnow()
        events = [
            {'title': 'Surgery - Patient #124', 'start_time': now.replace(hour=10, minute=0), 'end_time': now.replace(hour=12, minute=0), 'event_type': 'surgery'},
            {'title': 'OPD Consultation', 'start_time': now.replace(hour=13, minute=0), 'end_time': now.replace(hour=16, minute=0), 'event_type': 'opd'},
            {'title': 'Staff Meeting', 'start_time': now.replace(hour=16, minute=30), 'end_time': now.replace(hour=17, minute=30), 'event_type': 'meeting'}
        ]
        for data in events:
            event = DoctorEvent(**data)
            db.session.add(event)

    # --- Seed Nurse Tasks ---
    if not NurseTask.query.first():
        print("Seeding Nurse Tasks...")
        tasks = [
            {'patient_name': 'John Doe', 'bed_number': 'ICU-04', 'task_description': 'Check Vitals', 'due_time': '10:00 AM', 'status': 'Pending', 'priority': 'High'},
            {'patient_name': 'Alice Smith', 'bed_number': 'Gen-12', 'task_description': 'Insulin Injection', 'due_time': '10:15 AM', 'status': 'Completed', 'priority': 'Medium'},
            {'patient_name': 'Bob Jones', 'bed_number': 'ICU-01', 'task_description': 'Change Drip', 'due_time': '10:30 AM', 'status': 'Pending', 'priority': 'High'}
        ]
        for data in tasks:
            task = NurseTask(**data)
            db.session.add(task)

    # --- Seed Staff (HR) ---
    if not Staff.query.first():
        print("Seeding Staff Data...")
        # Just create some dummy count logic later, but let's add some rows if needed for complex HR
        # For now, we will just use the counts in the route, or seed dummy rows to count.
        # Let's seed 145 staff members loosely
        roles = ['Nurse', 'Doctor', 'Receptionist', 'Cleaner', 'Admin']
        for i in range(145):
            db.session.add(Staff(name=f'Staff {i}', role='Staff', department='General', status='Present' if i < 132 else 'On Leave'))


    db.session.commit()
    print("All seeding complete.")
