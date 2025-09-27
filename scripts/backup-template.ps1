# Template Backup Script
# Creates timestamped backups of the claude-docker-template

param(
    [string]$BackupLocation = "$env:USERPROFILE\Documents\Backups\claude-template",
    [switch]$IncludeDB = $false
)

$TemplateDir = Split-Path -Parent $PSScriptRoot
$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$BackupName = "claude-docker-template_$Timestamp"
$BackupPath = Join-Path $BackupLocation $BackupName

# Create backup directory
New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null

Write-Host "Creating backup: $BackupName" -ForegroundColor Green

# Copy all files except excluded ones
$ExcludePatterns = @(
    "*.db",
    "*.sqlite*",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "venv",
    "node_modules",
    ".git"
)

if (-not $IncludeDB) {
    Write-Host "Excluding database files (use -IncludeDB to include)" -ForegroundColor Yellow
}

# Copy template files
Get-ChildItem -Path $TemplateDir -Recurse | Where-Object {
    $item = $_
    $shouldExclude = $false

    foreach ($pattern in $ExcludePatterns) {
        if ($item.Name -like $pattern -or $item.FullName -like "*\$pattern\*") {
            if ($pattern -like "*.db" -or $pattern -like "*.sqlite*") {
                if ($IncludeDB) {
                    continue
                }
            }
            $shouldExclude = $true
            break
        }
    }

    -not $shouldExclude
} | ForEach-Object {
    $relativePath = $_.FullName.Substring($TemplateDir.Length + 1)
    $targetPath = Join-Path $BackupPath $relativePath
    $targetDir = Split-Path $targetPath -Parent

    if (-not (Test-Path $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    }

    if ($_.PSIsContainer -eq $false) {
        Copy-Item $_.FullName $targetPath -Force
    }
}

# Create backup info file
$BackupInfo = @{
    "Timestamp" = $Timestamp
    "TemplateDir" = $TemplateDir
    "BackupPath" = $BackupPath
    "IncludedDB" = $IncludeDB
    "FileCount" = (Get-ChildItem -Path $BackupPath -Recurse -File).Count
} | ConvertTo-Json

$BackupInfo | Out-File -FilePath (Join-Path $BackupPath "backup-info.json") -Encoding UTF8

Write-Host "Backup completed successfully!" -ForegroundColor Green
Write-Host "Location: $BackupPath" -ForegroundColor Cyan
Write-Host "Files backed up: $((Get-ChildItem -Path $BackupPath -Recurse -File).Count)" -ForegroundColor Cyan

# Clean up old backups (keep last 10)
$OldBackups = Get-ChildItem -Path $BackupLocation -Directory |
    Where-Object { $_.Name -like "claude-docker-template_*" } |
    Sort-Object CreationTime -Descending |
    Select-Object -Skip 10

if ($OldBackups) {
    Write-Host "Cleaning up old backups..." -ForegroundColor Yellow
    $OldBackups | ForEach-Object {
        Remove-Item $_.FullName -Recurse -Force
        Write-Host "Removed: $($_.Name)" -ForegroundColor Gray
    }
}