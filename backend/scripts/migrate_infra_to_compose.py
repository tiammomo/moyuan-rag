#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_ROOT.parent
DEFAULT_COMPOSE_FILE = BACKEND_ROOT / "docker-compose.yaml"
DEFAULT_HELPER_IMAGE = "docker.m.daocloud.io/library/alpine:3.20"

APP_SERVICES = ["backend", "parser", "splitter", "vectorizer", "recall", "front"]
SOURCE_CONTAINERS = [
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
]

MAPPINGS = [
    {"name": "MySQL data", "container": "rag-mysql8", "source_path": "/var/lib/mysql", "target_volume": "rag-mysql-data"},
    {"name": "Elasticsearch data", "container": "rag-es7", "source_path": "/usr/share/elasticsearch/data", "target_volume": "rag-es-data"},
    {"name": "etcd data", "container": "rag-etcd", "source_path": "/etcd", "target_volume": "rag-etcd-data"},
    {"name": "MinIO data", "container": "rag-minio", "source_path": "/data", "target_volume": "rag-minio-data"},
    {"name": "Milvus data", "container": "rag-milvus", "source_path": "/var/lib/milvus", "target_volume": "rag-milvus-data"},
    {"name": "Redis data", "container": "rag-redis", "source_path": "/data", "target_volume": "rag-redis-data"},
    {"name": "Zookeeper data", "container": "rag-zookeeper", "source_path": "/var/lib/zookeeper/data", "target_volume": "rag-zookeeper-data"},
    {"name": "Zookeeper log", "container": "rag-zookeeper", "source_path": "/var/lib/zookeeper/log", "target_volume": "rag-zookeeper-log"},
    {"name": "Zookeeper secrets", "container": "rag-zookeeper", "source_path": "/etc/zookeeper/secrets", "target_volume": "rag-zookeeper-secrets"},
    {"name": "Kafka data", "container": "rag-kafka", "source_path": "/var/lib/kafka/data", "target_volume": "rag-kafka-data"},
    {"name": "Kafka secrets", "container": "rag-kafka", "source_path": "/etc/kafka/secrets", "target_volume": "rag-kafka-secrets"},
]


class MigrationError(RuntimeError):
    """Raised when infra migration fails."""


def log_step(message: str) -> None:
    print(f"==> {message}", flush=True)


def run_command(args: list[str], *, capture_output: bool = False, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=capture_output,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() if result.stderr else ""
        raise MigrationError(
            f"Command failed ({result.returncode}): {' '.join(args)}" + (f"\n{stderr}" if stderr else "")
        )
    return result


def run_docker(args: list[str], *, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return run_command(["docker", *args], capture_output=capture_output)


def container_exists(name: str, *, running_only: bool = False) -> bool:
    args = ["ps"]
    if not running_only:
        args.append("-a")
    args.extend(["--filter", f"name=^{name}$", "--format", "{{.Names}}"])
    result = run_docker(args, capture_output=True)
    return any(line.strip() == name for line in result.stdout.splitlines())


def volume_exists(name: str) -> bool:
    result = run_docker(["volume", "ls", "--filter", f"name=^{name}$", "--format", "{{.Name}}"], capture_output=True)
    return any(line.strip() == name for line in result.stdout.splitlines())


def ensure_volume_exists(name: str) -> None:
    if volume_exists(name):
        return
    log_step(f"creating target volume {name}")
    run_docker(["volume", "create", name])


def volume_has_data(name: str, helper_image: str) -> bool:
    if not volume_exists(name):
        return False
    result = run_docker(
        ["run", "--rm", "-v", f"{name}:/to", helper_image, "sh", "-c", "find /to -mindepth 1 -print -quit"],
        capture_output=True,
    )
    return bool(result.stdout.strip())


def inspect_container(container: str) -> list[dict[str, Any]]:
    result = run_docker(["inspect", container], capture_output=True)
    payload = json.loads(result.stdout)
    if not isinstance(payload, list):
        raise MigrationError(f"Unexpected inspect payload for container {container}")
    return [item for item in payload if isinstance(item, dict)]


def get_container_mount_info(container: str, destination: str) -> dict[str, Any] | None:
    inspect_payload = inspect_container(container)
    if not inspect_payload:
        return None
    for mount in inspect_payload[0].get("Mounts") or []:
        if mount.get("Destination") == destination:
            return mount
    return None


def resolve_migration_source(mapping: dict[str, str]) -> dict[str, Any]:
    if not container_exists(mapping["container"]):
        return {"exists": False, "kind": "missing", "reference": "", "summary": "container not found"}

    mount = get_container_mount_info(mapping["container"], mapping["source_path"])
    if mount and mount.get("Type") == "volume" and mount.get("Name"):
        return {
            "exists": True,
            "kind": "volume",
            "reference": str(mount["Name"]),
            "summary": f"volume:{mount['Name']}",
        }

    return {
        "exists": True,
        "kind": "container",
        "reference": mapping["source_path"],
        "summary": f"container-path:{mapping['source_path']}",
    }


def source_size(mapping: dict[str, str], source: dict[str, Any], helper_image: str) -> str:
    if not source["exists"]:
        return "missing"
    if source["kind"] == "volume":
        result = run_docker(
            ["run", "--rm", "-v", f"{source['reference']}:/from", helper_image, "sh", "-c", "du -sh /from 2>/dev/null | awk '{print $1}'"],
            capture_output=True,
        )
        return result.stdout.strip() or "unknown"

    result = run_docker(
        ["exec", mapping["container"], "sh", "-c", f"du -sh '{mapping['source_path']}' 2>/dev/null | awk '{{print $1}}'"],
        capture_output=True,
    )
    return result.stdout.strip() or "unknown"


def clear_volume(target_volume: str, helper_image: str) -> None:
    log_step(f"clearing existing data in {target_volume}")
    run_docker(
        [
            "run",
            "--rm",
            "-v",
            f"{target_volume}:/to",
            helper_image,
            "sh",
            "-c",
            "rm -rf /to/* /to/.[!.]* /to/..?* 2>/dev/null || true",
        ]
    )


def copy_volume_to_volume(source_volume: str, target_volume: str, helper_image: str) -> None:
    run_docker(
        [
            "run",
            "--rm",
            "-v",
            f"{source_volume}:/from",
            "-v",
            f"{target_volume}:/to",
            helper_image,
            "sh",
            "-c",
            "cp -a /from/. /to/",
        ]
    )


def copy_container_path_to_volume(container: str, source_path: str, target_volume: str, helper_image: str) -> None:
    temp_dir = Path(tempfile.mkdtemp(prefix="rag-migrate-"))
    try:
        run_docker(["cp", f"{container}:{source_path}/.", str(temp_dir)])
        run_docker(
            [
                "run",
                "--rm",
                "-v",
                f"{target_volume}:/to",
                "-v",
                f"{temp_dir}:/from",
                helper_image,
                "sh",
                "-c",
                "cp -a /from/. /to/",
            ]
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def stop_compose_app_services(compose_file: Path) -> None:
    log_step("stopping compose app services")
    run_docker(["compose", "-f", str(compose_file), "stop", *APP_SERVICES])


def stop_source_containers() -> None:
    log_step("stopping standalone dependency containers")
    for container in SOURCE_CONTAINERS:
        if container_exists(container, running_only=True):
            run_docker(["stop", container])


def remove_source_containers() -> None:
    log_step("removing standalone dependency containers so compose can take ownership")
    for container in SOURCE_CONTAINERS:
        if container_exists(container):
            run_docker(["rm", container])


def start_compose_stack(compose_file: Path) -> None:
    log_step("starting compose-managed full stack")
    run_docker(["compose", "-f", str(compose_file), "up", "-d"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate standalone infra containers into compose-managed external volumes.")
    parser.add_argument("--compose-file", default=str(DEFAULT_COMPOSE_FILE))
    parser.add_argument("--helper-image", default=DEFAULT_HELPER_IMAGE)
    parser.add_argument("--cutover", action="store_true", help="Execute the migration instead of only printing the plan.")
    parser.add_argument("--force", action="store_true", help="Allow overwriting target volumes that already contain data.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    compose_file = Path(args.compose_file).resolve()

    log_step(f"compose file: {compose_file}")
    log_step(f"helper image: {args.helper_image}")

    resolved_mappings: list[dict[str, Any]] = []
    for mapping in MAPPINGS:
        source = resolve_migration_source(mapping)
        resolved = {
            "name": mapping["name"],
            "container": mapping["container"],
            "source_path": mapping["source_path"],
            "source_kind": source["kind"],
            "source_reference": source["reference"],
            "source_summary": source["summary"],
            "source_size": source_size(mapping, source, args.helper_image),
            "target_volume": mapping["target_volume"],
            "target_exists": volume_exists(mapping["target_volume"]),
            "target_has_data": volume_has_data(mapping["target_volume"], args.helper_image),
        }
        resolved_mappings.append(resolved)

    log_step("migration plan")
    for item in resolved_mappings:
        print(
            f"- {item['name']}: "
            f"source={item['source_summary']}, size={item['source_size']}, "
            f"target={item['target_volume']}, target_exists={item['target_exists']}, "
            f"target_has_data={item['target_has_data']}"
        )

    if not args.cutover:
        log_step("plan mode only; no containers or volumes were changed")
        return 0

    log_step("cutover mode requested")
    for item in resolved_mappings:
        if item["target_has_data"] and not args.force:
            raise MigrationError(
                f"target volume {item['target_volume']} already has data; rerun with --force after verifying it is safe to overwrite"
            )

    stop_compose_app_services(compose_file)
    stop_source_containers()

    for item in resolved_mappings:
        if item["source_kind"] == "missing":
            log_step(f"skipping {item['name']} because source container is missing")
            continue

        ensure_volume_exists(item["target_volume"])
        if volume_has_data(item["target_volume"], args.helper_image) and args.force:
            clear_volume(item["target_volume"], args.helper_image)

        log_step(f"copying {item['name']} into {item['target_volume']}")
        if item["source_kind"] == "volume":
            copy_volume_to_volume(item["source_reference"], item["target_volume"], args.helper_image)
        else:
            copy_container_path_to_volume(
                item["container"],
                item["source_path"],
                item["target_volume"],
                args.helper_image,
            )

    remove_source_containers()
    start_compose_stack(compose_file)
    log_step("cutover completed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MigrationError as exc:
        print(f"[migrate-infra-to-compose] ERROR: {exc}", flush=True)
        raise SystemExit(1)
