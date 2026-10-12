@echo off
cd /d "%~dp0"
python -c "import PySide6, cv2, mss, pynput, PIL" 2>/dev/null || python -m pip install -r requirements.txt
start "" pythonw macro_app.py
