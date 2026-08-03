$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting TouchKeys server..."
Write-Host "(Press Ctrl+C to stop)"
python (Join-Path $ProjectRoot "gui.py")
