"""Direct pymysql check - bypass SQLAlchemy entirely."""
import pymysql

conn = pymysql.connect(
    host='localhost', port=3307,
    user='hospital_user', password='Mysql',
    database='hospital_db'
)
cur = conn.cursor()
cur.execute("SHOW COLUMNS FROM lab_reports")
rows = cur.fetchall()
print("Columns in lab_reports table:")
for r in rows:
    print(f"  {r[0]:25s} {r[1]}")

print()
# Try the exact failing query
try:
    cur.execute("SELECT lab_order_id FROM lab_reports LIMIT 1")
    print("SELECT lab_order_id: OK")
except Exception as e:
    print(f"SELECT lab_order_id FAILED: {e}")

cur.close()
conn.close()
