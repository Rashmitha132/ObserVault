<#
.SYNOPSIS
    Displays status and diagnostics for the ObserVault Windows Collector daemon.
#>
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $RootDir

python -m collector.runtime status
