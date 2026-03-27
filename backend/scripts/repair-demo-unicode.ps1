param(
    [string]$BaseUrl = "http://localhost:38084/api/v1",
    [string]$Username = "readme_demo_0327",
    [string]$Password = "Demo123456!",
    [int]$RobotId = 0,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$backendRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $backendRoot ".venv\\Scripts\\python.exe"
if (-not (Test-Path $pythonPath)) {
    $pythonPath = "python"
}

$scriptPath = Join-Path $PSScriptRoot "repair_demo_unicode.py"
$arguments = @(
    $scriptPath,
    "--base-url", $BaseUrl,
    "--username", $Username,
    "--password", $Password
)

if ($RobotId -gt 0) {
    $arguments += @("--robot-id", $RobotId)
}

if ($DryRun) {
    $arguments += "--dry-run"
}

& $pythonPath @arguments
exit $LASTEXITCODE
