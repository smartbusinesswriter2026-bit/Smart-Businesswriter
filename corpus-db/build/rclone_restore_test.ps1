<#
.SYNOPSIS
  Test restore: prove that the bytes in Cloudflare R2 are the corpus.

.DESCRIPTION
  DATABASE.md step 13 asks for a restore that reproduces the database and
  rebuilds the index. This script does that, end to end:

    1. copy corpus.sqlite to a test directory (the record under test)
    2. copy the PDF bytes back from the bucket (rclone copy)
    3. hash every restored PDF and compare it with documents.sha256
    4. point the test copy of the database at the restored files
    5. rebuild a Meilisearch index from the restored record, on its own port,
       so the live index is not touched
    6. ask both indexes a known phrase and compare the answers
    7. write the report to corpus-db\test_restore\restore_report.md

  The test instance runs on port 7701 with its own data directory and is
  stopped at the end.

.PARAMETER Source
  Where the bytes are: an rclone remote ("corpus-r2:bucket/pdfs") or a local
  path for a dry run against a local mirror.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File corpus-db\build\rclone_restore_test.ps1
#>
[CmdletBinding()]
param(
  [string]$Source = "corpus-r2:smart-business-writer-corpus/pdfs",
  [string]$Remote = "corpus-r2",
  [string]$Database = "",
  [string]$TestDir = "",
  [int]$Port = 7701,
  [string]$LiveUrl = "http://127.0.0.1:7700"
)

$ErrorActionPreference = 'Stop'

$BuildDir = $PSScriptRoot
$CorpusDir = Split-Path -Parent $BuildDir
if (-not $Database) { $Database = Join-Path $CorpusDir 'corpus.sqlite' }
if (-not $TestDir) { $TestDir = Join-Path $CorpusDir 'test_restore' }
$DbCopy = Join-Path $TestDir 'corpus.sqlite'
$PdfDir = Join-Path $TestDir 'pdfs'
$MeiliDir = Join-Path $TestDir 'meili'
$ReportPath = Join-Path $TestDir 'restore_report.md'
$VerifyJson = Join-Path $TestDir 'verify.json'
$CompareJson = Join-Path $TestDir 'compare.json'
$PlanFile = Join-Path $TestDir 'r2_plan.json'
$FilesFrom = Join-Path $TestDir 'r2_files.txt'
$SecretsDir = Join-Path $BuildDir '_secrets'
$ConfigFile = Join-Path $SecretsDir 'rclone_corpus.conf'

New-Item -ItemType Directory -Force -Path $TestDir | Out-Null
New-Item -ItemType Directory -Force -Path $PdfDir | Out-Null
New-Item -ItemType Directory -Force -Path $SecretsDir | Out-Null

$rclone = Join-Path $BuildDir 'tools\rclone.exe'
if (-not (Test-Path -LiteralPath $rclone)) {
  $found = Get-Command rclone -ErrorAction SilentlyContinue
  if ($found) { $rclone = $found.Source } else { Write-Output 'rclone was not found.'; exit 2 }
}
$python = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $python) { Write-Output 'python was not found on PATH.'; exit 2 }
$meilisearch = Join-Path $CorpusDir 'meilisearch.exe'
if (-not (Test-Path -LiteralPath $meilisearch)) { Write-Output "meilisearch.exe was not found at $meilisearch."; exit 2 }

$isRemote = ($Source -match '^([A-Za-z0-9_\-]+):') -and -not ($Source -match '^[A-Za-z]:')
if ($isRemote) {
  $env:RCLONE_CONFIG = $ConfigFile
  & $python.Source (Join-Path $BuildDir 'r2_credentials.py') write --config $ConfigFile --remote $Remote
  if ($LASTEXITCODE -ne 0) { Write-Output 'No usable R2 credentials.'; exit 2 }
}

Write-Output '--- 1. the record under test ---'
Copy-Item -LiteralPath $Database -Destination $DbCopy -Force
Write-Output "copied $Database to $DbCopy"

Write-Output '--- 2. the bytes back from the bucket ---'
& $rclone 'copy' $Source $PdfDir --log-level INFO
if ($LASTEXITCODE -ne 0) { Write-Output "rclone copy failed with exit code $LASTEXITCODE."; exit $LASTEXITCODE }

Write-Output '--- 3. the bytes against documents.sha256 ---'
& $python.Source (Join-Path $BuildDir 'r2_plan.py') plan --db $Database --files-from $FilesFrom --json $PlanFile | Out-Null
$plan = Get-Content -LiteralPath $PlanFile -Raw -Encoding UTF8 | ConvertFrom-Json
& $python.Source (Join-Path $BuildDir 'r2_plan.py') verify --db $DbCopy --source-root $plan.source_root --root $PdfDir --json $VerifyJson
$verifyExit = $LASTEXITCODE
$verify = Get-Content -LiteralPath $VerifyJson -Raw -Encoding UTF8 | ConvertFrom-Json

Write-Output '--- 4. the record points at the restored files ---'
& $python.Source (Join-Path $BuildDir 'r2_plan.py') relink --db $DbCopy --source-root $plan.source_root --root $PdfDir

Write-Output "--- 5. the index rebuilt from the restored record (port $Port) ---"
# The argument list is one string: the data directory has spaces in its path,
# and Start-Process does not quote array elements for you.
$meiliArgs = '--db-path "{0}" --http-addr 127.0.0.1:{1} --no-analytics' -f $MeiliDir, $Port
$meiliOut = Join-Path $TestDir 'meili_test.log'
$meili = Start-Process -FilePath $meilisearch -ArgumentList $meiliArgs -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput $meiliOut -RedirectStandardError (Join-Path $TestDir 'meili_test.err')
$healthy = $false
for ($i = 0; $i -lt 60; $i++) {
  Start-Sleep -Seconds 1
  if ($meili.HasExited) { break }
  try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3
    if ($health.status -eq 'available') { $healthy = $true; break }
  } catch { }
}
if (-not $healthy) {
  Write-Output 'the test Meilisearch instance did not become available.'
  if (Test-Path -LiteralPath $meiliOut) { Write-Output '--- what it said ---'; Get-Content -LiteralPath $meiliOut -Tail 20 }
  if (Test-Path -LiteralPath (Join-Path $TestDir 'meili_test.err')) { Get-Content -LiteralPath (Join-Path $TestDir 'meili_test.err') -Tail 20 }
  Stop-Process -Id $meili.Id -Force -ErrorAction SilentlyContinue
  exit 2
}

try {
  $env:BP_CORPUS_DB = $DbCopy
  $env:CORPUS_MEILI_URL = "http://127.0.0.1:$Port"
  $env:CORPUS_INDEX = 'pages'
  & $python.Source (Join-Path $BuildDir 'corpus_lib.py') --index
  if ($LASTEXITCODE -ne 0) { Write-Output 'the index could not be rebuilt.'; exit 1 }

  Write-Output '--- 6. the known phrase, asked of both indexes ---'
  $phrase = (& $python.Source (Join-Path $BuildDir 'r2_plan.py') phrase --db $DbCopy | ConvertFrom-Json)
  Write-Output ("phrase: '{0}' -> {1} page {2}" -f $phrase.phrase, $phrase.doc_id, $phrase.pdf_page)
  & $python.Source (Join-Path $BuildDir 'r2_plan.py') compare `
    --live $LiveUrl --rebuilt "http://127.0.0.1:$Port" --index pages --db $DbCopy `
    --phrase $phrase.phrase --expect-doc $phrase.doc_id --expect-page $phrase.pdf_page `
    --json $CompareJson
  $compareExit = $LASTEXITCODE
  $compare = Get-Content -LiteralPath $CompareJson -Raw -Encoding UTF8 | ConvertFrom-Json
} finally {
  Stop-Process -Id $meili.Id -Force -ErrorAction SilentlyContinue
}

# ── the report ──────────────────────────────────────────────────────────────
$notOk = @($verify.results | Where-Object { $_.status -ne 'ok' })
$pass = ($verifyExit -eq 0) -and ($compareExit -eq 0) -and $compare.same_top_hit -and $compare.rebuilt_matches_record
$lines = @()
$lines += '# R2 test restore report'
$lines += ''
$lines += ('Generated: {0} (UTC)' -f (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))
$lines += ''
$lines += ('**Result: {0}**' -f $(if ($pass) { 'PASS' } else { 'FAIL' }))
$lines += ''
$lines += '## What was restored'
$lines += ''
$lines += ('- Source: `{0}`' -f $Source)
$lines += ('- Record: `{0}` (copy of `{1}`)' -f $DbCopy, $Database)
$lines += ('- Bytes: `{0}`' -f $PdfDir)
$lines += ('- Source root on this machine: `{0}`' -f $plan.source_root)
$lines += ('- Documents in the record: {0}' -f $verify.documents)
$lines += ''
$lines += '## The bytes against the record'
$lines += ''
$lines += ('- SHA-256 matches documents.sha256: {0} of {1}' -f ($verify.documents - $notOk.Count), $verify.documents)
foreach ($item in $notOk) {
  $lines += ('- **{0}**: {1}' -f $item.doc_id, $item.status)
}
$lines += ''
$lines += '## The rebuilt index'
$lines += ''
$lines += ('- Rebuilt from: `{0}`' -f $DbCopy)
$lines += ('- Test instance: `http://127.0.0.1:{0}` (its own data directory, the live index was not touched)' -f $Port)
$lines += ('- Known phrase: `{0}`' -f $compare.phrase)
$lines += ('- The record says: `{0}` page {1}' -f $phrase.doc_id, $phrase.pdf_page)
$lines += ('- The rebuilt index answered: `{0}` page {1}' -f $compare.rebuilt_top[0], $compare.rebuilt_top[1])
$lines += ('- The live index answered: `{0}` page {1}' -f $compare.live_top[0], $compare.live_top[1])
$lines += ('- Same answer: {0}' -f $compare.same_top_hit)
$lines += ('- Documents in the live index: {0}; in the rebuilt index: {1}' -f $compare.live_documents, $compare.rebuilt_documents)
$lines += ('- Pages the record holds: {0}; of those, pages of documents the record marks enrichable: {1}' -f $compare.record_pages, $compare.record_enrichable_pages)
if ($compare.only_in_live_count -gt 0) {
  $lines += ('- The live index holds {0} pages the rebuilt index does not. The index is disposable and the record is the truth (D-03):' -f $compare.only_in_live_count)
  foreach ($property in $compare.only_in_live_by_document.PSObject.Properties) {
    $detail = $property.Value
    $lines += ('  - `{0}`: {1} pages (page {2} to {3})' -f $property.Name, $detail.pages, $detail.first_page, $detail.last_page)
  }
}
if ($compare.in_index_but_not_in_record.Count -gt 0) {
  foreach ($docId in $compare.in_index_but_not_in_record) {
    $lines += ('- **`{0}` is in the live index and is not in the record at all** - a stale page from a document the corpus no longer holds.' -f $docId)
  }
}
if ($compare.only_in_rebuilt_count -gt 0) {
  $lines += ('- Only in the rebuilt index: {0} pages' -f $compare.only_in_rebuilt_count)
  foreach ($pair in $compare.only_in_rebuilt) { $lines += ('  - `{0}` page {1}' -f $pair[0], $pair[1]) }
}
$lines += ''
Set-Content -LiteralPath $ReportPath -Value $lines -Encoding UTF8

Write-Output ''
Write-Output ("report written: {0}" -f $ReportPath)
if ($pass) { Write-Output 'RESULT: PASS'; exit 0 } else { Write-Output 'RESULT: FAIL'; exit 1 }
