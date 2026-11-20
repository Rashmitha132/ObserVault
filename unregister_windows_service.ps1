<#
.SYNOPSIS
    Unregisters the ObserVault Collector Windows autostart Scheduled Task.
#>
[CmdletBinding()]
param()

$TaskName = "ObserVaultCollector"

try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
    Write-Host "[+] Successfully removed Windows autostart task '$TaskName'." -ForegroundColor Green
} catch {
    Write-Host "Task '$TaskName' does not exist or has already been removed." -ForegroundColor Yellow
}
