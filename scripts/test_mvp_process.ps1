$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDirectory "mvp_process.ps1")
$script:Passed = 0

function Assert-Equal([object]$Actual, [object]$Expected, [string]$Message) {
    if ($Actual -ne $Expected) { throw "$Message Expected '$Expected', got '$Actual'." }
    $script:Passed++
}
function Assert-True([bool]$Value, [string]$Message) {
    if (-not $Value) { throw $Message }
    $script:Passed++
}
function Assert-False([bool]$Value, [string]$Message) {
    if ($Value) { throw $Message }
    $script:Passed++
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("oai-d41-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempRoot | Out-Null

try {
    $repoRoot = Join-Path $tempRoot "O-AI"
    New-Item -ItemType Directory -Path $repoRoot | Out-Null
    $pidPath = Join-Path $tempRoot "backend.pid"

    $state = Get-OAiMvpPidState -Path $pidPath -Name "backend" -RepositoryRoot $repoRoot -ProcessResolver { param($id) $null }
    Assert-Equal $state.Status "Missing" "Missing PID classification failed."

    Set-Content -LiteralPath $pidPath -Value "" -NoNewline
    $state = Get-OAiMvpPidState -Path $pidPath -Name "backend" -RepositoryRoot $repoRoot -ProcessResolver { param($id) $null }
    Assert-Equal $state.Status "Invalid" "Empty PID classification failed."

    Set-Content -LiteralPath $pidPath -Value "not-a-pid" -NoNewline
    $state = Get-OAiMvpPidState -Path $pidPath -Name "backend" -RepositoryRoot $repoRoot -ProcessResolver { param($id) $null }
    Assert-Equal $state.Status "Invalid" "Non-numeric PID classification failed."

    Set-Content -LiteralPath $pidPath -Value "0" -NoNewline
    $state = Get-OAiMvpPidState -Path $pidPath -Name "backend" -RepositoryRoot $repoRoot -ProcessResolver { param($id) $null }
    Assert-Equal $state.Status "Invalid" "Zero PID classification failed."

    Set-Content -LiteralPath $pidPath -Value "4321" -NoNewline
    $state = Get-OAiMvpPidState -Path $pidPath -Name "backend" -RepositoryRoot $repoRoot -ProcessResolver { param($id) $null }
    Assert-Equal $state.Status "Dead" "Dead PID classification failed."

    $foreign = [pscustomobject]@{ ProcessId = 4321; CommandLine = "C:\Windows\System32\notepad.exe" }
    $state = Get-OAiMvpPidState -Path $pidPath -Name "backend" -RepositoryRoot $repoRoot -ProcessResolver { param($id) $foreign }
    Assert-Equal $state.Status "Foreign" "Foreign PID classification failed."

    $backend = [pscustomobject]@{
        ProcessId = 4321
        CommandLine = ('"' + (Join-Path $repoRoot ".venv\Scripts\python.exe") + '" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000')
    }
    $state = Get-OAiMvpPidState -Path $pidPath -Name "backend" -RepositoryRoot $repoRoot -ProcessResolver { param($id) $backend }
    Assert-Equal $state.Status "Owned" "Backend ownership classification failed."

    $frontendPid = Join-Path $tempRoot "frontend.pid"
    Set-Content -LiteralPath $frontendPid -Value "5432" -NoNewline
    $frontend = [pscustomobject]@{
        ProcessId = 5432
        CommandLine = ('node "' + (Join-Path $repoRoot "frontend\node_modules\next\dist\server\lib\start-server.js") + '" --hostname 127.0.0.1 --port 3000')
    }
    $state = Get-OAiMvpPidState -Path $frontendPid -Name "frontend" -RepositoryRoot $repoRoot -ProcessResolver { param($id) $frontend }
    Assert-Equal $state.Status "Owned" "Frontend ownership classification failed."

    $wrongPortFrontend = [pscustomobject]@{
        ProcessId = 5432
        CommandLine = ('node "' + (Join-Path $repoRoot "frontend\node_modules\next\dist\server\lib\start-server.js") + '" --hostname 127.0.0.1 --port 3999')
    }
    Assert-False (Test-OAiMvpProcessOwnership -Name "frontend" -RepositoryRoot $repoRoot -Process $wrongPortFrontend) "Frontend ownership accepted the wrong port."

    Assert-Equal (Get-OAiMvpStartDisposition -Status "Missing") "proceed" "Missing PID should permit start."
    Assert-Equal (Get-OAiMvpStartDisposition -Status "Dead") "cleanup" "Dead PID should be cleaned before start."
    Assert-Equal (Get-OAiMvpStartDisposition -Status "Foreign") "cleanup" "Foreign reused PID should be cleaned before start."
    Assert-Equal (Get-OAiMvpStartDisposition -Status "Owned") "block" "Owned process should block duplicate start."
    Assert-Equal (Get-OAiMvpStopDisposition -Status "Foreign") "cleanup" "Foreign PID must never be kill-eligible."
    Assert-Equal (Get-OAiMvpStopDisposition -Status "Owned") "kill" "Owned PID should be kill-eligible."

    Remove-OAiMvpPidFile -Path $pidPath
    Assert-False (Test-Path -LiteralPath $pidPath) "PID cleanup did not remove stale state."

    $outside = [pscustomobject]@{
        ProcessId = 4321
        CommandLine = '"C:\Other\python.exe" -m uvicorn app.main:app --app-dir backend --port 8000'
    }
    Assert-False (Test-OAiMvpProcessOwnership -Name "backend" -RepositoryRoot $repoRoot -Process $outside) "Backend outside the O-AI repository was incorrectly owned."

    Write-Host "D41 MVP process lifecycle tests passed: $script:Passed assertions."
} finally {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}