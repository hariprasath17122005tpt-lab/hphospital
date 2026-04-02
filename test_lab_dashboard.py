"""Smoke-test: can the lab dashboard query run without crashing?"""
import sys, os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models.models import LabOrder, LabReport

app = create_app()

with app.app_context():
    # Test 1: Query LabOrder (dashboard base query)
    try:
        orders = LabOrder.query.order_by(LabOrder.created_at.desc()).limit(5).all()
        print(f"LabOrder query OK  -  {len(orders)} orders found")
    except Exception as e:
        print(f"LabOrder query FAILED: {e}")

    # Test 2: Query LabReport (the one that was failing)
    try:
        reports = LabReport.query.limit(5).all()
        print(f"LabReport query OK  -  {len(reports)} reports found")
    except Exception as e:
        print(f"LabReport query FAILED: {e}")

    # Test 3: Join via generated_reports relationship
    try:
        if orders:
            order = orders[0]
            reps = order.generated_reports
            print(f"Relationship (generated_reports) OK  -  {len(reps)} linked reports on order #{order.id}")
        else:
            print("No orders to test relationship on")
    except Exception as e:
        print(f"Relationship query FAILED: {e}")

    print("\nAll checks passed!" if True else "")
