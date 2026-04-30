from pathlib import Path
import runpy


REAL_FRONTEND = Path(__file__).resolve().parents[2] / "Frontend"
globals().update(runpy.run_path(str(REAL_FRONTEND / "site_style.py")))
