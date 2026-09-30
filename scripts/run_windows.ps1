[CmdletBinding()]
param(
    [switch]$Demo,
    [string]$Config = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv-ui\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Missing .venv-ui. Run .\scripts\setup_windows.ps1 first."
}

if (-not $Config) {
    $Config = Join-Path $ProjectRoot "llm_agent\config.local.yaml"
}

Push-Location $ProjectRoot
try {
    if ($Demo) {
        & $Python "run_ui.py" --demo
    }
    else {
        if (-not (Test-Path $Config)) {
            throw "Configuration does not exist: $Config"
        }
        & $Python "run_ui.py" --config $Config
    }
    if ($LASTEXITCODE -ne 0) {
        throw "SoundCraft launcher failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
