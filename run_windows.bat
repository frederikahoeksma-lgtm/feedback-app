@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM  EKX Live Feedback App — Windows setup & run script
REM  Double-click this file, or run it from Command Prompt / PowerShell
REM ─────────────────────────────────────────────────────────────────────────────

echo.
echo   EKX Live Feedback App
echo   -------------------------------------------

REM ── 1. Find Python ───────────────────────────────────────────────────────────
where python >nul 2>&1
IF ERRORLEVEL 1 (
    echo   ERROR: Python was not found. Download it from https://www.python.org/downloads/
    echo          Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

FOR /F "tokens=*" %%i IN ('python --version') DO SET PYVER=%%i
echo   Found %PYVER%

REM ── 2. Create virtual environment ────────────────────────────────────────────
IF NOT EXIST "venv\" (
    echo   Creating virtual environment...
    python -m venv venv
)

REM ── 3. Activate + install deps ───────────────────────────────────────────────
call venv\Scripts\activate.bat
echo   Installing dependencies...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

REM ── 4. Start app ─────────────────────────────────────────────────────────────
echo.
echo   Admin UI  ->  http://localhost:5000
echo   Press CTRL+C to stop.
echo.
python app.py
pause
