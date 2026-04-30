from pathlib import Path
import runpy
import sys


REAL_FRONTEND = Path(__file__).resolve().parents[2] / "Frontend"
sys.path.insert(0, str(REAL_FRONTEND))
runpy.run_path(str(REAL_FRONTEND / "app.py"), run_name="__main__")
