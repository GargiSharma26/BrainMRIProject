import io
import base64
import os

import requests
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def get_api_base_url():
    default_url = os.getenv("API_BASE_URL", "http://127.0.0.1:5055")
    try:
        return st.secrets.get("API_BASE_URL", default_url).rstrip("/")
    except Exception:
        return default_url.rstrip("/")


API_BASE_URL = get_api_base_url()
PREDICT_URL = f"{API_BASE_URL}/predict"
HEALTH_URL = f"{API_BASE_URL}/health"
PATIENT_RECORDS_URL = f"{API_BASE_URL}/patient-records"


def create_pdf(name, age, condition, symptoms, prediction, confidence, scores):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    score_lines = [
        Paragraph(f"{label}: {score}%", styles["Normal"])
        for label, score in scores.items()
    ]

    elements = [
        Paragraph("Brain MRI Analysis Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph("<b>Patient Details</b>", styles["Heading2"]),
        Spacer(1, 8),
        Paragraph(f"Name: {name}", styles["Normal"]),
        Paragraph(f"Age: {age}", styles["Normal"]),
        Paragraph(f"Existing Condition: {condition}", styles["Normal"]),
        Paragraph(f"Symptoms: {symptoms or 'Not provided'}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("<b>AI Model Output</b>", styles["Heading2"]),
        Spacer(1, 8),
        Paragraph(f"Prediction: {prediction}", styles["Normal"]),
        Paragraph(f"Confidence: {confidence}%", styles["Normal"]),
        Spacer(1, 8),
        Paragraph("<b>Class Scores</b>", styles["Heading3"]),
        *score_lines,
        Spacer(1, 12),
        Paragraph(
            "Disclaimer: This report is generated for educational project demonstration only and is not a medical diagnosis.",
            styles["Italic"],
        ),
    ]

    doc.build(elements)
    buffer.seek(0)
    return buffer


def check_backend():
    try:
        response = requests.get(HEALTH_URL, timeout=20)
        if response.status_code == 200:
            return response.json()
        return {"status": "error", "detail": response.text}
    except Exception as exc:
        return {"status": "offline", "detail": str(exc)}


def predict_mri(uploaded_file):
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            uploaded_file.type,
        )
    }

    response = requests.post(PREDICT_URL, files=files, timeout=60)
    if response.status_code != 200:
        try:
            error_body = response.json()
            detail = error_body.get("detail", response.text)
            if isinstance(detail, dict):
                return {
                    "error": detail.get("message", "Prediction failed."),
                    "mri_probability": detail.get("mri_probability"),
                }
            return {"error": detail}
        except Exception:
            return {"error": response.text}

    return response.json()


def save_patient_record(name, age, condition, symptoms, result):
    payload = {
        "patient_name": name,
        "age": int(age),
        "condition": condition,
        "symptoms": symptoms or "",
        "prediction": result["prediction"],
        "confidence": float(result["confidence"]),
        "scores": result.get("scores", {}),
        "mri_validation": result.get("mri_validation", {}),
    }

    try:
        response = requests.post(PATIENT_RECORDS_URL, json=payload, timeout=15)
        if response.status_code == 200:
            return response.json()
        return {"error": response.text}
    except Exception as exc:
        return {"error": str(exc)}


def confidence_note(confidence):
    if confidence >= 85:
        return "High model confidence for this uploaded image."
    if confidence >= 60:
        return "Moderate confidence. Review image quality and class scores."
    return "Low confidence. Use a clearer MRI image and treat the result carefully."


st.set_page_config(page_title="Brain MRI Analysis", layout="wide")

st.markdown(
    """
    <style>
    .stButton>button {
        background-color: #1f77ff;
        color: white;
        border-radius: 8px;
        height: 42px;
        width: 100%;
        font-weight: 700;
    }
    .metric-panel {
        background-color:#f3f7ff;
        border:1px solid #d8e6ff;
        padding:18px;
        border-radius:8px;
        text-align:center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("System Status")
    health = check_backend()
    if health.get("status") == "ok":
        st.success("Backend connected")
        st.write(f"Model downloaded: {health.get('model_downloaded')}")
        st.write(f"Model loaded: {health.get('model_loaded')}")
        st.write(f"Database ready: {health.get('database_ready')}")
    else:
        st.error("Backend unavailable")
        st.caption(
            health.get(
                "detail",
                "Set API_BASE_URL to your deployed Render backend URL.",
            )
        )

    st.divider()
    st.caption("Classes")
    st.write("Healthy Brain")
    st.write("Brain Tumor")
    st.write("Alzheimer's")
    st.write("Multiple Sclerosis")

st.title("Brain MRI Multi-Disease Detection")
st.caption("Upload a brain MRI scan to generate an AI-assisted classification report.")

st.warning(
    "Upload only brain MRI images. Non-MRI images, screenshots, code images, or unrelated photos can produce incorrect predictions."
)
st.info(
    "Educational project disclaimer: this tool is not a medical diagnosis and must not replace professional clinical advice."
)

left_col, right_col = st.columns([1, 1])

with left_col:
    st.subheader("Patient Information")
    name = st.text_input("Patient Name *")
    age = st.number_input("Age *", min_value=1, max_value=120, step=1)
    condition = st.selectbox(
        "Existing Condition *",
        ["None", "Diabetes", "Hypertension", "Thyroid", "Heart Disease", "Asthma", "Other"],
    )

    other_condition = ""
    if condition == "Other":
        other_condition = st.text_input("Describe Your Condition *")

    symptoms = st.text_area("Symptoms (Optional)")

with right_col:
    st.subheader("MRI Upload")
    uploaded_file = st.file_uploader(
        "Upload Brain MRI Image *",
        type=["jpg", "png", "jpeg"],
        help="Use a clear axial/sagittal/coronal brain MRI image.",
    )
    if uploaded_file:
        st.image(uploaded_file, caption="Selected MRI image", use_container_width=True)

if st.button("Analyze MRI", key="analyze_btn"):
    errors = []

    if not name:
        errors.append("Patient name is required.")
    if condition == "Other" and not other_condition:
        errors.append("Please describe the condition.")
    if not uploaded_file:
        errors.append("Please upload a brain MRI image.")
    if health.get("status") != "ok":
        errors.append("Backend is not connected. Start FastAPI first.")

    if errors:
        for error in errors:
            st.error(error)
    else:
        with st.spinner("Processing MRI with trained model..."):
            result = predict_mri(uploaded_file)

        if "error" in result:
            st.error(result["error"])
            if result.get("mri_probability") is not None:
                st.caption(f"MRI validation confidence: {result['mri_probability']}%")
        else:
            prediction = result["prediction"]
            confidence = result["confidence"]
            scores = result.get("scores", {})
            gradcam_overlay = result.get("gradcam_overlay")
            final_condition = other_condition if condition == "Other" else condition
            saved_record = save_patient_record(
                name,
                age,
                final_condition,
                symptoms,
                result,
            )
            pdf = create_pdf(name, age, final_condition, symptoms, prediction, confidence, scores)

            st.success("Analysis complete")
            if "error" in saved_record:
                st.warning(f"Analysis finished, but patient record was not saved: {saved_record['error']}")
            else:
                st.caption(f"Patient record saved with ID {saved_record.get('id')}.")

            result_col, confidence_col = st.columns([1, 1])
            with result_col:
                st.markdown(
                    f"""
                    <div class='metric-panel'>
                        <div>Prediction</div>
                        <h2 style='color:#1f77ff; margin-bottom:0;'>{prediction}</h2>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with confidence_col:
                st.markdown(
                    f"""
                    <div class='metric-panel'>
                        <div>Confidence</div>
                        <h2 style='color:#1f77ff; margin-bottom:0;'>{confidence}%</h2>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.caption(confidence_note(confidence))

            with st.expander("Class probability scores", expanded=True):
                for label, score in scores.items():
                    st.progress(min(float(score) / 100, 1.0), text=f"{label}: {score}%")

            if gradcam_overlay:
                st.subheader("Grad-CAM Model Attention Heatmap")
                st.caption(
                    "The highlighted regions show image areas that most influenced the predicted class."
                )
                original_col, heatmap_col = st.columns(2)
                with original_col:
                    st.image(uploaded_file, caption="Original MRI", use_container_width=True)
                with heatmap_col:
                    heatmap_bytes = base64.b64decode(gradcam_overlay)
                    st.image(heatmap_bytes, caption="Grad-CAM Overlay", use_container_width=True)
                    st.caption(
                        "Brighter colors (yellow/white) showing highest attention and darker colors (blue/black) showing little to no impact."
                    )

            st.download_button(
                label="Download PDF Report",
                data=pdf,
                file_name="Brain_MRI_Report.pdf",
                mime="application/pdf",
            )
