from sqlalchemy import inspect, text

from app import create_app
from app.models.models import db


def main():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        if 'prescriptions' not in inspector.get_table_names():
            print("Table 'prescriptions' not found.")
            return

        expected_columns = {
            'diagnosis': "TEXT",
            'notes': "TEXT",
            'medicines': "TEXT",
            'duration': "VARCHAR(100)",
            'diet_recommendations': "TEXT",
            'exercise_recommendations': "TEXT",
            'expiry_date': "DATETIME",
            'image_path': "VARCHAR(255)",
            'is_verified': "BOOLEAN DEFAULT 0",
            'refill_requested': "BOOLEAN DEFAULT 0",
            'refill_status': "VARCHAR(50)",
        }

        existing = {c['name'] for c in inspector.get_columns('prescriptions')}
        changed = False

        for col, ddl in expected_columns.items():
            if col in existing:
                continue
            try:
                db.session.execute(text(f"ALTER TABLE prescriptions ADD COLUMN {col} {ddl}"))
                print(f"Added prescriptions.{col}")
                changed = True
            except Exception as e:
                print(f"Failed prescriptions.{col}: {e}")

        existing = {c['name'] for c in inspect(db.engine).get_columns('prescriptions')}

        try:
            if 'medicines' in existing and 'medicine_name' in existing:
                db.session.execute(text(
                    "UPDATE prescriptions SET medicines = medicine_name "
                    "WHERE (medicines IS NULL OR medicines = '') AND medicine_name IS NOT NULL"
                ))
                changed = True
            if 'medicines' in existing:
                db.session.execute(text(
                    "UPDATE prescriptions SET medicines = '[]' "
                    "WHERE medicines IS NULL OR medicines = ''"
                ))
                changed = True
            if 'duration' in existing and 'duration_days' in existing:
                db.session.execute(text(
                    "UPDATE prescriptions SET duration = CONCAT(duration_days, ' days') "
                    "WHERE (duration IS NULL OR duration = '') AND duration_days IS NOT NULL"
                ))
                changed = True
            if 'expiry_date' in existing and 'expires_at' in existing:
                db.session.execute(text(
                    "UPDATE prescriptions SET expiry_date = expires_at "
                    "WHERE expiry_date IS NULL AND expires_at IS NOT NULL"
                ))
                changed = True
        except Exception as e:
            print(f"Backfill warning: {e}")

        if changed:
            db.session.commit()
            print("Schema sync completed.")
        else:
            print("No schema changes needed.")


if __name__ == "__main__":
    main()

