<#
.SYNOPSIS
  Start the corpus search index - the one instance, on one port.

.DESCRIPTION
  The corpus search index is one Meilisearch process with one data directory:

      corpus-db\meilisearch.exe --db-path corpus-db\meili --http-addr 127.0.0.1:7700

  A second instance used to sit on the same port with an empty data directory
  (corpus-state\meili). Two processes on one port is not a race anyone wins:
  requests land on whichever socket the OS picks. This script refuses to start
  a second instance, so the port can only ever be held by the real one.

  Run it after a reboot, before anything asks the corpus a question. It does
  not rebuild the index: the index is derived from corpus.sqlite and can be
  rebuilt at any time with

      python corpus-db\build\corpus_lib.py --index

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File corpus-db\build\start_meilisearch.ps1
#>
[CmdletBinding()]
param(
  [string]$Address = "127.0.0.1:7700",
  [string]$DbPath = ""
)

$ErrorActionPreference = 'Stop'
$BuildDir = $PSScriptRoot
$CorpusDir = Split-Path -Parent $BuildDir
if (-not $DbPath) { $DbPath = Join-Path $CorpusDir 'meili' }
$Binary = Join-Path $CorpusDir 'meilisearch.exe'

if (-not (Test-Path -LiteralPath $Binary)) { Write-Output "not found: $Binary"; exit 2 }

# Already up? Then there is nothing to do, and nothing to double up on.
try {
  $health = Invoke-RestMethod -Uri ("http://{0}/health" -f $Address) -TimeoutSec 3
  if ($health.status -eq 'available') {
    Write-Output ("the search index is already running on {0}." -f $Address)
    exit 0
  }
} catch { }

# The port is taken by something that is not answering /health: say so rather
# than starting a second instance on top of it.
$listener = netstat -ano | Select-String (":{0}\s" -f ($Address -split ':')[-1]) | Select-Object -First 1
if ($listener) {
  Write-Output ("port {0} is already in use by something else:" -f ($Address -split ':')[-1])
  Write-Output $listener
  Write-Output 'Not starting a second instance. Stop that process first.'
  exit 1
}

New-Item -ItemType Directory -Force -Path $DbPath | Out-Null
$arguments = '--db-path "{0}" --http-addr {1}' -f $DbPath, $Address
Write-Output ("starting: meilisearch.exe {0}" -f $arguments)
Start-Process -FilePath $Binary -ArgumentList $arguments -WindowStyle Hidden | Out-Null

for ($i = 0; $i -lt 60; $i++) {
  Start-Sleep -Seconds 1
  try {
    $health = Invoke-RestMethod -Uri ("http://{0}/health" -f $Address) -TimeoutSec 3
    if ($health.status -eq 'available') {
      Write-Output ("the search index is up on {0} (data: {1})." -f $Address, $DbPath)
      exit 0
    }
  } catch { }
}
Write-Output 'the search index did not come up within 60 seconds.'
exit 1
