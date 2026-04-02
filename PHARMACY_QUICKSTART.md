# PHARMACY SYSTEM - QUICK START & TEST GUIDE

## 🚀 QUICK START (5 MINUTES)

### 1. Seed Database
```bash
python seed_medicines.py
```
Expected output: ✅ Seeding complete! Total medicines in database: 15

### 2. Restart Docker
```bash
docker compose down
docker compose up --build
```

### 3. Access System
```
http://localhost:5000/pharmacy/manage
```

---

## ✅ TESTING - THE 3 METHODS

### METHOD 1: EXCEL UPLOAD
1. Go to "1) Upload Medicines" section
2. Create Excel file with:
   ```
   medicine_name | brand | category | price | stock | supplier
   Aspirin       | Ecosprin | Pain Relief | 5 | 100 | Supplier1
   ```
3. Click "Upload" button
4. See success: "Inserted: 1, Updated: 0"

---

### METHOD 2: AUTOCOMPLETE SEARCH (CRITICAL TEST)
1. Go to "2) Search Medicines" section
2. Type: `par`
3. **MUST SEE DROPDOWN WITH:**
   - Paracetamol (Calpol, ₹10, Stock: 500)
   - Any other medicines matching
4. Click on "Paracetamol"
5. Input fills automatically ✓
6. Medicine info shows below dropdown ✓

---

### METHOD 3A: MANUAL ADD
1. Go to "3) Add Medicine Manually" section
2. Fill form:
   - Name: Paracetamol 1000mg
   - Brand: TestBrand
   - Category: Analgesic
   - Price: 15
   - Stock: 200
   - Supplier: TestSupplier
3. Click "Add Medicine"
4. See success alert ✓

---

### METHOD 3B: ADD STOCK MODAL (KEY TEST)
1. Click "Add Stock" button in header
2. Modal opens with autocomplete field
3. Type: `par`
4. See dropdown with suggestions
5. Click "Paracetamol"
6. **VERIFY MEDICINE INFO APPEARS:**
   - Name: Paracetamol
   - Brand: Calpol
   - Current Stock: 500 units
   - Price: ₹10
7. Enter Quantity: 50
8. Click "Add Stock"
9. See success: "Added 50 units to stock!" ✓
10. Database stock updated to 550 ✓

---

## 🔍 VERIFICATION CHECKLIST

### Frontend
- [ ] Page loads without JS errors
- [ ] All 3 sections visible
- [ ] Buttons are styled correctly
- [ ] Dark theme applied

### Autocomplete Search (MAIN)
- [ ] Typing < 2 chars shows no dropdown
- [ ] Typing 2+ chars shows dropdown
- [ ] Results show name, brand, price, stock
- [ ] Hover shows different background
- [ ] Click fills input field
- [ ] Click outside closes dropdown
- [ ] Different searches return different results

### Autocomplete Search (MODAL)
- [ ] Modal opens when clicking "Add Stock"
- [ ] Autocomplete works in modal
- [ ] Results match main search
- [ ] Selection updates blue info box
- [ ] Close modal without selecting works

### File Upload
- [ ] File input accepts .xlsx and .csv
- [ ] Shows upload success
- [ ] Medicines appear in search results

### Manual Add Form
- [ ] All fields accept input
- [ ] Name is required (can't submit empty)
- [ ] Form resets after successful submit
- [ ] Medicine appears in search results

### Add Stock Modal
- [ ] Quantity field accepts numbers
- [ ] Minimum quantity is 1
- [ ] Stock is added (not replaced)
- [ ] Old stock + quantity = new stock
- [ ] Modal closes after successful add

---

## 🐛 DEBUGGING - CHECK THESE IF ISSUES

### Autocomplete Not Working
```javascript
// Open browser console (F12) and check:
1. No red errors in Console tab
2. Network tab shows /pharmacy/search API calls
3. Responses show valid JSON arrays

// Test manually in console:
fetch('/pharmacy/search?q=par')
  .then(r => r.json())
  .then(d => console.log(d))
```

### Database Empty
```sql
-- SSH into Docker MySQL and run:
SELECT COUNT(*) FROM medicines;
-- Should show: 15+

-- If 0, run:
docker exec -it hospital-db-1 mysql -u hospital -p hospital
python seed_medicines.py
```

### Add Stock Returns Error
1. Check if medicine_id is correct
2. Ensure quantity is positive integer
3. Verify medicine exists in database
4. Check browser console for response details

---

## 📊 TEST DATA

After seeding, should have:
```
1. Paracetamol      | Calpol          | 10.0  | 500
2. Dolo 650         | Dolo            | 12.0  | 450
3. Crocin           | GlaxoSmithKline | 15.0  | 400
4. Azithromycin     | Zithromax       | 85.0  | 300
5. Amoxicillin      | Amoxil          | 45.0  | 350
6. Ibuprofen        | Brufen          | 20.0  | 600
7. Insulin          | Insulin Aspart  | 350.0 | 150
8. Metformin        | Glucophage      | 25.0  | 800
9. Lisinopril       | Prinivil        | 30.0  | 400
10. Atorvastatin    | Lipitor         | 45.0  | 500
11. Omeprazole      | Prilosec        | 18.0  | 550
12. Ranitidine      | Zantac          | 12.0  | 400
13. Aspirin         | Ecosprin        | 5.0   | 1000
14. Thiopental      | Sodium Pentothal| 120.0 | 100
15. Diclofenac      | Voltaren        | 22.0  | 350
```

---

## 🎯 SUCCESS CRITERIA

### ✅ PASS if:
- [x] All 3 methods work without errors
- [x] Autocomplete shows results for 2+ chars
- [x] Modal autocomplete works independently
- [x] Add Stock increases medicine stock correctly
- [x] Excel upload creates multiple medicines
- [x] Manual add creates single medicine
- [x] No console errors
- [x] UI is responsive and styled

### ❌ FAIL if:
- Autocomplete returns nothing
- Modal doesn't open
- Add Stock doesn't update database
- Upload creates no medicines
- JavaScript errors in console
- CSS not applied (unstyled)

---

## 📝 LOG SAMPLE OUTPUT

After running seed_medicines.py:
```
============================================================
  Seeding Database with Sample Medicines
============================================================

Seeding 15 medicines...
  ✅ Added: Paracetamol - Calpol
  ✅ Added: Dolo 650 - Dolo
  ✅ Added: Crocin - GlaxoSmithKline
  ✅ Added: Azithromycin - Zithromax
  ✅ Added: Amoxicillin - Amoxil
  ✅ Added: Ibuprofen - Brufen
  ✅ Added: Insulin - Insulin Aspart
  ✅ Added: Metformin - Glucophage
  ✅ Added: Lisinopril - Prinivil
  ✅ Added: Atorvastatin - Lipitor
  ✅ Added: Omeprazole - Prilosec
  ✅ Added: Ranitidine - Zantac
  ✅ Added: Aspirin - Ecosprin
  ✅ Added: Thiopental - Sodium Pentothal
  ✅ Added: Diclofenac - Voltaren

✅ Seeding complete! Total medicines in database: 15
```

---

## 🔗 QUICK LINKS

- Pharmacy Management Page: http://localhost:5000/pharmacy/manage
- API Docs: See PHARMACY_SYSTEM_COMPLETE.md
- Seed Script: seed_medicines.py
- Frontend Template: app/templates/pharmacy/manage_medicines.html
- Backend Routes: app/routes/pharmacy.py

---

## 💡 TIPS FOR TESTING

1. Open browser DevTools before testing (F12)
2. Clear browser cache if styles not updating
3. Check Network tab if API calls failing
4. Use Firefox DevTools for better layout inspection
5. Test on mobile by resizing browser window

---

## ⏱️ EXPECTED TIMES

- Seeding database: < 1 second
- Docker build: 2-3 minutes
- Page load: < 500ms
- Autocomplete search: 250ms debounce + API
- Add Stock modal: Opens instantly
- Add Stock submit: < 1 second

---

## 🎓 LEARNING RESOURCES

For troubleshooting JavaScript:
- Browser DevTools (F12 → Console)
- Network tab for API calls
- Elements tab for DOM structure

For database issues:
- Check MySQL connection
- Verify table structure: DESCRIBE medicines;
- Query data: SELECT * FROM medicines LIMIT 5;
- Check indexes: SHOW INDEX FROM medicines;

---

STATUS: ✅ ALL SYSTEMS GO
Ready for testing and deployment!
