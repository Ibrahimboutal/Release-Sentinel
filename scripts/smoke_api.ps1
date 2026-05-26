param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$manifest = Get-Content -Raw -Path (Join-Path $root "data/change_manifest.json") | ConvertFrom-Json
$body = @{
    manifest = $manifest
    scenario = "failing"
    persist = $false
} | ConvertTo-Json -Depth 20

Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/release-verdict" -ContentType "application/json" -Body $body

