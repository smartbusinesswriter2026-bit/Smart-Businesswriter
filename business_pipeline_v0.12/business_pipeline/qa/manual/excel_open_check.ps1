<#
    Open a workbook in Excel and report what Excel actually made of it.

    Usage:
        powershell -ExecutionPolicy Bypass -File qa/manual/excel_open_check.ps1 -Path <file.xlsx>

    Excel's repair prompt is the symptom under test.  With DisplayAlerts off, Excel
    repairs silently, so the repair is detected by what survives: the sheet count, the
    sheet names and the cell values.  A file Excel had to repair comes back with the
    unreadable content dropped - which is the "empty content" the owner reported.
#>
param(
    [Parameter(Mandatory = $true)][string]$Path,
    [int]$ExpectedSheets = 0
)

$ErrorActionPreference = 'Stop'
$full = (Resolve-Path $Path).Path

$excel = $null
$book = $null
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.AskToUpdateLinks = $false
    $excel.AlertBeforeOverwriting = $false
    $excel.EnableEvents = $false

    # the plain call: Excel opens what it can and repairs what it cannot, silently here
    $book = $excel.Workbooks.Open($full)

    $names = @()
    foreach ($sheet in $book.Worksheets) { $names += $sheet.Name }

    Write-Output ("OPENED      : " + $full)
    Write-Output ("SHEET COUNT : " + $book.Worksheets.Count)
    foreach ($sheet in $book.Worksheets) {
        $used = $sheet.UsedRange
        $rows = $used.Rows.Count
        $cols = $used.Columns.Count
        $first = ""
        if ($rows -gt 0 -and $cols -gt 0) {
            $first = [string]$sheet.Cells.Item(1, 1).Text
        }
        Write-Output ("  SHEET      : {0,-24} used {1}x{2}  A1='{3}'" -f $sheet.Name, $rows, $cols, $first)
    }

    if ($ExpectedSheets -gt 0 -and $book.Worksheets.Count -ne $ExpectedSheets) {
        Write-Output ("RESULT      : REPAIRED (expected {0} sheets, Excel produced {1})" -f $ExpectedSheets, $book.Worksheets.Count)
        $book.Close($false)
        exit 2
    }
    Write-Output "RESULT      : OK"
    $book.Close($false)
    $book = $null
    exit 0
}
catch {
    Write-Output ("OPEN FAILED : " + $_.Exception.Message)
    exit 1
}
finally {
    if ($book -ne $null) { try { $book.Close($false) } catch { } }
    if ($excel -ne $null) {
        try { $excel.Quit() } catch { }
        try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null } catch { }
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
