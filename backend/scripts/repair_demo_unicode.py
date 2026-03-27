#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


BASE_URL_DEFAULT = "http://localhost:38084/api/v1"
DEFAULT_USERNAME = "readme_demo_0327"
DEFAULT_PASSWORD = "Demo123456!"
DEFAULT_ROBOT_NAME = "README 截图机器人"
DEFAULT_ROBOT_DESCRIPTION = "用于 README 截图中的 MiniMax RAG 演示"
DEFAULT_ROBOT_PROMPT = (
    "你是 README 截图机器人，请基于知识库内容准确、简洁地回答用户问题，"
    "并优先给出与 RAG 工作流、混合检索和 MiniMax 接入相关的说明。"
)


@dataclass
class RepairSummary:
    robot_id: int
    sessions_updated: int
    sessions_deleted: int


def log(message: str) -> None:
    print(f"[repair-demo-unicode] {message}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repair corrupted demo robot text and session titles using UTF-8 safe API requests."
    )
    parser.add_argument("--base-url", default=BASE_URL_DEFAULT, help="API base URL.")
    parser.add_argument("--username", default=DEFAULT_USERNAME, help="Demo username.")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Demo password.")
    parser.add_argument("--robot-id", type=int, default=None, help="Target robot id. Defaults to the first robot.")
    parser.add_argument("--robot-name", default=DEFAULT_ROBOT_NAME, help="Robot name after repair.")
    parser.add_argument("--robot-description", default=DEFAULT_ROBOT_DESCRIPTION, help="Robot description after repair.")
    parser.add_argument("--robot-prompt", default=DEFAULT_ROBOT_PROMPT, help="Robot system prompt after repair.")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without mutating data.")
    return parser.parse_args()


def request_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
) -> Any:
    headers = {"Accept": "application/json"}
    data = None

    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            if not raw:
                return None
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method.upper()} {url} failed: {exc.code} {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method.upper()} {url} failed: {exc}") from exc


def is_placeholder_text(text: str | None) -> bool:
    if not text:
        return False
    stripped = text.strip()
    if not stripped:
        return False
    question_count = stripped.count("?")
    if question_count >= max(3, len(stripped) // 3):
        return True
    return "\ufffd" in stripped


def derive_title_from_messages(messages: list[dict[str, Any]]) -> str | None:
    for message in messages:
        if message.get("role") != "user":
            continue

        content = (message.get("content") or "").strip()
        if not content:
            continue
        if is_placeholder_text(content):
            return None

        candidate = content[:50]
        if len(content) > 50:
            candidate += "..."
        return candidate

    return None


def choose_robot(robots: list[dict[str, Any]], robot_id: int | None) -> dict[str, Any]:
    if not robots:
        raise RuntimeError("No robots found for the demo account.")

    if robot_id is None:
        return robots[0]

    for robot in robots:
        if int(robot["id"]) == robot_id:
            return robot

    raise RuntimeError(f"Robot {robot_id} was not found for the demo account.")


def repair_demo_content(args: argparse.Namespace) -> RepairSummary:
    log(f"logging in as {args.username}")
    login_payload = {"username": args.username, "password": args.password}
    login_result = request_json("POST", f"{args.base_url}/auth/login", payload=login_payload)
    token = login_result["access_token"]

    robots = request_json("GET", f"{args.base_url}/robots", token=token)["items"]
    robot = choose_robot(robots, args.robot_id)
    robot_id = int(robot["id"])
    log(f"target robot_id={robot_id}")

    robot_update_payload = {
        "name": args.robot_name,
        "system_prompt": args.robot_prompt,
        "description": args.robot_description,
    }
    if args.dry_run:
        log(f"would update robot {robot_id} -> {robot_update_payload['name']}")
    else:
        request_json("PUT", f"{args.base_url}/robots/{robot_id}", payload=robot_update_payload, token=token)
        log(f"updated robot {robot_id} name/prompt/description")

    sessions_response = request_json(
        "GET",
        f"{args.base_url}/chat/sessions?{urllib.parse.urlencode({'robot_id': robot_id, 'status_filter': 'active'})}",
        token=token,
    )
    sessions = sessions_response["sessions"]

    sessions_updated = 0
    sessions_deleted = 0

    for session in sessions:
        title = session.get("title") or ""
        if not is_placeholder_text(title):
            continue

        session_id = session["session_id"]
        detail = request_json("GET", f"{args.base_url}/chat/sessions/{session_id}", token=token)
        messages = detail.get("messages", [])
        recovered_title = derive_title_from_messages(messages)

        if recovered_title:
            if args.dry_run:
                log(f"would update session {session_id} title -> {recovered_title}")
            else:
                request_json(
                    "PUT",
                    f"{args.base_url}/chat/sessions/{session_id}",
                    payload={"title": recovered_title},
                    token=token,
                )
                log(f"updated session {session_id} title -> {recovered_title}")
            sessions_updated += 1
        else:
            if args.dry_run:
                log(f"would delete unrecoverable session {session_id}")
            else:
                request_json("DELETE", f"{args.base_url}/chat/sessions/{session_id}", token=token)
                log(f"deleted unrecoverable session {session_id}")
            sessions_deleted += 1

    return RepairSummary(
        robot_id=robot_id,
        sessions_updated=sessions_updated,
        sessions_deleted=sessions_deleted,
    )


def main() -> int:
    args = parse_args()
    try:
        summary = repair_demo_content(args)
    except Exception as exc:  # noqa: BLE001
        print(f"[repair-demo-unicode] error: {exc}", file=sys.stderr)
        return 1

    log(
        "completed "
        f"(robot_id={summary.robot_id}, sessions_updated={summary.sessions_updated}, "
        f"sessions_deleted={summary.sessions_deleted})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
