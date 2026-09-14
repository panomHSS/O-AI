$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repositoryRoot

$requiredPaths = @(
    ".env",
    "frontend/.env.local",
    ".venv/Scripts/python.exe",
    "frontend/node_modules",
    "data"
)
foreach ($path in $requiredPaths) {
    if (-not (Test-Path $path)) {
        throw "Missing '$path'. Run .\scripts\bootstrap.ps1 first."
    }
}

$stateDirectory = Join-Path $repositoryRoot "data/mvp"
$logDirectory = Join-Path $stateDirectory "logs"
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

function Assert-PortAvailable([int]$Port) {
    $listener = netstat.exe -ano -p tcp | Select-String "127.0.0.1:$Port\s+.*LISTENING"
    if ($listener.Count -gt 0) {
        throw "127.0.0.1:$Port is already in use. Stop the existing O-AI MVP or select a free local environment."
    }
}

function Remove-StalePid([string]$Path) {
    if (-not (Test-Path $Path)) { return }
    $processId = [int](Get-Content $Path -Raw)
    if (Get-Process -Id $processId -ErrorAction SilentlyContinue) {
        throw "O-AI MVP process $processId is still running. Run .\scripts\stop_mvp.ps1 first."
    }
    Remove-Item -LiteralPath $Path -Force
}

function Wait-ForLocalPort([int]$Port) {
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        $line = netstat.exe -ano -p tcp | Select-String "127.0.0.1:$Port\s+.*LISTENING" | Select-Object -First 1
        if ($line -and $line.Line -match "\s+(\d+)\s*$") {
            return [int]$Matches[1]
        }
        Start-Sleep -Seconds 1
    }
    throw "O-AI MVP did not begin listening on 127.0.0.1:$Port. Check data/mvp/logs."
}

$backendPid = Join-Path $stateDirectory "backend.pid"
$frontendPid = Join-Path $stateDirectory "frontend.pid"
Remove-StalePid $backendPid
Remove-StalePid $frontendPid
Assert-PortAvailable 8000
Assert-PortAvailable 3000

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$cmd = Join-Path $env:SystemRoot "System32/cmd.exe"
$backendCommand = 'start "" /b ""{0}"" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 1>"{1}" 2>"{2}"' -f `
    (Join-Path $repositoryRoot ".venv/Scripts/python.exe"), `
    (Join-Path $logDirectory "backend-$stamp.out.log"), `
    (Join-Path $logDirectory "backend-$stamp.err.log")
Push-Location $repositoryRoot
& $cmd /c $backendCommand
Pop-Location
$backendProcessId = Wait-ForLocalPort 8000

$frontendCommand = 'start "" /b npm.cmd run dev -- --hostname 127.0.0.1 --port 3000 1>"{0}" 2>"{1}"' -f `
    (Join-Path $logDirectory "frontend-$stamp.out.log"), `
    (Join-Path $logDirectory "frontend-$stamp.err.log")
Push-Location (Join-Path $repositoryRoot "frontend")
& $cmd /c $frontendCommand
Pop-Location
$frontendProcessId = Wait-ForLocalPort 3000

Set-Content -LiteralPath $backendPid -Value $backendProcessId -NoNewline
Set-Content -LiteralPath $frontendPid -Value $frontendProcessId -NoNewline

Write-Host "O-AI MVP starting on loopback only:"
Write-Host "  Backend:  http://127.0.0.1:8000"
Write-Host "  Frontend: http://127.0.0.1:3000"
Write-Host "Run .\scripts\smoke_mvp.ps1 after both processes are ready."
