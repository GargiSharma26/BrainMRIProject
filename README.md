[README.md](https://github.com/user-attachments/files/27231923/README.md)
# Brain MRI Multi-Disease Detection

An engineering final-year project that uses a Streamlit frontend and FastAPI backend to classify uploaded brain MRI images into four classes:

- Healthy Brain
- Brain Tumor
- Alzheimer's
- Multiple Sclerosis (MS)

The backend runs a trained Keras model, validates whether the uploaded image looks like a brain MRI, generates a Grad-CAM attention heatmap, and stores patient analysis records in a SQLite database.

> Important: This project is for educational demonstration only. It is not a medical diagnosis tool and must not replace professional clinical advice.

## Project Structure

```text
BrainMRIProject/
  Backend/
    main.py
    requirements.txt
    train_mri_validator.py
    model/
      final_brain_multi_disease_model.keras
      mri_validator.keras
  Frontend/
    app.py
    requirements.txt
    pages/
      Dashboard.py
      Heatmap.py
      Login.py
      Reset_Password.py
    .streamlit/
      secrets.toml.example
  render.yaml
  PROJECT_RUN_GUIDE.md
  README.md
```

## Main Features

- Streamlit login and patient information workflow
- MRI upload with JPG, JPEG, and PNG support
- FastAPI prediction endpoint using TensorFlow/Keras
- MRI-vs-non-MRI validation before disease prediction
- Four-class disease prediction with confidence score
- Class probability score display
- Grad-CAM heatmap overlay
- Heatmap explanation: brighter colors indicate highest model attention and darker colors indicate little to no impact
- PDF report generation
- Patient record storage through a backend SQLite database
- Deployment-ready Render backend configuration

## How The App Works

1. The user opens the Streamlit app.
2. The user enters login and patient details.
3. The user uploads a brain MRI image.
4. Streamlit sends the image to the FastAPI backend.
5. The backend validates the image, runs the Keras disease model, and generates Grad-CAM.
6. The dashboard displays the prediction, confidence, class scores, and heatmap.
7. The backend stores a patient analysis record in the database.
8. The user can download a PDF report.

## Backend API Endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/` | GET | API home message |
| `/health` | GET | Backend, model, validator, and database status |
| `/model-info` | GET | Loaded model input/output shape and class names |
| `/validator-info` | GET | MRI validator status |
| `/predict` | POST | Upload an MRI image and receive prediction results |
| `/patient-records` | POST | Save a patient analysis record |
| `/patient-records` | GET | View recent saved patient records |
| `/files` | GET | Optional Google Drive file listing |
| `/download-model` | GET | Optional model download from Google Drive |

## Local Setup

### 1. Backend

Open PowerShell:

```powershell
cd C:\Users\Gargi\OneDrive\Desktop\BrainMRIProject\Backend
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 5055
```

Check these URLs:

- http://127.0.0.1:5055/health
- http://127.0.0.1:5055/model-info
- http://127.0.0.1:5055/validator-info

### 2. Frontend

Open a second PowerShell window:

```powershell
cd C:\Users\Gargi\OneDrive\Desktop\BrainMRIProject\Frontend
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The Streamlit app usually opens at:

```text
http://localhost:8501
```

## Deployment For Always-Available Sharing

If you share only a Streamlit link but the backend is running on your laptop, the app will stop working when your laptop sleeps, disconnects, or turns off. To make the project work for teammates and teachers from any system, deploy both parts online:

- Backend: Render Web Service
- Frontend: Streamlit Community Cloud
- Code hosting: GitHub

For a truly always-live demo, use an always-on Render instance. Free backend services can sleep after inactivity, which may show temporary backend connection errors while the service wakes up.

### Deploy Backend On Render

1. Push this repository to GitHub.
2. In Render, create a new Blueprint or Web Service.
3. Use `render.yaml` from the project root.
4. Confirm these backend settings:

```text
Root Directory: Backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

5. Add these environment variables:

```text
PYTHON_VERSION = 3.12.10
DATABASE_PATH = /var/data/brain_mri_records.db
GOOGLE_CREDENTIALS_JSON = your full Google service account JSON, if using Google Drive endpoints
```

6. Attach a Render persistent disk:

```text
Name: brain-mri-data
Mount Path: /var/data
Size: 1 GB
```

7. After deployment, test:

```text
https://your-render-service.onrender.com/health
https://your-render-service.onrender.com/model-info
https://your-render-service.onrender.com/patient-records
```

### Deploy Frontend On Streamlit Community Cloud

1. Create a Streamlit app from the same GitHub repository.
2. Set the app path:

```text
Frontend/app.py
```

3. Add this Streamlit secret:

```toml
API_BASE_URL = "https://your-render-service.onrender.com"
```

4. Redeploy the Streamlit app.

Now anyone with the Streamlit link can use the project without depending on your laptop.

## Patient Database

The backend stores patient analysis records in SQLite. Each record contains:

- Patient name
- Age
- Existing condition
- Symptoms
- Predicted class
- Confidence score
- Class probability scores
- MRI validation metadata
- UTC timestamp

Locally, the database is created as:

```text
Backend/brain_mri_records.db
```

On Render, it is configured as:

```text
/var/data/brain_mri_records.db
```

Do not commit database files to GitHub. They are ignored in `.gitignore`.

## GitHub Safety

Do not upload private secrets:

- `Backend/credentials.json`
- `Frontend/.streamlit/secrets.toml`
- Local database files such as `*.db`, `*.sqlite`, or `*.sqlite3`

Use Render environment variables and Streamlit secrets instead.

## Demo Login Values

Use values that pass validation:

```text
Full Name: Gargi
Username: Gargi@1
Password: 123456
Email: gargi@test.com
Phone: 9876543210
```

## Limitations

- The model is for project demonstration, not clinical use.
- The MRI validator improves rejection of screenshots and unrelated images, but it is not clinical-grade.
- Render free services may sleep after inactivity. Use an always-on backend plan for reliable teacher/demo access.
- SQLite with a persistent disk is suitable for a project demo. For production, use a managed database such as PostgreSQL.
