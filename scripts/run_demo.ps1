param(
    [ValidateSet("auto", "happy", "failing", "ambiguous", "timeout")]
    [string]$Scenario = "failing"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

python -m releasesentinel run --scenario $Scenario --pretty
Write-Host ""
Write-Host "Start dashboard with:"
Write-Host "python -m releasesentinel serve --port 8000"

