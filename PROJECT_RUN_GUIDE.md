# Brain MRI Multi-Disease Detection Project

This project uses a Streamlit frontend, a FastAPI backend, Google Drive model storage, and a trained Keras model for brain MRI classification.

## Features

- Login and patient information form
- Brain MRI image upload
- Real Keras model prediction through FastAPI
- Four output classes:
  - Healthy Brain
  - Brain Tumor
  - Alzheimer's
  - Multiple Sclerosis (MS)
- Confidence score and class probability display
- MRI-vs-non-MRI validation model support
- Grad-CAM heatmap overlay for model explainability
- PDF report generation
- Google Drive integration for model/file listing

## Important Note

This is an educational engineering project. It is not a medical diagnosis tool and must not replace professional clinical advice.

## Backend Setup

Open PowerShell:

```powershell
cd C:\Users\Gargi\OneDrive\Desktop\BrainMRIProject\Backend
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 5055
```

Backend URLs:

- API home: http://127.0.0.1:5055
- API docs: http://127.0.0.1:5055/docs
- Health check: http://127.0.0.1:5055/health
- Model info: http://127.0.0.1:5055/model-info
- Validator info: http://127.0.0.1:5055/validator-info
- Download model: http://127.0.0.1:5055/download-model

## Train MRI Validator

The disease model always predicts one of the four disease classes. To reject screenshots, code images, and unrelated photos, train the separate MRI validator:

```powershell
cd C:\Users\Gargi\OneDrive\Desktop\BrainMRIProject\Backend
.\.venv\Scripts\activate
python train_mri_validator.py
```

This creates:

```text
C:\Users\Gargi\OneDrive\Desktop\BrainMRIProject\Backend\model\mri_validator.keras
```

After training, restart the backend. Then `/predict` will first check whether the uploaded image looks like a brain MRI. If it is not an MRI, the API rejects it before running disease classification.

## Frontend Setup

Open a second PowerShell window:

```powershell
cd C:\Users\Gargi\OneDrive\Desktop\BrainMRIProject\Frontend
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Frontend URL:

- Usually http://localhost:8501

## Demo Login Values

Use any values that pass validation. Example:

```text
Full Name: Gargi
Username: Gargi@1
Password: 123456
Email: gargi@test.com
Phone: 9876543210
```

## Project Workflow

1. Start FastAPI backend on port 5055.
2. Confirm `/health` and `/model-info` work.
3. Start Streamlit frontend.
4. Login.
5. Fill patient details.
6. Upload a brain MRI image.
7. Click Analyze MRI.
8. Review prediction, confidence, class scores, Grad-CAM heatmap, and download the PDF report.

## Current Limitation

The MRI validator improves rejection of screenshots and unrelated images, but it is still a lightweight project-level validator. For clinical-grade reliability, it should be trained with a larger and more diverse non-MRI dataset.

## Deployment Plan

Recommended setup:

- Backend: Render
- Frontend: Streamlit Community Cloud
- Code hosting: GitHub

### Safety Before GitHub

Do not upload this file publicly:

```text
Backend\credentials.json
```

The project includes `.gitignore` to avoid committing it. On Render, add the service account JSON as an environment variable instead:

```text
GOOGLE_CREDENTIALS_JSON
```

Paste the full JSON content from `credentials.json` as the value.

### Deploy Backend on Render

1. Push the project to GitHub.
2. Go to Render and create a new Blueprint or Web Service.
3. Use the included `render.yaml`, or configure manually:

```text
Root Directory: Backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

4. Add environment variable:

```text
GOOGLE_CREDENTIALS_JSON = full credentials JSON
```

5. After deployment, test:

```text
https://your-render-url.onrender.com/health
https://your-render-url.onrender.com/model-info
https://your-render-url.onrender.com/validator-info
```

### Deploy Frontend on Streamlit Community Cloud

1. Create a Streamlit app from the same GitHub repo.
2. Set the app path:

```text
Frontend/app.py
```

3. Add this Streamlit secret:

```toml
API_BASE_URL = "https://your-render-url.onrender.com"
```

4. Deploy and open the Streamlit URL.

### Local vs Deployed Backend URL

Locally, the frontend uses:

```text
http://127.0.0.1:5055
```

Online, it uses the `API_BASE_URL` secret or environment variable.
