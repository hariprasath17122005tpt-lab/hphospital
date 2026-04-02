from app import create_app, db
from sqlalchemy import text

app = create_app()

def fix_schema():
    with app.app_context():
        print("Checking/Updating HealthData schema...")
        
        columns_to_add = [
            ("temperature", "FLOAT"),
            ("diabetes_risk", "FLOAT"),
            ("heart_disease_risk", "FLOAT"),
            ("hypertension_risk", "FLOAT"),
            ("bmi", "FLOAT"),
            ("bmi_category", "VARCHAR(50)"),
            ("smoking", "BOOLEAN"),
            ("alcohol", "BOOLEAN"),
            ("exercise_minutes", "INTEGER"),
            ("sleep_hours", "FLOAT"),
            ("stress_level", "VARCHAR(50)")
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                db.session.execute(text(f"ALTER TABLE health_data ADD COLUMN {col_name} {col_type}"))
                db.session.commit()
                print(f"✅ Added {col_name} to health_data")
            except Exception as e:
                # Column likely exists
                db.session.rollback()
                print(f"ℹ️ Could not add {col_name} (might already exist): {e}")

        print("Schema update complete.")

if __name__ == "__main__":
    fix_schema()
