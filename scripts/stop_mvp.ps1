$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$stateDirectory = Join-Path $repositoryRoot "data/mvp"
. (Join-Path $PSScriptRoot "mvp_process.ps1")

function Stop-OwnedMvpProcess([string]$Name) {
    $pidPath = Join-Path $stateDirectory "$Name.pid"
    $state = Get-OAiMvpPidState -Path $pidPath -Name $Name -RepositoryRoot $repositoryRoot
    $disposition = Get-OAiMvpStopDisposition -Status $state.Status

    if ($disposition -eq "none") {
        Write-Host "No recorded $Name MVP process."
        return
    }

    if ($disposition -eq "kill") {
        & taskkill.exe /PID $state.ProcessId /T /F | Out-Null
        Write-Host "Stopped O-AI MVP $Name process $($state.ProcessId)."
        Remove-OAiMvpPidFile -Path $pidPath
        return
    }

    if ($state.Status -eq "Foreign") {
        Write-Warning "Recorded $Name PID $($state.ProcessId) belongs to another process. It was not stopped; stale PID state will be removed."
    } elseif ($state.Status -eq "Invalid") {
        Write-Warning "Recorded $Name PID state is invalid. Stale PID state will be removed."
    } elseif ($state.Status -eq "Dead") {
        Write-Host "Recorded $Name process $($state.ProcessId) is no longer running; removing stale PID state."
    }

    Remove-OAiMvpPidFile -Path $pidPath
}

Stop-OwnedMvpProcess "backend"
Stop-OwnedMvpProcess "frontend"

foreach ($port in @(8000, 3000)) {
    $listenerPid = Get-OAiMvpListenerPid -Port $port
    if ($null -ne $listenerPid) {
        throw "127.0.0.1:$port is still listening on process $listenerPid; it was not stopped because O-AI has no validated ownership for that listener."
    }
}

Write-Host "O-AI MVP backend and frontend loopback listeners are stopped."