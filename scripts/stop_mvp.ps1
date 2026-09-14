$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$stateDirectory = Join-Path $repositoryRoot "data/mvp"

function Stop-OwnedMvpProcess([string]$Name, [string]$ExpectedText) {
    $pidPath = Join-Path $stateDirectory "$Name.pid"
    if (-not (Test-Path $pidPath)) {
        Write-Host "No recorded $Name MVP process."
        return
    }
    $processId = [int](Get-Content $pidPath -Raw)
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    if (
        $process -and
        $process.CommandLine -like "*$repositoryRoot*" -and
        $process.CommandLine -like "*$ExpectedText*"
    ) {
        & taskkill.exe /PID $processId /T /F | Out-Null
        Write-Host "Stopped O-AI MVP $Name process $processId."
    } elseif ($process) {
        Write-Warning "Recorded $Name process $processId does not match the O-AI MVP command; it was not stopped."
        return
    }
    Remove-Item -LiteralPath $pidPath -Force
}

Stop-OwnedMvpProcess "backend" "uvicorn app.main:app"
Stop-OwnedMvpProcess "frontend" "node_modules\next\dist\server\lib\start-server.js"

foreach ($port in @(8000, 3000)) {
    $listener = netstat.exe -ano -p tcp | Select-String "127.0.0.1:$port\s+.*LISTENING"
    if ($listener.Count -gt 0) {
        throw "127.0.0.1:$port is still listening; it was not stopped because it is not an O-AI-owned MVP process."
    }
}

Write-Host "O-AI MVP backend and frontend loopback listeners are stopped."
