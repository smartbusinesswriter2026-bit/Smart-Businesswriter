# Run the full unittest suite in a given project root and capture it.
# Usage:  & 'D:\SMART BUSINESSWRITER\.scratch\run-suite.ps1' -Root <project root> -Tag <name>
#
# Output goes straight to files through Start-Process redirection: reading both pipes
# in sequence deadlocks as soon as the child fills the stderr buffer.
param(
    [Parameter(Mandatory = $true)][string]$Root,
    [Parameter(Mandatory = $true)][string]$Tag
)

$ErrorActionPreference = 'Continue'
$out = "D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\qa\baseline\$Tag-suite-out.txt"
$err = "D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\qa\baseline\$Tag-suite-err.txt"

$env:PYTHONPATH = "$Root\src"
$env:DEEPSEEK_API_KEY = ''
$env:BP_LLM_PROVIDER = ''
$env:BP_LLM_MODEL = ''

$sw = [Diagnostics.Stopwatch]::StartNew()
$p = Start-Process -FilePath 'python' `
    -ArgumentList '-m', 'unittest', 'discover', '-s', 'tests', '-v' `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $out `
    -RedirectStandardError $err `
    -NoNewWindow -PassThru
$p.WaitForExit()
$sw.Stop()

$tail = @()
if (Test-Path $out) { $tail += (Get-Content $out -Tail 3) }
if (Test-Path $err) { $tail += (Get-Content $err -Tail 3) }
Write-Output ("[{0}] exit={1} seconds={2:N0}" -f $Tag, $p.ExitCode, $sw.Elapsed.TotalSeconds)
$tail | ForEach-Object { Write-Output ("   " + $_) }
