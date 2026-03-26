param(
    [switch]$Build,
    [int]$HealthTimeoutSec = 180
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = (Resolve-Path (Join-Path $scriptRoot "..")).Path
$composeFile = Join-Path $backendRoot "docker-compose.yaml"
$ensureNetworkScript = Join-Path $scriptRoot "ensure-rag-network.ps1"
$ensureVolumesScript = Join-Path $scriptRoot "ensure-rag-volumes.ps1"

function Write-Step {
    param([string]$Message)
    Write-Output "==> $Message"
}

function Get-ComposeServices {
    $rawLines = & docker "compose" "-f" $composeFile "ps" "--all" "--format" "json"
    $services = @()

    foreach ($line in $rawLines) {
        $trimmed = [string]$line
        if ([string]::IsNullOrWhiteSpace($trimmed)) {
            continue
        }

        $services += $trimmed | ConvertFrom-Json
    }

    return $services
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

if (Test-Path $ensureNetworkScript) {
    Write-Step "ensuring docker network rag-net"
    & powershell "-ExecutionPolicy" "Bypass" "-File" $ensureNetworkScript
}

if (Test-Path $ensureVolumesScript) {
    Write-Step "ensuring docker volumes for rag compose stack"
    & powershell "-ExecutionPolicy" "Bypass" "-File" $ensureVolumesScript
}

$composeArgs = @("compose", "-f", $composeFile, "up", "-d")
if ($Build) {
    $composeArgs += "--build"
}

$baseServices = @(
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
    "backend"
)
$appServices = @("parser", "splitter", "vectorizer", "front")

Write-Step "starting rag compose infrastructure and backend"
& docker @($composeArgs + $baseServices)

Write-Step "waiting for compose backend readiness"
Wait-ComposeServiceReady -Service "backend" -TimeoutSec $HealthTimeoutSec -RequireHealthy

Write-Step "starting rag compose app services"
& docker @($composeArgs + $appServices)

Write-Step "waiting for compose frontend and workers"
Wait-ComposeServiceReady -Service "front" -TimeoutSec $HealthTimeoutSec -RequireHealthy
Wait-ComposeServiceReady -Service "parser" -TimeoutSec $HealthTimeoutSec
Wait-ComposeServiceReady -Service "splitter" -TimeoutSec $HealthTimeoutSec
Wait-ComposeServiceReady -Service "vectorizer" -TimeoutSec $HealthTimeoutSec

Write-Step "waiting for backend and frontend health"
Wait-HttpHealthy -Name "backend" -Url "http://localhost:8000/health" -TimeoutSec $HealthTimeoutSec
Wait-HttpHealthy -Name "front" -Url "http://localhost:3000" -TimeoutSec $HealthTimeoutSec

Write-Step "rag stack is ready"
Write-Output "Endpoints:"
Write-Output "  backend: http://localhost:8000"
Write-Output "  frontend: http://localhost:3000"
Write-Output "  kibana: http://localhost:5601"
Write-Output "  kafka-ui: http://localhost:8080"
Write-Output "  attu: http://localhost:8001"
