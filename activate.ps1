# Activate Python virtual environment and install dependencies
Write-Host "Activating Python virtual environment..." -ForegroundColor Green

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Green
pip install -r requirements.txt

Write-Host "Virtual environment ready!" -ForegroundColor Green
Write-Host "To run the app: python app.py" -ForegroundColor Yellow