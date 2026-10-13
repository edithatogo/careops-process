# PowerShell 7 metadata collector. Folder/Dataverse certification is separate.
param(
    [Parameter(Mandatory)] [string] $Mailbox,
    [Parameter(Mandatory)] [string] $OutputDirectory,
    [string] $PilotEntryPath,
    [string] $PreparePilotEntryPath,
    [string] $FolderId,
    [string] $Since,
    [string] $Until,
    [string] $PageSize = '100'
)
$ErrorActionPreference = 'Stop'
$stage = $null; $backup = $null; $destination = $null; $published = $false; $hmac = $null
$writerLock = $null; $lockPath = $null
function Get-MailPseudonym([string] $Domain, [string[]] $Values) {
    $payload = ConvertTo-Json -InputObject (@($Domain) + $Values) -Compress
    $digest = $hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($payload))
    $Domain + '_' + [Convert]::ToHexString($digest).ToLowerInvariant()
}
function Remove-MailStaging([string] $Path) {
    # Remove only known files, then the empty directory; never recursively.
    foreach ($name in @('mail-events.jsonl', 'manifest.json')) {
        $file = Join-Path $Path $name
        if (Test-Path -LiteralPath $file) { Remove-Item -LiteralPath $file -Force }
    }
    Remove-Item -LiteralPath $Path -Force
}
try {
    $pageSizeValue = 0
    if (-not [int]::TryParse($PageSize, [ref]$pageSizeValue) -or $pageSizeValue -lt 1 -or $pageSizeValue -gt 1000) { throw 'Invalid page size.' }
    if ([string]::IsNullOrWhiteSpace($Mailbox)) { throw 'Mailbox scope is required.' }
    if ($PSBoundParameters.ContainsKey('FolderId') -and [string]::IsNullOrWhiteSpace($FolderId)) { throw 'Invalid folder scope.' }
    $sinceBound = $null; $untilBound = $null
    foreach ($bound in @('Since', 'Until')) {
        $value = Get-Variable -Name $bound -ValueOnly
        if ($PSBoundParameters.ContainsKey($bound)) {
            $parsed = [datetimeoffset]::MinValue
            if ($value -notmatch '(Z|[+-]\d{2}:\d{2})$' -or -not [datetimeoffset]::TryParse($value, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::None, [ref]$parsed)) { throw 'Explicit valid timezone required.' }
            if ($bound -eq 'Since') { $sinceBound = $parsed } else { $untilBound = $parsed }
        }
    }
    if ($sinceBound -and $untilBound -and $sinceBound -ge $untilBound) { throw 'Invalid observation window.' }
    $key = [Convert]::FromBase64String($env:CAREOPS_MAIL_PSEUDONYM_KEY)
    if ($key.Length -lt 32) { throw 'A base64 key of at least 32 bytes is required.' }
    $hmac = [Security.Cryptography.HMACSHA256]::new($key)
    [Array]::Clear($key, 0, $key.Length)
    $mailboxRef = Get-MailPseudonym 'mailbox' @($Mailbox.Trim().ToLowerInvariant())
    $folderRef = if ($FolderId) { Get-MailPseudonym 'folder' @($mailboxRef, $FolderId) } else { $null }
    $sinceUtc = if ($sinceBound) { $sinceBound.UtcDateTime.ToString('o') } else { $null }
    $untilUtc = if ($untilBound) { $untilBound.UtcDateTime.ToString('o') } else { $null }
    $keyRef = Get-MailPseudonym 'key' @('careops-outlook-v1')
    $destination = [IO.Path]::GetFullPath($OutputDirectory)
    $parent = [IO.Path]::GetDirectoryName($destination)
    if (-not $parent -or $destination -eq [IO.Path]::GetPathRoot($destination)) { throw 'An output subdirectory is required.' }
    $outputRef = Get-MailPseudonym 'destination' @($destination)
    if ($PreparePilotEntryPath) {
        if ($PilotEntryPath) { throw 'Preparation and acquisition are mutually exclusive.' }
        $proposal = [ordered]@{
            source_owner_approved = $false; ig_approved = $false
            configuration_frozen = $false; rollback_retention_approved = $false
            authorised_source_partitions = @($(if ($folderRef) { $folderRef }))
            configuration_hash = '<sha256-of-approved-frozen-configuration>'
            evidence_reference = '<approved-evidence-location-reference>'
            acquisition_scope = [ordered]@{
                mailbox_ref = $mailboxRef; folder_ref = $folderRef
                since_utc = $sinceUtc; until_utc = $untilUtc
                output_directory_ref = $outputRef; whole_mailbox_approved = $false
            }
        }
        $proposalBytes = [Text.UTF8Encoding]::new($false).GetBytes(($proposal | ConvertTo-Json -Depth 8))
        $proposalStream = [IO.File]::Open([IO.Path]::GetFullPath($PreparePilotEntryPath), [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try { $proposalStream.Write($proposalBytes, 0, $proposalBytes.Length) } finally { $proposalStream.Dispose() }
        Write-Output 'Prepared an unapproved Outlook acquisition record; source access was not attempted.'
        return
    }
    # A token or a user-supplied mailbox is not source-owner/IG approval. Check
    # the private pilot record and its exact acquisition binding before I/O.
    if ([string]::IsNullOrWhiteSpace($PilotEntryPath)) { throw 'Approved pilot entry is required.' }
    $approvalText = Get-Content -LiteralPath $PilotEntryPath -Raw
    $approval = $approvalText | ConvertFrom-Json -AsHashtable -Depth 16
    $approvalFields = @('source_owner_approved', 'ig_approved', 'configuration_frozen', 'rollback_retention_approved', 'authorised_source_partitions', 'configuration_hash', 'evidence_reference', 'acquisition_scope')
    if ($approval -isnot [Collections.IDictionary] -or $approval.Count -ne $approvalFields.Count) { throw 'Invalid pilot entry shape.' }
    foreach ($field in $approvalFields) { if (-not $approval.Contains($field)) { throw 'Incomplete pilot entry.' } }
    foreach ($field in @('source_owner_approved', 'ig_approved', 'configuration_frozen', 'rollback_retention_approved')) {
        if ($approval[$field] -isnot [bool] -or $approval[$field] -ne $true) { throw 'Pilot approval gate is incomplete.' }
    }
    if ($approval.configuration_hash -isnot [string] -or $approval.configuration_hash -cnotmatch '^[a-f0-9]{64}$' -or
        $approval.evidence_reference -isnot [string] -or [string]::IsNullOrWhiteSpace($approval.evidence_reference) -or
        $approval.authorised_source_partitions -isnot [array] -or -not $approval.authorised_source_partitions.Count) { throw 'Invalid approval references.' }
    $partitions = $approval.authorised_source_partitions
    if (@($partitions | Where-Object { $_ -isnot [string] -or [string]::IsNullOrWhiteSpace($_) }).Count -or
        @($partitions | Sort-Object -Unique).Count -ne $partitions.Count) { throw 'Invalid approved source partitions.' }
    $scope = $approval.acquisition_scope
    $scopeFields = @('mailbox_ref', 'folder_ref', 'since_utc', 'until_utc', 'output_directory_ref', 'whole_mailbox_approved')
    if ($scope -isnot [Collections.IDictionary] -or $scope.Count -ne $scopeFields.Count) { throw 'Invalid approved acquisition scope.' }
    foreach ($field in $scopeFields) { if (-not $scope.Contains($field)) { throw 'Incomplete approved acquisition scope.' } }
    # ConvertFrom-Json date coercion differs across PowerShell versions. Keep
    # the exact JSON string/null bounds and reject other JSON primitive types.
    $approvalDocument = [Text.Json.JsonDocument]::Parse($approvalText)
    try {
        $scopeDocument = $approvalDocument.RootElement.GetProperty('acquisition_scope')
        foreach ($field in @('since_utc', 'until_utc')) { $scope[$field] = $scopeDocument.GetProperty($field).GetString() }
    } finally { $approvalDocument.Dispose(); $approvalText = $null }
    if ($scope.mailbox_ref -isnot [string] -or $scope.mailbox_ref -cne $mailboxRef -or
        $scope.folder_ref -cne $folderRef -or $scope.since_utc -cne $sinceUtc -or $scope.until_utc -cne $untilUtc -or
        $scope.output_directory_ref -isnot [string] -or $scope.output_directory_ref -cne $outputRef -or
        $scope.whole_mailbox_approved -isnot [bool]) { throw 'Acquisition does not match approved scope.' }
    if ($FolderId) {
        if ($partitions -cnotcontains $folderRef) { throw 'Folder absent from approved partitions.' }
    } elseif ($scope.whole_mailbox_approved -ne $true) { throw 'Mailbox-wide acquisition is not approved.' }
    $approvalHash = (Get-FileHash -LiteralPath $PilotEntryPath -Algorithm SHA256).Hash.ToLowerInvariant()
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $lockPath = Join-Path $parent ('.' + [IO.Path]::GetFileName($destination) + '.careops-mail.lock')
    $writerLock = [IO.File]::Open($lockPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    $previousIds = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $previousExists = Test-Path -LiteralPath $destination
    if ($previousExists) {
        $item = Get-Item -LiteralPath $destination
        if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Unsafe destination.' }
        $existing = @(Get-ChildItem -LiteralPath $destination -Force)
        if ($existing.Count -ne 2 -or @($existing | Where-Object { $_.Name -notin @('mail-events.jsonl', 'manifest.json') -or $_.PSIsContainer -or ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) }).Count) {
            throw 'Use a new dedicated exporter destination.'
        }
        $previous = Get-Content -LiteralPath (Join-Path $destination 'manifest.json') -Raw | ConvertFrom-Json
        $previousEvents = Join-Path $destination 'mail-events.jsonl'
        if ($previous.schema_version -ne '2.0.0' -or $previous.status -ne 'acquired' -or
            $previous.mailbox_ref -ne $mailboxRef -or $previous.key_ref -ne $keyRef -or
            $previous.folder_ref -ne $folderRef -or
            $previous.approval_hash -ne $approvalHash -or $previous.configuration_hash -ne $approval.configuration_hash -or
            $previous.since_utc -ne $sinceUtc -or $previous.until_utc -ne $untilUtc -or
            $previous.content_hash -ne (Get-FileHash -LiteralPath $previousEvents -Algorithm SHA256).Hash.ToLowerInvariant()) {
            throw 'Previous scope, key or integrity does not match.'
        }
        foreach ($line in Get-Content -LiteralPath $previousEvents) {
            $fact = $line | ConvertFrom-Json
            if ($fact.id -notmatch '^mail_[a-f0-9]{64}$') { throw 'Invalid previous identity.' }
            [void]$previousIds.Add($fact.id)
        }
    }
    # Suppress raw Azure CLI diagnostics, including identities and response data.
    $global:LASTEXITCODE = 0
    $token = az account get-access-token --resource-type ms-graph --query accessToken -o tsv 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace([string]$token)) { throw 'Authentication unavailable.' }
    $headers = @{ Authorization = "Bearer $token"; Prefer = 'IdType="ImmutableId"' }
    $select = 'id,conversationId,receivedDateTime,hasAttachments,importance,parentFolderId'
    $query = '$top=' + $pageSizeValue + '&$select=' + [uri]::EscapeDataString($select) + '&$orderby=receivedDateTime'
    $filters = @()
    if ($sinceUtc) { $filters += "receivedDateTime ge $sinceUtc" }
    if ($untilUtc) { $filters += "receivedDateTime lt $untilUtc" }
    if ($filters.Count) { $query += '&$filter=' + [uri]::EscapeDataString($filters -join ' and ') }
    $endpoint = 'https://graph.microsoft.com/v1.0/users/' + [uri]::EscapeDataString($Mailbox) + '/messages'
    if ($FolderId) {
        $endpoint = 'https://graph.microsoft.com/v1.0/users/' + [uri]::EscapeDataString($Mailbox) + '/mailFolders/' + [uri]::EscapeDataString($FolderId) + '/messages'
    }
    $expectedPath = ([uri]$endpoint).AbsolutePath
    $next = $endpoint + '?' + $query
    $seenPages = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $facts = [Collections.Generic.SortedDictionary[string,string]]::new([StringComparer]::Ordinal)
    $pageLedger = [Collections.Generic.List[object]]::new()
    $candidateCount = 0; $duplicateCount = 0; $rejectedCount = 0; $pagesRead = 0; $retryCount = 0
    while ($next) {
        $uri = [uri]$next
        if (-not $uri.IsAbsoluteUri -or $uri.Scheme -ne 'https' -or $uri.Host -ne 'graph.microsoft.com' -or
            $uri.Port -ne 443 -or $uri.UserInfo -or $uri.Fragment -or $uri.AbsolutePath -cne $expectedPath) {
            throw 'Unsafe pagination destination.'
        }
        if (-not $seenPages.Add($uri.AbsoluteUri)) { throw 'Pagination loop.' }
        $attempt = 0
        while ($true) {
            try {
                $page = Invoke-RestMethod -Uri $uri -Headers $headers -Method Get -TimeoutSec 60 -MaximumRedirection 0
                break
            } catch {
                $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
                $timeout = $_.Exception -is [TimeoutException] -or $_.Exception -is [Threading.Tasks.TaskCanceledException]
                if (($status -notin @(408, 429, 500, 502, 503, 504) -and -not $timeout) -or $attempt -ge 3) { throw 'Page acquisition failed.' }
                $delay = [math]::Pow(2, $attempt)
                $retryAfter = $_.Exception.Response.Headers.RetryAfter
                if ($retryAfter.Delta) { $delay = [math]::Max($delay, $retryAfter.Delta.TotalSeconds) }
                if ($retryAfter.Date) { $delay = [math]::Max($delay, ($retryAfter.Date - [datetimeoffset]::UtcNow).TotalSeconds) }
                if ($delay -gt 60) { throw 'Retry delay exceeds bounded local budget.' }
                Start-Sleep -Seconds ([math]::Ceiling($delay))
                $attempt++; $retryCount++
            }
        }
        $hasValue = if ($page -is [Collections.IDictionary]) { $page.Contains('value') } else { $null -ne $page.PSObject.Properties['value'] }
        if (-not $hasValue -or $null -eq $page.value -or $page.value -is [string] -or
            $page.value -is [Collections.IDictionary] -or $page.value -isnot [Collections.IEnumerable]) { throw 'Malformed page.' }
        $pagesRead++
        $beforeCandidates = $candidateCount; $beforeAcquired = $facts.Count
        $beforeDuplicates = $duplicateCount; $beforeRejected = $rejectedCount
        $pageFactIds = [Collections.Generic.List[string]]::new()
        foreach ($message in $page.value) {
            $candidateCount++
            if ($FolderId -and $message.parentFolderId -cne $FolderId) { throw 'Source violated folder scope.' }
            $timestamp = [datetimeoffset]::MinValue
            if ($message.id -isnot [string] -or [string]::IsNullOrWhiteSpace($message.id) -or
                $message.parentFolderId -isnot [string] -or [string]::IsNullOrWhiteSpace($message.parentFolderId) -or
                $message.conversationId -isnot [string] -or [string]::IsNullOrWhiteSpace($message.conversationId) -or
                $message.hasAttachments -isnot [bool] -or $message.receivedDateTime -isnot [string] -or
                $message.receivedDateTime -notmatch '(Z|[+-]\d{2}:\d{2})$' -or
                -not [datetimeoffset]::TryParse($message.receivedDateTime, [ref]$timestamp) -or
                $message.importance -notin @('low', 'normal', 'high')) { $rejectedCount++; continue }
            if (($sinceBound -and $timestamp -lt $sinceBound) -or ($untilBound -and $timestamp -ge $untilBound)) { throw 'Source violated observation window.' }
            $id = Get-MailPseudonym 'mail' @($mailboxRef, $message.id, $message.parentFolderId)
            $record = [ordered]@{
                id = $id; activity = 'email_received'; timestamp_utc = $timestamp.UtcDateTime.ToString('o')
                source_system = 'outlook'; object_ids = @(Get-MailPseudonym 'conversation' @($mailboxRef, $message.conversationId))
                folder_id = Get-MailPseudonym 'folder' @($mailboxRef, $message.parentFolderId)
                has_attachments = $message.hasAttachments; importance = $message.importance
            } | ConvertTo-Json -Compress -Depth 5
            if ($facts.ContainsKey($id)) {
                if ($facts[$id] -cne $record) { throw 'Conflicting duplicate identity.' }
                $duplicateCount++; continue
            }
            $facts.Add($id, $record)
            $pageFactIds.Add($id)
        }
        $continuation = $page.'@odata.nextLink'
        if ($null -ne $continuation -and ($continuation -isnot [string] -or -not $continuation)) { throw 'Malformed continuation.' }
        $next = $continuation
        if ($FolderId) {
            $pageLedger.Add([ordered]@{
                folder_id = $folderRef; page_number = $pagesRead
                candidate_count = $candidateCount - $beforeCandidates
                acquired_count = $facts.Count - $beforeAcquired
                duplicate_count = $duplicateCount - $beforeDuplicates
                rejected_count = $rejectedCount - $beforeRejected
                fact_ids = @($pageFactIds.ToArray()); next_link_exhausted = -not $next
            })
        }
    }
    $stage = Join-Path $parent ('.careops-mail-stage-' + [guid]::NewGuid())
    New-Item -ItemType Directory -Path $stage | Out-Null
    $eventsPath = Join-Path $stage 'mail-events.jsonl'
    $text = if ($facts.Count) { ($facts.Values -join "`n") + "`n" } else { '' }
    [IO.File]::WriteAllText($eventsPath, $text, [Text.UTF8Encoding]::new($false))
    $newIds = @($facts.Keys | Where-Object { -not $previousIds.Contains($_) }).Count
    $hash = (Get-FileHash -LiteralPath $eventsPath -Algorithm SHA256).Hash.ToLowerInvariant()
    [ordered]@{
        schema_version = '2.0.0'; run_id = [guid]::NewGuid().ToString(); status = 'acquired'
        mailbox_ref = $mailboxRef; key_ref = $keyRef; pseudonymization_version = 'hmac-sha256-json-array-v1'
        approval_hash = $approvalHash; configuration_hash = $approval.configuration_hash
        folder_ref = $folderRef; page_ledger = @($pageLedger.ToArray())
        since_utc = $sinceUtc; until_utc = $untilUtc; pages_read = $pagesRead
        candidate_count = $candidateCount; acquired_count = $facts.Count
        duplicate_count = $duplicateCount; rejected_count = $rejectedCount; retry_count = $retryCount
        emitted_count = $facts.Count; filtered_count = 0; dead_letter_count = $rejectedCount
        new_identity_count = $newIds; replay_compared = $previousExists
        idempotency_replay_verified = ($previousExists -and $newIds -eq 0 -and $previousIds.Count -eq $facts.Count -and $previous.content_hash -eq $hash)
        pagination_exhausted = $true; no_raw_content_stored = $true; full_mailbox_verified = $false
        reconciled = ($candidateCount -eq $facts.Count + $duplicateCount + $rejectedCount)
        folder_inventory_verified = $false; dataverse_reconciled = $false; content_hash = $hash
        content_hash_encoding = 'sha256:utf8-jsonl-lf'
        generated_at_utc = [datetime]::UtcNow.ToString('o')
        scope = 'Graph message collection; folder policy and full-mailbox coverage unverified'
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $stage 'manifest.json') -Encoding utf8
    # Move the directory as one artifact; preserve previous output on failures.
    if ($previousExists) {
        $backup = Join-Path $parent ('.careops-mail-backup-' + [guid]::NewGuid())
        Move-Item -LiteralPath $destination -Destination $backup
    }
    Move-Item -LiteralPath $stage -Destination $destination
    $stage = $null; $published = $true
    if ($backup) { Remove-MailStaging $backup; $backup = $null }
    Write-Output "Acquired $($facts.Count) minimized Outlook facts; full-mailbox verification pending."
} catch {
    # Never emit source responses, mailbox identity, token, paths or raw arguments.
    throw 'Outlook acquisition failed closed. Check approved scope, key, access and destination integrity.'
} finally {
    $cleanupFailed = $false
    try {
        if (-not $published -and $backup -and -not (Test-Path -LiteralPath $destination)) { Move-Item -LiteralPath $backup -Destination $destination }
    } catch { $cleanupFailed = $true }
    try {
        if ($stage -and (Test-Path -LiteralPath $stage)) { Remove-MailStaging $stage }
    } catch { $cleanupFailed = $true }
    if ($hmac) { $hmac.Dispose() }
    try {
        if ($writerLock) { $writerLock.Dispose(); [IO.File]::Delete($lockPath) }
    } catch { $cleanupFailed = $true }
    $token = $null; $headers = $null
    if ($cleanupFailed) { throw 'Outlook recovery requires operator inspection of the approved artifact location; retained backup must be verified.' }
}
