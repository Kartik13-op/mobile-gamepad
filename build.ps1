[CmdletBinding()]
param()

# Build a single-file, self-contained Windows executable. The resulting EXE
# contains the Python runtime, application packages, web UI, pywebview data,
# and ViGEm client DLLs; Python and .venv are not needed on the target PC.
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path $PSScriptRoot).Path
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
$specPath = Join-Path $projectRoot 'main.spec'
$executablesPath = Join-Path $projectRoot 'Executables'
$exePath = Join-Path $executablesPath 'TouchKeys_v3.1.exe'
$buildPath = Join-Path $projectRoot 'build'
$distPath = Join-Path $projectRoot 'dist'
$driverPath = Join-Path $projectRoot 'installers\ViGEmBus_1.22.0_x64_x86_arm64.exe'

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    throw 'TouchKeys Python environment was not found. Run setup.ps1 first.'
}
if (-not (Test-Path -LiteralPath $specPath -PathType Leaf)) {
    throw "PyInstaller spec was not found: $specPath"
}
if (-not (Test-Path -LiteralPath $driverPath -PathType Leaf)) {
    throw "ViGEmBus installer was not found: $driverPath"
}

New-Item -ItemType Directory -Path $executablesPath -Force | Out-Null

Write-Host '[TouchKeys] Installing/updating build dependencies.' -ForegroundColor Cyan
& $venvPython -m pip install -r (Join-Path $projectRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed with exit code $LASTEXITCODE." }
& $venvPython -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) { throw "PyInstaller installation failed with exit code $LASTEXITCODE." }

# Remove only this project's generated build outputs and requested release EXE.
Remove-Item -LiteralPath $exePath -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $buildPath -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $distPath -Recurse -Force -ErrorAction SilentlyContinue

Write-Host '[TouchKeys] Building standalone TouchKeys_v3.1.exe.' -ForegroundColor Cyan
& $venvPython -m PyInstaller $specPath --clean --noconfirm `
    --distpath $executablesPath --workpath $buildPath
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE."
}

if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
    throw "The build completed but $exePath was not created."
}

# Keep the driver installer beside the EXE as a convenient release artifact.
$releaseDriverPath = Join-Path $executablesPath 'ViGEmBus_1.22.0_x64_x86_arm64.exe'
Copy-Item -LiteralPath $driverPath -Destination $releaseDriverPath -Force

# Do not leave generated PyInstaller work folders in the project tree.
Remove-Item -LiteralPath $buildPath -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $distPath -Recurse -Force -ErrorAction SilentlyContinue

$sizeMb = [math]::Round((Get-Item -LiteralPath $exePath).Length / 1MB, 1)
Write-Host "[TouchKeys] Created $exePath ($sizeMb MB)" -ForegroundColor Green
Write-Host "[TouchKeys] Driver installer copied to $releaseDriverPath" -ForegroundColor Green
