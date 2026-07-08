@echo off
REM Menu Planner - Local Development Startup Script

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║   Menu Planner - Starting Local Development Server    ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
    echo Installing dependencies...
    call venv\Scripts\pip.exe install -r requirements.txt
    echo.
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Create required directories
if not exist "data" mkdir data
if not exist "logs" mkdir logs

REM Create .env if it doesn't exist
if not exist ".env" (
    echo Creating .env file...
    copy .env.example .env
)

echo.
echo ✅ Environment activated
echo.
echo 🚀 Starting Flask app on http://localhost:5000
echo    Press Ctrl+C to stop
echo.

REM Run the app
REM B57 (2026-07): flask_app.py now imports from deployment/app_core.py, so
REM it must be launched as a package from the project root (python -m flask),
REM not as a standalone script (python deployment/flask_app.py) - the latter
REM doesn't put the project root on sys.path the way running as a module
REM does, so Python can't resolve the "deployment" package it's importing
REM from. --debug keeps the same auto-reload-on-change + in-browser
REM traceback behavior the old app.run(debug=True) call gave.
set FLASK_DEBUG=1
python -m flask --app deployment.flask_app run --host=0.0.0.0 --port=5000

pause
