import sys
import os

# Add app to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models.models import LabTestTemplate
import json

app = create_app()

templates = [
    {
        "test_name": "Complete Blood Count (CBC)",
        "fields": {
            "Hemoglobin": "g/dL",
            "WBC Count": "cells/mcL",
            "RBC Count": "million/mcL",
            "Platelets": "per mcL",
            "Hematocrit": "%"
        },
        "normal_ranges": {
            "Hemoglobin": "13.8-17.2",
            "WBC Count": "4500-11000",
            "RBC Count": "4.5-5.9",
            "Platelets": "150000-450000",
            "Hematocrit": "41-50"
        }
    },
    {
        "test_name": "Lipid Profile",
        "fields": {
            "Total Cholesterol": "mg/dL",
            "HDL (Good)": "mg/dL",
            "LDL (Bad)": "mg/dL",
            "Triglycerides": "mg/dL"
        },
        "normal_ranges": {
            "Total Cholesterol": "< 200",
            "HDL (Good)": "> 40",
            "LDL (Bad)": "< 100",
            "Triglycerides": "< 150"
        }
    },
    {
        "test_name": "Blood Sugar (Fasting)",
        "fields": {
            "Fasting Blood Sugar": "mg/dL"
        },
        "normal_ranges": {
            "Fasting Blood Sugar": "70-99"
        }
    },
    {
        "test_name": "Thyroid Profile (T3, T4, TSH)",
        "fields": {
            "TSH": "mIU/L",
            "Free T4": "ng/dL",
            "Free T3": "pg/mL"
        },
        "normal_ranges": {
            "TSH": "0.4-4.0",
            "Free T4": "0.8-1.8",
            "Free T3": "2.3-4.2"
        }
    }
]

with app.app_context():
    for data in templates:
        existing = LabTestTemplate.query.filter_by(test_name=data['test_name']).first()
        if existing:
            existing.fields = json.dumps(data['fields'])
            existing.normal_ranges = json.dumps(data['normal_ranges'])
            print(f"Updated {data['test_name']}")
        else:
            new_tpl = LabTestTemplate(
                test_name=data['test_name'],
                fields=json.dumps(data['fields']),
                normal_ranges=json.dumps(data['normal_ranges'])
            )
            db.session.add(new_tpl)
            print(f"Created {data['test_name']}")
    db.session.commit()
    print("Seed completed successfully!")
