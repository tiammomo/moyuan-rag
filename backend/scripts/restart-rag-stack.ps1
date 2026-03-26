param(
    [string[]]$Services = @("backend"),
    [switch]$IncludeDependents,
    [int]$HealthTimeoutSec = 180
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = (Resolve-Path (Join-Path $scriptRoot "..")).Path
$composeFile = Join-Path $backendRoot "docker-compose.yaml"
$backendUrl = "http://localhost:38084/health"
$frontUrl = "http://localhost:33004"
$knownServices = @(
    "mysql8",
    "es",
    "kibana",
    "etcd",
    "minio",
    "milvus-standalone",
    "attu",
    "redis",
    "zookeeper",
    "kafka",
    "kafka-ui",
    "backend",
    "parser",
    "splitter",
    "vectorizer",
    "front"
)
$dependentMap = @{
    "mysql8" = @("backend", "parser", "splitter", "vectorizer", "front")
    "es" = @("backend", "parser", "splitter", "vectorizer", "front", "kibana")
    "etcd" = @("milvus-standalone", "attu", "backend", "parser", "splitter", "vectorizer", "front")
    "minio" = @("milvus-standalone", "backend", "parser", "splitter", "vectorizer", "front")
    "milvus-standalone" = @("attu", "backend", "parser", "splitter", "vectorizer", "front")
    "redis" = @("backend", "parser", "splitter", "vectorizer", "front")
    "zookeeper" = @("kafka", "kafka-ui", "backend", "parser", "splitter", "vectorizer", "front")
    "kafka" = @("kafka-ui", "backend", "parser", "splitter", "vectorizer", "front")
    "backend" = @("parser", "splitter", "vectorizer", "front")
}

$requestedServices = @()
foreach ($item in $Services) {
    if ([string]::IsNullOrWhiteSpace($item)) {
        continue
    }

    $requestedServices += ($item -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

if ($requestedServices.Count -eq 0) {
    throw "No compose services were requested."
}

function Write-Step {
    param([string]$Message)
    Write-Output "==> $Message"
}

function Get-ComposeServices {
    $rawLines = & docker "compose" "-f" $composeFile "ps" "--all" "--format" "json"
    $result = @()

    foreach ($line in $rawLines) {
        $trimmed = [string]$line
        if ([string]::IsNullOrWhiteSpace($trimmed)) {
            continue
        }

        $result += $trimmed | ConvertFrom-Json
    }

    return $result
}

function Wait-ComposeServiceReady {
    param(
        [string]$Service,
        [int]$TimeoutSec,
        [switch]$RequireHealthy
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $lastStatus = "unknown"

    while ((Get-Date) -lt $deadline) {
        $serviceInfo = Get-ComposeServices | Where-Object { $_.Service -eq $Service } | Select-Object -First 1
        if ($serviceInfo) {
            $lastStatus = $serviceInfo.Status
            $isRunning = $serviceInfo.State -eq "running"
            $healthOk = (-not $RequireHealthy) -or [string]::IsNullOrWhiteSpace($serviceInfo.Health) -or $serviceInfo.Health -eq "healthy"
            if ($isRunning -and $healthOk) {
                Write-Output "   ready: $Service -> $($serviceInfo.Status)"
                return
            }
        }

        Start-Sleep -Seconds 2
    }

    throw "$Service did not become ready within $TimeoutSec seconds. Last compose status: $lastStatus"
}

function Wait-HttpHealthy {
    param(
        [string]$Name,
        [string]$Url,
        [int]$TimeoutSec
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
                Write-Output "   healthy: $Name -> $Url"
                return
            }
        } catch {
        }

        Start-Sleep -Seconds 2
    }

    throw "$Name did not become healthy within $TimeoutSec seconds: $Url"
}

foreach ($service in $requestedServices) {
    if ($knownServices -notcontains $service) {
        throw "Unknown compose service: $service"
    }
}

$targets = New-Object System.Collections.Generic.List[string]
foreach ($service in $knownServices) {
    if ($requestedServices -contains $service) {
        $targets.Add($service)
        continue
    }

    if (-not $IncludeDependents) {
        continue
    }

    foreach ($source in $requestedServices) {
        if ($dependentMap.ContainsKey($source) -and $dependentMap[$source] -contains $service) {
            $targets.Add($service)
            break
        }
    }
}

if ($targets.Count -eq 0) {
    throw "No compose services selected for restart."
}

Write-Step "restarting compose services: $($targets -join ', ')"
& docker "compose" "-f" $composeFile "restart" @targets

Write-Step "ensuring compose services are running"
& docker "compose" "-f" $composeFile "up" "-d" @targets

Write-Step "waiting for compose services to become ready"
foreach ($service in $targets) {
    $requiresHealth = @("backend", "front", "kafka") -contains $service
    Wait-ComposeServiceReady -Service $service -TimeoutSec $HealthTimeoutSec -RequireHealthy:$requiresHealth
}

if ($targets -contains "backend") {
    Wait-HttpHealthy -Name "backend" -Url $backendUrl -TimeoutSec $HealthTimeoutSec
}

if ($targets -contains "front") {
    Wait-HttpHealthy -Name "front" -Url $frontUrl -TimeoutSec $HealthTimeoutSec
}

Write-Step "restart completed"
