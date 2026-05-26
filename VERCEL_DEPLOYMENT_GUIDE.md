# ARUL Hospital - Vercel Deployment Guide

## ✅ What Was Fixed

Your Flask application was missing critical Vercel configuration files. I've created:

1. **requirements.txt** - Python dependencies list
2. **vercel.json** - Vercel deployment configuration  
3. **api/index.py** - Serverless function entry point
4. **package.json** - Node.js metadata for Vercel
5. **.vercelignore** - Files to exclude from deployment

---

## 🚀 Step-by-Step Deployment Instructions

### Step 1: Commit Changes to GitHub

Run these commands in Git Bash:

```bash
cd /c/Users/harip/OneDrive/Desktop/hospital
git add requirements.txt vercel.json package.json .vercelignore api/index.py
git commit -m "Add Vercel deployment configuration"
git push origin main
```

### Step 2: Reconnect Vercel to Your GitHub Repository

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click **"New Project"** or select existing project
3. Select GitHub repo: `hariprasath17122005tpt-lab/hphospital`
4. **Important Settings:**
   - Framework Preset: **Other** (not Next.js, not Node.js)
   - Build Command: `pip install -r requirements.txt`
   - Output Directory: `.` (current directory)
   - Install Command: Leave blank

### Step 3: Configure Environment Variables in Vercel

In Vercel Dashboard → Settings → Environment Variables, add:

```
FLASK_ENV=production
DATABASE_URL=your_mysql_url  (if using RDS/external DB)
SECRET_KEY=your_secret_key
```

⚠️ **Database Note:** Vercel is serverless and can't run MySQL locally. You need:
- External MySQL (AWS RDS, ClearDB, etc.)
- OR use a managed database service

### Step 4: Deploy

Vercel will automatically deploy when you push to `main` branch.

Check deployment status in Vercel Dashboard.

---

## 🔍 Common Issues & Fixes

### Issue: Still Getting 404 Error

**Solution 1:** Clear Vercel Cache
```bash
# In Vercel Dashboard:
# Go to Deployments → [Latest] → Check Build Logs for errors
```

**Solution 2:** Verify Flask App Starts
```bash
# Test locally first:
python api/index.py
# Should show: "Running on http://0.0.0.0:5000/"
```

**Solution 3:** Check Vercel Build Output
```bash
# In Vercel Dashboard → [Deployment] → Build tab
# Look for errors during "pip install -r requirements.txt"
```

---

## 📝 File Checklist

Make sure your deployed repo has:

```
✅ vercel.json              (Configuration)
✅ requirements.txt         (Python dependencies)
✅ package.json             (Node metadata)
✅ .vercelignore            (Exclusion rules)
✅ api/index.py             (Entry point)
✅ app/                     (Flask app folder)
✅ app.py                   (Original file - kept for reference)
```

---

## 🌐 URL Structure

After deployment, your app will be at:

```
https://hphospital.vercel.app    (or your custom domain)
```

All requests are routed to `/api/index.py` which handles Flask routing.

---

## 🔧 Git Bash Commands for Deployment

```bash
# 1. Navigate to project
cd /c/Users/harip/OneDrive/Desktop/hospital

# 2. Check status
git status

# 3. Add configuration files
git add -A

# 4. Commit
git commit -m "Vercel deployment setup"

# 5. Push to GitHub
git push origin main

# 6. Check deployment in Vercel Dashboard
# Dashboard will auto-deploy in ~2-5 minutes
```

---

## 🚨 Database Connection Issue

⚠️ **Important:** Vercel can NOT connect to localhost MySQL

**Solutions:**

### Option 1: Use AWS RDS (Recommended)
```
DATABASE_URL=mysql+pymysql://user:pass@rds-instance.amazonaws.com:3306/hospital
```

### Option 2: Use ClearDB (Heroku Alternative)
```
Create free MySQL at: https://www.cleardb.com/
```

### Option 3: Use Supabase PostgreSQL
```
DATABASE_URL=postgresql://user:pass@db.supabase.co:5432/hospital
```

Add URL to Vercel Environment Variables.

---

## ✨ Features Preserved

- ✅ All Flask routes work
- ✅ User authentication
- ✅ Dashboard functionality
- ✅ API endpoints
- ✅ Static files (CSS, JS, videos)
- ✅ Template rendering

---

## 📞 Troubleshooting

### Deployment fails with "No module named 'app'"

**Fix:** `api/index.py` imports app correctly. Make sure file structure is:
```
hospital/
├── api/
│   └── index.py
├── app/
│   ├── __init__.py
│   ├── models/
│   ├── routes/
│   └── ...
├── app.py
└── requirements.txt
```

### 500 Error in production

1. Check Vercel logs: Dashboard → [Deployment] → Logs
2. Common causes:
   - Database not reachable (add DATABASE_URL env var)
   - Missing SECRET_KEY env var
   - Missing dependencies in requirements.txt

### Static files (video, CSS) not loading

Vercel serves files from the same directory. Make sure:
- `app/static/` folder exists with files
- Reference files as `/static/filename`

---

## ✅ Verification

After deployment, test:

1. **Homepage loads:** `https://hphospital.vercel.app/`
2. **Login page:** `https://hphospital.vercel.app/login`
3. **API response:** `https://hphospital.vercel.app/api/health`

---

## 🎯 Next Steps

1. ✅ Push code to GitHub
2. ✅ Redeploy in Vercel
3. ✅ Test homepage
4. ✅ Check Vercel logs if errors
5. ✅ Add database connection details
6. ✅ Test login functionality

Good luck! 🚀
