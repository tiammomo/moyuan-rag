#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from typing import Any


TOPICS = [
    "rag.document.upload.dlq",
    "rag.document.parsed.dlq",
    "rag.document.chunks.dlq",
]


def run_docker(args: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["docker", *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        input=input_text,
        capture_output=True,
        check=False,
    )
    return result


def fetch_messages(topic: str, max_messages: int, timeout_seconds: int) -> list[str]:
    fetch_command = (
        f"timeout {timeout_seconds} kafka-console-consumer "
        f"--bootstrap-server localhost:29092 "
        f"--topic {topic} --from-beginning --max-messages {max_messages} 2>/dev/null"
    )
    result = run_docker(["exec", "rag-kafka", "bash", "-lc", fetch_command])
    if result.returncode not in (0, 124):
        raise RuntimeError(f"Failed to read topic {topic} from rag-kafka: {result.stderr.strip()}")
    return [line for line in result.stdout.splitlines() if line.strip()]


def fetch_message_at_offset(topic: str, partition: int, offset: int) -> str:
    fetch_command = (
        "timeout 10 kafka-console-consumer "
        "--bootstrap-server localhost:29092 "
        f"--topic {topic} --partition {partition} --offset {offset} --max-messages 1 2>/dev/null"
    )
    result = run_docker(["exec", "rag-kafka", "bash", "-lc", fetch_command])
    if result.returncode not in (0, 124):
        raise RuntimeError(
            f"Failed to read DLQ message from {topic} partition {partition} offset {offset}: {result.stderr.strip()}"
        )
    if not result.stdout.strip():
        raise RuntimeError(f"No DLQ message found at {topic} partition {partition} offset {offset}")
    return result.stdout.strip()


def show_messages(topic: str, max_messages: int, timeout_seconds: int, raw: bool) -> int:
    print(f"[kafka-dlq] Reading up to {max_messages} message(s) from {topic}", flush=True)
    messages = fetch_messages(topic, max_messages, timeout_seconds)
    if not messages:
        print(f"[kafka-dlq] No messages found in {topic}", flush=True)
        return 0

    if raw:
        for line in messages:
            print(line)
        return 0

    for line in messages:
        try:
            print(json.dumps(json.loads(line), indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            print(line)
    return 0


def replay_message(topic: str, partition: int, offset: int, dry_run: bool) -> int:
    raw_message = fetch_message_at_offset(topic, partition, offset)
    record = json.loads(raw_message)

    source_topic = record.get("source_topic")
    payload = record.get("payload")
    if not source_topic:
        raise RuntimeError("DLQ record is missing source_topic")
    if not payload:
        raise RuntimeError("DLQ record is missing payload")

    try:
        json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError("DLQ payload is not valid JSON and will not be replayed.") from exc

    if dry_run:
        print(json.dumps(record, indent=2, ensure_ascii=False))
        return 0

    payload_base64 = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    produce_command = (
        f"base64 -d | kafka-console-producer --bootstrap-server localhost:29092 --topic {source_topic} >/dev/null"
    )
    result = run_docker(
        ["exec", "-i", "rag-kafka", "bash", "-lc", produce_command],
        input_text=f"{payload_base64}\n",
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to replay message into {source_topic}: {result.stderr.strip()}")

    print(
        f"[replay-kafka-dlq] Replayed {topic} partition={partition} offset={offset} -> {source_topic}",
        flush=True,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect or replay Kafka DLQ records from the local rag-kafka container.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    show_parser = subparsers.add_parser("show", help="Read DLQ records.")
    show_parser.add_argument("--topic", choices=TOPICS, default=TOPICS[0])
    show_parser.add_argument("--max-messages", type=int, default=20)
    show_parser.add_argument("--timeout-seconds", type=int, default=10)
    show_parser.add_argument("--raw", action="store_true")

    replay_parser = subparsers.add_parser("replay", help="Replay a DLQ record back to its source topic.")
    replay_parser.add_argument("--topic", choices=TOPICS, required=True)
    replay_parser.add_argument("--partition", type=int, default=0)
    replay_parser.add_argument("--offset", type=int, required=True)
    replay_parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "show":
            return show_messages(args.topic, args.max_messages, args.timeout_seconds, args.raw)
        if args.command == "replay":
            return replay_message(args.topic, args.partition, args.offset, args.dry_run)
        parser.error(f"Unsupported command: {args.command}")
    except Exception as exc:  # noqa: BLE001
        print(f"[kafka-dlq] ERROR: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
