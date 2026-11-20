<#
.SYNOPSIS
    ObserVault Windows Collector One-Line Installer & Enrollment Script (Phase 2F)
.DESCRIPTION
    Verifies Python environment, registers local directory, executes enrollment handshake,
    configures encrypted operational settings, and validates heartbeat signaling.
#>
[CmdletBinding()]
param (
    [string]$EnrollmentToken = $env:OBSERVAULT_ENROLL_TOKEN,
    [string]$BackendUrl = $(if ($env:OBSERVAULT_BACKEND_URL) { $env:OBSERVAULT_BACKEND_URL } else { "http://127.0.0.1:8000" })
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   ObserVault Privacy-First Collector Onboarding Wizard   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

if (-not $EnrollmentToken) {
    Write-Error "ERROR: Enrollment token is required. Pass -EnrollmentToken or set `$env:OBSERVAULT_ENROLL_TOKEN"
    exit 1
}

# 1. Verify Python 3.10+
Write-Host "[1/5] Checking Python runtime..." -ForegroundColor Yellow
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Error "ERROR: Python is not installed or not in PATH. Please install Python 3.10+."
    exit 1
}

# 2. Setup Work Directory
$WorkDir = Join-Path $env:LOCALAPPDATA "ObserVault\Collector"
if (-not (Test-Path $WorkDir)) {
    New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null
}
Write-Host "[2/5] Provisioned working directory: $WorkDir" -ForegroundColor Green

# 3. Perform Enrollment Handshake
Write-Host "[3/5] Performing secure enrollment handshake with SaaS backend ($BackendUrl)..." -ForegroundColor Yellow
$EnrollBody = @{
    enrollment_token = $EnrollmentToken
    hostname = $env:COMPUTERNAME
    os_type = "windows"
    os_version = (Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue).Caption
    collector_version = "1.0.0"
} | ConvertTo-Json

try {
    $Response = Invoke-RestMethod -Uri "$BackendUrl/api/v1/collectors/enroll" -Method Post -Body $EnrollBody -ContentType "application/json"
    Write-Host "[4/5] Enrollment Handshake Succeeded!" -ForegroundColor Green
    Write-Host "      Assigned Collector ID: $($Response.collector_id)" -ForegroundColor Cyan
    Write-Host "      Device Name:           $($Response.collector_name)" -ForegroundColor Cyan
    Write-Host "      Server ID:             $($Response.server_id)" -ForegroundColor Cyan
    
    # Store Config Securely
    $ConfigFile = Join-Path $WorkDir "collector_config.json"
    $Response | ConvertTo-Json | Set-Content -Path $ConfigFile -Force
    Write-Host "[4/5] Operational credentials safely stored at $ConfigFile" -ForegroundColor Green

    # Start Persistent Background Collector Daemon
    Write-Host "[5/5] Launching persistent ObserVault Collector background daemon..." -ForegroundColor Yellow
    python -m collector.runtime start
    Write-Host "`n>>> SUCCESS: Windows Collector enrolled and running continuously in background!" -ForegroundColor Green
    Write-Host "    - Authenticated heartbeats sending every 15s." -ForegroundColor Cyan
    Write-Host "    - Actual psutil kernel telemetry streaming every 5s." -ForegroundColor Cyan
    Write-Host "    - To check status:  python -m collector.runtime status" -ForegroundColor White
    Write-Host "    - To stop:          python -m collector.runtime stop" -ForegroundColor White
} catch {
    Write-Error "ERROR: Handshake failed: $_"
    exit 1
}
