$ErrorActionPreference = "Continue"
$venv = "D:\Agri App\backend\.venv\Scripts\python.exe"
$backend = "D:\Agri App\backend"

Write-Host "=== AgriAI Test Suite ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "--- Unit Tests ---" -ForegroundColor Yellow
& $venv -m pytest tests/unit/ -v --tb=short --no-header 2>&1

Write-Host ""
Write-Host "--- Integration Tests ---" -ForegroundColor Yellow
& $venv -m pytest tests/integration/ -v --tb=short --no-header 2>&1

Write-Host ""
Write-Host "--- Full Suite with Coverage ---" -ForegroundColor Yellow
& $venv -m pytest tests/ -v --tb=short --cov=app --cov-report=term-missing --no-header 2>&1

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Cyan
