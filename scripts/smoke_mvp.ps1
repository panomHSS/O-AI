$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repositoryRoot
$apiBase = "http://127.0.0.1:8000/api/v1"
$requestId = "mvp-smoke-$([guid]::NewGuid().ToString('N'))"
$workspaceHeaders = @{
    "X-Request-ID" = $requestId
    "X-OAI-Workspace" = "personal"
}

function Invoke-OaiRequest([string]$Method, [string]$Uri, [object]$Body = $null, [hashtable]$Headers = @{}) {
    $parameters = @{ Method = $Method; Uri = $Uri; Headers = $Headers; UseBasicParsing = $true }
    if ($null -ne $Body) {
        $parameters.ContentType = "application/json"
        $parameters.Body = ($Body | ConvertTo-Json -Compress)
    }
    try {
        return Invoke-WebRequest @parameters
    } catch {
        $response = $_.Exception.Response
        if ($null -eq $response) { throw }
        $reader = [System.IO.StreamReader]::new($response.GetResponseStream())
        $content = $reader.ReadToEnd()
        $reader.Dispose()
        return [pscustomobject]@{ StatusCode = [int]$response.StatusCode; Content = $content; Headers = $response.Headers }
    }
}

# Resolve only deployment values; an absent override inherits its matching common value.
function Get-OaiDeploymentValue([string]$Text, [string]$Name, [string]$Default) {
    $matchesForSetting = [regex]::Matches($Text, "(?m)^\s*" + [regex]::Escape($Name) + "\s*=\s*([^\r\n]*)")
    if ($matchesForSetting.Count -eq 0) { return $Default }
    $value = $matchesForSetting[$matchesForSetting.Count - 1].Groups[1].Value.Trim()
    if ($value -match '^("([^"\r\n]*)"|''([^''\r\n]*)'')\s*(#.*)?$') {
        if ($value.StartsWith('"')) { $value = $Matches[2] } else { $value = $Matches[3] }
    } else {
        $value = ($value -replace '\s+#.*$', '').Trim()
    }
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Deployment setting '$Name' is empty. Omit an optional override to inherit the common setting."
    }
    return $value
}

$health = Invoke-OaiRequest "GET" "$apiBase/health" $null @{ "X-Request-ID" = $requestId }
if ($health.StatusCode -ne 200) { throw "Backend health check failed with HTTP $($health.StatusCode)." }
$healthBody = $health.Content | ConvertFrom-Json
if (-not $healthBody.success -or -not $healthBody.data.database_revision) { throw "Backend health did not report a valid database revision." }
if ($health.Headers["X-Request-ID"] -ne $requestId) { throw "Backend did not preserve X-Request-ID." }
Write-Host "Backend health and database revision: OK ($($healthBody.data.database_revision))"

foreach ($frontendUrl in @("http://localhost:3000/chat", "http://127.0.0.1:3000/chat")) {
    $frontend = Invoke-OaiRequest "GET" $frontendUrl
    if ($frontend.StatusCode -ne 200) { throw "Frontend reachability check failed for $frontendUrl with HTTP $($frontend.StatusCode)." }
}
Write-Host "Frontend localhost and 127.0.0.1 reachability: OK"

$negative = Invoke-OaiRequest "POST" "$apiBase/chat" @{ message = "" } $workspaceHeaders
if ($negative.StatusCode -ne 422 -or $negative.Content -match "Traceback|Exception") { throw "Safe negative chat check failed." }
Write-Host "Safe chat error envelope: OK"

$deploymentEnv = Get-Content ".env" -Raw
$localEnabled = $deploymentEnv -match "(?m)^OAI_LOCAL_AI_ENABLED\s*=\s*true\s*$"
$openAiConfigured = $deploymentEnv -match "(?m)^OPENAI_API_KEY\s*=\s*[^\s#]+\s*$"

if ($localEnabled) {
    $commonModel = Get-OaiDeploymentValue $deploymentEnv "OAI_LOCAL_AI_MODEL" "qwen3.5:9b"
    $generalChatModel = Get-OaiDeploymentValue $deploymentEnv "OAI_LOCAL_AI_GENERAL_CHAT_MODEL" $commonModel
    $engineeringModel = Get-OaiDeploymentValue $deploymentEnv "OAI_LOCAL_AI_SOFTWARE_ENGINEERING_MODEL" $commonModel
    $runtimeUrl = (Get-OaiDeploymentValue $deploymentEnv "OAI_LOCAL_AI_BASE_URL" "http://127.0.0.1:11434").TrimEnd("/")
    $tags = Invoke-OaiRequest "GET" "$runtimeUrl/api/tags"
    if ($tags.StatusCode -ne 200) { throw "Local AI is enabled but Ollama is unavailable (HTTP $($tags.StatusCode))." }
    $installedModels = @((($tags.Content | ConvertFrom-Json).models) | ForEach-Object { $_.name })
    $profileModels = @(
        @{ Profile = "local_ai.general_chat.v1"; Model = $generalChatModel },
        @{ Profile = "local_ai.software_engineering.v1"; Model = $engineeringModel }
    )
    foreach ($profileModel in $profileModels) {
        if ($installedModels -cnotcontains $profileModel.Model) {
            throw "Local AI profile '$($profileModel.Profile)' requires exact installed model '$($profileModel.Model)'. No model/profile/Cloud fallback is attempted."
        }
        Write-Host "Local AI profile $($profileModel.Profile): exact model '$($profileModel.Model)' available"
    }
    # Existing normal Chat smoke exercises General Chat; Engineering is availability-only here.
    $chat = Invoke-OaiRequest "POST" "$apiBase/chat" @{ message = "Use local AI for this command." } $workspaceHeaders
    if ($chat.StatusCode -ne 200) { throw "Explicit Local AI chat failed with HTTP $($chat.StatusCode): $($chat.Content)" }
    $chatBody = $chat.Content | ConvertFrom-Json
    if (-not $chatBody.success -or -not $chatBody.data.conversation_id) { throw "Local AI chat did not return a successful conversation." }
    $conversation = Invoke-OaiRequest "GET" "$apiBase/conversations/$($chatBody.data.conversation_id)" $null $workspaceHeaders
    if ($conversation.StatusCode -ne 200) { throw "Conversation persistence check failed." }
    Write-Host "Local AI General Chat ($generalChatModel) O-AI E2E and conversation persistence: OK"
    Write-Host "Software Engineering ($engineeringModel): availability checked; inference requires guided acceptance"
} elseif ($openAiConfigured) {
    $chat = Invoke-OaiRequest "POST" "$apiBase/chat" @{ message = "MVP smoke test." } $workspaceHeaders
    if ($chat.StatusCode -ne 200) { throw "Configured ChatGPT smoke failed with HTTP $($chat.StatusCode)." }
    $chatBody = $chat.Content | ConvertFrom-Json
    if (-not $chatBody.data.conversation_id) { throw "ChatGPT smoke did not return a conversation ID." }
    $conversation = Invoke-OaiRequest "GET" "$apiBase/conversations/$($chatBody.data.conversation_id)" $null $workspaceHeaders
    if ($conversation.StatusCode -ne 200) { throw "Conversation persistence check failed." }
    Write-Host "ChatGPT O-AI E2E and conversation persistence: OK"
} else {
    Write-Host "Local AI E2E: SKIPPED (OAI_LOCAL_AI_ENABLED is false)"
    Write-Host "ChatGPT smoke: SKIPPED (OPENAI_API_KEY is not configured)"
    Write-Host "Conversation persistence smoke: SKIPPED (no AI provider is configured)"
}
