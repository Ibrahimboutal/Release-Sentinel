$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -m pytest

