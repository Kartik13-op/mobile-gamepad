[CmdletBinding()]
param()

# TouchKeys first-time setup. This script is intentionally verbose so that
# users can see exactly which software is being installed and why.
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '.')).Path
$installerRoot = Join-Path $projectRoot 'installers'
$pythonManagerInstaller = Join-Path $installerRoot 'python-manager-26.3.msix'
$driverInstaller = Join-Path $installerRoot 'ViGEmBus_1.22.0_x64_x86_arm64.exe'
$venvPath = Join-Path $projectRoot '.venv'
$venvPython = Join-Path $venvPath 'Scripts\python.exe'
$requirementsPath = Join-Path $projectRoot 'requirements.txt'
$touchKeysExe = Join-Path $projectRoot 'TouchKeys.exe'
$desktopPath = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktopPath 'TouchKeys.lnk'

function Write-Step {
    param([string]$Message)
    Write-Host "`n[TouchKeys] $Message" -ForegroundColor Cyan
}

function Test-Command {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Install-PythonManager {
    if (-not (Test-Path -LiteralPath $pythonManagerInstaller -PathType Leaf)) {
        throw "Python Manager installer was not found at $pythonManagerInstaller"
    }

    Write-Step 'Installing Python Manager from installers\python-manager-26.3.msix.'
    try {
        Add-AppxPackage -Path $pythonManagerInstaller -ErrorAction Stop
        Write-Host 'Python Manager installed.' -ForegroundColor Green
    }
    catch {
        # Re-running setup is safe when the same/newer MSIX is already present.
        $message = $_.Exception.Message
        if ($message -match 'already installed|higher version|same version') {
            Write-Host 'Python Manager is already installed; continuing.' -ForegroundColor Yellow
        }
        else {
            throw "Python Manager installation failed: $message"
        }
    }
}

function Resolve-PythonManager {
    $pyCommand = Get-Command 'py.exe' -ErrorAction SilentlyContinue
    if ($null -eq $pyCommand) {
        $windowsAppsPy = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\py.exe'
        if (Test-Path -LiteralPath $windowsAppsPy -PathType Leaf) {
            return $windowsAppsPy
        }
    }
    else {
        return $pyCommand.Source
    }
    return $null
}

function Install-PythonRuntime {
    $pythonManager = Resolve-PythonManager
    if ($null -eq $pythonManager) {
        throw 'Python Manager was installed but py.exe is not available yet. Restart PowerShell and run setup.ps1 again.'
    }

    Write-Step 'Installing the Python 3.12 runtime through Python Manager.'
    & $pythonManager install 3.12
    if ($LASTEXITCODE -ne 0) {
        throw "Python 3.12 installation failed with exit code $LASTEXITCODE."
    }

    $pythonPath = (& $pythonManager -3.12 -c 'import sys; print(sys.executable)' | Select-Object -Last 1).ToString().Trim()
    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw "Python Manager did not return a usable Python executable: $pythonPath"
    }
    return $pythonPath
}

Write-Host 'TouchKeys setup' -ForegroundColor Cyan
Write-Host "Project folder: $projectRoot"
Write-Host 'This setup installs Python for TouchKeys, creates its private environment, installs dependencies, and installs the ViGEmBus driver required for virtual Xbox controllers.'
Write-Host 'A Windows administrator prompt is expected only when installing ViGEmBus.' -ForegroundColor Yellow

Install-PythonManager
$basePython = Install-PythonRuntime

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    Write-Step 'Creating TouchKeys private Python environment.'
    & $basePython -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        throw "Virtual environment creation failed with exit code $LASTEXITCODE."
    }
}
else {
    Write-Step 'TouchKeys private Python environment already exists; reusing it.'
}

Write-Step 'Installing or updating TouchKeys Python dependencies from requirements.txt.'
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "pip upgrade failed with exit code $LASTEXITCODE."
}
& $venvPython -m pip install -r $requirementsPath
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed with exit code $LASTEXITCODE."
}

if (-not (Test-Path -LiteralPath $driverInstaller -PathType Leaf)) {
    throw "ViGEmBus installer was not found at $driverInstaller"
}

Write-Step 'Opening the ViGEmBus driver installer.'
Write-Host 'ViGEmBus is the Windows driver that lets TouchKeys create virtual Xbox 360 controllers.'
Write-Host 'Please approve the administrator prompt and complete that installer.' -ForegroundColor Yellow
$driverProcess = Start-Process -FilePath $driverInstaller -Verb RunAs -Wait -PassThru
if ($driverProcess.ExitCode -ne 0) {
    throw "ViGEmBus installation failed with exit code $($driverProcess.ExitCode)."
}

if (Test-Path -LiteralPath $touchKeysExe -PathType Leaf) {
    Write-Step 'Creating a desktop shortcut.'
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $touchKeysExe
    $shortcut.WorkingDirectory = $projectRoot
    $shortcut.IconLocation = "$touchKeysExe,0"
    $shortcut.Description = 'Launch the TouchKeys mobile gamepad server and monitor.'
    $shortcut.Save()
    Write-Host "Desktop shortcut created: $shortcutPath" -ForegroundColor Green
}
else {
    Write-Host "TouchKeys.exe was not found at $touchKeysExe; no shortcut was created." -ForegroundColor Yellow
    Write-Host 'Build or copy the root executable, then run setup.ps1 again to create the shortcut.' -ForegroundColor Yellow
}

Write-Host "`nSetup completed successfully." -ForegroundColor Green
Write-Host 'Start TouchKeys from the desktop shortcut or by double-clicking TouchKeys.exe.' -ForegroundColor Cyan
Write-Host 'The first launch may open a terminal window because the launcher starts the Python backend.'
