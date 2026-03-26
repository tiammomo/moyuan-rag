param(
    [string]$ComposeFile = "",
    [string]$HelperImage = "docker.m.daocloud.io/library/alpine:3.20",
    [switch]$Cutover,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = (Resolve-Path (Join-Path $scriptRoot "..")).Path

if (-not $ComposeFile) {
    $ComposeFile = Join-Path $backendRoot "docker-compose.yaml"
}

$appServices = @("backend", "parser", "splitter", "vectorizer", "front")
$sourceContainers = @(
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
    "rag-kafka-ui"
)

$mappings = @(
    @{ Name = "MySQL data"; Container = "rag-mysql8"; SourcePath = "/var/lib/mysql"; TargetVolume = "rag-mysql-data" },
    @{ Name = "Elasticsearch data"; Container = "rag-es7"; SourcePath = "/usr/share/elasticsearch/data"; TargetVolume = "rag-es-data" },
    @{ Name = "etcd data"; Container = "rag-etcd"; SourcePath = "/etcd"; TargetVolume = "rag-etcd-data" },
    @{ Name = "MinIO data"; Container = "rag-minio"; SourcePath = "/data"; TargetVolume = "rag-minio-data" },
    @{ Name = "Milvus data"; Container = "rag-milvus"; SourcePath = "/var/lib/milvus"; TargetVolume = "rag-milvus-data" },
    @{ Name = "Redis data"; Container = "rag-redis"; SourcePath = "/data"; TargetVolume = "rag-redis-data" },
    @{ Name = "Zookeeper data"; Container = "rag-zookeeper"; SourcePath = "/var/lib/zookeeper/data"; TargetVolume = "rag-zookeeper-data" },
    @{ Name = "Zookeeper log"; Container = "rag-zookeeper"; SourcePath = "/var/lib/zookeeper/log"; TargetVolume = "rag-zookeeper-log" },
    @{ Name = "Zookeeper secrets"; Container = "rag-zookeeper"; SourcePath = "/etc/zookeeper/secrets"; TargetVolume = "rag-zookeeper-secrets" },
    @{ Name = "Kafka data"; Container = "rag-kafka"; SourcePath = "/var/lib/kafka/data"; TargetVolume = "rag-kafka-data" },
    @{ Name = "Kafka secrets"; Container = "rag-kafka"; SourcePath = "/etc/kafka/secrets"; TargetVolume = "rag-kafka-secrets" }
)

function Write-Step {
    param([string]$Message)
    Write-Output "==> $Message"
}

function Test-ContainerExists {
    param([string]$Name)

    $output = docker ps -a --filter "name=^${Name}$" --format "{{.Names}}"
    return ($output -split "`n" | Where-Object { $_ -eq $Name }).Count -gt 0
}

function Test-RunningContainerExists {
    param([string]$Name)

    $output = docker ps --filter "name=^${Name}$" --format "{{.Names}}"
    return ($output -split "`n" | Where-Object { $_ -eq $Name }).Count -gt 0
}

function Test-VolumeExists {
    param([string]$Name)

    $output = docker volume ls --filter "name=^${Name}$" --format "{{.Name}}"
    return ($output -split "`n" | Where-Object { $_ -eq $Name }).Count -gt 0
}

function Ensure-VolumeExists {
    param([string]$Name)

    if (Test-VolumeExists -Name $Name) {
        return
    }

    Write-Step "creating target volume $Name"
    docker volume create $Name | Out-Null
}

function Test-VolumeHasData {
    param([string]$Name)

    if (-not (Test-VolumeExists -Name $Name)) {
        return $false
    }

    $output = & docker "run" "--rm" "-v" "${Name}:/to" $HelperImage "sh" "-c" "find /to -mindepth 1 -print -quit"
    return -not [string]::IsNullOrWhiteSpace(($output | Out-String))
}

function Get-ContainerMountInfo {
    param(
        [string]$Container,
        [string]$Destination
    )

    $inspect = docker inspect $Container | ConvertFrom-Json
    $mount = $inspect[0].Mounts | Where-Object { $_.Destination -eq $Destination } | Select-Object -First 1
    if (-not $mount) {
        return $null
    }

    return $mount
}

function Resolve-MigrationSource {
    param([hashtable]$Mapping)

    if (-not (Test-ContainerExists -Name $Mapping.Container)) {
        return [PSCustomObject]@{
            Exists = $false
            Kind = "missing"
            Reference = ""
            Summary = "container not found"
        }
    }

    $mount = Get-ContainerMountInfo -Container $Mapping.Container -Destination $Mapping.SourcePath
    if ($mount -and $mount.Type -eq "volume" -and $mount.Name) {
        return [PSCustomObject]@{
            Exists = $true
            Kind = "volume"
            Reference = $mount.Name
            Summary = "volume:$($mount.Name)"
        }
    }

    return [PSCustomObject]@{
        Exists = $true
        Kind = "container"
        Reference = $Mapping.SourcePath
        Summary = "container-path:$($Mapping.SourcePath)"
    }
}

function Get-SourceSize {
    param(
        [hashtable]$Mapping,
        [pscustomobject]$Source
    )

    if (-not $Source.Exists) {
        return "missing"
    }

    if ($Source.Kind -eq "volume") {
        $output = & docker "run" "--rm" "-v" "$($Source.Reference):/from" $HelperImage "sh" "-c" "du -sh /from 2>/dev/null | awk '{print `$1}'"
        return (($output | Out-String).Trim())
    }

    $output = & docker "exec" $Mapping.Container "sh" "-c" "du -sh '$($Mapping.SourcePath)' 2>/dev/null | awk '{print `$1}'"
    return (($output | Out-String).Trim())
}

function Copy-VolumeToVolume {
    param(
        [string]$SourceVolume,
        [string]$TargetVolume
    )

    & docker "run" "--rm" "-v" "${SourceVolume}:/from" "-v" "${TargetVolume}:/to" $HelperImage "sh" "-c" "cp -a /from/. /to/"
}

function Copy-ContainerPathToVolume {
    param(
        [string]$Container,
        [string]$SourcePath,
        [string]$TargetVolume
    )

    $tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("rag-migrate-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $tempDir | Out-Null

    try {
        $copySource = "${Container}:${SourcePath}/."
        & docker "cp" $copySource $tempDir
        & docker "run" "--rm" "-v" "${TargetVolume}:/to" "-v" "${tempDir}:/from" $HelperImage "sh" "-c" "cp -a /from/. /to/"
    } finally {
        if (Test-Path $tempDir) {
            Remove-Item -Path $tempDir -Recurse -Force
        }
    }
}

function Stop-ComposeAppServices {
    Write-Step "stopping compose app services"
    $serviceList = $appServices -join " "
    cmd /c "docker compose -f ""$ComposeFile"" stop $serviceList >NUL 2>&1"
    if ($LASTEXITCODE -ne 0) {
        throw "failed to stop compose app services"
    }
}

function Stop-SourceContainers {
    Write-Step "stopping standalone dependency containers"
    foreach ($container in $sourceContainers) {
        if (Test-RunningContainerExists -Name $container) {
            docker stop $container | Out-Null
        }
    }
}

function Remove-SourceContainers {
    Write-Step "removing standalone dependency containers so compose can take ownership"
    foreach ($container in $sourceContainers) {
        if (Test-ContainerExists -Name $container) {
            docker rm $container | Out-Null
        }
    }
}

function Start-ComposeStack {
    Write-Step "starting compose-managed full stack"
    & docker "compose" "-f" $ComposeFile "up" "-d"
}

Write-Step "compose file: $ComposeFile"
Write-Step "helper image: $HelperImage"

$resolvedMappings = @()
foreach ($mapping in $mappings) {
    $source = Resolve-MigrationSource -Mapping $mapping
    $size = Get-SourceSize -Mapping $mapping -Source $source
    $targetExists = Test-VolumeExists -Name $mapping.TargetVolume
    $targetHasData = Test-VolumeHasData -Name $mapping.TargetVolume

    $resolvedMappings += [PSCustomObject]@{
        Name = $mapping.Name
        Container = $mapping.Container
        SourcePath = $mapping.SourcePath
        SourceKind = $source.Kind
        SourceReference = $source.Reference
        SourceSummary = $source.Summary
        SourceSize = $size
        TargetVolume = $mapping.TargetVolume
        TargetExists = $targetExists
        TargetHasData = $targetHasData
    }
}

Write-Step "migration plan"
foreach ($item in $resolvedMappings) {
    Write-Output "- $($item.Name): source=$($item.SourceSummary), size=$($item.SourceSize), target=$($item.TargetVolume), target_exists=$($item.TargetExists), target_has_data=$($item.TargetHasData)"
}

if (-not $Cutover) {
    Write-Step "plan mode only; no containers or volumes were changed"
    exit 0
}

Write-Step "cutover mode requested"

foreach ($item in $resolvedMappings) {
    if ($item.TargetHasData -and -not $Force) {
        throw "target volume $($item.TargetVolume) already has data; rerun with -Force after verifying it is safe to overwrite"
    }
}

Stop-ComposeAppServices
Stop-SourceContainers

foreach ($item in $resolvedMappings) {
    if ($item.SourceKind -eq "missing") {
        Write-Step "skipping $($item.Name) because source container is missing"
        continue
    }

    Ensure-VolumeExists -Name $item.TargetVolume

    if ((Test-VolumeHasData -Name $item.TargetVolume) -and $Force) {
        Write-Step "clearing existing data in $($item.TargetVolume)"
        & docker "run" "--rm" "-v" "$($item.TargetVolume):/to" $HelperImage "sh" "-c" "rm -rf /to/* /to/.[!.]* /to/..?* 2>/dev/null || true"
    }

    Write-Step "copying $($item.Name) into $($item.TargetVolume)"
    if ($item.SourceKind -eq "volume") {
        Copy-VolumeToVolume -SourceVolume $item.SourceReference -TargetVolume $item.TargetVolume
    } else {
        Copy-ContainerPathToVolume -Container $item.Container -SourcePath $item.SourcePath -TargetVolume $item.TargetVolume
    }
}

Remove-SourceContainers
Start-ComposeStack

Write-Step "cutover completed"
