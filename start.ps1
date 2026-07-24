<#
.SYNOPSIS
    Quick-launch the TouchKeys gamepad server.
    Assumes setup.ps1 has been run once already.
#>
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Virtual environment not found."
    Write-Host "Run setup.ps1 first, or start manually:"
    Write-Host "    python gui.py"
    exit 1
}

Write-Host "Starting TouchKeys server..."
Write-Host "(Press Ctrl+C to stop)"
& $venvPython (Join-Path $ProjectRoot "gui.py")
