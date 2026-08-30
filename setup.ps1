[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $projectRoot '.venv'
$venvPython = Join-Path $venvPath 'Scripts\python.exe'
$requirementsPath = Join-Path $projectRoot 'requirements.txt'
$driverInstaller = Join-Path $projectRoot 'installers\ViGEmBus_1.22.0_x64_x86_arm64.exe'

function Find-Python {
    $commands = @('py', 'python')

    foreach ($commandName in $commands) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            try {
                $versionOutput = (& $command.Source --version 2>&1 | Out-String).Trim()
                if ($LASTEXITCODE -eq 0 -and $versionOutput -match 'Python (\d+\.\d+)') {
                    if ([version]$matches[1] -ge [version]'3.9') {
                        return $command.Source
                    }
                }
            }
            catch {
            }
        }
    }

    $knownPaths = @(
        (Join-Path $env:LocalAppData 'Programs\Python\Python312\python.exe'),
        (Join-Path $env:LocalAppData 'Programs\Python\Python311\python.exe'),
        (Join-Path $env:ProgramFiles 'Python312\python.exe'),
        (Join-Path $env:ProgramFiles 'Python311\python.exe')
    )

    foreach ($path in $knownPaths) {
        if (Test-Path $path) {
            return $path
        }
    }

    return $null
}

Write-Host 'TouchKeys setup' -ForegroundColor Cyan

$pythonCommand = Find-Python
if ($null -eq $pythonCommand) {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($null -eq $winget) {
        throw 'Python 3.9 or newer was not found, and winget is unavailable. Install Python from https://www.python.org/downloads/ and run setup.ps1 again.'
    }

    Write-Host 'Python was not found. Installing Python 3.12 with winget...' -ForegroundColor Yellow
    & $winget.Source install --id Python.Python.3.12 --exact --scope user --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "Python installation failed with exit code $LASTEXITCODE."
    }

    $pythonCommand = Find-Python
    if ($null -eq $pythonCommand) {
        throw 'Python was installed, but no Python executable could be located. Restart PowerShell and run setup.ps1 again.'
    }
}

Write-Host "Using Python: $pythonCommand"

if (-not (Test-Path $venvPython)) {
    Write-Host 'Creating the .venv virtual environment...' -ForegroundColor Yellow
    & $pythonCommand -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        throw "Virtual environment creation failed with exit code $LASTEXITCODE."
    }
}

Write-Host 'Installing Python dependencies...' -ForegroundColor Yellow
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "pip upgrade failed with exit code $LASTEXITCODE."
}
& $venvPython -m pip install -r $requirementsPath
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed with exit code $LASTEXITCODE."
}

if (-not (Test-Path $driverInstaller)) {
    throw "ViGEmBus installer was not found at $driverInstaller."
}

Write-Host 'Launching the ViGEmBus driver installer...' -ForegroundColor Yellow
$driverProcess = Start-Process -FilePath $driverInstaller -Verb RunAs -Wait -PassThru
if ($driverProcess.ExitCode -ne 0) {
    throw "ViGEmBus installation failed with exit code $($driverProcess.ExitCode)."
}

Write-Host ''
Write-Host 'Setup completed successfully.' -ForegroundColor Green
Write-Host 'Run the application with:' -ForegroundColor Cyan
Write-Host "  & '$venvPython' '$projectRoot\gui.py'"
