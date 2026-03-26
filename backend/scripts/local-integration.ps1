param(
    [string]$UploadFile = "",
    [switch]$StartInfra,
    [switch]$SyncDeps,
    [switch]$StopStartedProcesses,
    [int]$HealthTimeoutSec = 120,
    [int]$PollTimeoutSec = 180
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = (Resolve-Path (Join-Path $scriptRoot "..")).Path
$repoRoot = (Resolve-Path (Join-Path $backendRoot "..")).Path
$venvPython = Join-Path $backendRoot ".venv\Scripts\python.exe"
$envFile = Join-Path $backendRoot ".env"
$logDir = Join-Path $backendRoot "run-logs"
$ensureNetworkScript = Join-Path $scriptRoot "ensure-rag-network.ps1"
$ensureVolumesScript = Join-Path $scriptRoot "ensure-rag-volumes.ps1"
$startedProcesses = @()

function Write-Step {
    param([string]$Message)
    Write-Output "==> $Message"
}

function Get-BootstrapPython {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return @($python.Source)
    }

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return @($py.Source, "-3")
    }

    throw "python or py was not found in PATH."
}

function Ensure-Venv {
    if (Test-Path $venvPython) {
        return $false
    }

    Write-Step "creating backend virtual environment"
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($uv) {
        & $uv.Source "venv" ".venv"
        return $true
    }

    $bootstrap = Get-BootstrapPython
    $bootstrapExe = $bootstrap[0]
    $bootstrapArgs = @()
    if ($bootstrap.Length -gt 1) {
        $bootstrapArgs += $bootstrap[1..($bootstrap.Length - 1)]
    }
    $bootstrapArgs += @("-m", "venv", ".venv")
    & $bootstrapExe @bootstrapArgs
    return $true
}

function Install-Dependencies {
    Write-Step "installing backend dependencies"
    & $venvPython "-m" "pip" "install" "-r" "requirements.txt"
}

function Test-BackendHealth {
    try {
        $response = Invoke-RestMethod "http://localhost:8000/health" -TimeoutSec 5
        return $response.status -eq "healthy"
    } catch {
        return $false
    }
}

function Wait-BackendHealth {
    param(
        [int]$TimeoutSec,
        $BackendProcess
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-BackendHealth) {
            return
        }

        if ($BackendProcess -and $BackendProcess.HasExited) {
            throw "backend process exited early with code $($BackendProcess.ExitCode)"
        }

        Start-Sleep -Seconds 1
    }

    throw "backend health check did not pass within $TimeoutSec seconds"
}

function Test-TcpPort {
    param(
        [string]$HostName,
        [int]$Port
    )

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(1000, $false)) {
            return $false
        }
        $client.EndConnect($async) | Out-Null
        return $true
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

function Wait-TcpPort {
    param(
        [string]$Name,
        [string]$HostName,
        [int]$Port,
        [int]$TimeoutSec = 120
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-TcpPort -HostName $HostName -Port $Port) {
            return
        }
        Start-Sleep -Seconds 1
    }

    throw "$Name on $HostName`:$Port did not become reachable within $TimeoutSec seconds"
}

function Test-PythonModuleRunning {
    param([string]$Module)

    $pattern = [regex]::Escape($Module)
    $processes = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match "^python" -and $_.CommandLine -match $pattern
    }
    return ($processes | Measure-Object).Count -gt 0
}

function Start-BackgroundPython {
    param(
        [string]$Name,
        [string[]]$Arguments
    )

    $stdout = Join-Path $logDir "$Name.out.log"
    $stderr = Join-Path $logDir "$Name.err.log"
    $process = Start-Process `
        -FilePath $venvPython `
        -ArgumentList $Arguments `
        -WorkingDirectory $backendRoot `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -PassThru

    $script:startedProcesses += $process
    Start-Sleep -Seconds 2
    if ($process.HasExited) {
        throw "$Name exited early with code $($process.ExitCode). Check $stderr"
    }

    return $process
}

function Show-RecentLog {
    param([string]$Path)

    if (Test-Path $Path) {
        Write-Output "---- $Path ----"
        Get-Content $Path -Tail 40
    }
}

try {
    if (-not (Test-Path $envFile)) {
        throw "backend/.env is required. Create it from backend/.env.example and set safe local secrets first."
    }

    if (-not $UploadFile) {
        $UploadFile = Join-Path $repoRoot "docs\optimization-roadmap.md"
    }

    if (-not (Test-Path $UploadFile)) {
        throw "upload file does not exist: $UploadFile"
    }

    New-Item -ItemType Directory -Force -Path $logDir | Out-Null

    if ($StartInfra) {
        if (Test-Path $ensureNetworkScript) {
            Write-Step "ensuring docker network rag-net"
            & powershell "-ExecutionPolicy" "Bypass" "-File" $ensureNetworkScript
        }

        if (Test-Path $ensureVolumesScript) {
            Write-Step "ensuring docker volumes for compose"
            & powershell "-ExecutionPolicy" "Bypass" "-File" $ensureVolumesScript
        }

        Write-Step "starting docker compose infrastructure"
        & docker "compose" "-f" (Join-Path $backendRoot "docker-compose.yaml") "up" "-d"
        Wait-TcpPort -Name "MySQL" -HostName "127.0.0.1" -Port 3306
        Wait-TcpPort -Name "Redis" -HostName "127.0.0.1" -Port 6379
        Wait-TcpPort -Name "Elasticsearch" -HostName "127.0.0.1" -Port 9200
        Wait-TcpPort -Name "Milvus" -HostName "127.0.0.1" -Port 19530
        Wait-TcpPort -Name "Kafka" -HostName "127.0.0.1" -Port 9094
    }

    Push-Location $backendRoot
    try {
        $venvCreated = Ensure-Venv
        if ($SyncDeps -or $venvCreated) {
            Install-Dependencies
        }

        Write-Step "running alembic upgrade head"
        & $venvPython "-m" "alembic" "-c" "alembic.ini" "upgrade" "head"

        $backendProcess = $null
        if (-not (Test-BackendHealth)) {
            Write-Step "starting backend api"
            $backendProcess = Start-BackgroundPython `
                -Name "integration-backend" `
                -Arguments @("-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000")
            Wait-BackendHealth -TimeoutSec $HealthTimeoutSec -BackendProcess $backendProcess
        } else {
            Write-Step "backend api is already healthy"
        }

        foreach ($worker in @(
            @{ Name = "integration-parser"; Module = "app.workers.parser" },
            @{ Name = "integration-splitter"; Module = "app.workers.splitter" },
            @{ Name = "integration-vectorizer"; Module = "app.workers.vectorizer" }
        )) {
            if (Test-PythonModuleRunning -Module $worker.Module) {
                Write-Step "$($worker.Module) is already running"
                continue
            }

            Write-Step "starting $($worker.Module)"
            Start-BackgroundPython -Name $worker.Name -Arguments @("-m", $worker.Module) | Out-Null
        }

        Write-Step "running local integration scenario"
        & $venvPython `
            (Join-Path $scriptRoot "run_local_integration.py") `
            "--upload-file" (Resolve-Path $UploadFile).Path `
            "--poll-timeout" $PollTimeoutSec

        Write-Step "integration finished"
        Write-Output "Logs:"
        Write-Output "  $(Join-Path $logDir 'integration-backend.err.log')"
        Write-Output "  $(Join-Path $logDir 'integration-parser.err.log')"
        Write-Output "  $(Join-Path $logDir 'integration-splitter.err.log')"
        Write-Output "  $(Join-Path $logDir 'integration-vectorizer.err.log')"
    } finally {
        Pop-Location
    }
} catch {
    Write-Output "local integration failed: $($_.Exception.Message)"
    Show-RecentLog -Path (Join-Path $logDir "integration-backend.err.log")
    Show-RecentLog -Path (Join-Path $logDir "integration-parser.err.log")
    Show-RecentLog -Path (Join-Path $logDir "integration-splitter.err.log")
    Show-RecentLog -Path (Join-Path $logDir "integration-vectorizer.err.log")
    throw
} finally {
    if ($StopStartedProcesses -and $startedProcesses.Count -gt 0) {
        Write-Step "stopping processes started by this script"
        $startedProcesses | ForEach-Object {
            if ($_ -and -not $_.HasExited) {
                Stop-Process -Id $_.Id -Force
            }
        }
    }
}
