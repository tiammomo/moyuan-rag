param(
    [ValidateSet("rag.document.upload.dlq", "rag.document.parsed.dlq", "rag.document.chunks.dlq")]
    [string]$Topic = "rag.document.upload.dlq",
    [int]$MaxMessages = 20,
    [int]$TimeoutSeconds = 10,
    [switch]$Raw
)

$ErrorActionPreference = "Stop"

Write-Host "[kafka-dlq] Reading up to $MaxMessages message(s) from $Topic"

$dockerCommand = @(
    "exec",
    "rag-kafka",
    "bash",
    "-lc",
    "timeout $TimeoutSeconds kafka-console-consumer --bootstrap-server localhost:29092 --topic $Topic --from-beginning --max-messages $MaxMessages 2>/dev/null"
)

$messages = & docker @dockerCommand

if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 124) {
    throw "Failed to read topic $Topic from rag-kafka"
}

if (-not $messages) {
    Write-Host "[kafka-dlq] No messages found in $Topic"
    exit 0
}

if ($Raw) {
    $messages
    exit 0
}

$messages | ForEach-Object {
    $line = $_.Trim()
    if (-not $line) {
        return
    }

    try {
        $line | ConvertFrom-Json | ConvertTo-Json -Depth 10
    } catch {
        $line
    }
}
