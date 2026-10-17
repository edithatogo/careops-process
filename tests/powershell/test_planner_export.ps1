# Execute real projection, serialization and publication against synthetic Graph pages.
$ErrorActionPreference = 'Stop'
$exporter = Join-Path $PSScriptRoot '../../scripts/export-planner-corpus.ps1'
$root = Join-Path ([IO.Path]::GetTempPath()) ('careops-planner-test-' + [guid]::NewGuid())
$oldKey = $env:CAREOPS_PSEUDONYM_KEY
$env:CAREOPS_PSEUDONYM_KEY = [Convert]::ToBase64String([byte[]](1..32))
[IO.Directory]::CreateDirectory($root) | Out-Null
$global:pages = @(); $global:index = 0; $global:tokenFailure = $false; $global:sleeps = 0
$global:requests = [Collections.Generic.List[string]]::new()
function global:az { if ($global:tokenFailure) { throw 'RAW-TOKEN' }; 'RAW-BEARER' }
function global:Invoke-RestMethod {
    param($Uri, $Headers, $Method, $TimeoutSec, $MaximumRedirection)
    $global:requests.Add($Uri)
    if ($global:index -ge $global:pages.Count) { throw 'RAW-ERROR' }
    $page = $global:pages[$global:index++]
    if ($page -is [Exception]) { throw $page }
    $page
}
function global:Start-Sleep { param($Seconds); $global:sleeps++ }
function Assert($Condition, $Message) { if (-not $Condition) { throw $Message } }
function Reset($Pages) { $global:pages = @($Pages); $global:index = 0; $global:sleeps = 0; $global:requests.Clear() }
function Export($Path) { & $exporter -OutputPath $Path | Out-Null }
function Fails($Path) {
    $failed = $false
    try { Export $Path } catch {
        $failed = $true
        Assert ($_.ToString() -notmatch 'RAW-|synthetic@example') 'Protected error leaked'
    }
    Assert $failed 'Expected failure'
}
$task = @{
    id = 'RAW-ID'; planId = 'RAW-ID'; bucketId = 'RAW-ID'
    createdDateTime = '2026-01-01T10:00:00+10:00'; completedDateTime = '2026-01-02T00:00:00Z'
    title = 'RAW-TITLE'; description = 'RAW-DESCRIPTION'; assignments = @{ 'RAW-USER' = @{} }
}
try {
    $path = Join-Path $root 'planner.json'
    Reset @(@{ value = @() }); Export $path
    $empty = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    Assert ($empty.facts -is [array] -and $empty.facts.Count -eq 0) 'Empty facts must serialize as []'
    $bad = $task.Clone(); $bad.createdDateTime = 'invalid'
    Reset @(@{ value = @($task, $task, $bad) }); Export $path
    $text = Get-Content -LiteralPath $path -Raw; $result = $text | ConvertFrom-Json
    Assert ($text -notmatch 'RAW-|synthetic@example') 'Protected output leaked'
    Assert ($result.candidate_count -eq 3 -and $result.accepted_candidate_count -eq 1 -and $result.duplicate_count -eq 1 -and $result.rejected_count -eq 1 -and $result.acquired_count -eq 2) 'Candidate/event counts do not reconcile'
    $objects = $result.facts[0].object_ids
    Assert (($objects[0] -split ':')[1] -ne ($objects[1] -split ':')[1]) 'Pseudonym domains collide'
    Assert ($text -match '2026-01-01T00:00:00.0000000Z') 'Timestamp not normalized to UTC'
    $hash = $result.content_hash
    Reset @(@{ value = @($task) }); Export $path
    Assert ((Get-Content $path -Raw | ConvertFrom-Json).content_hash -eq $hash) 'Replay hash differs'
    $other = $task.Clone(); $other.id = 'RAW-OTHER'
    Reset @(@{ value = @($other, $task) }); Export $path
    $orderedHash = (Get-Content $path -Raw | ConvertFrom-Json).content_hash
    Reset @(@{ value = @($task, $other) }); Export $path
    Assert ((Get-Content $path -Raw | ConvertFrom-Json).content_hash -eq $orderedHash) 'Source ordering changed fact hash'
    Reset @(@{ value = @($task) }); Export $path
    $before = Get-Content $path -Raw
    $busy = [IO.File]::Open($path, 'Open', 'ReadWrite', 'None')
    try {
        Reset @(@{ value = @($other) })
        if ($IsWindows) {
            Fails $path
        } else {
            # Unix rename replaces the directory entry while the open reader
            # retains the original inode. Verify both sides of that atomic commit.
            Export $path
            $reader = [IO.StreamReader]::new($busy, [Text.Encoding]::UTF8, $true, 1024, $true)
            try { Assert ($reader.ReadToEnd() -ceq $before) 'Open reader observed a torn snapshot' }
            finally { $reader.Dispose() }
            Assert ((Get-Content $path -Raw) -cne $before) 'Unix replacement did not publish'
        }
    } finally { $busy.Dispose() }
    if ($IsWindows) { Assert ((Get-Content $path -Raw) -ceq $before) 'Interrupted publication damaged old snapshot' }
    Reset @(@{ value = @($task) }); Export $path
    Assert (@(Get-ChildItem $root -Filter '*.tmp').Count -eq 0) 'Failed staging left temporary output'
    $transient = [Exception]::new('RAW-429')
    $transient | Add-Member -NotePropertyName Response -NotePropertyValue ([pscustomobject]@{ StatusCode = 429 })
    Reset @($transient, @{ value = @($task) }); Export $path
    Assert ($global:requests.Count -eq 2 -and $global:sleeps -eq 1) 'Transient acquisition did not retry once'
    Assert ((Get-Content $path -Raw | ConvertFrom-Json).retry_count -eq 1) 'Retry count unmeasured'
    Reset @($transient, $transient, $transient); Fails $path
    Assert ($global:requests.Count -eq 3) 'Retry budget not bounded'
    $next = 'https://graph.microsoft.com/v1.0/me/planner/tasks?$skip=1'
    Reset @(@{ value = @($task); '@odata.nextLink' = $next }, @{ value = @($task) }); Export $path
    Assert ($global:requests.Count -eq 2) 'Pagination not followed'
    foreach ($uri in @('https://evil.example/tasks', 'http://graph.microsoft.com/v1.0/me/planner/tasks', 'https://graph.microsoft.com/v1.0/users/another/planner/tasks', 'https://graph.microsoft.com:444/v1.0/me/planner/tasks')) {
        Reset @(@{ value = @($task); '@odata.nextLink' = $uri }); Fails $path
        Assert ($global:requests.Count -eq 1) 'Bearer sent to unsafe destination'
    }
    Reset @(@{ value = @($task); '@odata.nextLink' = $next }, @{ value = @($task); '@odata.nextLink' = $next }); Fails $path
    Reset @(@{ value = @($task); '@odata.nextLink' = $next }, [Exception]::new('RAW-API-FAILURE')); Fails $path
    $conflict = $task.Clone(); $conflict.completedDateTime = '2026-01-03T00:00:00Z'
    Reset @(@{ value = @($task, $conflict) }); Fails $path
    Reset @(@{ wrong = @() }); Fails $path
    $global:tokenFailure = $true; Reset @(); Fails $path; $global:tokenFailure = $false
    $env:CAREOPS_PSEUDONYM_KEY = ''; Reset @(); Fails $path
    Assert ((Get-Content $path -Raw | ConvertFrom-Json).acquired_count -eq 2) 'Failure damaged previous output'
    Write-Output 'PASS: Planner privacy, empty results, domain separation, reconciliation, replay and fail-closed pagination'
} finally {
    $env:CAREOPS_PSEUDONYM_KEY = $oldKey
    if ([IO.Path]::GetFullPath($root).StartsWith([IO.Path]::GetFullPath([IO.Path]::GetTempPath()))) { Remove-Item -LiteralPath $root -Recurse -Force }
    Remove-Item Function:\az, Function:\Invoke-RestMethod, Function:\Start-Sleep -ErrorAction SilentlyContinue
}
