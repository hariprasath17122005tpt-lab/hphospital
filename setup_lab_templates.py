import json
from app import create_app
from app.models.models import db, LabOrder

def upgrade_lab_system():
    app = create_app()
    with app.app_context():
        # First safely create new tables (we've added LabTestTemplate and new columns to LabReport)
        db.create_all()

        # Update PENDING to CREATED
        orders = LabOrder.query.filter_by(status='PENDING').all()
        for o in orders:
            o.status = 'CREATED'
        db.session.commit()
        print(f"Updated {len(orders)} orders to CREATED status")

        # Create basic templates
        from app.models.models import LabTestTemplate
        templates = [
            {
                "name": "Complete Blood Count (CBC)",
                "fields": {
                    "Hemoglobin": "g/dL",
                    "RBC Count": "10^6/µL",
                    "WBC Count": "/µL",
                    "Platelets": "10^3/µL",
                    "Neutrophils": "%",
                    "Lymphocytes": "%",
                    "Monocytes": "%"
                },
                "ranges": {
                    "Hemoglobin": "13.0 - 17.0",
                    "RBC Count": "4.5 - 5.5",
                    "WBC Count": "4000 - 11000",
                    "Platelets": "150 - 450",
                    "Neutrophils": "40 - 80",
                    "Lymphocytes": "20 - 40",
                    "Monocytes": "2 - 10"
                }
            },
            {
                "name": "Blood Test",
                "fields": {
                    "Result Detail": "text",
                    "Interpretation": "text"
                },
                "ranges": {}
            },
            {
                "name": "Kidney Function Test (KFT)",
                "fields": {
                    "Urea": "mg/dL",
                    "Creatinine": "mg/dL",
                    "Uric Acid": "mg/dL",
                    "Sodium": "mEq/L",
                    "Potassium": "mEq/L"
                },
                "ranges": {
                    "Urea": "15 - 40",
                    "Creatinine": "0.6 - 1.2",
                    "Uric Acid": "3.5 - 7.2",
                    "Sodium": "135 - 145",
                    "Potassium": "3.5 - 5.0"
                }
            },
            {
                "name": "Liver Function Test (LFT)",
                "fields": {
                    "Total Bilirubin": "mg/dL",
                    "Direct Bilirubin": "mg/dL",
                    "SGOT (AST)": "U/L",
                    "SGPT (ALT)": "U/L",
                    "Alkaline Phosphatase": "U/L"
                },
                "ranges": {
                    "Total Bilirubin": "0.2 - 1.2",
                    "Direct Bilirubin": "0.0 - 0.3",
                    "SGOT (AST)": "5 - 40",
                    "SGPT (ALT)": "7 - 56",
                    "Alkaline Phosphatase": "44 - 147"
                }
            },
             {
                "name": "Blood Sugar (Fasting)",
                "fields": {
                    "Fasting Blood Sugar": "mg/dL"
                },
                "ranges": {
                    "Fasting Blood Sugar": "70 - 100"
                }
            }
        ]

        for t in templates:
            ext = LabTestTemplate.query.filter_by(test_name=t['name']).first()
            if not ext:
                ext = LabTestTemplate(
                    test_name=t['name'],
                    fields=t['fields'],
                    normal_ranges=t['ranges']
                )
                db.session.add(ext)
            else:
                ext.fields = t['fields']
                ext.normal_ranges = t['ranges']

        db.session.commit()
        print("Templates seeded successfully!")

        # Fix DB schema for SQLite drop column if necessary
        try:
            db.session.execute("ALTER TABLE lab_reports ADD COLUMN lab_order_id INTEGER REFERENCES lab_orders(id)")
            db.session.commit()
            print("Added lab_order_id to lab_reports")
        except Exception as e:
            db.session.rollback()
            print("lab_order_id might already exist or err:", str(e))
        
        try:
            db.session.execute("ALTER TABLE lab_reports ADD COLUMN report_data JSON")
            db.session.commit()
            print("Added report_data to lab_reports")
        except Exception as e:
            db.session.rollback()
            print("report_data might already exist or err:", str(e))

if __name__ == "__main__":
    upgrade_lab_system()
