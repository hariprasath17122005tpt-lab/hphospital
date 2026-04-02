-- ============================================================
--  Hospital Management System — AWS RDS MySQL Setup Script
--  Run this ONCE after creating your RDS instance to prepare
--  the database, user, and privileges.
--
--  Connect as root/admin:
--    mysql -h <rds-endpoint> -u admin -p < aws_rds_setup.sql
--
--  Or via MySQL Workbench / DBeaver
-- ============================================================

-- 1. Create the database (if it doesn't already exist)
CREATE DATABASE IF NOT EXISTS hospital_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- 2. Create a dedicated app user (replace 'securepassword' with a real one)
-- IMPORTANT: Use the SAME credentials you put in .env.production
CREATE USER IF NOT EXISTS 'hospital_user'@'%'
    IDENTIFIED WITH caching_sha2_password BY 'securepassword';

-- 3. Grant only what the app needs — never use GRANT ALL in production
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP
    ON hospital_db.*
    TO 'hospital_user'@'%';

-- 4. Apply changes
FLUSH PRIVILEGES;

-- 5. Verify
SHOW GRANTS FOR 'hospital_user'@'%';
