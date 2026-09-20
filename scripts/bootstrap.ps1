param([switch]$Native, [switch]$Coco, [switch]$Development, [switch]$Research, [switch]$Geo, [switch]$GeometryValidation)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.13 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Python 3.13 virtual-environment creation failed." }
}
$python = Join-Path (Get-Location) ".venv\Scripts\python.exe"
$extras = @()
if ($Native) { $extras += "native" }
if ($Coco) { $extras += "coco" }
if ($Development) { $extras += "dev" }
if ($Research) { $extras += "research" }
if ($Geo) { $extras += "geo" }
if ($GeometryValidation) { $extras += "geometry-validation" }
$target = "."
if ($extras.Count -gt 0) { $target = ".[" + ($extras -join ",") + "]" }
& $python -m pip install -e $target
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed; no existing environments were modified." }
& $python -m cvsubstrate doctor
