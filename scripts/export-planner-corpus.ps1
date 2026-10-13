[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if ([string]::IsNullOrWhiteSpace($env:CAREOPS_PSEUDONYM_KEY)) {
    throw 'CAREOPS_PSEUDONYM_KEY must be set for stable pseudonymisation.'
}

function Get-Pseudonym {
    param([Parameter(Mandatory = $true)][string]$Value)
    $hmac = [System.Security.Cryptography.HMACSHA256]::new(
        [System.Text.Encoding]::UTF8.GetBytes($env:CAREOPS_PSEUDONYM_KEY)
    )
    try {
        $bytes = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($Value))
        return [Convert]::ToHexString($bytes).ToLowerInvariant()
    }
    finally {
        $hmac.Dispose()
    }
}

$token = az account get-access-token --resource-type ms-graph --query accessToken -o tsv
if ([string]::IsNullOrWhiteSpace($token)) {
    throw 'Azure CLI did not return a Microsoft Graph token.'
}
$headers = @{ Authorization = "Bearer $token" }
$uri = 'https://graph.microsoft.com/v1.0/me/planner/tasks?$top=100&$select=id,planId,bucketId,createdDateTime,completedDateTime,percentComplete'
$tasks = [System.Collections.Generic.List[object]]::new()
$pagesRead = 0

while ($null -ne $uri) {
    $response = Invoke-RestMethod -Method Get -Uri $uri -Headers $headers
    $pagesRead += 1
    foreach ($task in @($response.value)) {
        $tasks.Add($task)
    }
    $nextProperty = $response.PSObject.Properties['@odata.nextLink']
    $uri = if ($null -ne $nextProperty) { [string]$nextProperty.Value } else { $null }
}

$facts = [System.Collections.Generic.List[object]]::new()
foreach ($task in $tasks) {
    $taskId = Get-Pseudonym -Value ([string]$task.id)
    $planId = Get-Pseudonym -Value ([string]$task.planId)
    $objectIds = @("task:$taskId", "plan:$planId")
    if ($null -ne $task.bucketId -and -not [string]::IsNullOrWhiteSpace([string]$task.bucketId)) {
        $bucketId = Get-Pseudonym -Value ([string]$task.bucketId)
        $objectIds += "bucket:$bucketId"
    }
    if ($null -ne $task.createdDateTime) {
        $facts.Add([ordered]@{
            id = "$taskId`:created"
            activity = 'planner_task_created'
            timestamp_utc = ([DateTimeOffset]$task.createdDateTime).ToUniversalTime().ToString('o')
            source_system = 'microsoft_graph_planner'
            object_ids = $objectIds
        })
    }
    if ($null -ne $task.completedDateTime) {
        $facts.Add([ordered]@{
            id = "$taskId`:completed"
            activity = 'planner_task_completed'
            timestamp_utc = ([DateTimeOffset]$task.completedDateTime).ToUniversalTime().ToString('o')
            source_system = 'microsoft_graph_planner'
            object_ids = $objectIds
        })
    }
}

$factsJson = $facts | ConvertTo-Json -Depth 8 -Compress
$sha256 = [System.Security.Cryptography.SHA256]::Create()
try {
    $contentHash = [Convert]::ToHexString(
        $sha256.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($factsJson))
    ).ToLowerInvariant()
}
finally {
    $sha256.Dispose()
}

$result = [ordered]@{
    contract_version = '1.0.0'
    evidence_class = 'live_corpus'
    generated_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
    source = 'microsoft_graph_planner'
    container = 'assigned_tasks'
    pages_read = $pagesRead
    candidate_count = $tasks.Count
    acquired_count = $facts.Count
    duplicate_count = 0
    rejected_count = 0
    exhausted = $true
    content_hash = $contentHash
    checkpoint_state = 'full_snapshot_exhausted'
    watermark_utc = $null
    excluded_content_fields = @('narrative', 'identity', 'assignment_membership')
    tenant_wide_coverage = $null
    facts = $facts
}

$parent = Split-Path -Parent $OutputPath
if (-not [string]::IsNullOrWhiteSpace($parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding utf8NoBOM
Write-Output ([ordered]@{
    source = $result.source
    pages_read = $result.pages_read
    candidate_count = $result.candidate_count
    acquired_count = $result.acquired_count
    exhausted = $result.exhausted
    content_hash = $result.content_hash
    output_path = $OutputPath
} | ConvertTo-Json -Compress)
