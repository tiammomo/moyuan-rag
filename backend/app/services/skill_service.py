"""
Filesystem-backed skill registry service for the bootstrap slice.
"""

from __future__ import annotations

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

import yaml
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.robot import Robot
from app.models.robot_skill_binding import RobotSkillBinding
from app.models.user import User
from app.schemas.skill import (
    SkillBindingCreate,
    SkillBindingUpdate,
    SkillDetail,
    SkillInstallResponse,
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

    async def install_local_skill(self, db: AsyncSession, package: UploadFile, current_user: User) -> SkillInstallResponse:
        if not package.filename or not package.filename.lower().endswith(".zip"):
            raise HTTPException(status_code=400, detail="Only .zip skill packages are supported")

        self.ensure_layout()
        package_bytes = await package.read()
        archive_name = f"{uuid.uuid4().hex}-{os.path.basename(package.filename)}"
        archive_path = self.uploads_dir / archive_name
        archive_path.write_bytes(package_bytes)

        quarantine_root = self.quarantine_dir / uuid.uuid4().hex
        try:
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
                "checksum": self._sha256(package_bytes),
                "install_path": target_dir.relative_to(self.install_root).as_posix(),
                "manifest_path": (target_dir / "skill.yaml").relative_to(self.install_root).as_posix(),
                "readme_path": (target_dir / "SKILL.md").relative_to(self.install_root).as_posix(),
                "installed_at": datetime.now(timezone.utc).isoformat(),
                "installed_by": getattr(current_user, "username", None),
            }
            self._upsert_registry_record(record)
            detail = await self.get_skill_detail(db, slug)
            return SkillInstallResponse(message="Skill installed successfully", skill=detail)
        finally:
            shutil.rmtree(quarantine_root, ignore_errors=True)

    async def install_remote_skill(self, package_url: str, checksum: str | None) -> None:
        _ = (package_url, checksum)
        if not settings.ENABLE_REMOTE_SKILL_INSTALL:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Remote skill install is disabled. Enable ENABLE_REMOTE_SKILL_INSTALL to use this endpoint.",
            )

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Remote skill install is not implemented in the bootstrap slice.",
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
        bindings: list[SkillRobotBindingDetail] = []
        for binding, robot_name in result.all():
            bindings.append(
                SkillRobotBindingDetail(
                    robot_id=binding.robot_id,
                    robot_name=robot_name,
                    skill_slug=binding.skill_slug,
                    skill_version=binding.skill_version,
                    priority=binding.priority,
                    status=binding.status,
                    binding_config=binding.binding_config or {},
                    created_at=binding.created_at,
                    updated_at=binding.updated_at,
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

    async def bind_skill_to_robot(
        self,
        db: AsyncSession,
        robot_id: int,
        skill_slug: str,
        payload: SkillBindingCreate,
        current_user: User,
    ) -> SkillRobotBindingDetail:
        await self._get_robot_for_binding(db, robot_id, current_user)
        detail = await self.get_skill_detail(db, skill_slug)

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
        return next(item for item in bindings if item.skill_slug == skill_slug)

    async def update_robot_skill_binding(
        self,
        db: AsyncSession,
        robot_id: int,
        skill_slug: str,
        payload: SkillBindingUpdate,
        current_user: User,
    ) -> SkillRobotBindingDetail:
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

        if payload.priority is not None:
            binding.priority = payload.priority
        if payload.status is not None:
            binding.status = payload.status
        if payload.binding_config is not None:
            binding.binding_config = payload.binding_config

        await db.commit()
        bindings = await self.get_robot_skill_bindings(db, robot_id, current_user)
        return next(item for item in bindings if item.skill_slug == skill_slug)

    async def unbind_skill_from_robot(
        self,
        db: AsyncSession,
        robot_id: int,
        skill_slug: str,
        current_user: User,
    ) -> None:
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

        await db.delete(binding)
        await db.commit()


skill_service = SkillService()
