#!/usr/bin/env python
"""
Laboratory workflow regression checks (doctor-referred + walk-in LabOrder).

Run from project root: python test_lab_workflow.py

Requires the same database as the app (MySQL in dev). Creates no persistent data
when imports-only checks pass; optional integration block may be skipped.
"""
import os
import sys


def test_model_and_imports():
    from app.models.models import LabOrder, Billing
    assert LabOrder.__tablename__ == 'lab_orders'
    # Walk-in billing allows null doctor on ORM model
    col = LabOrder.__table__.c.get('doctor_id')
    assert col is not None
    doc_col = Billing.__table__.c.get('doctor_id')
    assert doc_col.nullable is True
    from app.routes.lab import (
        SOURCE_DOCTOR,
        SOURCE_WALK_IN,
        _validate_lab_order_source,
        _create_lab_order_row,
        LAB_ORDER_STATUSES,
    )
    assert _validate_lab_order_source(SOURCE_DOCTOR, 1) is True
    assert _validate_lab_order_source(SOURCE_DOCTOR, None) is False
    assert _validate_lab_order_source(SOURCE_WALK_IN, None) is True
    assert 'COMPLETED' in LAB_ORDER_STATUSES
    print('[OK] Model + lab route helpers')


def test_app_factory():
    os.environ.setdefault('FLASK_ENV', 'development')
    from app import create_app
    from app.models.models import db, LabOrder
    app = create_app()
    with app.app_context():
        db.create_all()
        c = LabOrder.query.count()
        assert c >= 0
    print('[OK] App factory + LabOrder query')


def main():
    test_model_and_imports()
    test_app_factory()
    print('All laboratory workflow checks passed.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print('[FAIL]', e)
        sys.exit(1)
