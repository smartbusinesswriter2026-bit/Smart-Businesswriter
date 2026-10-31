<#
.SYNOPSIS
  Nightly one-way sync of the corpus PDF bytes to Cloudflare R2 (DATABASE.md step 13).

.DESCRIPTION
  The corpus database is the system of record (D-03). This script reads the
  record, asks rclone to mirror exactly those documents into the bucket, and
  then checks that the bucket holds exactly them - no missing document, no
  extra object. One document per work (D-25): the destination mirrors the
  record, and rclone sync never pulls anything back.

  Only PDF bytes go to R2. corpus.sqlite, the Meilisearch data directory and
  the build artefacts stay on this machine.

  The bucket is private. It is reached through the S3 endpoint with a
  bucket-scoped R2 API token; no r2.dev subdomain is ever used (G-07).

.PARAMETER Destination
  The rclone destination. A remote ("corpus-r2:bucket/pdfs") or a local path
  for a dry run.

.PARAMETER DryRun
  Ask rclone what it would do, without moving any bytes.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File corpus-db\build\rclone_sync.ps1
#>
[CmdletBinding()]
param(
  [string]$Destination = "corpus-r2:smart-business-writer-corpus/pdfs",
  [string]$Remote = "corpus-r2",
  [string]$Database = "",
  [string]$LogFile = "",
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$BuildDir = $PSScriptRoot
$CorpusDir = Split-Path -Parent $BuildDir
if (-not $Database) { $Database = Join-Path $CorpusDir 'corpus.sqlite' }
if (-not $LogFile) { $LogFile = Join-Path $BuildDir '_logs\rclone_sync.log' }
$LogDir = Split-Path -Parent $LogFile
$PlanFile = Join-Path $LogDir 'r2_plan.json'
$FilesFrom = Join-Path $LogDir 'r2_files.txt'
$SecretsDir = Join-Path $BuildDir '_secrets'
$ConfigFile = Join-Path $SecretsDir 'rclone_corpus.conf'

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
New-Item -ItemType Directory -Force -Path $SecretsDir | Out-Null

function Write-Log {
  param([string]$Message)
  $line = "[{0}] {1}" -f (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'), $Message
  Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
  Write-Output $line
}

# ── the tools ────────────────────────────────────────────────────────────────
$rclone = Join-Path $BuildDir 'tools\rclone.exe'
if (-not (Test-Path -LiteralPath $rclone)) {
  $found = Get-Command rclone -ErrorAction SilentlyContinue
  if ($found) { $rclone = $found.Source } else {
    Write-Log "FATAL: rclone was not found. Expected $BuildDir\tools\rclone.exe."
    exit 2
  }
}
$python = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $python) { Write-Log 'FATAL: python was not found on PATH.'; exit 2 }

Write-Log "=== corpus -> R2 sync starting (destination: $Destination) ==="

# ── credentials and the rclone remote ───────────────────────────────────────
# A local destination needs no credentials; a remote does, and without them
# the run stops here rather than half-finishing.
$isRemote = ($Destination -match '^([A-Za-z0-9_\-]+):') -and -not ($Destination -match '^[A-Za-z]:')
if ($isRemote) {
  $env:RCLONE_CONFIG = $ConfigFile
  & $python.Source (Join-Path $BuildDir 'r2_credentials.py') write --config $ConfigFile --remote $Remote
  if ($LASTEXITCODE -ne 0) {
    Write-Log 'FATAL: no usable R2 credentials. The sync did not run.'
    exit 2
  }
}

# ── the plan: which bytes go, and under which key ───────────────────────────
# A path that is spelled with a different case than the file on disk is the
# same file to Windows and a different name to R2. The record is corrected
# first, and the correction is logged, so that no document is silently skipped.
$repairRaw = & $python.Source (Join-Path $BuildDir 'r2_plan.py') repair-paths --db $Database
if ($LASTEXITCODE -ne 0) {
  Write-Log 'FATAL: the paths in the record could not be read. Nothing was synced.'
  exit 2
}
$repair = ($repairRaw -join "`n") | ConvertFrom-Json
if ($repair.repaired -gt 0) {
  foreach ($change in $repair.changes) {
    Write-Log ("path spelling corrected in the record: {0} ({1} -> {2})" -f `
      $change.doc_id, $change.recorded, $change.on_disk)
  }
}

& $python.Source (Join-Path $BuildDir 'r2_plan.py') plan --db $Database --files-from $FilesFrom --json $PlanFile
if ($LASTEXITCODE -ne 0) {
  Write-Log 'FATAL: the plan could not be built from the corpus database. Nothing was synced.'
  exit 2
}
$plan = Get-Content -LiteralPath $PlanFile -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Log ("plan: {0} documents, {1} bytes, source root {2}" -f $plan.entries.Count, $plan.total_bytes, $plan.source_root)

# ── the sync ────────────────────────────────────────────────────────────────
$rcloneArgs = @('sync', $plan.source_root, $Destination,
  '--files-from', $FilesFrom,
  '--log-file', $LogFile,
  '--log-level', 'INFO',
  '--stats', '30s',
  '--stats-one-line')
if ($DryRun) { $rcloneArgs += '--dry-run' }
Write-Log ("running: rclone {0}" -f ($rcloneArgs -join ' '))
& $rclone @rcloneArgs
if ($LASTEXITCODE -ne 0) {
  Write-Log "FATAL: rclone sync failed with exit code $LASTEXITCODE."
  exit $LASTEXITCODE
}
Write-Log 'rclone sync finished.'

# ── the check: the bucket holds exactly the record ──────────────────────────
if (-not $DryRun) {
  $listing = & $rclone 'lsjson' $Destination
  if ($LASTEXITCODE -ne 0) {
    Write-Log 'FATAL: the bucket could not be listed, so the mirror is unproven.'
    exit $LASTEXITCODE
  }
  $objects = $listing | ConvertFrom-Json
  $planned = @{}
  foreach ($entry in $plan.entries) { $planned[$entry.rel_path] = $entry }
  $present = @{}
  foreach ($object in $objects) { $present[$object.Path] = $object.Size }

  $missing = @($planned.Keys | Where-Object { -not $present.ContainsKey($_) })
  $extra = @($present.Keys | Where-Object { -not $planned.ContainsKey($_) })
  $wrongSize = @()
  foreach ($path in $planned.Keys) {
    if ($present.ContainsKey($path) -and $present[$path] -ne $planned[$path].size) {
      $wrongSize += $path
    }
  }

  foreach ($path in $extra) {
    Write-Log "removing an object the record does not name: $path"
    & $rclone 'deletefile' ("{0}/{1}" -f $Destination, $path)
  }
  foreach ($path in $missing) { Write-Log "MISSING in the bucket: $path" }
  foreach ($path in $wrongSize) {
    Write-Log ("SIZE MISMATCH: {0} (record {1} bytes, bucket {2} bytes)" -f $path, $planned[$path].size, $present[$path])
  }
  Write-Log ("bucket now holds {0} objects for {1} documents; missing {2}, size mismatches {3}" -f `
    ($planned.Count - $missing.Count + $extra.Count), $planned.Count, $missing.Count, $wrongSize.Count)

  if ($missing.Count -gt 0 -or $wrongSize.Count -gt 0) {
    Write-Log 'FATAL: the bucket does not match the record. The r2_key column was not updated.'
    exit 1
  }

  # ── the record: where each document's bytes now live ──────────────────────
  & $python.Source (Join-Path $BuildDir 'r2_plan.py') record --db $Database --plan $PlanFile
  if ($LASTEXITCODE -ne 0) {
    Write-Log 'FATAL: the R2 keys could not be written back to the database.'
    exit 1
  }
  Write-Log ("wrote documents.r2_key for {0} documents" -f $plan.entries.Count)
}

Write-Log '=== sync complete ==='
exit 0
