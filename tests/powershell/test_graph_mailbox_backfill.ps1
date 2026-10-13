# Offline behavioural regression tests. Network and token acquisition are mocked;
# the exporter, JSON serialization and filesystem publication execute normally.
$ErrorActionPreference = 'Stop'
$exporter = Join-Path $PSScriptRoot '../../scripts/Invoke-GraphMailboxBackfill.ps1'
$root = Join-Path ([IO.Path]::GetTempPath()) ('careops-mail-test-' + [guid]::NewGuid())
$oldSecret = $env:CAREOPS_MAIL_PSEUDONYM_KEY
$env:CAREOPS_MAIL_PSEUDONYM_KEY = [Convert]::ToBase64String([byte[]](1..32))
New-Item -ItemType Directory -Path $root | Out-Null
$global:requests = [Collections.Generic.List[string]]::new()
$global:pages = @()
$global:pageIndex = 0
$global:tokenFailure = $false
$global:publishFailure = $false
$global:rollbackFailure = $false
$global:sleeps = [Collections.Generic.List[int]]::new()
function global:Start-Sleep { param($Seconds); $global:sleeps.Add($Seconds) }
Add-Type -TypeDefinition @'
public class MailTestHttpException : System.Exception {
    public System.Net.Http.HttpResponseMessage Response { get; }
    public MailTestHttpException(int code) : base("RAW-HTTP-ERROR") {
        Response = new System.Net.Http.HttpResponseMessage((System.Net.HttpStatusCode)code);
    }
}
'@
function global:Move-Item {
    param($LiteralPath, $Destination)
    if ($global:publishFailure -and [IO.Path]::GetFileName($LiteralPath).StartsWith('.careops-mail-stage-')) {
        throw 'RAW-PUBLISH-ERROR'
    }
    if ($global:rollbackFailure -and [IO.Path]::GetFileName($LiteralPath).StartsWith('.careops-mail-backup-')) {
        throw 'RAW-ROLLBACK-ERROR'
    }
    Microsoft.PowerShell.Management\Move-Item -LiteralPath $LiteralPath -Destination $Destination
}
function global:az { if ($global:tokenFailure) { throw 'RAW-TOKEN-ERROR' }; 'test-token' }
function global:Invoke-RestMethod {
    param($Uri, $Headers, $Method, $TimeoutSec, $MaximumRedirection)
    $global:requests.Add([string]$Uri)
    if ($global:pageIndex -ge $global:pages.Count) { throw 'RAW-API-ERROR' }
    $page = $global:pages[$global:pageIndex++]
    if ($page -is [Exception]) { throw $page }
    $page
}
function Assert($Condition, $Message) { if (-not $Condition) { throw $Message } }
function Reset-Pages($Values) {
    $global:pages = @($Values); $global:pageIndex = 0; $global:requests.Clear()
}
function Export($Directory, $Extra = @{}) {
    & $exporter -Mailbox 'synthetic@example.invalid' -OutputDirectory $Directory @Extra | Out-Null
}
function Expect-Failure($Directory, $Extra = @{}) {
    $failed = $false
    try { Export $Directory $Extra } catch {
        $failed = $true
        Assert ($_.ToString() -notmatch 'RAW-|test-token|synthetic@example') 'Protected diagnostics leaked'
    }
    Assert $failed 'Expected a fail-closed exporter error'
}
$message = @{
    id = 'RAW-MESSAGE'; conversationId = 'RAW-CONVERSATION'; parentFolderId = 'RAW-FOLDER'
    receivedDateTime = '2026-01-01T00:00:00Z'; hasAttachments = $false; importance = 'normal'
    subject = 'RAW-SUBJECT'; from = @{ emailAddress = @{ address = 'RAW-SENDER' } }
    toRecipients = @(@{ emailAddress = @{ address = 'RAW-RECIPIENT' } })
    internetMessageId = 'RAW-INTERNET-ID'
}
try {
    $output = Join-Path $root 'output'
    Reset-Pages @(@{ value = @($message); '@odata.nextLink' = 'https://graph.microsoft.com/v1.0/users/synthetic%40example.invalid/messages?$skip=1' }, @{ value = @($message) })
    Export $output
    $projection = Get-Content (Join-Path $output 'mail-events.jsonl') -Raw
    $manifestText = Get-Content (Join-Path $output 'manifest.json') -Raw
    Assert (($projection + $manifestText) -notmatch 'RAW-|synthetic@example') 'Raw protected data persisted'
    $fact = $projection | ConvertFrom-Json
    Assert ($fact.id -match '^mail_[a-f0-9]{64}$') 'Message identity must be keyed and pseudonymous'
    Assert ($fact.object_ids.Count -eq 1) 'Conversation object linkage missing'
    $manifest = $manifestText | ConvertFrom-Json
    Assert ($manifest.candidate_count -eq 2 -and $manifest.acquired_count -eq 1 -and $manifest.duplicate_count -eq 1) 'Counts must reconcile duplicates'
    Assert ($manifest.status -eq 'acquired' -and -not $manifest.full_mailbox_verified) 'Message-list pagination cannot certify full mailbox scope'
    Assert ($global:requests.Count -eq 2) 'Continuation not followed'
    Assert ($global:requests[0] -notmatch 'subject|Recipients|internetMessageId|sentDateTime|from') 'Request includes prohibited or unused fields'
    Reset-Pages @(@{ value = @($message, $message) })
    $folderOutput = Join-Path $root 'folder'; Export $folderOutput @{ FolderId = 'RAW-FOLDER' }
    Assert ($global:requests[0].Contains('/mailFolders/RAW-FOLDER/messages?')) 'Folder-scoped acquisition broadened to the mailbox'
    $folderManifest = Get-Content (Join-Path $folderOutput 'manifest.json') -Raw | ConvertFrom-Json
    Assert ($folderManifest.folder_ref -eq 'folder_eda190b23749fa934f58cefc3d745902b410c484c42e996f06ce635c89681207') 'Pseudonym encoding differs from independent Python HMAC fixture'
    Assert ($folderManifest.page_ledger.Count -eq 1) 'Measured folder page ledger missing'
    Assert ($folderManifest.page_ledger[0].candidate_count -eq 2 -and $folderManifest.page_ledger[0].duplicate_count -eq 1) 'Folder page counts not measured'
    Assert ($folderManifest.page_ledger[0].fact_ids.Count -eq 1 -and $folderManifest.page_ledger[0].next_link_exhausted) 'Folder page membership/exhaustion missing'
    Reset-Pages @(@{ value = @($message) }); Expect-Failure $folderOutput @{ FolderId = 'ANOTHER-FOLDER' }
    Assert ($global:requests.Count -eq 0) 'Replay changed folder scope'
    Reset-Pages @(@{ value = @($message) }); Expect-Failure (Join-Path $root 'wrong-folder') @{ FolderId = 'ANOTHER-FOLDER' }
    Reset-Pages @(@{ value = @($message) })
    Export $output
    Assert ((Get-Content (Join-Path $output 'mail-events.jsonl') -Raw) -eq $projection) 'Replay appended or changed identities'
    Assert ((Get-Content (Join-Path $output 'manifest.json') -Raw | ConvertFrom-Json).new_identity_count -eq 0) 'Replay must report zero new identities'
    Reset-Pages @(@{ value = @($message) })
    Export (Join-Path $root 'window') @{ Since = [datetimeoffset]'2026-01-01T10:00:00+10:00'; Until = [datetimeoffset]'2026-01-02T10:00:00+10:00' }
    $query = [uri]::UnescapeDataString($global:requests[0])
    Assert ($query.Contains('&$filter=receivedDateTime ge 2026-01-01T00:00:00.0000000Z and receivedDateTime lt 2026-01-02T00:00:00.0000000Z')) 'UTC window filter not encoded correctly'
    Assert ($query -notmatch '`') 'Literal backtick in query'
    foreach ($extra in @(@{ PageSize = 0 }, @{ PageSize = 1001 }, @{ Since = [datetimeoffset]'2026-02-01Z'; Until = [datetimeoffset]'2026-01-01Z' })) {
        Reset-Pages @(); Expect-Failure (Join-Path $root 'invalid') $extra
        Assert ($global:requests.Count -eq 0) 'Invalid arguments contacted API'
    }
    foreach ($extra in @(@{ Since = '2026-01-01' }, @{ Since = 'RAW-BAD-DATE' }, @{ PageSize = 'RAW-BAD-PAGE-SIZE' }, @{ FolderId = ' ' })) {
        Reset-Pages @(); Expect-Failure (Join-Path $root 'invalid-input') $extra
        Assert ($global:requests.Count -eq 0) 'Invalid input reached acquisition'
    }
    Reset-Pages @(@{ value = @() })
    $empty = Join-Path $root 'empty'; Export $empty
    Assert ((Get-Item (Join-Path $empty 'mail-events.jsonl')).Length -eq 0) 'Empty projection must be a zero-byte JSONL file'
    foreach ($next in @('https://evil.example/v1.0/messages', 'http://graph.microsoft.com/v1.0/messages', 'https://graph.microsoft.com/v1.0/users/another/messages', 'https://graph.microsoft.com:444/v1.0/users/synthetic%40example.invalid/messages')) {
        Reset-Pages @(@{ value = @($message); '@odata.nextLink' = $next })
        Expect-Failure $output
        Assert ((Get-Content (Join-Path $output 'mail-events.jsonl') -Raw) -eq $projection) 'Failure damaged previous projection'
        Assert ($global:requests.Count -eq 1) 'Unsafe continuation received bearer token'
    }
    $loop = 'https://graph.microsoft.com/v1.0/users/synthetic%40example.invalid/messages?$skip=1'
    Reset-Pages @(@{ value = @($message); '@odata.nextLink' = $loop }, @{ value = @($message); '@odata.nextLink' = $loop })
    Expect-Failure $output
    Assert ($global:requests.Count -eq 2) 'Repeated continuation was not stopped'
    Reset-Pages @(@{ value = @($message); '@odata.nextLink' = $loop }, [Exception]::new('RAW-API-ERROR'))
    Expect-Failure $output
    Assert ((Get-Content (Join-Path $output 'mail-events.jsonl') -Raw) -eq $projection) 'Interrupted acquisition damaged valid output'
    Reset-Pages @(@{ unexpected = 'RAW-INVALID-PAGE' }); Expect-Failure $output
    Reset-Pages @(@{ value = @{ unexpected = 'RAW-INVALID-PAGE' } }); Expect-Failure $output
    $conflict = $message.Clone(); $conflict.receivedDateTime = '2026-01-02T00:00:00Z'
    Reset-Pages @(@{ value = @($message, $conflict) }); Expect-Failure $output
    $global:tokenFailure = $true; Reset-Pages @(); Expect-Failure $output; $global:tokenFailure = $false
    Reset-Pages @(@{ value = @($message) }); $global:publishFailure = $true
    Expect-Failure $output; $global:publishFailure = $false
    Assert ((Get-Content (Join-Path $output 'mail-events.jsonl') -Raw) -eq $projection) 'Publication failure lost previous valid output'
    Assert (@(Get-ChildItem $root -Directory -Force | Where-Object Name -like '.careops-mail-*').Count -eq 0) 'Failed publication left staging artifacts'
    $invalid = $message.Clone(); $invalid.id = ''
    Reset-Pages @(@{ value = @($invalid, $message) })
    $rejections = Join-Path $root 'rejections'; Export $rejections
    $manifest = Get-Content (Join-Path $rejections 'manifest.json') -Raw | ConvertFrom-Json
    Assert ($manifest.candidate_count -eq 2 -and $manifest.rejected_count -eq 1 -and $manifest.acquired_count -eq 1) 'Rejected candidates not measured'
    Reset-Pages @(@{ value = @() }); Export $rejections
    Assert (-not (Get-Content (Join-Path $rejections 'manifest.json') -Raw | ConvertFrom-Json).idempotency_replay_verified) 'Removed identities falsely certified unchanged replay'
    Reset-Pages @(@{ value = @($message) })
    $wrongKey = [Convert]::ToBase64String([byte[]](2..33))
    $env:CAREOPS_MAIL_PSEUDONYM_KEY = $wrongKey
    Expect-Failure $output
    Assert ($global:requests.Count -eq 0) 'Scope/key mismatch contacted API'
    $env:CAREOPS_MAIL_PSEUDONYM_KEY = [Convert]::ToBase64String([byte[]](1..32))
    Reset-Pages @(@{ value = @($message) })
    Expect-Failure $output @{ Since = [datetimeoffset]'2026-01-02T00:00:00Z' }
    Assert ($global:requests.Count -eq 0) 'Changed replay scope contacted API'
    Reset-Pages @(@{ value = @($message) })
    Expect-Failure (Join-Path $root 'outside-window') @{ Since = [datetimeoffset]'2026-01-02T00:00:00Z' }
    $global:sleeps.Clear()
    Reset-Pages @([MailTestHttpException]::new(429), @{ value = @($message) })
    $retryOutput = Join-Path $root 'retry'; Export $retryOutput
    Assert ($global:requests.Count -eq 2 -and $global:sleeps.Count -eq 1) 'Transient HTTP failure not retried'
    Assert ((Get-Content (Join-Path $retryOutput 'manifest.json') -Raw | ConvertFrom-Json).retry_count -eq 1) 'Retries not measured'
    Reset-Pages @([TimeoutException]::new('RAW-TIMEOUT'), @{ value = @($message) })
    Export (Join-Path $root 'timeout')
    Assert ($global:requests.Count -eq 2) 'Transport timeout not retried'
    $throttle = [MailTestHttpException]::new(429)
    $throttle.Response.Headers.RetryAfter = [Net.Http.Headers.RetryConditionHeaderValue]::new([timespan]::FromSeconds(7))
    $global:sleeps.Clear(); Reset-Pages @($throttle, @{ value = @($message) })
    Export (Join-Path $root 'retry-after')
    Assert (($global:sleeps -join ',') -eq '7') 'Retry-After was ignored'
    $global:sleeps.Clear()
    Reset-Pages @([MailTestHttpException]::new(503), [MailTestHttpException]::new(503), [MailTestHttpException]::new(503), [MailTestHttpException]::new(503))
    Expect-Failure $output
    Assert ($global:requests.Count -eq 4 -and ($global:sleeps -join ',') -eq '1,2,4') 'Retries must have bounded exponential backoff'
    Reset-Pages @([MailTestHttpException]::new(403)); Expect-Failure $output
    Assert ($global:requests.Count -eq 1) 'Access denial must not be retried'
    $lockPath = Join-Path $root '.output.careops-mail.lock'
    $heldLock = [IO.File]::Open($lockPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    try {
        Reset-Pages @(@{ value = @($message) }); Expect-Failure $output
        Assert ($global:requests.Count -eq 0) 'Concurrent writer was not blocked before acquisition'
    } finally { $heldLock.Dispose(); [IO.File]::Delete($lockPath) }
    Reset-Pages @(@{ value = @($message) })
    $rollbackOutput = Join-Path $root 'rollback'; Export $rollbackOutput
    Reset-Pages @(@{ value = @($message) })
    $global:publishFailure = $true; $global:rollbackFailure = $true
    try { Expect-Failure $rollbackOutput } finally { $global:publishFailure = $false; $global:rollbackFailure = $false }
    $savedBackup = @(Get-ChildItem $root -Directory -Force | Where-Object Name -like '.careops-mail-backup-*')
    Assert ($savedBackup.Count -eq 1 -and (Get-Content (Join-Path $savedBackup[0].FullName 'mail-events.jsonl') -Raw) -eq $projection) 'Failed recovery did not preserve a verified backup'
    Assert (-not (Test-Path (Join-Path $root '.rollback.careops-mail.lock'))) 'Failed recovery leaked writer lock'
    $env:CAREOPS_MAIL_PSEUDONYM_KEY = ''; Reset-Pages @(); Expect-Failure $output
    Write-Output 'PASS: Outlook exporter offline privacy, pagination, replay, window and failure regressions'
} finally {
    $env:CAREOPS_MAIL_PSEUDONYM_KEY = $oldSecret
    # Only the literal freshly-created test directory is removed.
    if ([IO.Path]::GetFullPath($root).StartsWith([IO.Path]::GetFullPath([IO.Path]::GetTempPath()))) {
        Remove-Item -LiteralPath $root -Recurse -Force
    }
    Remove-Item Function:\az, Function:\Invoke-RestMethod, Function:\Move-Item, Function:\Start-Sleep -ErrorAction SilentlyContinue
}
