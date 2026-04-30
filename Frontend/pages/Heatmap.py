import streamlit as st


st.set_page_config(page_title="Model Explainability", layout="centered")

st.title("Model Explainability")
st.info("Grad-CAM heatmap visualization is now available after each successful MRI analysis.")

st.markdown(
    """
    The backend generates a Grad-CAM overlay from the last convolutional layer of the CNN backbone.
    The dashboard displays the original MRI next to the heatmap overlay after prediction.

    This helps explain which regions of the MRI contributed most strongly to the model's selected class.
    """
)

if st.button("Back to Dashboard"):
    st.switch_page("pages/Dashboard.py")
