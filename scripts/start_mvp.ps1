$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repositoryRoot
. (Join-Path $PSScriptRoot "mvp_process.ps1")

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
    $listenerPid = Get-OAiMvpListenerPid -Port $Port
    if ($null -ne $listenerPid) {
        throw "127.0.0.1:$Port is already in use by process $listenerPid. O-AI will not stop an unknown listener."
    }
}

function Prepare-MvpPidForStart([string]$Name, [string]$Path) {
    $state = Get-OAiMvpPidState -Path $Path -Name $Name -RepositoryRoot $repositoryRoot
    $disposition = Get-OAiMvpStartDisposition -Status $state.Status

    if ($disposition -eq "block") {
        throw "O-AI MVP $Name process $($state.ProcessId) is still running. Run .\scripts\stop_mvp.ps1 first."
    }

    if ($disposition -eq "cleanup") {
        if ($state.Status -eq "Foreign") {
            Write-Warning "Recorded $Name PID $($state.ProcessId) belongs to another process. O-AI will not stop it; stale PID state will be removed."
        } elseif ($state.Status -eq "Invalid") {
            Write-Warning "Recorded $Name PID state is invalid. Stale PID state will be removed."
        }
        Remove-OAiMvpPidFile -Path $Path
    }
}

function Start-DetachedCommand([string]$Command, [string]$WorkingDirectory) {
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = Join-Path $env:SystemRoot "System32/cmd.exe"
    $startInfo.Arguments = "/d /s /c $Command"
    $startInfo.WorkingDirectory = $WorkingDirectory
    $startInfo.UseShellExecute = $true
    $process = [System.Diagnostics.Process]::Start($startInfo)
    if ($null -eq $process) { throw "Could not start O-AI MVP command." }
    return $process
}

function Wait-ForOwnedLocalPort([string]$Name, [int]$Port) {
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        $listenerPid = Get-OAiMvpListenerPid -Port $Port
        if ($null -ne $listenerPid) {
            $process = Get-OAiMvpProcessById -ProcessId $listenerPid
            if ($process -and (Test-OAiMvpProcessOwnership -Name $Name -RepositoryRoot $repositoryRoot -Process $process)) {
                return $listenerPid
            }
            throw "127.0.0.1:$Port began listening from process $listenerPid, but it is not the expected O-AI MVP $Name process."
        }
        Start-Sleep -Seconds 1
    }
    throw "O-AI MVP $Name did not begin listening on 127.0.0.1:$Port. Check data/mvp/logs."
}

function Stop-StartedLauncher([object]$Launcher, [string]$Name) {
    if ($null -eq $Launcher) { return }
    try {
        if (-not $Launcher.HasExited) {
            & taskkill.exe /PID $Launcher.Id /T /F | Out-Null
            Write-Warning "Cleaned up partially started O-AI MVP $Name launcher process $($Launcher.Id)."
        }
    } catch {
        Write-Warning "Could not clean up partially started $Name launcher process: $($_.Exception.Message)"
    }
}

function Stop-ValidatedOwnedPid([string]$Name, [string]$PidPath, [Nullable[int]]$ExpectedPid) {
    if ($null -eq $ExpectedPid) { return }

    $state = Get-OAiMvpPidState -Path $PidPath -Name $Name -RepositoryRoot $repositoryRoot
    if ($state.Status -eq "Owned" -and $state.ProcessId -eq $ExpectedPid) {
        & taskkill.exe /PID $ExpectedPid /T /F | Out-Null
    }
    Remove-OAiMvpPidFile -Path $PidPath
}

$backendPid = Join-Path $stateDirectory "backend.pid"
$frontendPid = Join-Path $stateDirectory "frontend.pid"
Prepare-MvpPidForStart "backend" $backendPid
Prepare-MvpPidForStart "frontend" $frontendPid
Assert-PortAvailable 8000
Assert-PortAvailable 3000

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backendLauncher = $null
$frontendLauncher = $null
$backendProcessId = $null
$frontendProcessId = $null

try {
    $backendCommand = '""{0}" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 1>"{1}" 2>"{2}""' -f `
        (Join-Path $repositoryRoot ".venv/Scripts/python.exe"), `
        (Join-Path $logDirectory "backend-$stamp.out.log"), `
        (Join-Path $logDirectory "backend-$stamp.err.log")
    $backendLauncher = Start-DetachedCommand $backendCommand $repositoryRoot
    $backendProcessId = Wait-ForOwnedLocalPort "backend" 8000
    Set-Content -LiteralPath $backendPid -Value $backendProcessId -NoNewline

    $frontendCommand = '""npm.cmd run dev -- --hostname 127.0.0.1 --port 3000 1>"{0}" 2>"{1}""' -f `
        (Join-Path $logDirectory "frontend-$stamp.out.log"), `
        (Join-Path $logDirectory "frontend-$stamp.err.log")
    $frontendLauncher = Start-DetachedCommand $frontendCommand (Join-Path $repositoryRoot "frontend")
    $frontendProcessId = Wait-ForOwnedLocalPort "frontend" 3000
    Set-Content -LiteralPath $frontendPid -Value $frontendProcessId -NoNewline
} catch {
    Stop-ValidatedOwnedPid -Name "frontend" -PidPath $frontendPid -ExpectedPid $frontendProcessId
    Stop-StartedLauncher -Launcher $frontendLauncher -Name "frontend"
    Stop-ValidatedOwnedPid -Name "backend" -PidPath $backendPid -ExpectedPid $backendProcessId
    Stop-StartedLauncher -Launcher $backendLauncher -Name "backend"
    throw
}

Write-Host "O-AI MVP starting on loopback only:"
Write-Host "  Backend:  http://127.0.0.1:8000"
Write-Host "  Frontend: http://127.0.0.1:3000"
Write-Host "Run .\scripts\smoke_mvp.ps1 after both processes are ready."