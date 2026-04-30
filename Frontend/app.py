import re
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


HEALTH_URL = f"{get_api_base_url()}/health"


def check_backend():
    try:
        response = requests.get(HEALTH_URL, timeout=10)
        if response.status_code == 200:
            return response.json()
        return {"error": f"API error {response.status_code}"}
    except Exception as exc:
        return {"error": str(exc)}


def valid_username(username):
    return re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[\W_]).{6,}$", username)


def valid_email(email):
    return re.match(r"^[^@]+@[^@]+\.[^@]+$", email)


def valid_phone(phone):
    return phone.isdigit() and len(phone) == 10


def valid_password(password):
    return len(password) >= 6


st.set_page_config(
    page_title="Brain MRI Login",
    page_icon="lock",
    layout="centered",
    initial_sidebar_state="collapsed",
)
apply_theme()

st.markdown(
    """
    <div style='text-align:center; margin-bottom:22px;'>
        <div class='status-pill'>Brain MRI Multi-Disease Detection</div>
        <h1 style='color:#102a56; margin-bottom:5px;'>Login</h1>
        <div style='width:120px; height:2px; background-color:#1f77ff; margin:auto;'></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div class='login-box'>", unsafe_allow_html=True)

name = st.text_input("Full Name *")
username = st.text_input("Username *")
st.caption("Use at least 6 characters with one uppercase letter, one lowercase letter, and one special character.")
password = st.text_input("Password *", type="password")
st.caption("Use at least 6 characters.")
email = st.text_input("Email Address *")
st.caption("Example: name@example.com")
phone = st.text_input("Phone Number *")
st.caption("Use exactly 10 digits, with numbers only.")

if username and not valid_username(username):
    st.warning("Username needs uppercase, lowercase, and a special character.")
if password and not valid_password(password):
    st.warning("Password must be at least 6 characters.")
if email and not valid_email(email):
    st.warning("Please enter a valid email address.")
if phone and not valid_phone(phone):
    st.warning("Phone number must be exactly 10 digits.")

if st.button("Login"):
    errors = []

    if not name:
        errors.append("Name is required")
    if not username or not valid_username(username):
        errors.append("Username must include uppercase, lowercase and special character")
    if not password or not valid_password(password):
        errors.append("Password must be at least 6 characters")
    if not email or not valid_email(email):
        errors.append("Enter a valid email")
    if not phone or not valid_phone(phone):
        errors.append("Phone must be exactly 10 digits")

    if errors:
        for error in errors:
            st.error(error)
    else:
        backend = check_backend()
        if "error" in backend:
            st.warning(f"Login accepted, but backend is not reachable yet: {backend['error']}")
        st.session_state["logged_in"] = True
        st.session_state["name"] = name
        st.switch_page("pages/Dashboard.py")

if st.button("Forgot Password?", key="forgot_btn"):
    st.switch_page("pages/Reset_Password.py")

st.markdown("</div>", unsafe_allow_html=True)
