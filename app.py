import os
from time import sleep
from dotenv import load_dotenv
from app import create_app, db
from sqlalchemy import text

load_dotenv()

# Build app
app = create_app(os.environ.get('FLASK_ENV', 'development'))

# Wait for MySQL readiness (retry logic)
def wait_for_database(timeout=60, interval=2):
    attempts = int(timeout / interval)
    for i in range(attempts):
        try:
            with app.app_context():
                db.session.execute(text('SELECT 1'))
            print("Database connected")
            return
        except Exception as ex:
            print("Waiting for database... (attempt %d/%d)" % (i + 1, attempts), ex)
            sleep(interval)
    raise RuntimeError("Could not connect to database after %s seconds" % timeout)

wait_for_database()

@app.route('/')
def hello():
    return 'CarePoint Hospital Management System is running!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
