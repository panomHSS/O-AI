$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repositoryRoot

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

if (-not (Test-Path "frontend/.env.local")) {
    Copy-Item "frontend/.env.example" "frontend/.env.local"
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    throw "Python 3.14 must be installed and available as 'python'."
}

if (-not (Test-Path ".venv/Scripts/python.exe")) {
    & $pythonCommand.Source -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
& npm.cmd --prefix frontend ci
