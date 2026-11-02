$ErrorActionPreference = 'Continue'
$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$tmp = "D:\SMART BUSINESSWRITER\.uitmp"

# The probe reports what the browser's own parser did with the page.
$probe = @'
<script>
(function () {
  var head = document.head;
  var out = {
    doctype: document.doctype ? (document.doctype.name || 'present') : 'none',
    headCount: document.getElementsByTagName('head').length,
    headChildren: head ? head.children.length : -1,
    iconLinksInHead: head ? head.querySelectorAll('link[rel~="icon"]').length : -1,
    appleTouchInHead: head ? head.querySelectorAll('link[rel~="apple-touch-icon"]').length : -1,
    iconLinksAnywhere: document.querySelectorAll('link[rel~="icon"]').length,
    appleTouchAnywhere: document.querySelectorAll('link[rel~="apple-touch-icon"]').length,
    title: document.title
  };
  var pre = document.createElement('pre');
  pre.textContent = 'PROBE ' + JSON.stringify(out, null, 1);
  pre.style.cssText = 'position:fixed;inset:0;z-index:99999;background:#fff;color:#000;font:17px monospace;padding:24px;white-space:pre-wrap';
  document.documentElement.appendChild(pre);
})();
</script>
</body>
'@

function Build-Probe([string]$html, [string]$outFile) {
    $index = $html.LastIndexOf('</body>')
    if ($index -lt 0) { throw "no </body> in $outFile" }
    $patched = $html.Substring(0, $index) + $probe + $html.Substring($index + 7)
    [System.IO.File]::WriteAllText($outFile, $patched, (New-Object System.Text.UTF8Encoding($false)))
}

# AFTER: exactly what the server sends right now.
$served = (Invoke-WebRequest -Uri 'http://127.0.0.1:8021/' -UseBasicParsing -TimeoutSec 10).Content
Build-Probe $served "$tmp\probe_after.html"

# BEFORE: the committed page, before this fix.
$before = git show HEAD:business_pipeline_v0.12/business_pipeline/web/index.html | Out-String
Build-Probe $before "$tmp\probe_before.html"

foreach ($name in @('before', 'after')) {
    $png = "$tmp\probe_$name.png"
    if (Test-Path $png) { Remove-Item $png -Force }
    & $chrome --headless=old --disable-gpu --no-sandbox --user-data-dir="$tmp\chrome-shot-profile2" --screenshot="$png" --window-size=900,520 --virtual-time-budget=5000 "file:///$($png.Replace('\','/').Replace('.png','.html'))" > $null 2>$null
    if (Test-Path $png) { "$name -> $((Get-Item $png).Length) bytes" } else { "$name -> NO SCREENSHOT" }
}
