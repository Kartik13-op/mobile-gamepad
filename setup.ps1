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
$specPath = Join-Path $projectRoot 'main.spec'
$buildPath = Join-Path $projectRoot 'build'
$distPath = Join-Path $projectRoot 'dist'
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
        throw 'Python Manager is not available and no Python 3.12 installation was found.'
    }

    # Reuse Python 3.12 when it is already installed. Python Manager can write
    # progress text to stdout, so accept only output lines that resolve to a file.
    $existingOutput = @(& $pythonManager -3.12 -c 'import sys; print(sys.executable)' 2>$null)
    foreach ($candidate in $existingOutput) {
        $candidate = ([string]$candidate).Trim()
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            Write-Host "Using existing Python 3.12: $candidate" -ForegroundColor Green
            return $candidate
        }
    }

    Write-Step 'Installing the Python 3.12 runtime through Python Manager.'
    & $pythonManager install 3.12
    if ($LASTEXITCODE -ne 0) {
        throw "Python 3.12 installation failed with exit code $LASTEXITCODE."
    }

    $pythonOutput = @(& $pythonManager -3.12 -c 'import sys; print(sys.executable)' 2>$null)
    $pythonPath = $null
    foreach ($candidate in $pythonOutput) {
        $candidate = ([string]$candidate).Trim()
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            $pythonPath = $candidate
            break
        }
    }
    if ($null -eq $pythonPath) {
        throw "Python Manager did not return a usable Python executable."
    }
    return $pythonPath
}

Write-Host 'TouchKeys setup' -ForegroundColor Cyan
Write-Host "Project folder: $projectRoot"
Write-Host 'This setup installs Python for TouchKeys, creates its private environment, installs dependencies, and installs the ViGEmBus driver required for virtual Xbox controllers.'
Write-Host 'A Windows administrator prompt is expected only when installing ViGEmBus.' -ForegroundColor Yellow

# Install Python Manager only when it is not already available.
if ($null -eq (Resolve-PythonManager)) {
    Install-PythonManager
}
else {
    Write-Host 'Python Manager is already available; checking for Python 3.12.' -ForegroundColor Green
}
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

Write-Step 'Building the local TouchKeys.exe launcher.'
Write-Host 'The executable is built on this computer from the checked-out source.' -ForegroundColor Yellow
& $venvPython -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller installation failed with exit code $LASTEXITCODE."
}

Remove-Item -LiteralPath $touchKeysExe -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $buildPath -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $distPath -Recurse -Force -ErrorAction SilentlyContinue

& $venvPython -m PyInstaller $specPath --clean --noconfirm --distpath $projectRoot --workpath $buildPath
if ($LASTEXITCODE -ne 0) {
    throw "TouchKeys.exe build failed with exit code $LASTEXITCODE."
}
if (-not (Test-Path -LiteralPath $touchKeysExe -PathType Leaf)) {
    throw "The build completed but $touchKeysExe was not created."
}

Remove-Item -LiteralPath $buildPath -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $distPath -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Created local launcher: $touchKeysExe" -ForegroundColor Green

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
    throw "The local TouchKeys.exe build is missing at $touchKeysExe."
}

Write-Host "`nSetup completed successfully." -ForegroundColor Green
Write-Host 'Start TouchKeys from the desktop shortcut or by double-clicking TouchKeys.exe.' -ForegroundColor Cyan
Write-Host 'The first launch may open a terminal window because the launcher starts the Python backend.'
