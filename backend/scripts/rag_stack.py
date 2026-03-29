#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
FRONTEND_ROOT = REPO_ROOT / "front"
COMPOSE_FILE = BACKEND_ROOT / "docker-compose.yaml"
NETWORK_NAME = "rag-net"
BACKEND_API_URL = "http://localhost:38084"
BACKEND_HEALTH_URL = "http://localhost:38084/health"
FRONT_URL = "http://localhost:33004"
KIBANA_URL = "http://localhost:5601"
KAFKA_UI_URL = "http://localhost:8080"
ATTU_URL = "http://localhost:8001"
PLAYWRIGHT_SMOKE_ROOT = FRONTEND_ROOT / "test-results" / "playwright-smoke" / "operator"
ENSURE_SMOKE_ADMIN_SCRIPT = BACKEND_ROOT / "scripts" / "ensure_smoke_admin.py"

NETWORK_CONTAINERS = [
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
    "rag-recall",
    "rag-front",
]

REQUIRED_VOLUMES = [
    "rag-mysql-data",
    "rag-es-data",
    "rag-kibana-logs",
    "rag-etcd-data",
    "rag-minio-data",
    "rag-milvus-data",
    "rag-redis-data",
    "rag-zookeeper-data",
    "rag-zookeeper-log",
    "rag-zookeeper-secrets",
    "rag-kafka-data",
    "rag-kafka-secrets",
]

KNOWN_SERVICES = [
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
    "recall",
    "front",
]

DEPENDENT_MAP = {
    "mysql8": ["backend", "parser", "splitter", "vectorizer", "recall", "front"],
    "es": ["backend", "parser", "splitter", "vectorizer", "recall", "front", "kibana"],
    "etcd": ["milvus-standalone", "attu", "backend", "parser", "splitter", "vectorizer", "recall", "front"],
    "minio": ["milvus-standalone", "backend", "parser", "splitter", "vectorizer", "recall", "front"],
    "milvus-standalone": ["attu", "backend", "parser", "splitter", "vectorizer", "recall", "front"],
    "redis": ["backend", "parser", "splitter", "vectorizer", "recall", "front"],
    "zookeeper": ["kafka", "kafka-ui", "backend", "parser", "splitter", "vectorizer", "recall", "front"],
    "kafka": ["kafka-ui", "backend", "parser", "splitter", "vectorizer", "recall", "front"],
    "backend": ["parser", "splitter", "vectorizer", "recall", "front"],
}

BASE_SERVICES = [
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
]

APP_SERVICES = ["parser", "splitter", "vectorizer", "recall", "front"]


class StackCommandError(RuntimeError):
    """Raised when a stack command fails."""


def log_step(message: str) -> None:
    print(f"==> {message}", flush=True)


def run_command(
    args: list[str],
    *,
    capture_output: bool = False,
    input_text: str | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=cwd or BACKEND_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        input=input_text,
        capture_output=capture_output,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() if result.stderr else ""
        raise StackCommandError(
            f"Command failed ({result.returncode}): {' '.join(args)}"
            + (f"\n{stderr}" if stderr else "")
        )
    return result


def run_docker(args: list[str], *, capture_output: bool = False, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return run_command(["docker", *args], capture_output=capture_output, input_text=input_text)


def run_frontend_command(args: list[str], *, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return run_command(args, capture_output=capture_output, cwd=FRONTEND_ROOT)


def npm_executable() -> str:
    return "npm.cmd" if sys.platform == "win32" else "npm"


def parse_json_lines(payload: str) -> list[dict[str, Any]]:
    raw = payload.strip()
    if not raw:
        return []
    if raw.startswith("["):
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        if isinstance(parsed, dict):
            return [parsed]
        return []
    rows: list[dict[str, Any]] = []
    for line in raw.splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue
        rows.append(json.loads(trimmed))
    return rows


def service_ports(service: dict[str, Any]) -> str:
    publishers = service.get("Publishers") or []
    if isinstance(publishers, list) and publishers:
        values = []
        for item in publishers:
            published = item.get("PublishedPort")
            target = item.get("TargetPort")
            url = item.get("URL") or ""
            protocol = item.get("Protocol") or ""
            if published and target:
                values.append(f"{url}:{published}->{target}/{protocol}".strip(":"))
        if values:
            return ", ".join(values)
    ports = service.get("Ports")
    if isinstance(ports, str):
        return ports
    return ""


def get_compose_services() -> list[dict[str, Any]]:
    result = run_docker(
        ["compose", "-f", str(COMPOSE_FILE), "ps", "--all", "--format", "json"],
        capture_output=True,
    )
    rows = parse_json_lines(result.stdout)
    services: list[dict[str, Any]] = []
    for row in rows:
        row["PortsSummary"] = service_ports(row)
        services.append(row)
    return services


def docker_network_exists(name: str) -> bool:
    result = run_docker(
        ["network", "ls", "--filter", f"name=^{name}$", "--format", "{{.Name}}"],
        capture_output=True,
    )
    return any(line.strip() == name for line in result.stdout.splitlines())


def docker_volume_exists(name: str) -> bool:
    result = run_docker(
        ["volume", "ls", "--filter", f"name=^{name}$", "--format", "{{.Name}}"],
        capture_output=True,
    )
    return any(line.strip() == name for line in result.stdout.splitlines())


def docker_container_exists(name: str, *, running_only: bool = False) -> bool:
    args = ["ps"]
    if not running_only:
        args.append("-a")
    args.extend(["--filter", f"name=^{name}$", "--format", "{{.Names}}"])
    result = run_docker(args, capture_output=True)
    return any(line.strip() == name for line in result.stdout.splitlines())


def network_members(name: str) -> list[str]:
    result = run_docker(["network", "inspect", name], capture_output=True)
    payload = json.loads(result.stdout)
    if not payload:
        return []
    containers = (payload[0] or {}).get("Containers") or {}
    members = []
    for item in containers.values():
        if isinstance(item, dict) and item.get("Name"):
            members.append(str(item["Name"]))
    return sorted(members)


def ensure_network(name: str = NETWORK_NAME) -> None:
    if not docker_network_exists(name):
        log_step(f"creating docker network {name}")
        run_docker(["network", "create", "--driver", "bridge", "--attachable", name])
    else:
        log_step(f"docker network {name} already exists")

    members = set(network_members(name))
    for container in NETWORK_CONTAINERS:
        if not docker_container_exists(container):
            log_step(f"skip {container} (container does not exist)")
            continue
        if container in members:
            log_step(f"{container} is already attached to {name}")
            continue
        log_step(f"connecting {container} to {name}")
        run_docker(["network", "connect", name, container])

    log_step(f"current members in {name}")
    for member in network_members(name):
        print(member)


def ensure_volumes() -> None:
    log_step("ensuring Docker volumes for rag compose stack")
    for volume in REQUIRED_VOLUMES:
        if docker_volume_exists(volume):
            continue
        print(f"   creating: {volume}")
        run_docker(["volume", "create", volume])
    log_step("volume check completed")


def wait_compose_service_ready(service: str, timeout_sec: int, require_healthy: bool = False) -> None:
    deadline = time.time() + timeout_sec
    last_status = "unknown"

    while time.time() < deadline:
        service_info = next((item for item in get_compose_services() if item.get("Service") == service), None)
        if service_info:
            last_status = str(service_info.get("Status") or "unknown")
            is_running = service_info.get("State") == "running"
            health = str(service_info.get("Health") or "")
            health_ok = (not require_healthy) or (not health) or health == "healthy"
            if is_running and health_ok:
                print(f"   ready: {service} -> {last_status}", flush=True)
                return
        time.sleep(2)

    raise StackCommandError(
        f"{service} did not become ready within {timeout_sec} seconds. Last compose status: {last_status}"
    )


def http_ok(url: str, timeout: int = 5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (urllib.error.HTTPError, urllib.error.URLError):
        return False


def wait_http_healthy(name: str, url: str, timeout_sec: int) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if http_ok(url):
            print(f"   healthy: {name} -> {url}", flush=True)
            return
        time.sleep(2)
    raise StackCommandError(f"{name} did not become healthy within {timeout_sec} seconds: {url}")


def timestamp_segment() -> str:
    return time.strftime("%Y%m%d-%H%M%S", time.localtime())


def copy_tree(source_dir: Path, destination_dir: Path) -> None:
    if destination_dir.exists():
        shutil.rmtree(destination_dir)
    shutil.copytree(source_dir, destination_dir)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2, ensure_ascii=False)}\n", encoding="utf-8")


def start_stack(build: bool, health_timeout_sec: int) -> None:
    ensure_network()
    ensure_volumes()

    compose_args = ["compose", "-f", str(COMPOSE_FILE), "up", "-d"]
    if build:
        compose_args.append("--build")

    log_step("starting rag compose infrastructure and backend")
    run_docker([*compose_args, *BASE_SERVICES])

    log_step("waiting for compose backend readiness")
    wait_compose_service_ready("backend", health_timeout_sec, require_healthy=True)

    log_step("starting rag compose app services")
    run_docker([*compose_args, *APP_SERVICES])

    log_step("waiting for compose frontend and workers")
    wait_compose_service_ready("front", health_timeout_sec, require_healthy=True)
    for service in ("parser", "splitter", "vectorizer", "recall"):
        wait_compose_service_ready(service, health_timeout_sec)

    log_step("waiting for backend and frontend health")
    wait_http_healthy("backend", BACKEND_HEALTH_URL, health_timeout_sec)
    wait_http_healthy("front", FRONT_URL, health_timeout_sec)

    log_step("rag stack is ready")
    print("Endpoints:")
    print("  backend: http://localhost:38084")
    print("  frontend: http://localhost:33004")
    print("  kibana: http://localhost:5601")
    print("  kafka-ui: http://localhost:8080")
    print("  attu: http://localhost:8001")


def run_playwright_smoke(
    *,
    base_url: str,
    api_url: str,
    username: str | None,
    password: str | None,
    email: str | None,
    output_root: Path,
    headed: bool,
    install_browser: bool,
    start_stack_first: bool,
    build: bool,
    health_timeout_sec: int,
    ensure_admin: bool,
) -> None:
    if start_stack_first:
        log_step("ensuring local rag stack is ready before Playwright smoke")
        start_stack(build=build, health_timeout_sec=health_timeout_sec)

    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = output_root / "runs" / timestamp_segment()
    latest_dir = output_root / "latest"
    latest_index_path = output_root / "latest-run.json"

    if install_browser:
        log_step("installing Playwright chromium browser")
        run_frontend_command([npm_executable(), "run", "smoke:playwright:install"])

    if ensure_admin:
        ensure_args = [sys.executable, str(ENSURE_SMOKE_ADMIN_SCRIPT)]
        if username:
            ensure_args.extend(["--username", username])
        if password:
            ensure_args.extend(["--password", password])
        if email:
            ensure_args.extend(["--email", email])
        log_step("ensuring dedicated Playwright smoke admin exists")
        run_command(ensure_args)

    smoke_args = [
        npm_executable(),
        "run",
        "smoke:playwright",
        "--",
        "--output-dir",
        str(run_dir),
        "--base-url",
        base_url,
        "--api-url",
        api_url,
    ]
    if username:
        smoke_args.extend(["--username", username])
    if password:
        smoke_args.extend(["--password", password])
    if headed:
        smoke_args.append("--headed")

    log_step("running Playwright smoke workflow")
    run_failed = False
    failure_message: str | None = None
    try:
        run_frontend_command(smoke_args)
    except StackCommandError as exc:
        run_failed = True
        failure_message = str(exc)

    summary_path = run_dir / "summary.json"
    summary_payload: dict[str, Any] = {}
    if summary_path.exists():
        copy_tree(run_dir, latest_dir)
        try:
            summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            summary_payload = {}

    latest_index = {
        "latest_run_dir": str(run_dir),
        "latest_summary_path": str(summary_path) if summary_path.exists() else None,
        "latest_artifact_dir": str(latest_dir) if latest_dir.exists() else None,
        "base_url": base_url,
        "api_url": api_url,
        "status": summary_payload.get("status") if summary_payload else ("failed" if run_failed else None),
    }
    write_json(latest_index_path, latest_index)

    print(f"Artifacts root: {output_root}")
    print(f"Latest run dir: {run_dir}")
    if latest_dir.exists():
        print(f"Latest artifact mirror: {latest_dir}")
    if summary_path.exists():
        print(f"Latest summary: {summary_path}")
    if summary_payload.get("steps"):
        print("Step results:")
        for step in summary_payload["steps"]:
            if not isinstance(step, dict):
                continue
            print(f"  - {step.get('name')}: {step.get('status')}")

    if run_failed:
        raise StackCommandError(failure_message or "Playwright smoke failed.")


def endpoint_status(name: str, url: str, compose_service: str, services: list[dict[str, Any]]) -> dict[str, Any]:
    service_info = next((item for item in services if item.get("Service") == compose_service), {})
    service_state = service_info.get("State")
    warning = None
    reachable = False
    status_code = None

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            reachable = True
            status_code = response.status
            if service_state != "running":
                warning = f"Endpoint reachable while compose service '{compose_service}' is not running."
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        if service_state == "running":
            warning = f"Endpoint returned {exc.code} while compose service '{compose_service}' is running."
    except urllib.error.URLError:
        if service_state == "running":
            warning = f"Endpoint is unreachable while compose service '{compose_service}' is running."

    return {
        "Name": name,
        "Url": url,
        "ComposeService": compose_service,
        "ServiceState": service_state,
        "Reachable": reachable,
        "StatusCode": status_code,
        "Warning": warning,
    }


def format_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "(no rows)"

    widths = {column: len(column) for column in columns}
    normalized: list[dict[str, str]] = []
    for row in rows:
        normalized_row: dict[str, str] = {}
        for column in columns:
            value = row.get(column, "")
            text = "" if value is None else str(value)
            normalized_row[column] = text
            widths[column] = max(widths[column], len(text))
        normalized.append(normalized_row)

    header = "  ".join(column.ljust(widths[column]) for column in columns)
    separator = "  ".join("-" * widths[column] for column in columns)
    body = [
        "  ".join(row[column].ljust(widths[column]) for column in columns)
        for row in normalized
    ]
    return "\n".join([header, separator, *body])


def print_status(json_output: bool) -> None:
    services = sorted(get_compose_services(), key=lambda item: str(item.get("Service", "")))
    endpoints = [
        endpoint_status("backend", BACKEND_HEALTH_URL, "backend", services),
        endpoint_status("front", FRONT_URL, "front", services),
        endpoint_status("kibana", KIBANA_URL, "kibana", services),
        endpoint_status("kafka-ui", KAFKA_UI_URL, "kafka-ui", services),
        endpoint_status("attu", ATTU_URL, "attu", services),
    ]
    summary = {
        "TotalServices": len(services),
        "RunningServices": sum(1 for item in services if item.get("State") == "running"),
        "HealthyServices": sum(1 for item in services if item.get("Health") == "healthy"),
        "NonRunningServices": [item.get("Service") for item in services if item.get("State") != "running"],
        "UnhealthyServices": [
            item.get("Service")
            for item in services
            if item.get("Health") not in (None, "", "healthy")
        ],
    }
    payload = {
        "Summary": summary,
        "Services": [
            {
                "Service": item.get("Service"),
                "Name": item.get("Name"),
                "State": item.get("State"),
                "Health": item.get("Health"),
                "Status": item.get("Status"),
                "Ports": item.get("PortsSummary"),
            }
            for item in services
        ],
        "Endpoints": endpoints,
    }

    if json_output:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    print("RAG Stack Summary")
    print(f"  services: {summary['RunningServices']}/{summary['TotalServices']} running")
    print(f"  healthy: {summary['HealthyServices']}")
    if summary["NonRunningServices"]:
        print(f"  non-running: {', '.join(summary['NonRunningServices'])}")
    if summary["UnhealthyServices"]:
        print(f"  unhealthy: {', '.join(summary['UnhealthyServices'])}")

    print()
    print("Services")
    print(
        format_table(
            payload["Services"],
            ["Service", "Name", "State", "Health", "Status", "Ports"],
        )
    )
    print()
    print("Endpoints")
    print(
        format_table(
            endpoints,
            ["Name", "ComposeService", "ServiceState", "Reachable", "StatusCode", "Warning", "Url"],
        )
    )


def normalize_services(raw_services: list[str]) -> list[str]:
    normalized: list[str] = []
    for item in raw_services:
        for value in item.split(","):
            candidate = value.strip()
            if candidate:
                normalized.append(candidate)
    return normalized


def expand_restart_targets(requested_services: list[str], include_dependents: bool) -> list[str]:
    targets: list[str] = []
    for service in requested_services:
        if service not in KNOWN_SERVICES:
            raise StackCommandError(f"Unknown compose service: {service}")

    for service in KNOWN_SERVICES:
        if service in requested_services and service not in targets:
            targets.append(service)
            continue
        if not include_dependents:
            continue
        for source in requested_services:
            if service in DEPENDENT_MAP.get(source, []) and service not in targets:
                targets.append(service)
                break
    return targets


def restart_services(requested_services: list[str], include_dependents: bool, health_timeout_sec: int) -> None:
    targets = expand_restart_targets(requested_services, include_dependents)
    if not targets:
        raise StackCommandError("No compose services selected for restart.")

    log_step(f"restarting compose services: {', '.join(targets)}")
    run_docker(["compose", "-f", str(COMPOSE_FILE), "restart", *targets])

    log_step("ensuring compose services are running")
    run_docker(["compose", "-f", str(COMPOSE_FILE), "up", "-d", *targets])

    log_step("waiting for compose services to become ready")
    for service in targets:
        requires_health = service in {"backend", "front", "kafka"}
        wait_compose_service_ready(service, health_timeout_sec, require_healthy=requires_health)

    if "backend" in targets:
        wait_http_healthy("backend", BACKEND_HEALTH_URL, health_timeout_sec)
    if "front" in targets:
        wait_http_healthy("front", FRONT_URL, health_timeout_sec)

    log_step("restart completed")


def show_logs(services: list[str], tail: int, follow: bool, show_all: bool) -> None:
    args = ["compose", "-f", str(COMPOSE_FILE), "logs", "--tail", str(tail)]
    if follow:
        args.append("--follow")
    normalized_services = normalize_services(services)
    if not show_all and normalized_services:
        args.extend(normalized_services)

    result = subprocess.run(["docker", *args], cwd=BACKEND_ROOT, check=False)
    if result.returncode != 0:
        raise StackCommandError(f"docker compose logs failed with exit code {result.returncode}")


def stop_stack(remove_containers: bool, remove_orphans: bool, timeout_sec: int) -> None:
    if remove_containers:
        args = ["compose", "-f", str(COMPOSE_FILE), "down"]
        if remove_orphans:
            args.append("--remove-orphans")
        log_step("removing rag compose containers")
        run_docker(args)
        print("Shared external volumes were preserved.")
        return

    log_step("stopping rag compose services")
    run_docker(["compose", "-f", str(COMPOSE_FILE), "stop", "--timeout", str(timeout_sec)])
    print("Containers are stopped but preserved. Use 'python backend/scripts/rag_stack.py start' to bring them back.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cross-platform operator CLI for the local RAG compose stack.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ensure_network_parser = subparsers.add_parser("ensure-network", help="Ensure docker network rag-net exists.")
    ensure_network_parser.add_argument("--network-name", default=NETWORK_NAME)

    subparsers.add_parser("ensure-volumes", help="Ensure external docker volumes exist.")

    start_parser = subparsers.add_parser("start", help="Start the local RAG stack.")
    start_parser.add_argument("--build", action="store_true", help="Rebuild images before startup.")
    start_parser.add_argument("--health-timeout-sec", type=int, default=180)

    status_parser = subparsers.add_parser("status", help="Show compose service and endpoint status.")
    status_parser.add_argument("--json", action="store_true", help="Emit JSON instead of a table.")

    logs_parser = subparsers.add_parser("logs", help="Show compose logs.")
    logs_parser.add_argument("--services", nargs="*", default=["backend", "front", "parser", "splitter", "vectorizer", "recall"])
    logs_parser.add_argument("--tail", type=int, default=200)
    logs_parser.add_argument("--follow", action="store_true")
    logs_parser.add_argument("--all", action="store_true", help="Show logs for all compose services.")

    restart_parser = subparsers.add_parser("restart", help="Restart one or more compose services.")
    restart_parser.add_argument("services", nargs="+")
    restart_parser.add_argument("--include-dependents", action="store_true")
    restart_parser.add_argument("--health-timeout-sec", type=int, default=180)

    smoke_parser = subparsers.add_parser("smoke", help="Run the frontend Playwright smoke workflow.")
    smoke_parser.add_argument("--base-url", default=FRONT_URL)
    smoke_parser.add_argument("--api-url", default=BACKEND_API_URL)
    smoke_parser.add_argument("--username")
    smoke_parser.add_argument("--password")
    smoke_parser.add_argument("--email")
    smoke_parser.add_argument("--headed", action="store_true")
    smoke_parser.add_argument("--install-browser", action="store_true")
    smoke_parser.add_argument("--start-stack", action="store_true")
    smoke_parser.add_argument("--build", action="store_true", help="Rebuild images when used with --start-stack.")
    smoke_parser.add_argument("--health-timeout-sec", type=int, default=180)
    smoke_parser.add_argument("--output-root", default=str(PLAYWRIGHT_SMOKE_ROOT))
    smoke_parser.add_argument("--ensure-admin", action="store_true")

    stop_parser = subparsers.add_parser("stop", help="Stop compose services or remove containers.")
    stop_parser.add_argument("--remove-containers", action="store_true")
    stop_parser.add_argument("--remove-orphans", action="store_true")
    stop_parser.add_argument("--timeout-sec", type=int, default=30)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "ensure-network":
            ensure_network(args.network_name)
        elif args.command == "ensure-volumes":
            ensure_volumes()
        elif args.command == "start":
            start_stack(build=args.build, health_timeout_sec=args.health_timeout_sec)
        elif args.command == "status":
            print_status(json_output=args.json)
        elif args.command == "logs":
            show_logs(args.services, tail=args.tail, follow=args.follow, show_all=args.all)
        elif args.command == "restart":
            restart_services(
                normalize_services(args.services),
                include_dependents=args.include_dependents,
                health_timeout_sec=args.health_timeout_sec,
            )
        elif args.command == "smoke":
            run_playwright_smoke(
                base_url=args.base_url,
                api_url=args.api_url,
                username=args.username,
                password=args.password,
                email=args.email,
                output_root=Path(args.output_root).resolve(),
                headed=args.headed,
                install_browser=args.install_browser,
                start_stack_first=args.start_stack,
                build=args.build,
                health_timeout_sec=args.health_timeout_sec,
                ensure_admin=args.ensure_admin,
            )
        elif args.command == "stop":
            stop_stack(
                remove_containers=args.remove_containers,
                remove_orphans=args.remove_orphans,
                timeout_sec=args.timeout_sec,
            )
        else:
            parser.error(f"Unsupported command: {args.command}")
    except StackCommandError as exc:
        print(f"[rag-stack] ERROR: {exc}", file=sys.stderr, flush=True)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
