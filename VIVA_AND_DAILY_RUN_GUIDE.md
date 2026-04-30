# Brain MRI Project: Daily Run, Viva, Deployment, and Team Guide

This guide explains how to run the project daily, how the full system works, how patient data is stored, how to explain the project in viva, and what must be done to make the app available to others even when the laptop is off.

## 1. Important Project Truth

The project has two separate parts:

1. Backend API
   - Folder: `Backend`
   - Technology: FastAPI, TensorFlow/Keras, SQLite
   - Job: Loads the MRI model, predicts disease class, creates Grad-CAM heatmap, stores patient records.

2. Frontend Website
   - Folder: `Frontend`
   - Technology: Streamlit
   - Job: Shows login page, patient form, MRI uploader, prediction result, heatmap, and PDF report button.

Both parts must run at the same time.

If the frontend is running but backend is off, the app will show backend connection errors.

## 2. Python Version Rule

Always use Python 3.12 for this project.

Do not run the project with global Python 3.14 because TensorFlow is not installed/supported properly there.

The daily scripts created in this project force the app to use each folder's virtual environment:

- Backend script: `Backend\run_backend.ps1`
- Frontend script: `Frontend\run_frontend.ps1`

These scripts use:

```text
Backend\.venv\Scripts\python.exe
Frontend\.venv\Scripts\python.exe
```

So they avoid the global Python 3.14.

## 3. One-Time Setup

Only do this when setting up the project for the first time, or if `.venv` gets deleted.

### 3.1 Backend Setup

Open PowerShell:

```powershell
cd C:\Users\Gargi\OneDrive\Desktop\BrainMRIProject\Backend
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Check Python version:

```powershell
.\.venv\Scripts\python.exe --version
```

It should show Python 3.12.

### 3.2 Frontend Setup

Open another PowerShell:

```powershell
cd C:\Users\Gargi\OneDrive\Desktop\BrainMRIProject\Frontend
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Check Python version:

```powershell
.\.venv\Scripts\python.exe --version
```

It should show Python 3.12.

## 4. Daily Run Steps

Follow these steps every day. No coding is needed.

### Step 1: Start Backend

Open PowerShell:

```powershell
cd C:\Users\Gargi\OneDrive\Desktop\BrainMRIProject\Backend
.\run_backend.ps1
```

Keep this PowerShell window open.

Backend local URL:

```text
http://127.0.0.1:5055
```

Check backend health:

```text
http://127.0.0.1:5055/health
```

### Step 2: Start Frontend

Open a second PowerShell window:

```powershell
cd C:\Users\Gargi\OneDrive\Desktop\BrainMRIProject\Frontend
.\run_frontend.ps1
```

Keep this PowerShell window open.

Streamlit will show a local URL like:

```text
http://localhost:8501
```

Open that link in the browser.

### Step 3: Use The App

1. Fill login details.
2. Fill patient details.
3. Upload brain MRI image.
4. Click Analyze MRI.
5. View prediction, confidence, class scores, and Grad-CAM heatmap.
6. Download PDF report if needed.

## 5. If Laptop Is Off, Can Other People Use It?

Locally, no.

If backend and frontend are running only on the laptop, then teammates and teachers cannot use the full project after the laptop is turned off, disconnected, or sleeping.

To make the app usable by anyone anytime, deploy it online:

- Backend must be deployed on Render.
- Frontend must be deployed on Streamlit Community Cloud.
- Streamlit must point to the Render backend URL using `API_BASE_URL`.

For truly always-live use, use an always-on Render backend plan. Free Render services can sleep after inactivity and may take time to wake up.

## 6. Online Deployment Setup

### 6.1 Backend On Render

Use the project file:

```text
render.yaml
```

Render backend settings:

```text
Root Directory: Backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

Environment variables:

```text
PYTHON_VERSION = 3.12.10
DATABASE_PATH = /var/data/brain_mri_records.db
GOOGLE_CREDENTIALS_JSON = full service account JSON if Google Drive endpoints are needed
```

Persistent disk:

```text
Name: brain-mri-data
Mount Path: /var/data
Size: 1 GB
```

Important reason for persistent disk:

Render normally has an ephemeral filesystem, meaning files created by the running service can be lost after restart/redeploy. The persistent disk keeps the SQLite patient database available.

### 6.2 Frontend On Streamlit Community Cloud

Streamlit app path:

```text
Frontend/app.py
```

Add this Streamlit secret:

```toml
API_BASE_URL = "https://your-render-backend-url.onrender.com"
```

After this, Streamlit will call the online Render backend instead of your laptop.

## 7. Patient Data Storage

Patient records are stored by the backend in SQLite.

Local database file:

```text
C:\Users\Gargi\OneDrive\Desktop\BrainMRIProject\Backend\brain_mri_records.db
```

Render database path:

```text
/var/data/brain_mri_records.db
```

The database stores:

- Patient name
- Age
- Existing condition
- Symptoms
- Prediction
- Confidence score
- Class probability scores
- MRI validation metadata
- Date and time of analysis

## 8. How To Access Patient Data

### Method 1: Browser API

Start backend, then open:

```text
http://127.0.0.1:5055/patient-records
```

On deployed Render backend:

```text
https://your-render-backend-url.onrender.com/patient-records
```

This shows recent saved records in JSON format.

### Method 2: SQLite Viewer

Use any SQLite database viewer, such as:

- DB Browser for SQLite
- VS Code SQLite extension

Open this file:

```text
C:\Users\Gargi\OneDrive\Desktop\BrainMRIProject\Backend\brain_mri_records.db
```

Table name:

```text
patient_records
```

### Method 3: PowerShell Quick Check

If SQLite command-line tools are installed, use:

```powershell
sqlite3 C:\Users\Gargi\OneDrive\Desktop\BrainMRIProject\Backend\brain_mri_records.db "SELECT * FROM patient_records;"
```

If `sqlite3` is not installed, use the browser API method.

## 9. Heatmap Explanation

The project includes Grad-CAM heatmap output.

The dashboard shows this explanation below the heatmap:

```text
Brighter colors (yellow/white) showing highest attention and darker colors (blue/black) showing little to no impact.
```

Meaning:

- Yellow/white areas: The AI model focused strongly on those image regions.
- Blue/black areas: Those regions had little or no effect on the final prediction.

This helps make the model result more explainable during demonstration.

## 10. Technology Stack

### Frontend

- Streamlit
- Requests
- ReportLab
- Pillow

Frontend responsibilities:

- User login form
- Patient form
- MRI image upload
- Calling backend API
- Showing prediction result
- Showing confidence score
- Showing class scores
- Showing Grad-CAM heatmap
- Generating downloadable PDF report

### Backend

- FastAPI
- Uvicorn
- TensorFlow/Keras
- NumPy
- Pillow
- SQLite
- Google Drive API support

Backend responsibilities:

- API server
- Image validation
- MRI disease prediction
- Grad-CAM generation
- Patient record storage
- Model info and health status endpoints

### Machine Learning

- Model type: Keras deep learning model
- Input size: 224 x 224 RGB image
- Output classes:
  - Healthy Brain
  - Brain Tumor
  - Alzheimer's
  - Multiple Sclerosis (MS)

### Database

- SQLite for local/project-level storage
- Persistent disk path on Render for deployment

## 11. Viva Explanation

This project is a web-based Brain MRI Multi-Disease Detection system. It uses a Streamlit frontend for user interaction and a FastAPI backend for model inference. The user uploads a brain MRI image, and the backend preprocesses it to the required model size. A trained Keras model predicts one of four possible classes: Healthy Brain, Brain Tumor, Alzheimer's, or Multiple Sclerosis.

Before prediction, the backend checks whether the uploaded image appears to be a valid MRI image. This prevents unrelated images, screenshots, and documents from being directly passed into the disease classifier. After prediction, the system calculates the confidence score and class probability scores.

To improve explainability, the backend generates a Grad-CAM heatmap. This heatmap highlights image regions that influenced the model's prediction. Brighter yellow/white areas show stronger model attention, while darker blue/black regions show little or no effect on the prediction.

The system also stores patient analysis records in a SQLite database. This allows previous analysis data to be reviewed using the `/patient-records` API endpoint or a SQLite viewer. For deployment, the backend can be hosted on Render and the frontend on Streamlit Community Cloud. This makes the project accessible through a public link without depending on the local laptop.

## 12. Common Errors And Fixes

### Error: TensorFlow Not Found

Cause:

The project is using global Python 3.14 instead of Python 3.12 virtual environment.

Fix:

Use the daily scripts:

```powershell
.\run_backend.ps1
.\run_frontend.ps1
```

### Error: Backend Not Connected

Cause:

Backend is not running, backend URL is wrong, or Render backend is sleeping.

Fix:

Local:

```text
Start Backend\run_backend.ps1
```

Online:

```text
Set Streamlit API_BASE_URL to the Render backend URL.
```

### Error: No Streamlit Secrets Found

This has been handled in the code. Local runs use:

```text
http://127.0.0.1:5055
```

Online runs should use Streamlit secrets:

```toml
API_BASE_URL = "https://your-render-backend-url.onrender.com"
```

## 13. Files Created For Easy Running

Backend daily launcher:

```text
C:\Users\Gargi\OneDrive\Desktop\BrainMRIProject\Backend\run_backend.ps1
```

Frontend daily launcher:

```text
C:\Users\Gargi\OneDrive\Desktop\BrainMRIProject\Frontend\run_frontend.ps1
```

Main README:

```text
C:\Users\Gargi\OneDrive\Desktop\BrainMRIProject\README.md
```

This viva and daily guide:

```text
C:\Users\Gargi\OneDrive\Desktop\BrainMRIProject\VIVA_AND_DAILY_RUN_GUIDE.md
```

## 14. Final Daily Checklist

1. Open PowerShell for backend.
2. Run:

```powershell
cd C:\Users\Gargi\OneDrive\Desktop\BrainMRIProject\Backend
.\run_backend.ps1
```

3. Open second PowerShell for frontend.
4. Run:

```powershell
cd C:\Users\Gargi\OneDrive\Desktop\BrainMRIProject\Frontend
.\run_frontend.ps1
```

5. Open Streamlit local URL.
6. Use the app.
7. Keep both PowerShell windows open while using the project.

