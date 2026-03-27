#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_ROOT.parent
REPO_ROOT = BACKEND_ROOT.parent
ENV_FILE = BACKEND_ROOT / ".env"
LOG_DIR = BACKEND_ROOT / "run-logs"
RUN_SCRIPT = SCRIPT_ROOT / "run_local_integration.py"
RAG_STACK_SCRIPT = SCRIPT_ROOT / "rag_stack.py"
BACKEND_HEALTH_URL = "http://localhost:38084/health"


def log_step(message: str) -> None:
    print(f"==> {message}", flush=True)


def detect_backend_health() -> bool:
    try:
        with urllib.request.urlopen(BACKEND_HEALTH_URL, timeout=5) as response:
            return 200 <= response.status < 300
    except (urllib.error.HTTPError, urllib.error.URLError):
        return False


def wait_backend_health(timeout_sec: int, process: subprocess.Popen[str] | None = None) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if detect_backend_health():
            return
        if process is not None and process.poll() is not None:
            raise RuntimeError(f"backend process exited early with code {process.returncode}")
        time.sleep(1)
    raise RuntimeError(f"backend health check did not pass within {timeout_sec} seconds")


def wait_tcp_port(name: str, host: str, port: int, timeout_sec: int = 120) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.settimeout(1.0)
            try:
                client.connect((host, port))
                return
            except OSError:
                time.sleep(1)
    raise RuntimeError(f"{name} on {host}:{port} did not become reachable within {timeout_sec} seconds")


def get_bootstrap_python() -> list[str]:
    python_bin = shutil.which("python")
    if python_bin:
        return [python_bin]
    py_launcher = shutil.which("py")
    if py_launcher:
        return [py_launcher, "-3"]
    raise RuntimeError("python or py was not found in PATH.")


def get_venv_python() -> Path:
    windows_python = BACKEND_ROOT / ".venv" / "Scripts" / "python.exe"
    posix_python = BACKEND_ROOT / ".venv" / "bin" / "python"
    if windows_python.exists():
        return windows_python
    if posix_python.exists():
        return posix_python
    return windows_python


def ensure_venv() -> bool:
    venv_python = get_venv_python()
    if venv_python.exists():
        return False

    log_step("creating backend virtual environment")
    uv_bin = shutil.which("uv")
    if uv_bin:
        result = subprocess.run([uv_bin, "venv", ".venv"], cwd=BACKEND_ROOT, check=False)
        if result.returncode != 0:
            raise RuntimeError("uv venv .venv failed")
        return True

    bootstrap = get_bootstrap_python()
    result = subprocess.run([*bootstrap, "-m", "venv", ".venv"], cwd=BACKEND_ROOT, check=False)
    if result.returncode != 0:
        raise RuntimeError("python -m venv .venv failed")
    return True


def install_dependencies(venv_python: Path) -> None:
    log_step("installing backend dependencies")
    result = subprocess.run(
        [str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=BACKEND_ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("pip install -r requirements.txt failed")


def start_background_python(
    venv_python: Path,
    *,
    name: str,
    arguments: list[str],
    started_processes: list[subprocess.Popen[str]],
) -> subprocess.Popen[str]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stdout_path = LOG_DIR / f"{name}.out.log"
    stderr_path = LOG_DIR / f"{name}.err.log"
    stdout_handle = stdout_path.open("w", encoding="utf-8")
    stderr_handle = stderr_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [str(venv_python), *arguments],
        cwd=BACKEND_ROOT,
        stdout=stdout_handle,
        stderr=stderr_handle,
        text=True,
    )
    process._stdout_handle = stdout_handle  # type: ignore[attr-defined]
    process._stderr_handle = stderr_handle  # type: ignore[attr-defined]
    started_processes.append(process)
    time.sleep(2)
    if process.poll() is not None:
        raise RuntimeError(f"{name} exited early with code {process.returncode}. Check {stderr_path}")
    return process


def close_process_handles(process: subprocess.Popen[str]) -> None:
    for attr in ("_stdout_handle", "_stderr_handle"):
        handle = getattr(process, attr, None)
        if handle is not None:
            try:
                handle.close()
            except Exception:  # noqa: BLE001
                pass


def show_recent_log(path: Path) -> None:
    if not path.exists():
        return
    print(f"---- {path} ----")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[-40:]:
        print(line)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cross-platform wrapper that prepares local dependencies and runs the integration scenario."
    )
    parser.add_argument("--upload-file", default=str(REPO_ROOT / "docs" / "optimization-roadmap.md"))
    parser.add_argument("--start-infra", action="store_true", help="Start the docker compose stack before the integration run.")
    parser.add_argument("--compose-build", action="store_true", help="Build images when starting the compose stack.")
    parser.add_argument("--sync-deps", action="store_true", help="Run pip install -r requirements.txt before the scenario.")
    parser.add_argument("--stop-started-processes", action="store_true", help="Stop any local backend/worker processes started by this wrapper.")
    parser.add_argument("--health-timeout-sec", type=int, default=120)
    parser.add_argument("--poll-timeout-sec", type=int, default=180)
    parser.add_argument("--base-url", default="http://localhost:38084/api/v1")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_processes: list[subprocess.Popen[str]] = []
    backend_process: subprocess.Popen[str] | None = None

    try:
        if not ENV_FILE.exists():
            raise RuntimeError("backend/.env is required. Create it from backend/.env.example first.")

        upload_path = Path(args.upload_file).resolve()
        if not upload_path.exists():
            raise RuntimeError(f"upload file does not exist: {upload_path}")

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        ensure_venv_created = ensure_venv()
        venv_python = get_venv_python()
        if args.sync_deps or ensure_venv_created:
            install_dependencies(venv_python)

        if args.start_infra:
            stack_args = [sys.executable, str(RAG_STACK_SCRIPT), "start", "--health-timeout-sec", str(args.health_timeout_sec)]
            if args.compose_build:
                stack_args.append("--build")
            result = subprocess.run(stack_args, cwd=REPO_ROOT, check=False)
            if result.returncode != 0:
                raise RuntimeError("failed to start compose infrastructure")
        else:
            log_step("running alembic upgrade head")
            alembic_result = subprocess.run(
                [str(venv_python), "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
                cwd=BACKEND_ROOT,
                check=False,
            )
            if alembic_result.returncode != 0:
                raise RuntimeError("alembic upgrade head failed")

            if not detect_backend_health():
                log_step("starting backend api")
                backend_process = start_background_python(
                    venv_python,
                    name="integration-backend",
                    arguments=["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "38084"],
                    started_processes=started_processes,
                )
                wait_backend_health(args.health_timeout_sec, backend_process)

                for name, module in (
                    ("integration-parser", "app.workers.parser"),
                    ("integration-splitter", "app.workers.splitter"),
                    ("integration-vectorizer", "app.workers.vectorizer"),
                ):
                    log_step(f"starting {module}")
                    start_background_python(
                        venv_python,
                        name=name,
                        arguments=["-m", module],
                        started_processes=started_processes,
                    )
            else:
                log_step("backend api is already healthy")

        wait_tcp_port("MySQL", "127.0.0.1", 3306)
        wait_tcp_port("Redis", "127.0.0.1", 6379)
        wait_tcp_port("Elasticsearch", "127.0.0.1", 9200)
        wait_tcp_port("Milvus", "127.0.0.1", 19530)
        wait_tcp_port("Kafka", "127.0.0.1", 9094)
        wait_backend_health(args.health_timeout_sec, backend_process)

        venv_python = get_venv_python()
        if not venv_python.exists():
            raise RuntimeError("backend virtual environment is missing. Run with --sync-deps or create backend/.venv first.")

        log_step("running local integration scenario")
        scenario_result = subprocess.run(
            [
                str(venv_python),
                str(RUN_SCRIPT),
                "--base-url",
                args.base_url,
                "--upload-file",
                str(upload_path),
                "--poll-timeout",
                str(args.poll_timeout_sec),
            ],
            cwd=BACKEND_ROOT,
            check=False,
        )
        if scenario_result.returncode != 0:
            raise RuntimeError("local integration scenario failed")

        log_step("integration finished")
        print("Logs:")
        print(f"  {LOG_DIR / 'integration-backend.err.log'}")
        print(f"  {LOG_DIR / 'integration-parser.err.log'}")
        print(f"  {LOG_DIR / 'integration-splitter.err.log'}")
        print(f"  {LOG_DIR / 'integration-vectorizer.err.log'}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[local-integration] ERROR: {exc}", file=sys.stderr, flush=True)
        for log_name in (
            "integration-backend.err.log",
            "integration-parser.err.log",
            "integration-splitter.err.log",
            "integration-vectorizer.err.log",
        ):
            show_recent_log(LOG_DIR / log_name)
        return 1
    finally:
        if args.stop_started_processes:
            log_step("stopping processes started by this script")
            for process in started_processes:
                if process.poll() is None:
                    process.terminate()
            for process in started_processes:
                close_process_handles(process)
        else:
            for process in started_processes:
                close_process_handles(process)


if __name__ == "__main__":
    raise SystemExit(main())
