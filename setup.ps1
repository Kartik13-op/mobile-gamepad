<#
.SYNOPSIS
    TouchKeys — one-click setup for Windows.
    Installs Python (if missing) + all pip dependencies, then launches the server.

.DESCRIPTION
    Run this script on a fresh Windows machine to get TouchKeys running
    with zero manual steps. The script:
      1. Checks for Python 3.9+ (in PATH or registered)
      2. Downloads and installs Python 3.13 silently if not found
      3. Creates a virtual environment in .venv/
      4. Installs all packages from requirements.txt
      5. Optionally starts the gamepad server

.NOTES
    Run this in the TouchKeys project root folder.
    You may need to unblock the script first:
        Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host ""
Write-Host "=============================================="
Write-Host "  TouchKeys Setup"
Write-Host "=============================================="
Write-Host ""

# ---- Step 1: Find or install Python ----

$python = $null

# Check if python is in PATH
try {
    $ver = & python --version 2>&1
    if ($ver -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -ge 3 -and $minor -ge 9) {
            $python = "python"
            Write-Host "  [OK] Found Python $major.$minor"
        }
    }
} catch {}

# Check py launcher
if (-not $python) {
    try {
        $ver = & py --version 2>&1
        if ($ver -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 9) {
                $python = "py"
                Write-Host "  [OK] Found Python $major.$minor (py launcher)"
            }
        }
    } catch {}
}

# Download and install Python if missing
if (-not $python) {
    Write-Host "  [..] Python 3.9+ not found. Downloading Python 3.13..."
    $url = "https://www.python.org/ftp/python/3.13.7/python-3.13.7-amd64.exe"
    $installer = "$env:TEMP\python-3.13.7-amd64.exe"

    try {
        $wc = New-Object System.Net.WebClient
        $wc.DownloadFile($url, $installer)
    } catch {
        Write-Host "  [!] Failed to download Python. Check your internet connection."
        Write-Host "      Manually install from: https://www.python.org/downloads/"
        exit 1
    }

    Write-Host "  [..] Installing Python 3.13 (silent)..."
    $proc = Start-Process -FilePath $installer -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0" -Wait -PassThru

    Remove-Item $installer -ErrorAction SilentlyContinue

    if ($proc.ExitCode -ne 0) {
        Write-Host "  [!] Python installer failed (exit code: $($proc.ExitCode))."
        Write-Host "      Try installing manually: https://www.python.org/downloads/"
        exit 1
    }

    # Refresh PATH so the new Python is visible
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")

    # Try python first, then py
    try { $ver = & python --version 2>&1; $python = "python" } catch {}
    if (-not $python) { try { $ver = & py --version 2>&1; $python = "py" } catch {} }

    if (-not $python) {
        Write-Host "  [!] Python was installed but not found in PATH."
        Write-Host "      Restart your terminal and try again, or add Python manually to PATH."
        exit 1
    }

    Write-Host "  [OK] Python 3.13 installed"
} else {
    Write-Host "  [OK] Python requirement satisfied"
}

# ---- Step 2: Create virtual environment ----

Write-Host ""
Write-Host "  [..] Creating virtual environment..."

if (Test-Path ".venv") {
    Write-Host "  [OK] Virtual environment already exists (.venv/)"
} else {
    try {
        & $python -m venv .venv
        Write-Host "  [OK] Created virtual environment (.venv/)"
    } catch {
        Write-Host "  [!] Failed to create virtual environment: $_"
        exit 1
    }
}

# Determine the Python executable inside the venv
$venvPython = if ($IsWindows -or $env:OS) {
    Join-Path $ProjectRoot ".venv\Scripts\python.exe"
} else {
    Join-Path $ProjectRoot ".venv/bin/python"
}

# ---- Step 3: Install pip dependencies ----

Write-Host ""
Write-Host "  [..] Installing pip dependencies..."

try {
    & $venvPython -m pip install --upgrade pip -q
    & $venvPython -m pip install -r requirements.txt -q
    Write-Host "  [OK] All dependencies installed"
} catch {
    Write-Host "  [!] pip install failed: $_"
    exit 1
}

# ---- Step 4: Launch server ----

Write-Host ""
Write-Host "=============================================="
Write-Host "  Setup complete!"
Write-Host "=============================================="
Write-Host ""

$launch = Read-Host "  Start the gamepad server now? (Y/n)"
if ($launch -eq "" -or $launch -eq "y" -or $launch -eq "Y") {
    Write-Host ""
    Write-Host "  Starting TouchKeys server..."
    Write-Host "  (Press Ctrl+C to stop)"
    Write-Host ""
    & $venvPython server.py
} else {
    Write-Host ""
    Write-Host "  To start later:"
    Write-Host "      .venv\Scripts\python server.py"
    Write-Host "  or double-click start.ps1"
    Write-Host ""
}
