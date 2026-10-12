@echo off
rem Builds dist\MacroStudio.exe (single file, no console window).
cd /d "%~dp0"
python -m pip install -r requirements.txt pyinstaller || exit /b 1
python -m PyInstaller --noconfirm --clean MacroStudio.spec || exit /b 1
echo.
echo Done: dist\MacroStudio.exe
