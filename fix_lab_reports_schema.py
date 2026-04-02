"""
Fix lab_reports table schema to match the ORM model.
Adds missing columns: lab_order_id, report_data
Drops removed column: report_file
Also ensures lab_test_templates table exists.
"""
import sys, os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from sqlalchemy import text

app = create_app()

MIGRATIONS = [
    # 1) Add lab_order_id if missing
    {
        "check": "SELECT 1 FROM information_schema.columns WHERE table_name='lab_reports' AND column_name='lab_order_id'",
        "run": "ALTER TABLE lab_reports ADD COLUMN lab_order_id INT NULL, ADD CONSTRAINT fk_labreport_order FOREIGN KEY (lab_order_id) REFERENCES lab_orders(id)",
        "label": "lab_reports.lab_order_id",
    },
    # 2) Add report_data (JSON) if missing
    {
        "check": "SELECT 1 FROM information_schema.columns WHERE table_name='lab_reports' AND column_name='report_data'",
        "run": "ALTER TABLE lab_reports ADD COLUMN report_data JSON NULL AFTER test_name",
        "label": "lab_reports.report_data",
    },
    # 3) Drop report_file if it still exists
    {
        "check_exists": "SELECT 1 FROM information_schema.columns WHERE table_name='lab_reports' AND column_name='report_file'",
        "run": "ALTER TABLE lab_reports DROP COLUMN report_file",
        "label": "DROP lab_reports.report_file",
    },
    # 4) Ensure lab_test_templates table exists
    {
        "check": "SELECT 1 FROM information_schema.tables WHERE table_name='lab_test_templates'",
        "run": """
            CREATE TABLE lab_test_templates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                test_name VARCHAR(100) NOT NULL UNIQUE,
                fields TEXT,
                normal_ranges TEXT
            )
        """,
        "label": "lab_test_templates table",
    },
]

with app.app_context():
    for m in MIGRATIONS:
        label = m["label"]
        try:
            if "check_exists" in m:
                # Run migration only if column EXISTS (i.e. we want to drop it)
                row = db.session.execute(text(m["check_exists"])).fetchone()
                if row:
                    print(f"  Dropping {label} ...")
                    db.session.execute(text(m["run"]))
                    db.session.commit()
                    print(f"  ✓ Dropped {label}")
                else:
                    print(f"  ✓ {label} already gone — skip")
            else:
                # Run migration only if column/table is MISSING
                row = db.session.execute(text(m["check"])).fetchone()
                if row:
                    print(f"  ✓ {label} already exists — skip")
                else:
                    print(f"  Adding {label} ...")
                    db.session.execute(text(m["run"]))
                    db.session.commit()
                    print(f"  ✓ Added {label}")
        except Exception as e:
            db.session.rollback()
            print(f"  ⚠ {label}: {e}")

    print("\nDone — lab_reports schema is now in sync with the ORM model.")
