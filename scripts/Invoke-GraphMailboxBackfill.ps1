param(
    [Parameter(Mandatory)] [string] $Mailbox,
    [Parameter(Mandatory)] [string] $OutputDirectory,
    [datetime] $Since,
    [datetime] $Until,
    [int] $PageSize = 100
)

$ErrorActionPreference = 'Stop'

if ($PageSize -lt 1 -or $PageSize -gt 1000) { throw 'PageSize must be between 1 and 1000.' }
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$token = az account get-access-token --resource-type ms-graph --query accessToken -o tsv
if (-not $token) { throw 'Azure CLI did not return a Microsoft Graph access token.' }
$headers = @{ Authorization = "Bearer $token" }

$select = 'id,conversationId,subject,from,toRecipients,ccRecipients,receivedDateTime,sentDateTime,hasAttachments,internetMessageId,parentFolderId'
$filter = @()
if ($Since) { $filter += "receivedDateTime ge $($Since.ToUniversalTime().ToString('o'))" }
if ($Until) { $filter += "receivedDateTime lt $($Until.ToUniversalTime().ToString('o'))" }
$query = "`$top=$PageSize&`$select=$select&`$orderby=receivedDateTime"
if ($filter.Count) { $query += '&`$filter=' + [uri]::EscapeDataString(($filter -join ' and ')) }

$uri = "https://graph.microsoft.com/v1.0/users/$([uri]::EscapeDataString($Mailbox))/messages?$query"
$eventsPath = Join-Path $OutputDirectory 'mail-events.jsonl'
$manifestPath = Join-Path $OutputDirectory 'manifest.json'
$count = 0
while ($uri) {
    $page = Invoke-RestMethod -Uri $uri -Headers $headers -Method Get
    foreach ($message in $page.value) {
        # Keep the corpus at metadata level; bodies and attachments are excluded.
        [pscustomobject]@{
            event_id = $message.id
            object_type = 'email'
            activity = 'received'
            timestamp = $message.receivedDateTime
            conversation_id = $message.conversationId
            subject = $message.subject
            sender = $message.from.emailAddress.address
            recipients = @($message.toRecipients.emailAddress.address)
            cc_recipients = @($message.ccRecipients.emailAddress.address)
            has_attachments = [bool]$message.hasAttachments
            parent_folder_id = $message.parentFolderId
            internet_message_id = $message.internetMessageId
        } | ConvertTo-Json -Compress -Depth 8 | Add-Content -LiteralPath $eventsPath -Encoding utf8
        $count++
    }
    $uri = $page.'@odata.nextLink'
}

[pscustomobject]@{
    mailbox = $Mailbox
    since = if ($Since) { $Since.ToUniversalTime().ToString('o') } else { $null }
    until = if ($Until) { $Until.ToUniversalTime().ToString('o') } else { $null }
    event_count = $count
    generated_at = [datetime]::UtcNow.ToString('o')
    source = 'Microsoft Graph /messages'
    content_policy = 'metadata-only; message bodies and attachments excluded'
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding utf8

Write-Output "Wrote $count metadata events to $eventsPath"
