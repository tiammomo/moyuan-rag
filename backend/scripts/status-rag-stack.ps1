param(
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = (Resolve-Path (Join-Path $scriptRoot "..")).Path
$composeFile = Join-Path $backendRoot "docker-compose.yaml"

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

function Get-EndpointStatus {
    param(
        [string]$Name,
        [string]$Url,
        [string]$ComposeService,
        [object[]]$ServiceList
    )

    $serviceState = (($ServiceList | Where-Object { $_.Service -eq $ComposeService } | Select-Object -First 1).State)
    $warning = $null

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
        if ($serviceState -ne "running") {
            $warning = "Endpoint reachable while compose service '$ComposeService' is not running."
        }

        return [PSCustomObject]@{
            Name = $Name
            Url = $Url
            ComposeService = $ComposeService
            ServiceState = $serviceState
            Reachable = $true
            StatusCode = [int]$response.StatusCode
            Warning = $warning
        }
    } catch {
        $statusCode = $null
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $statusCode = [int]$_.Exception.Response.StatusCode
        }

        if ($serviceState -eq "running") {
            $warning = "Endpoint is unreachable while compose service '$ComposeService' is running."
        }

        return [PSCustomObject]@{
            Name = $Name
            Url = $Url
            ComposeService = $ComposeService
            ServiceState = $serviceState
            Reachable = $false
            StatusCode = $statusCode
            Warning = $warning
        }
    }
}

$services = @(Get-ComposeServices | Sort-Object Service)
$endpoints = @(
    (Get-EndpointStatus -Name "backend" -Url "http://localhost:8000/health" -ComposeService "backend" -ServiceList $services)
    (Get-EndpointStatus -Name "front" -Url "http://localhost:3000" -ComposeService "front" -ServiceList $services)
    (Get-EndpointStatus -Name "kibana" -Url "http://localhost:5601" -ComposeService "kibana" -ServiceList $services)
    (Get-EndpointStatus -Name "kafka-ui" -Url "http://localhost:8080" -ComposeService "kafka-ui" -ServiceList $services)
    (Get-EndpointStatus -Name "attu" -Url "http://localhost:8001" -ComposeService "attu" -ServiceList $services)
)

$summary = [PSCustomObject]@{
    TotalServices = $services.Count
    RunningServices = @($services | Where-Object { $_.State -eq "running" }).Count
    HealthyServices = @($services | Where-Object { $_.Health -eq "healthy" }).Count
    NonRunningServices = @($services | Where-Object { $_.State -ne "running" } | Select-Object -ExpandProperty Service)
    UnhealthyServices = @($services | Where-Object { $_.Health -and $_.Health -ne "healthy" } | Select-Object -ExpandProperty Service)
}

$payload = [PSCustomObject]@{
    Summary = $summary
    Services = $services | Select-Object Service, Name, State, Health, Status, Ports
    Endpoints = $endpoints
}

if ($Json) {
    $payload | ConvertTo-Json -Depth 6
    exit 0
}

Write-Output "RAG Stack Summary"
Write-Output "  services: $($summary.RunningServices)/$($summary.TotalServices) running"
Write-Output "  healthy: $($summary.HealthyServices)"

if ($summary.NonRunningServices.Count -gt 0) {
    Write-Output "  non-running: $($summary.NonRunningServices -join ', ')"
}

if ($summary.UnhealthyServices.Count -gt 0) {
    Write-Output "  unhealthy: $($summary.UnhealthyServices -join ', ')"
}

Write-Output ""
Write-Output "Services"
$payload.Services | Format-Table -AutoSize

Write-Output ""
Write-Output "Endpoints"
$payload.Endpoints | Select-Object Name, ComposeService, ServiceState, Reachable, StatusCode, Warning, Url | Format-Table -AutoSize
