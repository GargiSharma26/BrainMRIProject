import streamlit as st


PRIMARY_BLUE = "#1f77ff"
DEEP_BLUE = "#0f4fc7"
LIGHT_BLUE = "#eef5ff"
BORDER_BLUE = "#cfe0ff"


def apply_theme():
    st.markdown(
        f"""
        <style>
        [data-testid="stSidebarNav"] {{
            display: none;
        }}
        .stApp {{
            background: linear-gradient(180deg, #f8fbff 0%, #ffffff 32%, #f5f9ff 100%);
        }}
        h1, h2, h3 {{
            color: #102a56;
        }}
        .block-container {{
            padding-top: 2rem;
        }}
        div.stButton > button,
        div.stDownloadButton > button {{
            background: {PRIMARY_BLUE} !important;
            color: #ffffff !important;
            border: 1px solid {PRIMARY_BLUE} !important;
            border-radius: 8px !important;
            min-height: 42px;
            width: 100%;
            font-weight: 700 !important;
            box-shadow: 0 8px 18px rgba(31, 119, 255, 0.18);
        }}
        div.stButton > button:hover,
        div.stDownloadButton > button:hover {{
            background: {DEEP_BLUE} !important;
            border-color: {DEEP_BLUE} !important;
            color: #ffffff !important;
        }}
        div.stButton > button:focus,
        div.stDownloadButton > button:focus {{
            box-shadow: 0 0 0 3px rgba(31, 119, 255, 0.22) !important;
        }}
        .login-box {{
            background-color: #ffffff;
            padding: 30px;
            border-radius: 8px;
            border: 1px solid {BORDER_BLUE};
            box-shadow: 0 12px 34px rgba(16, 42, 86, 0.10);
            max-width: 520px;
            margin: auto;
        }}
        .metric-panel {{
            background-color: {LIGHT_BLUE};
            border: 1px solid {BORDER_BLUE};
            padding: 18px;
            border-radius: 8px;
            text-align: center;
            min-height: 116px;
        }}
        .metric-panel div {{
            color: #48628c;
            font-size: 0.95rem;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .metric-panel h2 {{
            color: {PRIMARY_BLUE};
            margin-bottom: 0;
            font-size: 1.8rem;
        }}
        .heatmap-note {{
            background: #eaf3ff;
            border-left: 5px solid {PRIMARY_BLUE};
            color: #102a56;
            padding: 14px 16px;
            border-radius: 8px;
            font-size: 1.02rem;
            font-weight: 700;
            line-height: 1.45;
            margin-top: 10px;
        }}
        .status-pill {{
            display: inline-block;
            background: {LIGHT_BLUE};
            border: 1px solid {BORDER_BLUE};
            color: #102a56;
            padding: 8px 12px;
            border-radius: 999px;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
