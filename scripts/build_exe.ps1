param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

if (-not $SkipInstall) {
    python -m pip install -r requirements.txt
    python -m pip install -r requirements-build.txt
}

python -m PyInstaller --noconfirm --clean aica.spec

Write-Host ""
Write-Host "Build complete: dist\Chattodo\Chattodo.exe"
