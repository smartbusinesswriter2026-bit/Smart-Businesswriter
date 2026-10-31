<#
.SYNOPSIS
  Finish the R2 setup once the credentials are in place: bucket, upload, proof.

.DESCRIPTION
  One command that does everything that is left of Step 13 of DATABASE.md,
  in the order that cannot be reordered:

    1. write the rclone remote from corpus-db\build\_secrets\rclone_corpus.env
    2. create the bucket if it does not exist yet
    3. run the sync (19 documents, 625 MB) and its mirror check
    4. run the test restore: hash every restored file against documents.sha256,
       rebuild a search index from the restored record, ask both indexes the
       same question, write corpus-db\test_restore\restore_report.md

  It stops at the first thing that is not true, and says which one it was.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File corpus-db\build\finish_r2_setup.ps1
#>
[CmdletBinding()]
param(
  [string]$Bucket = "",
  [string]$Remote = "corpus-r2"
)

$ErrorActionPreference = 'Stop'
$BuildDir = $PSScriptRoot
$CorpusDir = Split-Path -Parent $BuildDir
$Secrets = Join-Path $BuildDir '_secrets\rclone_corpus.env'
$Config = Join-Path $BuildDir '_secrets\rclone_corpus.conf'
$LogFile = Join-Path $BuildDir '_logs\rclone_sync.log'

$rclone = Join-Path $BuildDir 'tools\rclone.exe'
if (-not (Test-Path -LiteralPath $rclone)) {
  $found = Get-Command rclone -ErrorAction SilentlyContinue
  if ($found) { $rclone = $found.Source } else { Write-Output 'rclone was not found.'; exit 2 }
}
$python = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $python) { Write-Output 'python was not found on PATH.'; exit 2 }

if (-not (Test-Path -LiteralPath $Secrets)) {
  Write-Output "no credentials file at $Secrets"
  Write-Output 'Fill in the two key lines in corpus-db\build\_secrets\rclone_corpus.env first.'
  exit 2
}

Write-Output '--- 1. the rclone remote ---'
$env:RCLONE_CONFIG = $Config
& $python.Source (Join-Path $BuildDir 'r2_credentials.py') write --config $Config --remote $Remote --env-file $Secrets
if ($LASTEXITCODE -ne 0) { Write-Output 'the credentials file is not complete.'; exit 2 }

$described = (& $python.Source (Join-Path $BuildDir 'r2_credentials.py') describe --env-file $Secrets) -join "`n" | ConvertFrom-Json
if (-not $Bucket) { $Bucket = $described.bucket }
$destination = '{0}:{1}/pdfs' -f $Remote, $Bucket

Write-Output '--- 2. the bucket ---'
# The token is scoped to one bucket, so ListBuckets is denied: probe the
# bucket itself rather than the account.
$probe = & $rclone 'lsjson' ("{0}:{1}" -f $Remote, $Bucket) 2>&1
if ($LASTEXITCODE -eq 0) {
  Write-Output ("the bucket {0} exists and is reachable." -f $Bucket)
} elseif (($probe -join ' ') -match 'NoSuchBucket|not found|404') {
  Write-Output ("creating the bucket {0}..." -f $Bucket)
  & $rclone 'mkdir' ("{0}:{1}" -f $Remote, $Bucket)
  if ($LASTEXITCODE -ne 0) { Write-Output 'the bucket could not be created.'; exit 1 }
  Write-Output ("bucket {0} created." -f $Bucket)
} else {
  Write-Output ("the bucket {0} could not be reached with this token:" -f $Bucket)
  Write-Output ($probe -join [Environment]::NewLine)
  Write-Output 'Check that the token is scoped to this bucket and has Object Read & Write.'
  exit 1
}

Write-Output '--- 3. the sync ---'
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $BuildDir 'rclone_sync.ps1') `
  -Destination $destination -Remote $Remote -LogFile $LogFile
if ($LASTEXITCODE -ne 0) { Write-Output 'the sync did not finish cleanly.'; exit 1 }

Write-Output '--- 4. the test restore ---'
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $BuildDir 'rclone_restore_test.ps1') `
  -Source $destination -Remote $Remote
if ($LASTEXITCODE -ne 0) { Write-Output 'the test restore did not pass.'; exit 1 }

Write-Output ''
Write-Output 'R2 setup finished. The report is in corpus-db\test_restore\restore_report.md'
