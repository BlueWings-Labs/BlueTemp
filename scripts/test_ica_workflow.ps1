# Test ICA workflow API (PowerShell)
#   $env:ICA_API_KEY = "your_x_api_key"
#   $env:ICA_FLOW_ID = "953b7d43-0475-4689-845a-3678a6e79aa3"
#   .\scripts\test_ica_workflow.ps1

$ErrorActionPreference = "Stop"

$flowId = if ($env:ICA_FLOW_ID) { $env:ICA_FLOW_ID } else { "953b7d43-0475-4689-845a-3678a6e79aa3" }
$apiKey = $env:ICA_API_KEY
if (-not $apiKey) {
    Write-Error "Set ICA_API_KEY (from Workflow -> Share -> API Access)"
}

$url = "https://langflow.servicesessentials.ibm.com/api/v1/run/$flowId" + "?stream=false"
$sessionId = if ($env:ICA_SESSION_ID) { $env:ICA_SESSION_ID } else { [guid]::NewGuid().ToString() }
$message = if ($env:ICA_WORKFLOW_MESSAGE) {
    $env:ICA_WORKFLOW_MESSAGE
} else {
    "Use get-repo-info for owner peteroin repo feedaily. Reply with name, language, stars only."
}

$body = @{
    output_type = "chat"
    input_type  = "chat"
    input_value = $message
    session_id  = $sessionId
} | ConvertTo-Json -Compress

Write-Host "POST $url"
Write-Host "session_id=$sessionId"
Write-Host ""

curl.exe --request POST `
    --url $url `
    --header "Content-Type: application/json" `
    --header "x-api-key: $apiKey" `
    --data $body
