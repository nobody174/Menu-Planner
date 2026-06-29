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
python deployment/flask_app.py
