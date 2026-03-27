"""
Filesystem-backed skill registry service for the bootstrap slice.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import logging
import os
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.robot import Robot
from app.models.skill_audit_log import SkillAuditLog
from app.models.skill_install_task import SkillInstallTask
from app.models.robot_skill_binding import RobotSkillBinding
from app.models.user import User
from app.schemas.skill import (
    RuntimeSkillPromptBundle,
    SkillAuditLogEntry,
    SkillAuditLogListResponse,
    SkillBindingCreate,
    SkillBindingUpdate,
    SkillDetail,
    SkillInstallResponse,
    SkillInstalledVariantInfo,
    SkillInstallTaskInfo,
    SkillInstallTaskListResponse,
    SkillListItem,
    SkillPromptFile,
    SkillRobotBindingDetail,
)


logger = logging.getLogger(__name__)


class SkillService:
    """Provides local registry, install, and robot binding operations."""

    @property
    def install_root(self) -> Path:
        return Path(settings.SKILL_INSTALL_ROOT)

    @property
    def registry_path(self) -> Path:
        return self.install_root / "registry" / "installed.json"

    @property
    def uploads_dir(self) -> Path:
        return self.install_root / "packages" / "uploads"

    @property
    def quarantine_dir(self) -> Path:
        return self.install_root / "quarantine"

    @property
    def extracted_dir(self) -> Path:
        return self.install_root / "extracted"

    def ensure_layout(self) -> None:
        for path in (
            self.registry_path.parent,
            self.uploads_dir,
            self.quarantine_dir,
            self.extracted_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

        if not self.registry_path.exists():
            self._write_registry({"skills": []})

    def _read_registry(self) -> dict[str, Any]:
        self.ensure_layout()
        raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return {"skills": raw}
        if "skills" not in raw or not isinstance(raw["skills"], list):
            raw["skills"] = []
        return raw

    def _write_registry(self, payload: dict[str, Any]) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _registry_map(self) -> dict[str, dict[str, Any]]:
        registry = self._read_registry()
        return {item["slug"]: item for item in registry["skills"]}

    def _to_absolute_path(self, relative_path: str | None) -> Path | None:
        if not relative_path:
            return None
        return self.install_root / Path(relative_path)

    def _read_manifest(self, manifest_path: Path | None) -> dict[str, Any]:
        if not manifest_path or not manifest_path.exists():
            return {}
        return yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}

    def _read_text(self, path: Path | None) -> str | None:
        if not path or not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def _build_prompt_keys(self, manifest: dict[str, Any]) -> list[str]:
        entrypoints = manifest.get("entrypoints") or {}
        return [str(key) for key in entrypoints.keys()]

    def _build_prompt_entries(self, manifest: dict[str, Any], install_dir: Path | None) -> list[SkillPromptFile]:
        if install_dir is None:
            return []

        prompts: list[SkillPromptFile] = []
        entrypoints = manifest.get("entrypoints") or {}
        for key, relative_path in entrypoints.items():
            prompt_path = install_dir / relative_path
            if not prompt_path.exists():
                continue
            prompts.append(
                SkillPromptFile(
                    key=str(key),
                    path=str(relative_path).replace("\\", "/"),
                    content=prompt_path.read_text(encoding="utf-8"),
                )
            )

        return prompts

    def _build_installed_variants(
        self,
        *,
        slug: str,
        current_record: dict[str, Any],
        bindings: list[SkillRobotBindingDetail],
    ) -> list[SkillInstalledVariantInfo]:
        skill_root = self.extracted_dir / slug
        if not skill_root.exists():
            return []

        bound_ids_by_version: dict[str, list[int]] = defaultdict(list)
        for binding in bindings:
            bound_ids_by_version[binding.skill_version].append(binding.robot_id)

        variants: list[SkillInstalledVariantInfo] = []
        for version_dir in sorted((path for path in skill_root.iterdir() if path.is_dir()), key=lambda item: item.name, reverse=True):
            manifest_path = version_dir / "skill.yaml"
            if not manifest_path.exists():
                continue

            manifest = self._read_manifest(manifest_path)
            version = str(manifest.get("version") or version_dir.name)
            prompt_keys = self._build_prompt_keys(manifest)
            installed_at = current_record.get("installed_at") if current_record.get("version") == version else None
            variants.append(
                SkillInstalledVariantInfo(
                    version=version,
                    install_path=version_dir.relative_to(self.install_root).as_posix(),
                    manifest_path=manifest_path.relative_to(self.install_root).as_posix(),
                    readme_available=(version_dir / "SKILL.md").exists(),
                    is_current=current_record.get("version") == version,
                    installed_at=installed_at,
                    prompt_keys=prompt_keys,
                    bound_robot_count=len(bound_ids_by_version[version]),
                    bound_robot_ids=sorted(bound_ids_by_version[version]),
                )
            )

        return variants

    def _build_binding_detail(
        self,
        binding: RobotSkillBinding,
        robot_name: str | None,
        record: dict[str, Any] | None,
    ) -> SkillRobotBindingDetail:
        manifest_path = self._to_absolute_path(record.get("manifest_path")) if record else None
        manifest = self._read_manifest(manifest_path)
        return SkillRobotBindingDetail(
            robot_id=binding.robot_id,
            robot_name=robot_name,
            skill_slug=binding.skill_slug,
            skill_name=record.get("name") if record else binding.skill_slug,
            skill_version=binding.skill_version,
            category=record.get("category") if record else None,
            skill_description=record.get("description") if record else None,
            priority=binding.priority,
            status=binding.status,
            prompt_keys=self._build_prompt_keys(manifest),
            binding_config=binding.binding_config or {},
            created_at=binding.created_at,
            updated_at=binding.updated_at,
        )

    async def _get_bound_counts(self, db: AsyncSession) -> dict[str, int]:
        if not hasattr(db, "execute") or db.execute is None:
            return {}
        result = await db.execute(
            select(RobotSkillBinding.skill_slug, func.count(RobotSkillBinding.id))
            .group_by(RobotSkillBinding.skill_slug)
        )
        return {slug: count for slug, count in result.all()}

    async def list_skills(self, db: AsyncSession) -> list[SkillListItem]:
        registry = self._read_registry()
        bound_counts = await self._get_bound_counts(db)
        items: list[SkillListItem] = []

        for raw in registry["skills"]:
            items.append(
                SkillListItem(
                    slug=raw["slug"],
                    name=raw.get("name", raw["slug"]),
                    version=raw.get("version", "0.0.0"),
                    description=raw.get("description"),
                    category=raw.get("category"),
                    source_type=raw.get("source_type", "local"),
                    status=raw.get("status", "active"),
                    install_path=raw["install_path"],
                    installed_at=raw.get("installed_at"),
                    readme_available=bool(raw.get("readme_path")),
                    bound_robot_count=bound_counts.get(raw["slug"], 0),
                )
            )

        items.sort(key=lambda item: item.name.lower())
        return items

    async def get_skill_detail(self, db: AsyncSession, slug: str) -> SkillDetail:
        registry = self._read_registry()
        record = next((item for item in registry["skills"] if item["slug"] == slug), None)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

        manifest_path = self._to_absolute_path(record.get("manifest_path"))
        manifest = self._read_manifest(manifest_path)
        install_dir = self._to_absolute_path(record.get("install_path"))
        readme_path = self._to_absolute_path(record.get("readme_path"))
        bindings = await self.get_robot_bindings(db, slug=slug)

        return SkillDetail(
            slug=record["slug"],
            name=record.get("name", record["slug"]),
            version=record.get("version", "0.0.0"),
            description=record.get("description"),
            category=record.get("category"),
            source_type=record.get("source_type", "local"),
            status=record.get("status", "active"),
            install_path=record["install_path"],
            installed_at=record.get("installed_at"),
            readme_available=bool(record.get("readme_path")),
            bound_robot_count=len(bindings),
            manifest=manifest,
            readme_content=self._read_text(readme_path),
            prompts=self._build_prompt_entries(manifest, install_dir),
            bound_robots=bindings,
            installed_variants=self._build_installed_variants(
                slug=slug,
                current_record=record,
                bindings=bindings,
            ),
        )

    def _sha256(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def _safe_extract_zip(self, archive_path: Path, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        dest_root = destination.resolve()

        with zipfile.ZipFile(archive_path, "r") as archive:
            for member in archive.infolist():
                target = (destination / member.filename).resolve()
                if not str(target).startswith(str(dest_root)):
                    raise HTTPException(status_code=400, detail="Invalid zip entry path")
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, open(target, "wb") as output:
                    shutil.copyfileobj(source, output)

    def _find_skill_root(self, quarantine_root: Path) -> Path:
        manifest_files = list(quarantine_root.rglob("skill.yaml"))
        if len(manifest_files) != 1:
            raise HTTPException(status_code=400, detail="Skill package must contain exactly one skill.yaml")
        return manifest_files[0].parent

    def _validate_skill_root(self, skill_root: Path) -> dict[str, Any]:
        manifest_path = skill_root / "skill.yaml"
        readme_path = skill_root / "SKILL.md"
        if not manifest_path.exists() or not readme_path.exists():
            raise HTTPException(status_code=400, detail="Skill package is missing skill.yaml or SKILL.md")

        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        slug = manifest.get("slug")
        version = manifest.get("version")
        if not slug or not version:
            raise HTTPException(status_code=400, detail="Skill manifest must define slug and version")

        entrypoints = manifest.get("entrypoints") or {}
        for relative_path in entrypoints.values():
            prompt_path = skill_root / relative_path
            if not prompt_path.exists():
                raise HTTPException(status_code=400, detail=f"Missing skill entrypoint: {relative_path}")

        return manifest

    def _upsert_registry_record(self, record: dict[str, Any]) -> None:
        registry = self._read_registry()
        registry["skills"] = [item for item in registry["skills"] if item["slug"] != record["slug"]]
        registry["skills"].append(record)
        registry["skills"].sort(key=lambda item: item["slug"])
        self._write_registry(registry)

    def _supports_persistence(self, db: AsyncSession) -> bool:
        return all(hasattr(db, attr) for attr in ("add", "commit", "refresh"))

    def _error_message(self, exc: Exception) -> str:
        if isinstance(exc, HTTPException):
            return str(exc.detail)
        return str(exc)

    def _merge_details(self, existing: dict[str, Any] | None, patch: dict[str, Any] | None) -> dict[str, Any]:
        merged = dict(existing or {})
        for key, value in (patch or {}).items():
            if value is not None:
                merged[key] = value
        return merged

    async def _create_install_task(
        self,
        db: AsyncSession,
        *,
        source_type: str,
        package_name: str | None,
        package_url: str | None,
        package_checksum: str | None,
        package_signature: str | None,
        signature_algorithm: str | None,
        current_user: User,
        details: dict[str, Any] | None = None,
    ) -> SkillInstallTask | None:
        if not self._supports_persistence(db):
            return None

        task = SkillInstallTask(
            source_type=source_type,
            package_name=package_name,
            package_url=package_url,
            package_checksum=package_checksum,
            package_signature=package_signature,
            signature_algorithm=signature_algorithm,
            requested_by_user_id=getattr(current_user, "id", None),
            requested_by_username=getattr(current_user, "username", None),
            status="pending",
            details=details or {},
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task

    async def _update_install_task(
        self,
        db: AsyncSession,
        task: SkillInstallTask | None,
        *,
        status_value: str,
        package_checksum: str | None = None,
        error_message: str | None = None,
        installed_skill_slug: str | None = None,
        installed_skill_version: str | None = None,
        details: dict[str, Any] | None = None,
        finished: bool = False,
    ) -> SkillInstallTask | None:
        if task is None or not self._supports_persistence(db):
            return task

        task.status = status_value
        if package_checksum is not None:
            task.package_checksum = package_checksum
        if error_message is not None:
            task.error_message = error_message
        if installed_skill_slug is not None:
            task.installed_skill_slug = installed_skill_slug
        if installed_skill_version is not None:
            task.installed_skill_version = installed_skill_version
        task.details = self._merge_details(task.details, details)
        if finished:
            task.finished_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(task)
        return task

    async def _record_audit_log(
        self,
        db: AsyncSession,
        *,
        action: str,
        target_type: str,
        status_value: str,
        current_user: User,
        message: str | None = None,
        robot_id: int | None = None,
        skill_slug: str | None = None,
        skill_version: str | None = None,
        install_task_id: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> SkillAuditLog | None:
        if not self._supports_persistence(db):
            return None

        log = SkillAuditLog(
            action=action,
            target_type=target_type,
            status=status_value,
            actor_user_id=getattr(current_user, "id", None),
            actor_username=getattr(current_user, "username", None),
            actor_role=getattr(current_user, "role", None),
            robot_id=robot_id,
            skill_slug=skill_slug,
            skill_version=skill_version,
            install_task_id=install_task_id,
            message=message,
            details=details or {},
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log

    def _validate_remote_install_request(
        self,
        package_url: str,
        checksum: str | None,
        signature: str | None,
    ) -> str:
        parsed = urlparse(package_url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"} or not host:
            raise HTTPException(status_code=400, detail="Remote skill package URL must be an absolute http(s) URL.")

        allowed_hosts = settings.SKILL_REMOTE_ALLOWED_HOSTS_LIST
        if allowed_hosts and host not in allowed_hosts:
            raise HTTPException(
                status_code=400,
                detail=f"Remote skill host {host} is not in the allowlist.",
            )

        if settings.SKILL_REMOTE_REQUIRE_CHECKSUM and not checksum:
            raise HTTPException(status_code=400, detail="Checksum is required for remote skill installation.")

        if settings.SKILL_REMOTE_REQUIRE_SIGNATURE and not signature:
            raise HTTPException(status_code=400, detail="Signature is required for remote skill installation.")

        return host

    async def list_install_tasks(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 50,
        status_filter: str | None = None,
        source_type: str | None = None,
        skill_slug: str | None = None,
        requested_by_username: str | None = None,
    ) -> SkillInstallTaskListResponse:
        stmt = select(SkillInstallTask).order_by(SkillInstallTask.created_at.desc())
        count_stmt = select(func.count(SkillInstallTask.id))

        if status_filter:
            stmt = stmt.where(SkillInstallTask.status == status_filter)
            count_stmt = count_stmt.where(SkillInstallTask.status == status_filter)
        if source_type:
            stmt = stmt.where(SkillInstallTask.source_type == source_type)
            count_stmt = count_stmt.where(SkillInstallTask.source_type == source_type)
        if skill_slug:
            stmt = stmt.where(SkillInstallTask.installed_skill_slug == skill_slug)
            count_stmt = count_stmt.where(SkillInstallTask.installed_skill_slug == skill_slug)
        if requested_by_username:
            stmt = stmt.where(SkillInstallTask.requested_by_username == requested_by_username)
            count_stmt = count_stmt.where(SkillInstallTask.requested_by_username == requested_by_username)

        total_result = await db.execute(count_stmt)
        result = await db.execute(stmt.offset(skip).limit(limit))
        items = [SkillInstallTaskInfo.model_validate(item) for item in result.scalars().all()]
        return SkillInstallTaskListResponse(total=total_result.scalar_one(), items=items)

    async def list_audit_logs(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        action_filter: str | None = None,
        status_filter: str | None = None,
        actor_username: str | None = None,
        skill_slug: str | None = None,
        robot_id: int | None = None,
    ) -> SkillAuditLogListResponse:
        stmt = select(SkillAuditLog).order_by(SkillAuditLog.created_at.desc())
        count_stmt = select(func.count(SkillAuditLog.id))

        if action_filter:
            stmt = stmt.where(SkillAuditLog.action == action_filter)
            count_stmt = count_stmt.where(SkillAuditLog.action == action_filter)
        if status_filter:
            stmt = stmt.where(SkillAuditLog.status == status_filter)
            count_stmt = count_stmt.where(SkillAuditLog.status == status_filter)
        if actor_username:
            stmt = stmt.where(SkillAuditLog.actor_username == actor_username)
            count_stmt = count_stmt.where(SkillAuditLog.actor_username == actor_username)
        if skill_slug:
            stmt = stmt.where(SkillAuditLog.skill_slug == skill_slug)
            count_stmt = count_stmt.where(SkillAuditLog.skill_slug == skill_slug)
        if robot_id is not None:
            stmt = stmt.where(SkillAuditLog.robot_id == robot_id)
            count_stmt = count_stmt.where(SkillAuditLog.robot_id == robot_id)

        total_result = await db.execute(count_stmt)
        result = await db.execute(stmt.offset(skip).limit(limit))
        items = [SkillAuditLogEntry.model_validate(item) for item in result.scalars().all()]
        return SkillAuditLogListResponse(total=total_result.scalar_one(), items=items)

    async def install_local_skill(self, db: AsyncSession, package: UploadFile, current_user: User) -> SkillInstallResponse:
        if not package.filename or not package.filename.lower().endswith(".zip"):
            raise HTTPException(status_code=400, detail="Only .zip skill packages are supported")

        self.ensure_layout()
        package_bytes = await package.read()
        package_checksum = self._sha256(package_bytes)
        archive_name = f"{uuid.uuid4().hex}-{os.path.basename(package.filename)}"
        archive_path = self.uploads_dir / archive_name
        archive_path.write_bytes(package_bytes)
        install_task = await self._create_install_task(
            db,
            source_type="local",
            package_name=package.filename,
            package_url=None,
            package_checksum=package_checksum,
            package_signature=None,
            signature_algorithm=None,
            current_user=current_user,
            details={"archive_name": archive_name},
        )

        quarantine_root = self.quarantine_dir / uuid.uuid4().hex
        try:
            await self._update_install_task(
                db,
                install_task,
                status_value="extracting",
                package_checksum=package_checksum,
                details={"quarantine_root": quarantine_root.name},
            )
            self._safe_extract_zip(archive_path, quarantine_root)
            skill_root = self._find_skill_root(quarantine_root)
            manifest = self._validate_skill_root(skill_root)

            slug = str(manifest["slug"])
            version = str(manifest["version"])
            target_dir = self.extracted_dir / slug / version
            if target_dir.exists():
                raise HTTPException(status_code=409, detail="This skill version is already installed")

            target_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(skill_root), str(target_dir))

            record = {
                "slug": slug,
                "name": manifest.get("name", slug),
                "version": version,
                "description": manifest.get("description"),
                "category": manifest.get("category"),
                "source_type": "local",
                "status": "active",
                "checksum": package_checksum,
                "install_path": target_dir.relative_to(self.install_root).as_posix(),
                "manifest_path": (target_dir / "skill.yaml").relative_to(self.install_root).as_posix(),
                "readme_path": (target_dir / "SKILL.md").relative_to(self.install_root).as_posix(),
                "installed_at": datetime.now(timezone.utc).isoformat(),
                "installed_by": getattr(current_user, "username", None),
            }
            self._upsert_registry_record(record)
            await self._update_install_task(
                db,
                install_task,
                status_value="installed",
                package_checksum=package_checksum,
                installed_skill_slug=slug,
                installed_skill_version=version,
                details={"install_path": record["install_path"]},
                finished=True,
            )
            await self._record_audit_log(
                db,
                action="skill.install_local",
                target_type="skill_install",
                status_value="success",
                current_user=current_user,
                message="Local skill package installed successfully.",
                skill_slug=slug,
                skill_version=version,
                install_task_id=getattr(install_task, "id", None),
                details={"package_name": package.filename, "checksum": package_checksum},
            )
            detail = await self.get_skill_detail(db, slug)
            return SkillInstallResponse(
                message="Skill installed successfully",
                skill=detail,
                install_task_id=getattr(install_task, "id", None),
            )
        except Exception as exc:
            if hasattr(db, "rollback"):
                await db.rollback()
            await self._update_install_task(
                db,
                install_task,
                status_value="failed",
                package_checksum=package_checksum,
                error_message=self._error_message(exc),
                details={"package_name": package.filename},
                finished=True,
            )
            await self._record_audit_log(
                db,
                action="skill.install_local",
                target_type="skill_install",
                status_value="failed",
                current_user=current_user,
                message=self._error_message(exc),
                install_task_id=getattr(install_task, "id", None),
                details={"package_name": package.filename, "checksum": package_checksum},
            )
            raise
        finally:
            shutil.rmtree(quarantine_root, ignore_errors=True)

    async def install_remote_skill(
        self,
        db: AsyncSession,
        *,
        package_url: str,
        checksum: str | None,
        signature: str | None,
        signature_algorithm: str | None,
        current_user: User,
    ) -> SkillInstallTask | None:
        install_task = await self._create_install_task(
            db,
            source_type="remote",
            package_name=None,
            package_url=package_url,
            package_checksum=checksum,
            package_signature=signature,
            signature_algorithm=signature_algorithm,
            current_user=current_user,
        )
        if not settings.ENABLE_REMOTE_SKILL_INSTALL:
            await self._update_install_task(
                db,
                install_task,
                status_value="rejected",
                error_message="Remote skill install is disabled.",
                finished=True,
            )
            await self._record_audit_log(
                db,
                action="skill.install_remote",
                target_type="skill_install",
                status_value="rejected",
                current_user=current_user,
                message="Remote skill install is disabled.",
                install_task_id=getattr(install_task, "id", None),
                details={"package_url": package_url},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Remote skill install is disabled. Enable ENABLE_REMOTE_SKILL_INSTALL to use this endpoint.",
            )

        host = self._validate_remote_install_request(package_url, checksum, signature)
        await self._update_install_task(
            db,
            install_task,
            status_value="verifying",
            details={"host": host},
        )
        await self._update_install_task(
            db,
            install_task,
            status_value="failed",
            error_message="Remote skill install is not implemented in the current controlled phase.",
            details={"host": host},
            finished=True,
        )
        await self._record_audit_log(
            db,
            action="skill.install_remote",
            target_type="skill_install",
            status_value="failed",
            current_user=current_user,
            message="Remote skill install is not implemented in the current controlled phase.",
            install_task_id=getattr(install_task, "id", None),
            details={
                "package_url": package_url,
                "checksum": checksum,
                "host": host,
                "signature_algorithm": signature_algorithm,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Remote skill install is not implemented in the current controlled phase.",
        )

    async def get_robot_bindings(
        self,
        db: AsyncSession,
        robot_id: int | None = None,
        slug: str | None = None,
    ) -> list[SkillRobotBindingDetail]:
        if not hasattr(db, "execute") or db.execute is None:
            return []
        stmt = select(RobotSkillBinding, Robot.name).join(Robot, Robot.id == RobotSkillBinding.robot_id)
        if robot_id is not None:
            stmt = stmt.where(RobotSkillBinding.robot_id == robot_id)
        if slug is not None:
            stmt = stmt.where(RobotSkillBinding.skill_slug == slug)
        stmt = stmt.order_by(RobotSkillBinding.priority.asc(), RobotSkillBinding.created_at.asc())

        result = await db.execute(stmt)
        registry_map = self._registry_map()
        bindings: list[SkillRobotBindingDetail] = []
        for binding, robot_name in result.all():
            bindings.append(
                self._build_binding_detail(
                    binding=binding,
                    robot_name=robot_name,
                    record=registry_map.get(binding.skill_slug),
                )
            )
        return bindings

    async def _get_robot_for_binding(self, db: AsyncSession, robot_id: int, current_user: User) -> Robot:
        result = await db.execute(select(Robot).where(Robot.id == robot_id))
        robot = result.scalar_one_or_none()
        if not robot:
            raise HTTPException(status_code=404, detail="Robot not found")
        if robot.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="You do not have permission to manage this robot")
        return robot

    async def get_robot_skill_bindings(
        self,
        db: AsyncSession,
        robot_id: int,
        current_user: User,
    ) -> list[SkillRobotBindingDetail]:
        await self._get_robot_for_binding(db, robot_id, current_user)
        return await self.get_robot_bindings(db, robot_id=robot_id)

    def _get_robot_modes(self, robot: Robot) -> set[str]:
        _ = robot
        return {"rag_chat"}

    def _validate_skill_constraints(self, robot: Robot, detail: SkillDetail) -> None:
        if detail.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Skill {detail.name} is not active and cannot be bound.",
            )
        constraints = detail.manifest.get("constraints") or {}
        allowed_modes = {str(item) for item in constraints.get("allowed_robot_modes") or []}
        if allowed_modes and not (self._get_robot_modes(robot) & allowed_modes):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Skill {detail.name} does not support this robot type. "
                    f"Allowed modes: {', '.join(sorted(allowed_modes))}."
                ),
            )

    async def get_runtime_skill_bundle(
        self,
        db: AsyncSession,
        robot_id: int,
    ) -> RuntimeSkillPromptBundle:
        if not hasattr(db, "execute") or db.execute is None:
            return RuntimeSkillPromptBundle()

        stmt = (
            select(RobotSkillBinding, Robot.name)
            .join(Robot, Robot.id == RobotSkillBinding.robot_id)
            .where(RobotSkillBinding.robot_id == robot_id, RobotSkillBinding.status == "active")
            .order_by(RobotSkillBinding.priority.asc(), RobotSkillBinding.created_at.asc())
        )
        result = await db.execute(stmt)
        registry_map = self._registry_map()

        active_skills: list[SkillRobotBindingDetail] = []
        system_prompts: list[str] = []
        retrieval_prompts: list[str] = []
        answer_prompts: list[str] = []

        for binding, robot_name in result.all():
            record = registry_map.get(binding.skill_slug)
            if not record:
                logger.warning("Skill binding points to missing registry slug: %s", binding.skill_slug)
                continue

            manifest_path = self._to_absolute_path(record.get("manifest_path"))
            install_dir = self._to_absolute_path(record.get("install_path"))
            manifest = self._read_manifest(manifest_path)
            prompt_entries = self._build_prompt_entries(manifest, install_dir)

            active_skills.append(
                self._build_binding_detail(
                    binding=binding,
                    robot_name=robot_name,
                    record=record,
                )
            )

            for entry in prompt_entries:
                content = entry.content.strip()
                if not content:
                    continue
                formatted = f"[{record.get('name', binding.skill_slug)}::{entry.key}]\n{content}"
                if entry.key == "system_prompt":
                    system_prompts.append(formatted)
                elif entry.key == "retrieval_prompt":
                    retrieval_prompts.append(formatted)
                elif entry.key == "answer_prompt":
                    answer_prompts.append(formatted)

        return RuntimeSkillPromptBundle(
            active_skills=active_skills,
            system_prompts=system_prompts,
            retrieval_prompts=retrieval_prompts,
            answer_prompts=answer_prompts,
        )

    async def bind_skill_to_robot(
        self,
        db: AsyncSession,
        robot_id: int,
        skill_slug: str,
        payload: SkillBindingCreate,
        current_user: User,
    ) -> SkillRobotBindingDetail:
        detail: SkillDetail | None = None
        try:
            robot = await self._get_robot_for_binding(db, robot_id, current_user)
            detail = await self.get_skill_detail(db, skill_slug)
            self._validate_skill_constraints(robot, detail)

            result = await db.execute(
                select(RobotSkillBinding).where(
                    RobotSkillBinding.robot_id == robot_id,
                    RobotSkillBinding.skill_slug == skill_slug,
                )
            )
            binding = result.scalar_one_or_none()

            if binding is None:
                count_result = await db.execute(
                    select(func.count(RobotSkillBinding.id)).where(RobotSkillBinding.robot_id == robot_id)
                )
                next_priority = payload.priority or (count_result.scalar_one() + 1) * 100
                binding = RobotSkillBinding(
                    robot_id=robot_id,
                    skill_slug=skill_slug,
                    skill_version=detail.version,
                    binding_config=payload.binding_config,
                    priority=next_priority,
                    status=payload.status,
                )
                db.add(binding)
            else:
                binding.skill_version = detail.version
                binding.binding_config = payload.binding_config
                binding.priority = payload.priority or binding.priority
                binding.status = payload.status

            await db.commit()
            bindings = await self.get_robot_skill_bindings(db, robot_id, current_user)
            bound = next(item for item in bindings if item.skill_slug == skill_slug)
            await self._record_audit_log(
                db,
                action="skill.bind",
                target_type="robot_skill_binding",
                status_value="success",
                current_user=current_user,
                message="Skill bound to robot successfully.",
                robot_id=robot_id,
                skill_slug=skill_slug,
                skill_version=bound.skill_version,
                details={"priority": bound.priority, "status": bound.status},
            )
            return bound
        except Exception as exc:
            if hasattr(db, "rollback"):
                await db.rollback()
            await self._record_audit_log(
                db,
                action="skill.bind",
                target_type="robot_skill_binding",
                status_value="failed",
                current_user=current_user,
                message=self._error_message(exc),
                robot_id=robot_id,
                skill_slug=skill_slug,
                skill_version=detail.version if detail else None,
                details={"requested_status": payload.status},
            )
            raise

    async def update_robot_skill_binding(
        self,
        db: AsyncSession,
        robot_id: int,
        skill_slug: str,
        payload: SkillBindingUpdate,
        current_user: User,
    ) -> SkillRobotBindingDetail:
        detail: SkillDetail | None = None
        try:
            robot = await self._get_robot_for_binding(db, robot_id, current_user)
            detail = await self.get_skill_detail(db, skill_slug)
            if payload.status != "disabled":
                self._validate_skill_constraints(robot, detail)
            result = await db.execute(
                select(RobotSkillBinding).where(
                    RobotSkillBinding.robot_id == robot_id,
                    RobotSkillBinding.skill_slug == skill_slug,
                )
            )
            binding = result.scalar_one_or_none()
            if not binding:
                raise HTTPException(status_code=404, detail="Skill binding not found")

            if payload.priority is not None:
                binding.priority = payload.priority
            if payload.status is not None:
                binding.status = payload.status
            if payload.binding_config is not None:
                binding.binding_config = payload.binding_config

            await db.commit()
            bindings = await self.get_robot_skill_bindings(db, robot_id, current_user)
            updated = next(item for item in bindings if item.skill_slug == skill_slug)
            await self._record_audit_log(
                db,
                action="skill.update_binding",
                target_type="robot_skill_binding",
                status_value="success",
                current_user=current_user,
                message="Skill binding updated successfully.",
                robot_id=robot_id,
                skill_slug=skill_slug,
                skill_version=updated.skill_version,
                details={"priority": updated.priority, "status": updated.status},
            )
            return updated
        except Exception as exc:
            if hasattr(db, "rollback"):
                await db.rollback()
            await self._record_audit_log(
                db,
                action="skill.update_binding",
                target_type="robot_skill_binding",
                status_value="failed",
                current_user=current_user,
                message=self._error_message(exc),
                robot_id=robot_id,
                skill_slug=skill_slug,
                skill_version=detail.version if detail else None,
                details={"requested_priority": payload.priority, "requested_status": payload.status},
            )
            raise

    async def unbind_skill_from_robot(
        self,
        db: AsyncSession,
        robot_id: int,
        skill_slug: str,
        current_user: User,
    ) -> None:
        try:
            await self._get_robot_for_binding(db, robot_id, current_user)
            result = await db.execute(
                select(RobotSkillBinding).where(
                    RobotSkillBinding.robot_id == robot_id,
                    RobotSkillBinding.skill_slug == skill_slug,
                )
            )
            binding = result.scalar_one_or_none()
            if not binding:
                raise HTTPException(status_code=404, detail="Skill binding not found")

            skill_version = binding.skill_version
            await db.delete(binding)
            await db.commit()
            await self._record_audit_log(
                db,
                action="skill.unbind",
                target_type="robot_skill_binding",
                status_value="success",
                current_user=current_user,
                message="Skill binding removed successfully.",
                robot_id=robot_id,
                skill_slug=skill_slug,
                skill_version=skill_version,
            )
        except Exception as exc:
            if hasattr(db, "rollback"):
                await db.rollback()
            await self._record_audit_log(
                db,
                action="skill.unbind",
                target_type="robot_skill_binding",
                status_value="failed",
                current_user=current_user,
                message=self._error_message(exc),
                robot_id=robot_id,
                skill_slug=skill_slug,
            )
            raise


skill_service = SkillService()
