<#
.SYNOPSIS
    Stops the active ObserVault Windows Collector daemon.
#>
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $RootDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "        ObserVault Windows Collector Daemon Stop          " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

python -m collector.runtime stop
