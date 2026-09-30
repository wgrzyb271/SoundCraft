[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvRoot = Join-Path $ProjectRoot ".venv-ui"
$Python = Join-Path $VenvRoot "Scripts\python.exe"

function Assert-LastExitCode([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}

if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw "npm.cmd was not found. Install Node.js LTS and reopen PowerShell."
}

Push-Location $ProjectRoot
try {
    if (-not (Test-Path $Python)) {
        if (Get-Command py.exe -ErrorAction SilentlyContinue) {
            & py.exe -3 -m venv $VenvRoot
        }
        elseif (Get-Command python.exe -ErrorAction SilentlyContinue) {
            & python.exe -m venv $VenvRoot
        }
        else {
            throw "Python was not found. Install Python 3.11 or 3.12 and reopen PowerShell."
        }
        Assert-LastExitCode "Creating Python virtual environment"
    }

    & $Python -m pip install --upgrade pip
    Assert-LastExitCode "Upgrading pip"

    & $Python -m pip install -r (Join-Path $ProjectRoot "requirements-ui.txt")
    Assert-LastExitCode "Installing Python dependencies"

    Push-Location (Join-Path $ProjectRoot "SoundCraft_frontend")
    try {
        & npm.cmd install
        Assert-LastExitCode "Installing frontend dependencies"
    }
    finally {
        Pop-Location
    }

    Write-Host ""
    Write-Host "SoundCraft Windows setup completed." -ForegroundColor Green
    Write-Host "Python: $Python"
    Write-Host "Next: configure llm_agent\config.local.yaml as described in INSTRUKCJA_WINDOWS.md"
}
finally {
    Pop-Location
}
