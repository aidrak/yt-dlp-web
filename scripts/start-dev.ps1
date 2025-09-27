#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Sets up the development environment for yt-dlp-web

.DESCRIPTION
    Creates Python virtual environment, installs dependencies, and sets up pre-commit hooks
#>

param(
    [switch]$Force  # Force recreate venv even if it exists
)

Write-Host "🚀 Setting up development environment for yt-dlp-web..." -ForegroundColor Green

# Check if venv exists and handle accordingly
if (Test-Path "venv" -PathType Container) {
    if ($Force) {
        Write-Host "🗑️ Removing existing virtual environment..." -ForegroundColor Yellow
        Remove-Item "venv" -Recurse -Force
    } else {
        Write-Host "📁 Virtual environment already exists. Use -Force to recreate." -ForegroundColor Yellow
        Write-Host "💡 Activating existing environment..." -ForegroundColor Cyan
        
        # Just activate and ensure latest deps
        & ".\venv\Scripts\Activate.ps1"
        pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
        
        Write-Host "✅ Development environment ready!" -ForegroundColor Green
        return
    }
}

# Create virtual environment
Write-Host "🐍 Creating Python virtual environment..." -ForegroundColor Cyan
python -m venv venv

# Activate virtual environment
Write-Host "⚡ Activating virtual environment..." -ForegroundColor Cyan
& ".\venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "📦 Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# Install dependencies
Write-Host "📚 Installing project dependencies..." -ForegroundColor Cyan
if (Test-Path "requirements.txt") {
    pip install -r requirements.txt
} else {
    Write-Host "⚠️ No requirements.txt found, skipping..." -ForegroundColor Yellow
}

Write-Host "🛠️ Installing development dependencies..." -ForegroundColor Cyan
if (Test-Path "requirements-dev.txt") {
    pip install -r requirements-dev.txt
} else {
    Write-Host "⚠️ No requirements-dev.txt found, skipping..." -ForegroundColor Yellow
}

# Set up pre-commit hooks if available
if (Get-Command "pre-commit" -ErrorAction SilentlyContinue) {
    Write-Host "🎣 Setting up pre-commit hooks..." -ForegroundColor Cyan
    pre-commit install
} else {
    Write-Host "⚠️ pre-commit not found, skipping git hooks setup..." -ForegroundColor Yellow
}

# Create .env from .env.example if it doesn't exist
if ((Test-Path ".env.example") -and (-not (Test-Path ".env"))) {
    Write-Host "📄 Creating .env from .env.example..." -ForegroundColor Cyan
    Copy-Item ".env.example" ".env"
    Write-Host "💡 Please edit .env file with your actual values" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ Development environment setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "🎯 Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit .env file with your configuration" -ForegroundColor White
Write-Host "  2. Run: claude (to start Claude Code)" -ForegroundColor White
Write-Host "  3. Start coding! 🎉" -ForegroundColor White
Write-Host ""