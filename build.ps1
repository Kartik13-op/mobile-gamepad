[CmdletBinding()]
param()

# Builds only the small root launcher. The application and its dependencies
# remain in backend/ and are installed by setup.ps1.
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '.')).Path
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
$specPath = Join-Path $projectRoot 'main.spec'
$exePath = Join-Path $projectRoot 'TouchKeys.exe'
$buildPath = Join-Path $projectRoot 'build'
$distPath = Join-Path $projectRoot 'dist'

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    throw 'TouchKeys Python environment was not found. Run setup.ps1 first.'
}

Write-Host '[TouchKeys] Installing the build-only PyInstaller package.' -ForegroundColor Cyan
& $venvPython -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller installation failed with exit code $LASTEXITCODE."
}

# These are generated build targets. Remove only the exact project-local paths.
Remove-Item -LiteralPath $exePath -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $buildPath -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $distPath -Recurse -Force -ErrorAction SilentlyContinue

Write-Host '[TouchKeys] Compiling TouchKeys.exe with the TouchKeys icon.' -ForegroundColor Cyan
& $venvPython -m PyInstaller $specPath --clean --noconfirm --distpath $projectRoot --workpath $buildPath
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE."
}

if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
    throw "The build completed but $exePath was not created."
}

# Do not leave generated build folders in the release tree.
Remove-Item -LiteralPath $buildPath -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $distPath -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "[TouchKeys] Created $exePath" -ForegroundColor Green
