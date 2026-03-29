#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_ROOT.parent
ENV_FILE = BACKEND_ROOT / ".env"


def get_venv_python() -> Path | None:
    windows_python = BACKEND_ROOT / ".venv" / "Scripts" / "python.exe"
    posix_python = BACKEND_ROOT / ".venv" / "bin" / "python"
    if windows_python.exists():
        return windows_python
    if posix_python.exists():
        return posix_python
    return None


def ensure_backend_python() -> None:
    try:
        import sqlalchemy  # noqa: F401
        return
    except ModuleNotFoundError:
        venv_python = get_venv_python()
        current_python = Path(sys.executable).resolve()
        if venv_python is None:
            raise RuntimeError(
                "sqlalchemy is not available in the current interpreter and backend/.venv was not found."
            )
        if current_python == venv_python.resolve():
            raise RuntimeError(
                "sqlalchemy is not available in backend/.venv. Install backend dependencies first."
            )
        os.execv(str(venv_python), [str(venv_python), __file__, *sys.argv[1:]])


def load_env_defaults(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env_defaults(ENV_FILE)
ensure_backend_python()

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import bcrypt  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from app.core.config import settings  # noqa: E402


class SmokeAdminError(RuntimeError):
    """Raised when smoke admin provisioning fails."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ensure the dedicated Playwright smoke admin exists with the expected credentials."
    )
    parser.add_argument("--username", default=os.environ.get("PLAYWRIGHT_SMOKE_USERNAME"))
    parser.add_argument("--email", default=os.environ.get("PLAYWRIGHT_SMOKE_EMAIL"))
    parser.add_argument("--password", default=os.environ.get("PLAYWRIGHT_SMOKE_PASSWORD"))
    parser.add_argument("--print-json", action="store_true")
    return parser.parse_args()


def resolve_credentials(args: argparse.Namespace) -> tuple[str, str, str]:
    username = (args.username or "").strip()
    password = args.password or ""
    email = (args.email or "").strip()

    if not username:
        raise SmokeAdminError(
            "Missing smoke admin username. Set PLAYWRIGHT_SMOKE_USERNAME or pass --username."
        )
    if not password:
        raise SmokeAdminError(
            "Missing smoke admin password. Set PLAYWRIGHT_SMOKE_PASSWORD or pass --password."
        )
    if not email:
        email = f"{username}@example.com"

    return username, email, password


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def ensure_smoke_admin(username: str, email: str, password: str) -> dict[str, object]:
    engine = create_engine(settings.DATABASE_URL)
    password_hash = hash_password(password)

    try:
        with engine.begin() as connection:
            existing = connection.execute(
                text(
                    "SELECT id, username, email, role, status "
                    "FROM rag_user WHERE username = :username"
                ),
                {"username": username},
            ).mappings().first()

            if existing:
                connection.execute(
                    text(
                        "UPDATE rag_user "
                        "SET email = :email, password_hash = :password_hash, role = :role, status = :status "
                        "WHERE id = :user_id"
                    ),
                    {
                        "user_id": existing["id"],
                        "email": email,
                        "password_hash": password_hash,
                        "role": "admin",
                        "status": 1,
                    },
                )
                return {
                    "result": "ok",
                    "action": "updated",
                    "username": username,
                    "email": email,
                    "role": "admin",
                    "status": 1,
                    "user_id": int(existing["id"]),
                }

            insert_result = connection.execute(
                text(
                    "INSERT INTO rag_user (username, email, password_hash, role, status) "
                    "VALUES (:username, :email, :password_hash, :role, :status)"
                ),
                {
                    "username": username,
                    "email": email,
                    "password_hash": password_hash,
                    "role": "admin",
                    "status": 1,
                },
            )
            user_id = int(insert_result.lastrowid or 0)
            return {
                "result": "ok",
                "action": "created",
                "username": username,
                "email": email,
                "role": "admin",
                "status": 1,
                "user_id": user_id,
            }
    finally:
        engine.dispose()


def main() -> int:
    args = parse_args()
    username, email, password = resolve_credentials(args)
    payload = ensure_smoke_admin(username=username, email=email, password=password)

    if args.print_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(
            f"[ensure-smoke-admin] {payload['action']} admin "
            f"{payload['username']} ({payload['email']})"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SmokeAdminError as exc:
        print(f"[ensure-smoke-admin] ERROR: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)
