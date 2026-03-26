param(
    [string]$NetworkName = "rag-net"
)

$ErrorActionPreference = "Stop"

$containers = @(
    "rag-mysql8",
    "rag-es7",
    "rag-kibana",
    "rag-etcd",
    "rag-minio",
    "rag-milvus",
    "rag-attu",
    "rag-redis",
    "rag-zookeeper",
    "rag-kafka",
    "rag-kafka-ui",
    "rag-backend",
    "rag-parser",
    "rag-splitter",
    "rag-vectorizer",
    "rag-front"
)

function Write-Step {
    param([string]$Message)
    Write-Output "==> $Message"
}

function Test-NetworkExists {
    param([string]$Name)

    $output = docker network ls --filter "name=^${Name}$" --format "{{.Name}}"
    return ($output -split "`n" | Where-Object { $_ -eq $Name }).Count -gt 0
}

function Get-ContainerNamesInNetwork {
    param([string]$Name)

    $json = docker network inspect $Name | ConvertFrom-Json
    if (-not $json -or -not $json[0].Containers) {
        return @()
    }

    return $json[0].Containers.PSObject.Properties.Value.Name
}

function Test-ContainerExists {
    param([string]$Name)

    $output = docker ps -a --filter "name=^${Name}$" --format "{{.Names}}"
    return ($output -split "`n" | Where-Object { $_ -eq $Name }).Count -gt 0
}

if (-not (Test-NetworkExists -Name $NetworkName)) {
    Write-Step "creating docker network $NetworkName"
    docker network create --driver bridge --attachable $NetworkName | Out-Null
} else {
    Write-Step "docker network $NetworkName already exists"
}

$connected = Get-ContainerNamesInNetwork -Name $NetworkName

foreach ($container in $containers) {
    if (-not (Test-ContainerExists -Name $container)) {
        Write-Step "skip $container (container does not exist)"
        continue
    }

    if ($connected -contains $container) {
        Write-Step "$container is already attached to $NetworkName"
        continue
    }

    Write-Step "connecting $container to $NetworkName"
    docker network connect $NetworkName $container
}

Write-Step "current members in $NetworkName"
docker network inspect $NetworkName --format "{{range .Containers}}{{println .Name}}{{end}}"
