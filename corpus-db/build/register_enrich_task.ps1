# Register the nightly corpus enrichment pass (Windows).
#
#   powershell -ExecutionPolicy Bypass -File corpus-db\build\register_enrich_task.ps1
#
# The task runs at 03:00, after the 02:00 R2 sync.  It is optional: the same
# work can be run by hand with corpus-db\build\enrich_cycle.bat.
#
# Nothing here is a runtime dependency of a paper run.  If the task is missing
# or the machine is off at 03:00, the pipeline still works; it simply learns
# more slowly.

$ErrorActionPreference = "Stop"
$script = Join-Path $PSScriptRoot "enrich_cycle.bat"
$name = "SmartBusinessWriter Corpus Enrichment"

if (-not (Test-Path $script)) {
    throw "The enrichment script was not found: $script"
}

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$script`"" -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd `
    -ExecutionTimeLimit (New-TimeSpan -Hours 4)

Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger `
    -Settings $settings -Description "Collect the sources paper runs needed and ingest the open ones into the corpus." `
    -Force | Out-Null

Write-Host "Registered '$name' (daily at 03:00)."
Write-Host "Run it now:  Start-ScheduledTask -TaskName '$name'"
Write-Host "Remove it:   Unregister-ScheduledTask -TaskName '$name' -Confirm:`$false"
