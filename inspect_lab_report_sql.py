import pymysql

conn = pymysql.connect(
    host='localhost', port=3307,
    user='hospital_user', password='Mysql',
    database='hospital_db',
    cursorclass=pymysql.cursors.DictCursor
)
cur = conn.cursor()
cur.execute("SELECT id, lab_order_id, test_name, report_data FROM lab_reports ORDER BY id desc LIMIT 5")
for r in cur.fetchall():
    print(r)
cur.execute("SELECT id, patient_id, test_name, status, result_data FROM lab_orders ORDER BY id desc LIMIT 5")
for r in cur.fetchall():
    print(r)
cur.close()
conn.close()
