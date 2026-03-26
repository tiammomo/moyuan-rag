param(
    [switch]$RemoveContainers,
    [switch]$RemoveOrphans,
    [int]$TimeoutSec = 30
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = (Resolve-Path (Join-Path $scriptRoot "..")).Path
$composeFile = Join-Path $backendRoot "docker-compose.yaml"

function Write-Step {
    param([string]$Message)
    Write-Output "==> $Message"
}

if ($RemoveContainers) {
    $args = @("compose", "-f", $composeFile, "down")
    if ($RemoveOrphans) {
        $args += "--remove-orphans"
    }

    Write-Step "removing rag compose containers"
    & docker @args
    Write-Output "Shared external volumes were preserved."
    exit 0
}

Write-Step "stopping rag compose services"
& docker "compose" "-f" $composeFile "stop" "--timeout" $TimeoutSec
Write-Output "Containers are stopped but preserved. Use start-rag-stack.ps1 to bring them back."
