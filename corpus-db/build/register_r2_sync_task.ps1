<#
.SYNOPSIS
  Register the nightly corpus -> R2 sync as a Windows scheduled task.

.DESCRIPTION
  The sync is a build-time and operations tool, so it is scheduled on the
  machine rather than inside the pipeline. The task runs every night at 02:00
  as the current user, calls corpus-db\build\rclone_sync.ps1, and writes its
  result to corpus-db\build\_logs\rclone_sync.log.

  The task is safe to register before the credentials exist: the sync stops
  with a named line in the log ("no usable R2 credentials") and moves no
  bytes, rather than half-finishing.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File corpus-db\build\register_r2_sync_task.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File corpus-db\build\register_r2_sync_task.ps1 -Remove
#>
[CmdletBinding()]
param(
  [string]$TaskName = "SmartBusinessWriter Corpus R2 Sync",
  [string]$Time = "02:00",
  [switch]$Remove
)

$ErrorActionPreference = 'Stop'
$BuildDir = $PSScriptRoot
$Script = Join-Path $BuildDir 'rclone_sync.ps1'
if (-not (Test-Path -LiteralPath $Script)) { Write-Output "not found: $Script"; exit 2 }

if ($Remove) {
  & schtasks '/Delete' '/TN' $TaskName '/F' | Out-Null
  Write-Output "removed the scheduled task: $TaskName"
  exit 0
}

$arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}"' -f $Script
$registered = $false

try {
  # The PowerShell route: no quoting problems with a path that has spaces.
  $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
  $trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::Parse($Time))
  $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
  $registered = $true
  Write-Output 'registered with Register-ScheduledTask.'
} catch {
  Write-Output ("Register-ScheduledTask refused: {0}" -f $_.Exception.Message)
}

if (-not $registered) {
  # The schtasks route: the whole command line goes through cmd, because
  # schtasks reads the quoted run string itself.
  $command = 'schtasks /Create /TN "{0}" /TR "{1}" /SC DAILY /ST {2} /F' -f $TaskName, $arguments, $Time
  cmd /c $command | Out-Null
  if ($LASTEXITCODE -ne 0) { Write-Output "schtasks failed with exit code $LASTEXITCODE"; exit $LASTEXITCODE }
  Write-Output 'registered with schtasks.'
}

Write-Output "scheduled task registered: $TaskName"
Write-Output ("  runs daily at {0}" -f $Time)
Write-Output ("  runs: {0}" -f $arguments)
Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue |
  Get-ScheduledTaskInfo -ErrorAction SilentlyContinue |
  Select-Object TaskName, LastRunTime, LastTaskResult, NextRunTime | Format-List
