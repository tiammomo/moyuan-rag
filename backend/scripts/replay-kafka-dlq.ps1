param(
    [ValidateSet("rag.document.upload.dlq", "rag.document.parsed.dlq", "rag.document.chunks.dlq")]
    [string]$Topic,
    [int]$Offset,
    [int]$Partition = 0,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if (-not $PSBoundParameters.ContainsKey("Topic")) {
    throw "Topic is required."
}

if (-not $PSBoundParameters.ContainsKey("Offset")) {
    throw "Offset is required."
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$pythonExe = Join-Path $repoRoot "backend/.venv/Scripts/python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Python virtual environment not found at $pythonExe"
}

$fetchCommand = "timeout 10 kafka-console-consumer --bootstrap-server localhost:29092 --topic $Topic --partition $Partition --offset $Offset --max-messages 1 2>/dev/null"
$rawMessage = & docker exec rag-kafka bash -lc $fetchCommand

if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 124) {
    throw "Failed to read DLQ message from $Topic partition $Partition offset $Offset"
}

if (-not $rawMessage) {
    throw "No DLQ message found at $Topic partition $Partition offset $Offset"
}

$record = $rawMessage | ConvertFrom-Json

if (-not $record.source_topic) {
    throw "DLQ record is missing source_topic"
}

if (-not $record.payload) {
    throw "DLQ record is missing payload"
}

try {
    $null = $record.payload | ConvertFrom-Json
} catch {
    throw "DLQ payload is not valid JSON and will not be replayed."
}

if ($DryRun) {
    $record | ConvertTo-Json -Depth 10
    exit 0
}

$topicBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes([string]$record.source_topic))
$payloadBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes([string]$record.payload))

@"
import asyncio
import base64
from aiokafka import AIOKafkaProducer

source_topic = base64.b64decode("$topicBase64").decode("utf-8")
payload = base64.b64decode("$payloadBase64")

async def main() -> None:
    producer = AIOKafkaProducer(bootstrap_servers="localhost:9094")
    await producer.start()
    try:
        await producer.send_and_wait(source_topic, payload)
    finally:
        await producer.stop()

asyncio.run(main())
"@ | & $pythonExe -

Write-Host "[replay-kafka-dlq] Replayed $Topic partition=$Partition offset=$Offset -> $($record.source_topic)"
