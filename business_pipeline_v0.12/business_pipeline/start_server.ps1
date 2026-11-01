# Start the Smart BusinessWriter API server on http://127.0.0.1:8000
# Run: .\start_server.ps1   (from business_pipeline_v0.12/business_pipeline)
# Launches detached so this terminal is not blocked; the server keeps running
# until you stop the python process or reboot.
$env:PYTHONPATH = "src"
Start-Process python -ArgumentList "-m bp.server 8000" -WorkingDirectory (Get-Location) -NoNewWindow `
    -RedirectStandardOutput "$env:TEMP\bp_server_stdout.log" `
    -RedirectStandardError "$env:TEMP\bp_server_stderr.log"
Write-Host "Server starting detached on http://127.0.0.1:8000"
Write-Host "Health:  http://127.0.0.1:8000/api/health"
Write-Host "Logs:    $env:TEMP\bp_server_stdout.log / $env:TEMP\bp_server_stderr.log"
