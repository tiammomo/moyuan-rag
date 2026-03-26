"""
Helpers for storing large document-processing artifacts outside Kafka.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Iterable

from app.core.config import settings


PIPELINE_ARTIFACTS_KEY = "pipeline_artifacts"


class PipelineStorage:
    """Persist worker artifacts under the shared file storage root."""

    def __init__(self) -> None:
        self.storage_root = Path(settings.FILE_STORAGE_PATH)
        self.pipeline_root = self.storage_root / "_pipeline"
        self.pipeline_root.mkdir(parents=True, exist_ok=True)

    def _document_dir(self, document_id: int) -> Path:
        path = self.pipeline_root / str(document_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _relative_path(self, path: Path) -> str:
        return path.relative_to(self.storage_root).as_posix()

    def save_text(self, document_id: int, artifact_name: str, content: str) -> str:
        path = self._document_dir(document_id) / f"{artifact_name}.txt"
        path.write_text(content, encoding="utf-8")
        return self._relative_path(path)

    def save_json(self, document_id: int, artifact_name: str, payload: Any) -> str:
        path = self._document_dir(document_id) / f"{artifact_name}.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self._relative_path(path)

    def read_text(self, relative_path: str) -> str:
        return self.resolve(relative_path).read_text(encoding="utf-8")

    def read_json(self, relative_path: str) -> Any:
        return json.loads(self.resolve(relative_path).read_text(encoding="utf-8"))

    def delete(self, relative_path: str | None) -> bool:
        if not relative_path:
            return False

        path = self.resolve(relative_path)
        if not path.exists():
            return False

        path.unlink()
        self._cleanup_empty_parents(path.parent)
        return True

    def delete_document_artifacts(self, document_id: int) -> bool:
        path = self.pipeline_root / str(document_id)
        if not path.exists():
            return False

        shutil.rmtree(path)
        return True

    def resolve(self, relative_path: str) -> Path:
        normalized = Path(str(relative_path).replace("\\", "/"))
        if normalized.is_absolute():
            return normalized
        return self.storage_root / normalized

    def _cleanup_empty_parents(self, path: Path) -> None:
        current = path
        while current != self.pipeline_root and current.exists():
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent


def set_pipeline_artifact(
    meta_data: dict | None,
    artifact_key: str,
    file_path: str,
    **extra: Any,
) -> dict:
    metadata = dict(meta_data or {})
    artifacts = dict(metadata.get(PIPELINE_ARTIFACTS_KEY) or {})
    artifact = {"file_path": file_path}
    artifact.update(extra)
    artifacts[artifact_key] = artifact
    metadata[PIPELINE_ARTIFACTS_KEY] = artifacts
    return metadata


def get_pipeline_artifact(meta_data: dict | None, artifact_key: str) -> dict[str, Any] | None:
    if not meta_data:
        return None

    artifacts = meta_data.get(PIPELINE_ARTIFACTS_KEY) or {}
    artifact = artifacts.get(artifact_key)
    if not artifact:
        return None

    return dict(artifact)


def clear_pipeline_artifacts(
    meta_data: dict | None,
    artifact_keys: Iterable[str] | None = None,
) -> dict:
    metadata = dict(meta_data or {})
    artifacts = dict(metadata.get(PIPELINE_ARTIFACTS_KEY) or {})

    if artifact_keys is None:
        artifacts.clear()
    else:
        for key in artifact_keys:
            artifacts.pop(key, None)

    if artifacts:
        metadata[PIPELINE_ARTIFACTS_KEY] = artifacts
    else:
        metadata.pop(PIPELINE_ARTIFACTS_KEY, None)

    return metadata


pipeline_storage = PipelineStorage()
