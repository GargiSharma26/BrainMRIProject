import os

import requests
import streamlit as st
from site_style import apply_theme


def get_api_base_url():
    default_url = os.getenv("API_BASE_URL", "http://127.0.0.1:5055")
    try:
        return st.secrets.get("API_BASE_URL", default_url).rstrip("/")
    except Exception:
        return default_url.rstrip("/")


PATIENT_RECORDS_URL = f"{get_api_base_url()}/patient-records"


def fetch_patient_records():
    try:
        response = requests.get(PATIENT_RECORDS_URL, timeout=15)
        if response.status_code == 200:
            return response.json()
        return {"error": response.text}
    except Exception as exc:
        return {"error": str(exc)}


st.set_page_config(
    page_title="Patient Records",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_theme()

if not st.session_state.get("logged_in"):
    st.warning("Please login first to access patient records.")
    if st.button("Go to Login"):
        st.switch_page("app.py")
    st.stop()

st.title("Patient Records")
st.caption("Recent saved MRI analysis records from the backend database.")

left_col, right_col = st.columns([1, 4])
with left_col:
    if st.button("Back to Dashboard"):
        st.switch_page("pages/Dashboard.py")

records_response = fetch_patient_records()

if "error" in records_response:
    st.error(f"Could not load patient records: {records_response['error']}")
    st.stop()

records = records_response.get("records", [])

if not records:
    st.info("No patient records are saved yet. Analyze an MRI first.")
    st.stop()

table_rows = []
for record in records:
    table_rows.append(
        {
            "ID": record.get("id"),
            "Patient Name": record.get("patient_name"),
            "Age": record.get("age"),
            "Condition": record.get("condition"),
            "Prediction": record.get("prediction"),
            "Confidence": record.get("confidence"),
            "Created At": record.get("created_at"),
        }
    )

st.dataframe(table_rows, use_container_width=True, hide_index=True)

with st.expander("View complete record details"):
    selected_id = st.selectbox(
        "Select record ID",
        [record.get("id") for record in records],
    )
    selected_record = next(
        record for record in records if record.get("id") == selected_id
    )
    st.json(selected_record)
