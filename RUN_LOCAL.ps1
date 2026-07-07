# Menu Planner - Local Development Startup Script (PowerShell)

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Menu Planner - Starting Local Development Server    ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv\Scripts\activate.ps1")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host ""
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    & ".\venv\Scripts\pip.exe" install -r requirements.txt
    Write-Host ""
}

# Activate virtual environment
& ".\venv\Scripts\Activate.ps1"

# Create required directories
if (-not (Test-Path "data")) { New-Item -ItemType Directory -Path "data" | Out-Null }
if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" | Out-Null }

# Create .env if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env" -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "✅ Environment activated" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 Starting Flask app on http://localhost:5000" -ForegroundColor Green
Write-Host "   Press Ctrl+C to stop" -ForegroundColor Green
Write-Host ""

# Run the app
# B57 (2026-07): flask_app.py now imports from deployment/app_core.py, so
# it must be launched as a package from the project root (python -m flask),
# not as a standalone script (python deployment/flask_app.py) - the latter
# doesn't put the project root on sys.path the way running as a module
# does, so Python can't resolve the "deployment" package it's importing
# from. --debug keeps the same auto-reload-on-change + in-browser
# traceback behavior the old app.run(debug=True) call gave.
$env:FLASK_DEBUG = "1"
python -m flask --app deployment.flask_app run --host=0.0.0.0 --port=5000
