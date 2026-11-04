# Step 7: run the full suite on HEAD (the baseline copy) and on the working tree,
# in sequence, so the two runs cannot contend for the machine.
$ErrorActionPreference = 'Continue'
$runner = 'D:\SMART BUSINESSWRITER\.scratch\run-suite.ps1'

& $runner -Root 'D:\SMART BUSINESSWRITER\.baseline_head\x\business_pipeline_v0.12\business_pipeline' -Tag 'seam-head'
& $runner -Root 'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline' -Tag 'seam-wt'
Write-Output 'BOTH SUITES DONE'
