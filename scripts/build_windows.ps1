param(
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = 'python'

if ($Clean) {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Root 'build')
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Root 'dist')
}

& $Python -m PyInstaller --noconfirm (Join-Path $Root 'image_bg_remover.spec')
