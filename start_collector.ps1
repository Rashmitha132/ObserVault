<#
.SYNOPSIS
    Starts the persistent ObserVault Windows Collector daemon.
.DESCRIPTION
    Runs the collector daemon in the background with automatic heartbeats every 15s
    and real-time psutil telemetry collection every 5s.
#>
param(
    [switch]$Foreground
)

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $RootDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       ObserVault Windows Collector Daemon Startup         " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

if ($Foreground) {
    Write-Host "[*] Launching collector in FOREGROUND mode..." -ForegroundColor Yellow
    python -m collector.runtime foreground
} else {
    Write-Host "[*] Launching collector in BACKGROUND DAEMON mode..." -ForegroundColor Yellow
    python -m collector.runtime start
    Write-Host ""
    Write-Host "Check status anytime with:" -ForegroundColor Cyan
    Write-Host "    .\status_collector.ps1" -ForegroundColor White
    Write-Host "Or stop anytime with:" -ForegroundColor Cyan
    Write-Host "    .\stop_collector.ps1" -ForegroundColor White
}
