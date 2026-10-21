[CmdletBinding()]
param([Parameter(Mandatory)] [string]$OutputPath)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Get-Pseudonym($Domain, $Value) {
    if ($Value -isnot [string] -or [string]::IsNullOrWhiteSpace($Value)) { throw 'Invalid source identity.' }
    $hmac = [Security.Cryptography.HMACSHA256]::new([Text.Encoding]::UTF8.GetBytes($env:CAREOPS_PSEUDONYM_KEY))
    try { [Convert]::ToHexString($hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes("$Domain`0$Value"))).ToLowerInvariant() }
    finally { $hmac.Dispose() }
}
function Get-Timestamp($Value) {
    if ($Value -isnot [string] -or $Value -notmatch '(Z|[+-]\d{2}:\d{2})$') { throw 'Invalid timestamp.' }
    try { ([datetimeoffset]$Value).UtcDateTime.ToString('o') } catch { throw 'Invalid timestamp.' }
}
function Get-Field($Record, $Name) {
    if ($Record -is [Collections.IDictionary]) { return ,$Record[$Name] }
    if ($null -eq $Record) { return $null }
    $property = $Record.PSObject.Properties[$Name]
    if ($property) { return ,$property.Value }
    return $null
}
try {
    if ([string]::IsNullOrWhiteSpace($env:CAREOPS_PSEUDONYM_KEY) -or [Text.Encoding]::UTF8.GetByteCount($env:CAREOPS_PSEUDONYM_KEY) -lt 32) { throw 'Pseudonym key of at least 32 bytes required.' }
    try { $token = az account get-access-token --resource-type ms-graph --query accessToken -o tsv 2>$null }
    catch { throw 'Token acquisition failed.' }
    if ([string]::IsNullOrWhiteSpace([string]$token)) { throw 'Token acquisition failed.' }
    $headers = @{ Authorization = "Bearer $token" }
    $uri = 'https://graph.microsoft.com/v1.0/me/planner/tasks?$top=100&$select=id,planId,bucketId,createdDateTime,completedDateTime'
    $visited = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $tasks = @{}; $facts = @{}; $duplicates = 0; $rejected = 0; $accepted = 0; $candidates = 0; $pages = 0; $retries = 0
    while ($uri) {
        $target = $null
        if (-not [uri]::TryCreate($uri, [UriKind]::Absolute, [ref]$target) -or
            $target.Scheme -ne 'https' -or $target.Host -ne 'graph.microsoft.com' -or $target.Port -ne 443 -or
            $target.UserInfo -or $target.Fragment -or $target.AbsolutePath -cne '/v1.0/me/planner/tasks' -or
            -not $visited.Add($target.AbsoluteUri) -or $pages -ge 100000) { throw 'Invalid or repeated Graph continuation.' }
        $response = $null
        for ($attempt = 0; $attempt -le 2; $attempt++) {
            try {
                $response = Invoke-RestMethod -Method Get -Uri $uri -Headers $headers -TimeoutSec 60 -MaximumRedirection 0
                break
            } catch {
                $status = 0
                if ($_.Exception.PSObject.Properties['Response'] -and $_.Exception.Response) { $status = [int]$_.Exception.Response.StatusCode }
                if ($status -notin @(429, 500, 502, 503, 504) -or $attempt -eq 2) { throw 'Graph acquisition failed.' }
                $retries++; Start-Sleep -Seconds ([math]::Pow(2, $attempt))
            }
        }
        $values = Get-Field $response 'value'
        if ($null -eq $values -or $values -isnot [array]) { throw 'Invalid Graph page.' }
        $pages++
        foreach ($task in $values) {
            $candidates++
            try {
                $taskId = Get-Pseudonym 'planner:task' (Get-Field $task 'id')
                $planId = Get-Pseudonym 'planner:plan' (Get-Field $task 'planId')
                $objects = @("task:$taskId", "plan:$planId")
                $bucket = Get-Field $task 'bucketId'
                if ($bucket) { $objects += 'bucket:' + (Get-Pseudonym 'planner:bucket' $bucket) }
                $events = @()
                foreach ($kind in @('created', 'completed')) {
                    $value = Get-Field $task ($kind + 'DateTime')
                    if ($null -ne $value) {
                        $events += [ordered]@{ id = "$taskId`:$kind"; activity = "planner_task_$kind"; timestamp_utc = (Get-Timestamp $value); source_system = 'microsoft_graph_planner'; object_ids = $objects }
                    }
                }
                if (-not $events.Count) { throw 'No observable lifecycle event.' }
                $canonical = ConvertTo-Json -InputObject @($events) -Compress -Depth 8
            } catch { $rejected++; continue }
            if ($tasks.ContainsKey($taskId)) {
                if ($tasks[$taskId] -cne $canonical) { throw 'Conflicting task replay.' }
                $duplicates++; continue
            }
            $tasks[$taskId] = $canonical; $accepted++
            foreach ($event in $events) { $facts[$event.id] = $event }
        }
        $uri = Get-Field $response '@odata.nextLink'
        if ($null -ne $uri -and ($uri -isnot [string] -or -not $uri)) { throw 'Invalid Graph continuation.' }
    }
    $orderedFacts = @($facts.Keys | Sort-Object -CaseSensitive | ForEach-Object { $facts[$_] })
    $factsJson = ConvertTo-Json -InputObject $orderedFacts -Depth 8 -Compress
    $hash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($factsJson))).ToLowerInvariant()
    $manifest = [ordered]@{
        contract_version = '1.0.0'; evidence_class = 'live_corpus'; generated_at_utc = [datetime]::UtcNow.ToString('o')
        source = 'microsoft_graph_planner'; container = 'assigned_tasks'; pages_read = $pages
        candidate_count = $candidates; accepted_candidate_count = $accepted; acquired_count = $facts.Count
        duplicate_count = $duplicates; rejected_count = $rejected; failure_count = 0; retry_count = $retries
        exhausted = $true; content_hash = $hash; checkpoint_state = 'assigned_snapshot_exhausted'
        watermark_utc = $null; excluded_content_fields = @('narrative', 'identity', 'assignment_membership')
        tenant_wide_coverage = $null; facts = $orderedFacts
    }
    $full = [IO.Path]::GetFullPath($OutputPath)
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($full)) | Out-Null
    $temporary = "$full.$([guid]::NewGuid()).tmp"
    # Atomic replacement on the same filesystem preserves the old snapshot until commit.
    try {
        [IO.File]::WriteAllText($temporary, (ConvertTo-Json -InputObject $manifest -Depth 8), [Text.UTF8Encoding]::new($false))
        [IO.File]::Move($temporary, $full, $true)
    } finally { if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) } }
    Write-Output "Acquired $($facts.Count) minimised Planner facts."
} catch { throw 'Planner export failed; previous output preserved.' }
