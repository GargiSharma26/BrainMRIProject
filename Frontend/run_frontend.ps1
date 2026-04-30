Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
& "$PSScriptRoot\.venv\Scripts\python.exe" -m streamlit run app.py
