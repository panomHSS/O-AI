Set-StrictMode -Version Latest

function New-OAiMvpPidState {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("Missing", "Invalid", "Dead", "Foreign", "Owned")]
        [string]$Status,
        [Nullable[int]]$ProcessId = $null,
        [object]$Process = $null
    )

    [pscustomobject]@{
        Status = $Status
        ProcessId = $ProcessId
        Process = $Process
    }
}

function Read-OAiMvpPidFile {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return New-OAiMvpPidState -Status "Missing"
    }

    $raw = Get-Content -LiteralPath $Path -Raw -ErrorAction SilentlyContinue
    if ($null -eq $raw) {
        return New-OAiMvpPidState -Status "Invalid"
    }

    $text = $raw.Trim()
    $processId = 0
    if (
        [string]::IsNullOrWhiteSpace($text) -or
        -not [int]::TryParse($text, [ref]$processId) -or
        $processId -le 0
    ) {
        return New-OAiMvpPidState -Status "Invalid"
    }

    return New-OAiMvpPidState -Status "Dead" -ProcessId $processId
}

function Get-OAiMvpProcessById {
    param([Parameter(Mandatory = $true)][int]$ProcessId)

    Get-CimInstance Win32_Process `
        -Filter "ProcessId = $ProcessId" `
        -ErrorAction SilentlyContinue
}

function Test-OAiMvpProcessOwnership {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("backend", "frontend")]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$RepositoryRoot,
        [Parameter(Mandatory = $true)]
        [object]$Process,
        [scriptblock]$ProcessResolver = $null
    )

    $commandLine = [string]$Process.CommandLine
    if ([string]::IsNullOrWhiteSpace($commandLine)) {
        return $false
    }

    $normalizedCommand = $commandLine.Replace("/", "\")
    $normalizedRoot = (
        [System.IO.Path]::GetFullPath($RepositoryRoot)
    ).TrimEnd("\", "/").Replace("/", "\")

    if (
        $normalizedCommand.IndexOf(
            $normalizedRoot,
            [System.StringComparison]::OrdinalIgnoreCase
        ) -lt 0
    ) {
        return $false
    }

    if ($Name -eq "backend") {
        foreach ($token in @(
            "uvicorn app.main:app",
            "--app-dir backend",
            "--port 8000"
        )) {
            if (
                $normalizedCommand.IndexOf(
                    $token,
                    [System.StringComparison]::OrdinalIgnoreCase
                ) -lt 0
            ) {
                return $false
            }
        }
        return $true
    }

    $frontendRoot = (Join-Path $normalizedRoot "frontend").Replace("/", "\")
    if (
        $normalizedCommand.IndexOf(
            $frontendRoot,
            [System.StringComparison]::OrdinalIgnoreCase
        ) -lt 0
    ) {
        return $false
    }

    $hasNextServer = (
        $normalizedCommand.IndexOf(
            "node_modules\next\dist\server\lib\start-server.js",
            [System.StringComparison]::OrdinalIgnoreCase
        ) -ge 0
    )
    if (-not $hasNextServer) {
        return $false
    }

    # Some Next.js versions put --port only on the parent CLI process while
    # the listening child is start-server.js.
    if (
        $normalizedCommand.IndexOf(
            "--port 3000",
            [System.StringComparison]::OrdinalIgnoreCase
        ) -ge 0
    ) {
        return $true
    }

    if ($null -eq $ProcessResolver) {
        $ProcessResolver = {
            param([int]$ResolvedProcessId)
            Get-OAiMvpProcessById -ProcessId $ResolvedProcessId
        }
    }

    $parentProperty = $Process.PSObject.Properties["ParentProcessId"]
    if ($null -eq $parentProperty) {
        return $false
    }

    $parentId = [int]$parentProperty.Value
    for ($depth = 0; $depth -lt 3 -and $parentId -gt 0; $depth++) {
        $parent = & $ProcessResolver $parentId
        if ($null -eq $parent) {
            return $false
        }

        $parentCommand = ([string]$parent.CommandLine).Replace("/", "\")
        $sameFrontendRoot = (
            $parentCommand.IndexOf(
                $frontendRoot,
                [System.StringComparison]::OrdinalIgnoreCase
            ) -ge 0
        )
        $hasNextCli = (
            $parentCommand.IndexOf(
                "next\dist\bin\next",
                [System.StringComparison]::OrdinalIgnoreCase
            ) -ge 0
        )
        $hasDev = (
            $parentCommand.IndexOf(
                " dev ",
                [System.StringComparison]::OrdinalIgnoreCase
            ) -ge 0
        )
        $hasHost = (
            $parentCommand.IndexOf(
                "--hostname 127.0.0.1",
                [System.StringComparison]::OrdinalIgnoreCase
            ) -ge 0
        )
        $hasPort = (
            $parentCommand.IndexOf(
                "--port 3000",
                [System.StringComparison]::OrdinalIgnoreCase
            ) -ge 0
        )

        if (
            $sameFrontendRoot -and
            $hasNextCli -and
            $hasDev -and
            $hasHost -and
            $hasPort
        ) {
            return $true
        }

        $nextParentProperty = $parent.PSObject.Properties["ParentProcessId"]
        if ($null -eq $nextParentProperty) {
            return $false
        }
        $parentId = [int]$nextParentProperty.Value
    }

    return $false
}

function Get-OAiMvpPidState {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)]
        [ValidateSet("backend", "frontend")]
        [string]$Name,
        [Parameter(Mandatory = $true)][string]$RepositoryRoot,
        [scriptblock]$ProcessResolver = $null
    )

    $pidState = Read-OAiMvpPidFile -Path $Path
    if ($pidState.Status -eq "Missing" -or $pidState.Status -eq "Invalid") {
        return $pidState
    }

    if ($null -eq $ProcessResolver) {
        $ProcessResolver = {
            param([int]$ResolvedProcessId)
            Get-OAiMvpProcessById -ProcessId $ResolvedProcessId
        }
    }

    $process = & $ProcessResolver ([int]$pidState.ProcessId)
    if ($null -eq $process) {
        return New-OAiMvpPidState `
            -Status "Dead" `
            -ProcessId $pidState.ProcessId
    }

    if (
        Test-OAiMvpProcessOwnership `
            -Name $Name `
            -RepositoryRoot $RepositoryRoot `
            -Process $process `
            -ProcessResolver $ProcessResolver
    ) {
        return New-OAiMvpPidState `
            -Status "Owned" `
            -ProcessId $pidState.ProcessId `
            -Process $process
    }

    return New-OAiMvpPidState `
        -Status "Foreign" `
        -ProcessId $pidState.ProcessId `
        -Process $process
}

function Remove-OAiMvpPidFile {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        Remove-Item -LiteralPath $Path -Force
    }
}

function Get-OAiMvpStartDisposition {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("Missing", "Invalid", "Dead", "Foreign", "Owned")]
        [string]$Status
    )

    switch ($Status) {
        "Owned" { return "block" }
        "Missing" { return "proceed" }
        default { return "cleanup" }
    }
}

function Get-OAiMvpStopDisposition {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("Missing", "Invalid", "Dead", "Foreign", "Owned")]
        [string]$Status
    )

    switch ($Status) {
        "Owned" { return "kill" }
        "Missing" { return "none" }
        default { return "cleanup" }
    }
}

function Get-OAiMvpListenerPid {
    param([Parameter(Mandatory = $true)][int]$Port)

    $line = netstat.exe -ano -p tcp |
        Select-String "127.0.0.1:$Port\s+.*LISTENING" |
        Select-Object -First 1

    if ($line -and $line.Line -match "\s+(\d+)\s*$") {
        return [int]$Matches[1]
    }

    return $null
}