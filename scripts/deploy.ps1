#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploys yt-dlp-web to production

.DESCRIPTION
    Builds production image, pushes to registry, and triggers deployment
#>

param(
    [string]$Registry = "ghcr.io/aidrak",
    [string]$ImageName = "yt-dlp-web",
    [string]$Tag = "latest",
    [switch]$SkipTests  # Skip running tests before deploy
)

$FullImageName = "${Registry}/${ImageName}:${Tag}"

Write-Host "🚀 Deploying yt-dlp-web to production..." -ForegroundColor Green

# Run tests first (unless skipped)
if (-not $SkipTests) {
    Write-Host "🧪 Running tests..." -ForegroundColor Cyan
    python -m pytest
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Tests failed! Deployment aborted." -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ All tests passed!" -ForegroundColor Green
}

# Build production image
Write-Host "🔨 Building production image: $FullImageName..." -ForegroundColor Cyan
docker build -t $FullImageName .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker build failed!" -ForegroundColor Red
    exit 1
}

# Push to registry
Write-Host "📤 Pushing to registry..." -ForegroundColor Cyan
docker push $FullImageName

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker push failed!" -ForegroundColor Red
    exit 1
}

# Trigger GitHub deployment (this will trigger Unraid auto-deploy)
Write-Host "📋 Committing and pushing to trigger deployment..." -ForegroundColor Cyan
git add .
git commit -m "Deploy: Built and pushed $FullImageName"
git push

Write-Host ""
Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host "🌐 Image: $FullImageName" -ForegroundColor Cyan
Write-Host "🖥️ Unraid will auto-deploy from the GitHub workflow" -ForegroundColor Cyan
Write-Host ""