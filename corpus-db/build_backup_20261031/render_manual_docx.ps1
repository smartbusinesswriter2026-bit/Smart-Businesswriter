# Export a built DOCX to PDF, for a rendered check.
#
#   powershell -ExecutionPolicy Bypass -File corpus-db\build\render_manual_docx.ps1 `
#       -Docx "D:\SMART BUSINESSWRITER\DATABASE.docx" `
#       -Pdf  "$env:TEMP\database-render.pdf"
#
# Word is the only high-fidelity renderer on this machine (there is no
# LibreOffice and no pdftoppm), so it is driven over COM.
#
# Guard: if this lands on an already-running Word instance - the owner's own
# window, for instance - that instance is NOT quit, its visibility is NOT
# changed, and only the document this script opened is closed. An instance
# started by this script is quit at the end.

param(
    [Parameter(Mandatory = $true)][string]$Docx,
    [Parameter(Mandatory = $true)][string]$Pdf
)

$ErrorActionPreference = 'Stop'

$before = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
Write-Output "word instances already running: $($before.Count)"

$word = New-Object -ComObject Word.Application
$after = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$started = @($after | Where-Object { $before -notcontains $_ }).Count -gt 0
Write-Output "this script started word: $started"

$doc = $null
try {
    # ConfirmConversions, ReadOnly, AddToRecentFiles
    $doc = $word.Documents.Open($Docx, $false, $true, $false)
    $doc.Fields.Update() | Out-Null          # builds the table of contents
    Write-Output "pages: $($doc.ComputeStatistics(2))"     # wdStatisticPages
    Write-Output "words: $($doc.ComputeStatistics(0))"     # wdStatisticWords
    Write-Output "tables: $($doc.Tables.Count)"
    $doc.ExportAsFixedFormat($Pdf, 17)                     # wdExportFormatPDF
    Write-Output "pdf written: $Pdf"
}
finally {
    if ($doc -ne $null) { $doc.Close(0) }                  # wdDoNotSaveChanges
    if ($started) { $word.Quit() }
    else { Write-Output "left the pre-existing Word instance running" }
}
