#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Tests the Docker container for yt-dlp-web

.DESCRIPTION
    Builds and runs the Docker container locally for testing
#>

param(
    [string]$ImageName = "yt-dlp-web",
    [string]$Tag = "latest",
    [int]$Port = 8000,
    [switch]$NoBuild,  # Skip building, just run existing image
    [switch]$Detached  # Run in detached mode
)

$FullImageName = "${ImageName}:${Tag}"

Write-Host "🐳 Testing Docker container for yt-dlp-web..." -ForegroundColor Green

if (-not $NoBuild) {
    Write-Host "🔨 Building Docker image: $FullImageName..." -ForegroundColor Cyan
    docker build -t $FullImageName .
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker build failed!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ Docker image built successfully!" -ForegroundColor Green
}

Write-Host "🚀 Starting container on port $Port..." -ForegroundColor Cyan

if ($Detached) {
    docker run -d -p "${Port}:8000" --name "yt-dlp-web-test" $FullImageName
    Write-Host "✅ Container started in detached mode!" -ForegroundColor Green
    Write-Host "🌐 Access your app at: http://localhost:$Port" -ForegroundColor Cyan
    Write-Host "🛑 Stop with: docker stop yt-dlp-web-test && docker rm yt-dlp-web-test" -ForegroundColor Yellow
}
else {
    Write-Host "🌐 Access your app at: http://localhost:$Port" -ForegroundColor Cyan
    Write-Host "🛑 Press Ctrl+C to stop" -ForegroundColor Yellow
    docker run -it -p "${Port}:8000" --rm $FullImageName
}