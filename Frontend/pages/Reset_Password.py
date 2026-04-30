import streamlit as st
from site_style import apply_theme


st.set_page_config(
    page_title="Reset Password",
    layout="centered",
    initial_sidebar_state="collapsed",
)
apply_theme()

st.title("Reset Password")
st.caption("Demo OTP flow for project presentation.")

phone = st.text_input("Phone Number *")
st.caption("Use exactly 10 digits.")
otp = st.text_input("OTP *")
st.caption("Use a 6 digit OTP. For demo, any 6 digits are accepted.")

if st.button("Verify and Reset"):
    errors = []

    if not phone or not phone.isdigit() or len(phone) != 10:
        errors.append("Phone number must be exactly 10 digits.")
    if not otp or not otp.isdigit() or len(otp) != 6:
        errors.append("OTP must be exactly 6 digits.")

    if errors:
        for error in errors:
            st.error(error)
    else:
        st.success("OTP verified for demo flow.")

if st.button("Back to Login"):
    st.switch_page("app.py")
