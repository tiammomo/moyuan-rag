#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from elasticsearch import Elasticsearch
from pymilvus import Collection, connections, utility
from sqlalchemy import create_engine, text


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402


class IntegrationError(RuntimeError):
    """Raised when the local integration run fails."""


@dataclass
class IntegrationArtifacts:
    llm_id: int
    knowledge_id: int
    document_id: int
    collection_name: str
    status_history: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the local backend integration flow and verify DB/ES/Milvus writes."
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:38084/api/v1",
        help="API base URL.",
    )
    parser.add_argument(
        "--upload-file",
        default=str(BACKEND_ROOT.parent / "docs" / "optimization-roadmap.md"),
        help="Path to the document uploaded during the test.",
    )
    parser.add_argument(
        "--password",
        default="LocalAdmin#2026",
        help="Password used for the generated integration admin.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=3.0,
        help="Seconds between document status polls.",
    )
    parser.add_argument(
        "--poll-timeout",
        type=int,
        default=180,
        help="Maximum seconds to wait for document processing.",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=60.0,
        help="Per-request timeout in seconds.",
    )
    parser.add_argument(
        "--username-prefix",
        default="integration_admin",
        help="Prefix used for generated test resources.",
    )
    return parser.parse_args()


def log_step(message: str) -> None:
    print(f"[local-integration] {message}", flush=True)


def retry_verification(
    action: Any,
    description: str,
    timeout_sec: float = 15.0,
    interval_sec: float = 1.0,
) -> Any:
    deadline = time.time() + timeout_sec
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            return action()
        except IntegrationError as exc:
            last_error = exc
            time.sleep(interval_sec)

    if last_error:
        raise last_error

    raise IntegrationError(f"{description} verification did not complete successfully")


def build_admin_payload(prefix: str, password: str) -> dict[str, Any]:
    run_id = f"{int(time.time())}_{uuid.uuid4().hex[:6]}"
    username = f"{prefix}_{run_id}"
    return {
        "username": username,
        "email": f"{username}@example.com",
        "password": password,
        "role": "admin",
        "run_id": run_id,
    }


def ensure_local_embedding_model() -> None:
    model_path = Path(settings.EMBEDDING_MODEL_PATH)
    if not model_path.is_absolute():
        model_path = (BACKEND_ROOT / model_path).resolve()

    if not model_path.exists():
        raise IntegrationError(
            f"Local embedding model path does not exist: {model_path}. "
            "Update EMBEDDING_MODEL_PATH in backend/.env before running the integration script."
        )


def get_health_url(base_url: str) -> str:
    parts = urlsplit(base_url)
    return urlunsplit((parts.scheme, parts.netloc, "/health", "", ""))


def ensure_api_reachable(base_url: str, timeout: float) -> None:
    health_url = get_health_url(base_url)
    try:
        response = httpx.get(health_url, timeout=timeout)
    except httpx.HTTPError as exc:
        raise IntegrationError(
            f"Backend API is not reachable at {health_url}. "
            "Start the backend first or run backend/scripts/local_integration.py."
        ) from exc

    if response.status_code != 200:
        raise IntegrationError(
            f"Backend health check failed at {health_url}: "
            f"{response.status_code} {response.text}"
        )


def require_success(response: httpx.Response, action: str) -> None:
    if response.is_success:
        return
    raise IntegrationError(
        f"{action} failed with status {response.status_code}: {response.text}"
    )


def run_api_flow(args: argparse.Namespace) -> tuple[IntegrationArtifacts, dict[str, Any]]:
    ensure_local_embedding_model()
    ensure_api_reachable(args.base_url, args.request_timeout)

    upload_path = Path(args.upload_file).resolve()
    if not upload_path.exists():
        raise IntegrationError(f"Upload file does not exist: {upload_path}")

    admin = build_admin_payload(args.username_prefix, args.password)
    mime_type = mimetypes.guess_type(upload_path.name)[0] or "application/octet-stream"
    llm_name = f"Local Tiny Embedding {admin['run_id']}"
    knowledge_name = f"Integration KB {admin['run_id']}"

    log_step(f"registering integration admin {admin['username']}")
    try:
        with httpx.Client(timeout=args.request_timeout) as client:
            register_response = client.post(
                f"{args.base_url}/auth/register",
                json={
                    "username": admin["username"],
                    "email": admin["email"],
                    "password": admin["password"],
                    "role": admin["role"],
                },
            )
            require_success(register_response, "register")

            log_step("logging in")
            login_response = client.post(
                f"{args.base_url}/auth/login",
                json={"username": admin["username"], "password": admin["password"]},
            )
            require_success(login_response, "login")
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            log_step("creating local embedding llm record")
            llm_response = client.post(
                f"{args.base_url}/llms",
                headers=headers,
                json={
                    "name": llm_name,
                    "model_type": "embedding",
                    "provider": "local",
                    "model_name": "bert-tiny",
                    "description": "Local integration smoke test model",
                },
            )
            require_success(llm_response, "create llm")
            llm_payload = llm_response.json()
            llm_id = llm_payload["id"]

            log_step("creating knowledge base")
            knowledge_response = client.post(
                f"{args.base_url}/knowledge",
                headers=headers,
                json={
                    "name": knowledge_name,
                    "embed_llm_id": llm_id,
                    "chunk_size": 300,
                    "chunk_overlap": 30,
                    "description": "Local integration smoke test knowledge base",
                },
            )
            require_success(knowledge_response, "create knowledge")
            knowledge_payload = knowledge_response.json()
            knowledge_id = knowledge_payload["id"]
            collection_name = knowledge_payload["vector_collection_name"]

            log_step(f"uploading {upload_path.name}")
            with upload_path.open("rb") as file_handle:
                upload_response = client.post(
                    f"{args.base_url}/documents/upload",
                    headers=headers,
                    params={"knowledge_id": knowledge_id},
                    files={"file": (upload_path.name, file_handle, mime_type)},
                )
            require_success(upload_response, "upload document")
            document_id = upload_response.json()["document_id"]

            log_step(f"polling document status for document_id={document_id}")
            deadline = time.time() + args.poll_timeout
            status_history: list[str] = []
            last_payload: dict[str, Any] | None = None
            while time.time() < deadline:
                status_response = client.get(
                    f"{args.base_url}/documents/{document_id}/status",
                    headers=headers,
                )
                require_success(status_response, "get document status")
                payload = status_response.json()
                status = payload["status"]
                if not status_history or status != status_history[-1]:
                    status_history.append(status)
                    log_step(f"status -> {status}")
                    last_payload = payload

                if status == "completed":
                    return (
                        IntegrationArtifacts(
                            llm_id=llm_id,
                            knowledge_id=knowledge_id,
                            document_id=document_id,
                            collection_name=collection_name,
                            status_history=status_history,
                        ),
                        last_payload or payload,
                    )

                if status == "failed":
                    raise IntegrationError(
                        f"document processing failed: {payload.get('error_msg') or payload}"
                    )

                time.sleep(args.poll_interval)
    except httpx.HTTPError as exc:
        raise IntegrationError(f"HTTP request failed during integration run: {exc}") from exc

    raise IntegrationError(
        f"timed out waiting for document processing after {args.poll_timeout} seconds"
    )


def verify_database(document_id: int, knowledge_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    engine = create_engine(settings.DATABASE_URL)
    try:
        with engine.connect() as connection:
            document_row = connection.execute(
                text(
                    "SELECT id, file_name, status, chunk_count, error_msg, knowledge_id "
                    "FROM rag_document WHERE id = :document_id"
                ),
                {"document_id": document_id},
            ).mappings().first()
            knowledge_row = connection.execute(
                text(
                    "SELECT id, document_count, total_chunks, vector_collection_name "
                    "FROM rag_knowledge WHERE id = :knowledge_id"
                ),
                {"knowledge_id": knowledge_id},
            ).mappings().first()
    finally:
        engine.dispose()

    if not document_row:
        raise IntegrationError(f"rag_document row not found for id={document_id}")
    if not knowledge_row:
        raise IntegrationError(f"rag_knowledge row not found for id={knowledge_id}")
    if document_row["status"] != "completed":
        raise IntegrationError(f"document status is not completed: {dict(document_row)}")
    if int(document_row["chunk_count"] or 0) <= 0:
        raise IntegrationError(f"document chunk_count is not positive: {dict(document_row)}")
    if int(knowledge_row["document_count"] or 0) <= 0:
        raise IntegrationError(f"knowledge document_count is not positive: {dict(knowledge_row)}")
    if int(knowledge_row["total_chunks"] or 0) < int(document_row["chunk_count"] or 0):
        raise IntegrationError(
            "knowledge total_chunks is lower than the document chunk_count: "
            f"{dict(knowledge_row)} vs {dict(document_row)}"
        )

    return dict(document_row), dict(knowledge_row)


def verify_elasticsearch(knowledge_id: int, expected_chunks: int) -> int:
    client = Elasticsearch([settings.ES_HOST])
    try:
        response = client.count(
            index=settings.ES_INDEX_NAME,
            body={"query": {"term": {"knowledge_id": knowledge_id}}},
        )
    finally:
        client.close()

    count = int(response["count"])
    if count < expected_chunks:
        raise IntegrationError(
            f"Elasticsearch chunk count {count} is lower than expected {expected_chunks}"
        )
    return count


def verify_milvus(collection_name: str, expected_chunks: int) -> int:
    alias = f"integration_{uuid.uuid4().hex[:8]}"
    connections.connect(alias=alias, host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
    try:
        if not utility.has_collection(collection_name, using=alias):
            raise IntegrationError(f"Milvus collection does not exist: {collection_name}")

        collection = Collection(collection_name, using=alias)
        collection.load()
        entity_count = int(collection.num_entities)
    finally:
        connections.disconnect(alias)

    if entity_count < expected_chunks:
        raise IntegrationError(
            f"Milvus entity count {entity_count} is lower than expected {expected_chunks}"
        )
    return entity_count


def main() -> int:
    args = parse_args()

    artifacts, last_status_payload = run_api_flow(args)
    document_row, knowledge_row = verify_database(
        document_id=artifacts.document_id,
        knowledge_id=artifacts.knowledge_id,
    )
    es_count = retry_verification(
        lambda: verify_elasticsearch(
            knowledge_id=artifacts.knowledge_id,
            expected_chunks=int(document_row["chunk_count"]),
        ),
        description="Elasticsearch",
    )
    milvus_count = retry_verification(
        lambda: verify_milvus(
            collection_name=artifacts.collection_name,
            expected_chunks=int(document_row["chunk_count"]),
        ),
        description="Milvus",
    )

    summary = {
        "result": "ok",
        "base_url": args.base_url,
        "upload_file": str(Path(args.upload_file).resolve()),
        "document": document_row,
        "knowledge": knowledge_row,
        "llm_id": artifacts.llm_id,
        "status_history": artifacts.status_history,
        "last_status_payload": last_status_payload,
        "es_chunk_count": es_count,
        "milvus_entity_count": milvus_count,
    }

    log_step("integration flow completed successfully")
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IntegrationError as exc:
        print(f"[local-integration] ERROR: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)
