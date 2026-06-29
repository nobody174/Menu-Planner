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
python deployment/flask_app.py

pause
