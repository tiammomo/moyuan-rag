param(
    [switch]$VerboseOutput
)

$ErrorActionPreference = "Stop"

$requiredVolumes = @(
    "rag-mysql-data",
    "rag-es-data",
    "rag-kibana-logs",
    "rag-etcd-data",
    "rag-minio-data",
    "rag-milvus-data",
    "rag-redis-data",
    "rag-zookeeper-data",
    "rag-zookeeper-log",
    "rag-zookeeper-secrets",
    "rag-kafka-data",
    "rag-kafka-secrets"
)

function Write-Step {
    param([string]$Message)
    Write-Output "==> $Message"
}

function Test-VolumeExists {
    param([string]$Name)

    $output = docker volume ls --filter "name=^${Name}$" --format "{{.Name}}"
    return ($output -split "`n" | Where-Object { $_ -eq $Name }).Count -gt 0
}

Write-Step "ensuring Docker volumes for rag compose stack"

foreach ($volume in $requiredVolumes) {
    if (Test-VolumeExists -Name $volume) {
        if ($VerboseOutput) {
            Write-Output "   exists: $volume"
        }
        continue
    }

    Write-Output "   creating: $volume"
    docker volume create $volume | Out-Null
}

Write-Step "volume check completed"
