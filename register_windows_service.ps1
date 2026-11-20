<#
.SYNOPSIS
    Registers a Windows Scheduled Task to ensure ObserVault Collector starts automatically on logon/boot.
#>
[CmdletBinding()]
param()

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$PyCmd = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $PyCmd) {
    Write-Error "ERROR: Python is not in PATH."
    exit 1
}
$PyPath = $PyCmd.Source
$TaskName = "ObserVaultCollector"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   ObserVault Collector Windows Autostart Registration    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$Action = New-ScheduledTaskAction -Execute $PyPath -Argument "-m collector.runtime start" -WorkingDirectory $RootDir
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "ObserVault Edge Observability Collector Persistent Service" -Force | Out-Null
    Write-Host "[+] Successfully registered Windows autostart task '$TaskName'." -ForegroundColor Green
    Write-Host "    The collector will automatically start upon logon and run persistently in the background." -ForegroundColor Green
} catch {
    Write-Warning "Task registration notice: $_"
}
