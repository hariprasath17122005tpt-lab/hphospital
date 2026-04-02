from app import create_app
from app.models.models import LabOrder, LabReport
app=create_app()
with app.app_context():
    r=LabReport.query.order_by(LabReport.id.desc()).first()
    o=LabOrder.query.order_by(LabOrder.id.desc()).first()
    print('LabReport', (r.id if r else None), 'order_id', (r.lab_order_id if r else None), 'test_name', (r.test_name if r else None), 'report_data', (r.report_data if r else None))
    print('LabOrder', (o.id if o else None), 'result_data', (o.result_data if o else None))
