param(
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = 'python'
$DistRoot = Join-Path $Root 'dist'
$AppDistDir = Join-Path $DistRoot 'BGRemover'

if ($Clean) {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Root 'build')
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Root 'dist')
}

& $Python -m PyInstaller --noconfirm (Join-Path $Root 'image_bg_remover.spec')

if (-not (Test-Path $AppDistDir)) {
    throw "Build output directory was not found: $AppDistDir"
}

Copy-Item -Force (Join-Path $Root 'LICENSE') $AppDistDir
Copy-Item -Force (Join-Path $Root 'THIRD_PARTY_LICENSES.txt') $AppDistDir
Copy-Item -Recurse -Force (Join-Path $Root 'licenses') (Join-Path $AppDistDir 'licenses')
