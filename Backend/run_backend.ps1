Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
& "$PSScriptRoot\.venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 5055
