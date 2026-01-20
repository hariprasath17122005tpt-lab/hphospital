# 🏥 MySQL Integration Guide for Hospital Management System

## Overview
Your Hospital Management System has been updated to use **MySQL Workbench** for data storage instead of SQLite. The AI chatbot code remains **completely untouched** as requested.

---

## 📋 Quick Setup Steps

### Step 1: Install MySQL Server (if not already installed)
1. Download MySQL Community Server from: https://dev.mysql.com/downloads/mysql/
2. Run the installer
3. Choose "Server only" option
4. Keep default settings (Port: 3306)
5. Complete installation

### Step 2: Verify MySQL is Running
```powershell
# Check if MySQL is running
netstat -ano | findstr :3306

# Or start MySQL service (Windows)
net start MySQL80
```

### Step 3: Install Python MySQL Dependencies
```powershell
cd c:\Users\harip\OneDrive\Desktop\hospital
python install_mysql_dependencies.py
```

### Step 4: Create Database and User
```powershell
cd c:\Users\harip\OneDrive\Desktop\hospital
python setup_mysql_db.py
```

When prompted:
- **MySQL root username**: `root` (or your configured root username)
- **MySQL root password**: (the password you set during MySQL installation)

The script will:
- ✅ Create database `hospital_db`
- ✅ Create user `hospital_user` with password `Mysql`
- ✅ Grant all necessary privileges
- ✅ Create all required tables automatically

### Step 5: Start Your Application
```powershell
cd c:\Users\harip\OneDrive\Desktop\hospital
python run_server_stable.py
```

---

## 📊 Database Structure

### Tables Created:
1. **hospitals** - Hospital information and multi-tenancy
2. **users** - User accounts (patients, doctors, admins)
3. **patients** - Patient profiles and medical history
4. **doctors** - Doctor profiles and specializations
5. **health_data** - Patient vital signs and risk assessments
6. **appointments** - Doctor-patient appointments
7. **prescriptions** - Medication prescriptions
8. **messages** - Doctor-patient messaging
9. **ai_chatbot_history** - AI chatbot interaction logs
10. **medical_records** - Patient medical records
11. **notifications** - System notifications

---

## 🔐 Database Credentials

```
Database: hospital_db
Username: hospital_user
Password: Mysql
Host: localhost
Port: 3307
```

---

## 📝 SQL Reference

### Manual Database Setup (Alternative)

If you prefer to set up manually, use MySQL Workbench:

1. Open MySQL Workbench
2. Connect to your MySQL server (root login)
3. Open SQL editor (Ctrl+Shift+O)
4. Paste content from: `mysql_database_setup.sql`
5. Execute (Ctrl+Enter)

### Verify Database Created:
```sql
SHOW DATABASES;
USE hospital_db;
SHOW TABLES;
```

### Check User Creation:
```sql
SELECT User, Host FROM mysql.user;
SHOW GRANTS FOR 'hospital_user'@'localhost';
```

---

## ⚙️ Configuration Files Updated

### `.env` (Environment Variables)
```env
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your_secret_key_here_change_in_production

# MySQL Configuration
DB_USER=hospital_user
DB_PASSWORD=Mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=hospital_db
```

### `config.py` (Flask Configuration)
```python
SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
```

---

## 🧪 Testing Your Setup

### Test 1: Database Connection
```python
python -c "
from config import Config
import mysql.connector

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='hospital_user',
        password='Mysql',
        database='hospital_db'
    )
    print('✅ MySQL Connection Successful!')
    conn.close()
except Exception as e:
    print(f'❌ Connection Failed: {e}')
"
```

### Test 2: Flask Application Health
```powershell
python verify_app_health.py
```

### Test 3: Check Database Tables
```python
python check_db_rows.py
```

---

## 🔄 AI Chatbot Integration

The AI chatbot code **remains untouched**. It continues to use:
- ✅ Flask backend (no changes)
- ✅ Ollama neural-chat model (no changes)
- ✅ System prompts (no changes)
- ✅ Routes and API endpoints (no changes)

**Data Storage:**
- Chatbot queries are logged in `ai_chatbot_history` table
- Patient context is pulled from `patients` table
- Doctor information from `doctors` table

---

## 🚀 Common Commands

### Start Application
```powershell
cd c:\Users\harip\OneDrive\Desktop\hospital
python run_server_stable.py
```

### Access Web Interface
```
http://localhost:5000
```

### Reset Database (Full Clean)
```powershell
# Drop and recreate everything
python setup_mysql_db.py

# When prompted, confirm you want to drop existing database
```

### Backup Database
```powershell
# Export database to SQL file
mysqldump -u hospital_user -pMysql hospital_db > hospital_db_backup.sql
```

### Restore Database
```powershell
# Import from backup
mysql -u hospital_user -pMysql hospital_db < hospital_db_backup.sql
```

---

## ⚠️ Troubleshooting

### Issue: "MySQL Connection Refused"
```powershell
# Check MySQL service status
Get-Service | findstr MySQL

# Start MySQL service
net start MySQL80
```

### Issue: "Access Denied for user 'hospital_user'"
```sql
-- Reset password as root
ALTER USER 'hospital_user'@'localhost' IDENTIFIED BY 'Mysql';
FLUSH PRIVILEGES;
```

### Issue: "Database hospital_db does not exist"
```powershell
# Recreate database
python setup_mysql_db.py
```

### Issue: "Table not found"
```powershell
# Rebuild all tables
python setup_mysql_db.py
```

---

## 📁 New Files Added

| File | Purpose |
|------|---------|
| `mysql_database_setup.sql` | Complete SQL schema and initialization |
| `setup_mysql_db.py` | Automated database and user creation |
| `install_mysql_dependencies.py` | Install MySQL Python packages |
| `MYSQL_SETUP_GUIDE.md` | This guide |

---

## 🛡️ Security Notes

1. **Change Default Password**: Update `Mysql` to a strong password
   ```sql
   ALTER USER 'hospital_user'@'localhost' IDENTIFIED BY 'your_new_password';
   ```

2. **Update .env file**: Change password in `.env` if modified

3. **Restrict User Access**: Remove unnecessary privileges
   ```sql
   REVOKE ALL PRIVILEGES ON *.* FROM 'hospital_user'@'%';
   ```

4. **Use SSL for Production**: Configure MySQL SSL certificates

5. **Backup Regularly**: Use mysqldump for automated backups

---

## 📞 Support

If you encounter issues:

1. **Check MySQL logs**: `C:\ProgramData\MySQL\MySQL Server 8.0\Data\`
2. **Check Flask logs**: Console output when running `run_server_stable.py`
3. **Verify credentials**: Double-check `.env` file
4. **Test connection**: Run the test command above

---

## ✅ Verification Checklist

- [ ] MySQL Server installed and running
- [ ] Python dependencies installed (`pip install -r requirements.txt`)
- [ ] Database created: `hospital_db`
- [ ] User created: `hospital_user` with password `Mysql`
- [ ] All tables created (11 tables total)
- [ ] Flask application starts without errors
- [ ] Web interface accessible at `http://localhost:5000`
- [ ] Chatbot responds to queries

---

**Setup Date**: December 27, 2025
**Database Type**: MySQL 8.0+
**Python Version**: 3.8+
**Flask Version**: 2.3.3
