param(
    [string[]]$Services = @("backend", "front", "parser", "splitter", "vectorizer", "recall"),
    [int]$Tail = 200,
    [switch]$Follow,
    [switch]$All
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = (Resolve-Path (Join-Path $scriptRoot "..")).Path
$composeFile = Join-Path $backendRoot "docker-compose.yaml"

$normalizedServices = @()
foreach ($item in $Services) {
    if ([string]::IsNullOrWhiteSpace($item)) {
        continue
    }

    $normalizedServices += ($item -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

$args = @("compose", "-f", $composeFile, "logs", "--tail", $Tail)
if ($Follow) {
    $args += "--follow"
}

if (-not $All -and $normalizedServices.Count -gt 0) {
    $args += $normalizedServices
}

& docker @args
