# Measure the full suite three ways: the pre-increment baseline, the current
# HEAD, and the working tree.
#
#   powershell -File qa/manual/suite_measure.ps1
#
# Each baseline is a byte-exact copy of its commit, built with `git archive`
# and proven byte-exact by `qa/manual/suite_treehash.py`.  The working tree is
# measured in a snapshot copy, so a second session working in the same tree
# cannot move the numbers underneath the measurement.
#
# The outputs land in qa/baseline/:
#
#   seam-pre-suite-err.txt    the pre-increment baseline  (commit d938095)
#   seam-head-suite-err.txt   the current HEAD             (commit f1bb0c5)
#   seam-wt-suite-err.txt     the working tree (snapshot)
#
# and `qa/manual/suite_compare.py` turns those three into the separation of
# pre-existing from new.

param(
    [string]$Repo = 'D:\SMART BUSINESSWRITER',
    [string]$Pre = 'd938095',
    [string]$Head = 'HEAD',
    [string]$OutDir = 'business_pipeline_v0.12\business_pipeline\qa\baseline'
)

$ErrorActionPreference = 'Stop'
Set-Location $Repo

$project = 'business_pipeline_v0.12\business_pipeline'

function New-BaseTree {
    param([string]$Rev, [string]$Dest)
    if (Test-Path $Dest) { Remove-Item -Recurse -Force $Dest }
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    $tar = Join-Path $Repo '.scratch\archive.tar'
    if (Test-Path $tar) { Remove-Item -Force $tar }
    Write-Output "archiving $Rev into $Dest ..."
    git archive --format=tar --output=$tar $Rev -- . `
        ':(exclude).baseline_head' ':(exclude).baseline_head2' `
        ':(exclude).baseline_pre' ':(exclude).snapshot_wt' ':(exclude)_baseline_wt'
    if ($LASTEXITCODE -ne 0) { throw "git archive failed ($LASTEXITCODE)" }
    tar -xf $tar -C $Dest
    if ($LASTEXITCODE -ne 0) { throw "tar failed ($LASTEXITCODE)" }
}

Write-Output "=== 1. the two baseline trees ==="
New-BaseTree -Rev $Pre  -Dest "$Repo\.baseline_pre\x"
New-BaseTree -Rev $Head -Dest "$Repo\.baseline_head2\x"

Write-Output ""
Write-Output "=== 2. the working-tree snapshot ==="
$snap = "$Repo\.snapshot_wt\$project"
if (Test-Path "$Repo\.snapshot_wt") { Remove-Item -Recurse -Force "$Repo\.snapshot_wt" }
New-Item -ItemType Directory -Force -Path (Split-Path $snap) | Out-Null
robocopy "$Repo\$project" $snap /E /XD '__pycache__' 'node_modules' /XF '*.pyc' `
    /NFL /NDL /NJH /NJS /NP /R:1 /W:1 | Out-Null
if ($LASTEXITCODE -gt 7) { throw "robocopy failed ($LASTEXITCODE)" }

$trees = @(
    @{ Name = 'seam-pre';  Dir = "$Repo\.baseline_pre\x\$project" },
    @{ Name = 'seam-head'; Dir = "$Repo\.baseline_head2\x\$project" },
    @{ Name = 'seam-wt';   Dir = $snap }
)

Write-Output ""
Write-Output "=== 3. the suite, in all three trees ==="
$running = @()
foreach ($t in $trees) {
    if (-not (Test-Path $t.Dir)) { throw "missing tree: $($t.Dir)" }
    # `bp` must be importable: without PYTHONPATH=src the first test module
    # imported fails with ModuleNotFoundError and its tests never run. The path
    # is absolute and per tree, so it cannot be read against the wrong cwd.
    $env:PYTHONPATH = "$($t.Dir)\src"
    $proc = Start-Process -FilePath 'python' `
        -ArgumentList '-m', 'unittest', 'discover', '-s', 'tests', '-v' `
        -WorkingDirectory $t.Dir `
        -RedirectStandardOutput "$Repo\$OutDir\$($t.Name)-suite-out.txt" `
        -RedirectStandardError "$Repo\$OutDir\$($t.Name)-suite-err.txt" `
        -NoNewWindow -PassThru
    Write-Output "started $($t.Name) pid=$($proc.Id)  PYTHONPATH=$env:PYTHONPATH"
    $running += @{ Name = $t.Name; Proc = $proc }
}

$clock = 0
while (@($running | Where-Object { -not $_.Proc.HasExited }).Count -gt 0) {
    Start-Sleep -Seconds 60
    $clock += 60
    $alive = @($running | Where-Object { -not $_.Proc.HasExited } | ForEach-Object { $_.Name })
    Write-Output "  t+${clock}s still running: " + ($alive -join ', ')
}
foreach ($t in $trees) {
    $err = "$Repo\$OutDir\$($t.Name)-suite-err.txt"
    if (-not (Test-Path $err)) { throw "no run log for $($t.Name) at $err" }
}

Write-Output ""
Write-Output "=== 4. the verdicts ==="
foreach ($t in $trees) {
    $err = "$Repo\$OutDir\$($t.Name)-suite-err.txt"
    Write-Output "----- $($t.Name) -----"
    Get-Content $err | Select-String -Pattern '^Ran \d+ tests|^OK$|^FAILED \(' |
        ForEach-Object { "   $($_.Line)" }
}
