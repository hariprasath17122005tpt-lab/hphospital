-- Migration SQL Script: Add Walk-in Patient Support
-- This script adds the UHID and makes user_id optional in the patients table

-- Step 1: Add UHID column
ALTER TABLE patients 
ADD COLUMN uhid VARCHAR(20) UNIQUE NOT NULL DEFAULT '' AFTER user_id;

-- Step 2: Add is_walk_in column
ALTER TABLE patients 
ADD COLUMN is_walk_in BOOLEAN DEFAULT FALSE AFTER address;

-- Step 3: Make user_id nullable
ALTER TABLE patients 
MODIFY COLUMN user_id INT UNIQUE NULL;

-- Step 4: Add index on phone for faster search
ALTER TABLE patients 
ADD INDEX idx_phone (phone);

-- Step 5: Add index on UHID for fast lookup
ALTER TABLE patients 
ADD INDEX idx_uhid (uhid);

-- Step 6: Populate UHID for existing patients
-- This generates UHID in format PAT-YYYY-XXXX for existing records
SET @year = YEAR(NOW());
SET @counter = 0;

UPDATE patients 
SET uhid = CONCAT('PAT-', @year, '-', LPAD((SELECT COUNT(*) FROM patients p2 WHERE p2.id <= patients.id), 4, '0')),
    is_walk_in = FALSE
WHERE uhid = '';

-- Step 7: Ensure all UHIDs are unique
-- If there are duplicates, this will need manual intervention

-- Verification queries
SELECT COUNT(*) as total_patients FROM patients;
SELECT COUNT(DISTINCT uhid) as unique_uhids FROM patients;
SELECT COUNT(*) as walkin_patients FROM patients WHERE is_walk_in = TRUE;
SELECT COUNT(*) as registered_patients FROM patients WHERE user_id IS NOT NULL;

-- Migration complete
COMMIT;
