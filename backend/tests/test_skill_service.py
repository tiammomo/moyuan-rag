import base64
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.core.config import settings
from app.models.skill_audit_log import SkillAuditLog
from app.models.skill_install_task import SkillInstallTask
from app.services.skill_service import skill_service


class FakeRowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeScalarListResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class FakeCountResult:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value


class FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeSession:
    def __init__(self, results=None):
        self._results = list(results or [])
        self.added = []
        self.deleted = []
        self.commits = 0
        self.rollbacks = 0
        self._next_id = 1
        self.statements = []

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = self._next_id
            self._next_id += 1
        self.added.append(obj)

    async def delete(self, obj):
        self.deleted.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, _obj):
        now = datetime.now(timezone.utc)
        if getattr(_obj, "created_at", None) is None:
            _obj.created_at = now
        if getattr(_obj, "updated_at", None) is None:
            _obj.updated_at = now
        return None

    async def rollback(self):
        self.rollbacks += 1

    async def execute(self, _stmt):
        self.statements.append(str(_stmt))
        if self._results:
            return self._results.pop(0)
        return FakeRowsResult([])


def _write_demo_skill(root: Path, slug: str = "demo-skill", version: str = "0.1.0") -> None:
    skill_root = root / "extracted" / slug / version
    skill_root.mkdir(parents=True, exist_ok=True)
    (skill_root / "prompts").mkdir(parents=True, exist_ok=True)
    (root / "registry").mkdir(parents=True, exist_ok=True)

    (skill_root / "skill.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                f"slug: {slug}",
                "name: Demo Skill",
                f"version: {version}",
                "category: demo",
                "description: Demo skill for tests",
                "entrypoints:",
                "  system_prompt: prompts/system.md",
            ]
        ),
        encoding="utf-8",
    )
    (skill_root / "SKILL.md").write_text("# Demo Skill\n", encoding="utf-8")
    (skill_root / "prompts" / "system.md").write_text("hello", encoding="utf-8")
    (root / "registry" / "installed.json").write_text(
        json.dumps(
            {
                "skills": [
                    {
                        "slug": slug,
                        "name": "Demo Skill",
                        "version": version,
                        "description": "Demo skill for tests",
                        "category": "demo",
                        "source_type": "local",
                        "status": "active",
                        "install_path": f"extracted/{slug}/{version}",
                        "manifest_path": f"extracted/{slug}/{version}/skill.yaml",
                        "readme_path": f"extracted/{slug}/{version}/SKILL.md",
                        "installed_at": "2026-03-27T12:00:00+08:00",
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _build_skill_zip_bytes(
    *,
    slug: str,
    version: str,
    name: str,
    category: str = "demo",
    description: str = "Installed from a remote zip package",
) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr(
            f"{slug}/skill.yaml",
            "\n".join(
                [
                    "schema_version: 1",
                    f"slug: {slug}",
                    f"name: {name}",
                    f"version: {version}",
                    f"category: {category}",
                    f"description: {description}",
                    "entrypoints:",
                    "  system_prompt: prompts/system.md",
                ]
            ),
        )
        archive.writestr(f"{slug}/SKILL.md", f"# {name}\n")
        archive.writestr(f"{slug}/prompts/system.md", "system prompt")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_list_skills_reads_registry(tmp_path: Path):
    original_root = settings.SKILL_INSTALL_ROOT
    settings.SKILL_INSTALL_ROOT = str(tmp_path)
    try:
        _write_demo_skill(tmp_path)
        items = await skill_service.list_skills(db=SimpleNamespace(execute=None))
    finally:
        settings.SKILL_INSTALL_ROOT = original_root

    assert len(items) == 1
    assert items[0].slug == "demo-skill"
    assert items[0].name == "Demo Skill"


@pytest.mark.asyncio
async def test_install_local_skill_writes_registry(tmp_path: Path):
    original_root = settings.SKILL_INSTALL_ROOT
    settings.SKILL_INSTALL_ROOT = str(tmp_path)
    try:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr(
                "demo-skill/skill.yaml",
                "\n".join(
                    [
                        "schema_version: 1",
                        "slug: local-demo",
                        "name: Local Demo Skill",
                        "version: 1.0.0",
                        "category: local",
                        "description: Installed from a zip package",
                        "entrypoints:",
                        "  system_prompt: prompts/system.md",
                    ]
                ),
            )
            archive.writestr("demo-skill/SKILL.md", "# Local Demo Skill\n")
            archive.writestr("demo-skill/prompts/system.md", "system prompt")
        buf.seek(0)

        upload = UploadFile(filename="local-demo.zip", file=buf)
        db = FakeSession()
        response = await skill_service.install_local_skill(
            db=db,
            package=upload,
            current_user=SimpleNamespace(id=1, username="admin", role="admin"),
        )
        registry = json.loads((tmp_path / "registry" / "installed.json").read_text(encoding="utf-8"))
    finally:
        settings.SKILL_INSTALL_ROOT = original_root

    assert response.skill.slug == "local-demo"
    assert response.install_task_id is not None
    assert registry["skills"][0]["slug"] == "local-demo"
    assert any(isinstance(item, SkillInstallTask) and item.status == "installed" for item in db.added)
    assert any(isinstance(item, SkillAuditLog) and item.action == "skill.install_local" for item in db.added)


@pytest.mark.asyncio
async def test_remote_install_rejected_when_disabled():
    original_flag = settings.ENABLE_REMOTE_SKILL_INSTALL
    settings.ENABLE_REMOTE_SKILL_INSTALL = False
    try:
        db = FakeSession()
        with pytest.raises(HTTPException) as exc_info:
            await skill_service.install_remote_skill(
                db,
                package_url="https://example.com/demo.zip",
                checksum=None,
                signature=None,
                signature_algorithm=None,
                current_user=SimpleNamespace(id=1, username="admin", role="admin"),
            )
    finally:
        settings.ENABLE_REMOTE_SKILL_INSTALL = original_flag

    assert exc_info.value.status_code == 403
    assert any(isinstance(item, SkillInstallTask) and item.status == "rejected" for item in db.added)
    assert any(isinstance(item, SkillAuditLog) and item.action == "skill.install_remote" for item in db.added)


@pytest.mark.asyncio
async def test_remote_install_downloads_and_installs_when_enabled(tmp_path: Path):
    original_values = {
        "SKILL_INSTALL_ROOT": settings.SKILL_INSTALL_ROOT,
        "ENABLE_REMOTE_SKILL_INSTALL": settings.ENABLE_REMOTE_SKILL_INSTALL,
        "SKILL_REMOTE_ALLOWED_HOSTS": settings.SKILL_REMOTE_ALLOWED_HOSTS,
        "SKILL_REMOTE_REQUIRE_CHECKSUM": settings.SKILL_REMOTE_REQUIRE_CHECKSUM,
        "SKILL_REMOTE_REQUIRE_SIGNATURE": settings.SKILL_REMOTE_REQUIRE_SIGNATURE,
        "SKILL_REMOTE_ED25519_PUBLIC_KEY": settings.SKILL_REMOTE_ED25519_PUBLIC_KEY,
    }
    package_bytes = _build_skill_zip_bytes(slug="remote-demo", version="2.0.0", name="Remote Demo Skill")
    checksum = hashlib.sha256(package_bytes).hexdigest()
    signing_key = Ed25519PrivateKey.generate()
    signature = base64.b64encode(signing_key.sign(package_bytes)).decode("utf-8")
    settings.SKILL_INSTALL_ROOT = str(tmp_path)
    settings.ENABLE_REMOTE_SKILL_INSTALL = True
    settings.SKILL_REMOTE_ALLOWED_HOSTS = "example.com"
    settings.SKILL_REMOTE_REQUIRE_CHECKSUM = True
    settings.SKILL_REMOTE_REQUIRE_SIGNATURE = False
    settings.SKILL_REMOTE_ED25519_PUBLIC_KEY = signing_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    try:
        db = FakeSession()
        url = "https://example.com/skills/remote-demo.zip"
        async with respx.mock:
            route = respx.get(url).mock(
                return_value=httpx.Response(
                    200,
                    content=package_bytes,
                    headers={
                        "content-length": str(len(package_bytes)),
                        "content-type": "application/zip",
                    },
                )
            )
            task = await skill_service.install_remote_skill(
                db,
                package_url=url,
                checksum=checksum,
                signature=signature,
                signature_algorithm="ed25519",
                current_user=SimpleNamespace(id=1, username="admin", role="admin"),
            )
        registry = json.loads((tmp_path / "registry" / "installed.json").read_text(encoding="utf-8"))
    finally:
        for key, value in original_values.items():
            setattr(settings, key, value)

    assert route.called
    assert task is not None
    assert task.status == "installed"
    assert task.installed_skill_slug == "remote-demo"
    assert task.installed_skill_version == "2.0.0"
    assert registry["skills"][0]["slug"] == "remote-demo"
    assert registry["skills"][0]["source_type"] == "remote"
    assert task.details["download"]["size_bytes"] == len(package_bytes)
    assert task.details["verification"]["checksum_verified"] is True
    assert task.details["verification"]["signature_verified"] is True
    assert any(isinstance(item, SkillInstallTask) and item.status == "installed" for item in db.added)
    assert any(
        isinstance(item, SkillAuditLog) and item.action == "skill.install_remote" and item.status == "success"
        for item in db.added
    )


@pytest.mark.asyncio
async def test_remote_install_rejects_checksum_mismatch(tmp_path: Path):
    original_values = {
        "SKILL_INSTALL_ROOT": settings.SKILL_INSTALL_ROOT,
        "ENABLE_REMOTE_SKILL_INSTALL": settings.ENABLE_REMOTE_SKILL_INSTALL,
        "SKILL_REMOTE_ALLOWED_HOSTS": settings.SKILL_REMOTE_ALLOWED_HOSTS,
        "SKILL_REMOTE_REQUIRE_CHECKSUM": settings.SKILL_REMOTE_REQUIRE_CHECKSUM,
        "SKILL_REMOTE_REQUIRE_SIGNATURE": settings.SKILL_REMOTE_REQUIRE_SIGNATURE,
        "SKILL_REMOTE_ED25519_PUBLIC_KEY": settings.SKILL_REMOTE_ED25519_PUBLIC_KEY,
    }
    package_bytes = _build_skill_zip_bytes(slug="remote-bad", version="1.0.0", name="Remote Bad Skill")
    settings.SKILL_INSTALL_ROOT = str(tmp_path)
    settings.ENABLE_REMOTE_SKILL_INSTALL = True
    settings.SKILL_REMOTE_ALLOWED_HOSTS = "example.com"
    settings.SKILL_REMOTE_REQUIRE_CHECKSUM = True
    settings.SKILL_REMOTE_REQUIRE_SIGNATURE = False
    settings.SKILL_REMOTE_ED25519_PUBLIC_KEY = ""

    try:
        db = FakeSession()
        url = "https://example.com/skills/remote-bad.zip"
        async with respx.mock:
            respx.get(url).mock(
                return_value=httpx.Response(
                    200,
                    content=package_bytes,
                    headers={
                        "content-length": str(len(package_bytes)),
                        "content-type": "application/zip",
                    },
                )
            )
            with pytest.raises(HTTPException) as exc_info:
                await skill_service.install_remote_skill(
                    db,
                    package_url=url,
                    checksum="0" * 64,
                    signature=None,
                    signature_algorithm=None,
                    current_user=SimpleNamespace(id=1, username="admin", role="admin"),
                )
    finally:
        for key, value in original_values.items():
            setattr(settings, key, value)

    assert exc_info.value.status_code == 400
    failed_task = next(item for item in db.added if isinstance(item, SkillInstallTask))
    assert failed_task.status == "rejected"
    assert failed_task.details["host"] == "example.com"
    assert any(
        isinstance(item, SkillAuditLog) and item.action == "skill.install_remote" and item.status == "rejected"
        for item in db.added
    )


@pytest.mark.asyncio
async def test_get_skill_detail_includes_installed_variants(tmp_path: Path):
    original_root = settings.SKILL_INSTALL_ROOT
    settings.SKILL_INSTALL_ROOT = str(tmp_path)
    try:
        _write_demo_skill(tmp_path, slug="demo-skill", version="0.2.0")
        old_version_root = tmp_path / "extracted" / "demo-skill" / "0.1.0"
        old_version_root.mkdir(parents=True, exist_ok=True)
        (old_version_root / "prompts").mkdir(parents=True, exist_ok=True)
        (old_version_root / "skill.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "slug: demo-skill",
                    "name: Demo Skill",
                    "version: 0.1.0",
                    "category: demo",
                    "description: Older variant",
                    "entrypoints:",
                    "  system_prompt: prompts/system.md",
                ]
            ),
            encoding="utf-8",
        )
        (old_version_root / "SKILL.md").write_text("# Demo Skill v0.1.0\n", encoding="utf-8")
        (old_version_root / "prompts" / "system.md").write_text("older guidance", encoding="utf-8")

        db = FakeSession(
            results=[
                FakeRowsResult(
                    [
                        (
                            SimpleNamespace(
                                robot_id=1,
                                skill_slug="demo-skill",
                                skill_version="0.2.0",
                                priority=100,
                                status="active",
                                binding_config={},
                                created_at="2026-03-28T10:00:00+08:00",
                                updated_at="2026-03-28T10:00:00+08:00",
                            ),
                            "Robot A",
                        ),
                        (
                            SimpleNamespace(
                                robot_id=2,
                                skill_slug="demo-skill",
                                skill_version="0.1.0",
                                priority=200,
                                status="active",
                                binding_config={},
                                created_at="2026-03-28T10:00:00+08:00",
                                updated_at="2026-03-28T10:00:00+08:00",
                            ),
                            "Robot B",
                        ),
                    ]
                )
            ]
        )
        detail = await skill_service.get_skill_detail(db, "demo-skill")
    finally:
        settings.SKILL_INSTALL_ROOT = original_root

    assert len(detail.installed_variants) == 2
    current_variant = next(item for item in detail.installed_variants if item.version == "0.2.0")
    old_variant = next(item for item in detail.installed_variants if item.version == "0.1.0")
    assert current_variant.is_current is True
    assert current_variant.bound_robot_count == 1
    assert old_variant.is_current is False
    assert old_variant.bound_robot_ids == [2]


@pytest.mark.asyncio
async def test_get_install_task_returns_task_info():
    task = SimpleNamespace(
        id=7,
        source_type="remote",
        package_name=None,
        package_url="https://example.com/demo.zip",
        package_checksum="abc123",
        package_signature=None,
        signature_algorithm=None,
        requested_by_user_id=1,
        requested_by_username="admin",
        status="rejected",
        installed_skill_slug=None,
        installed_skill_version=None,
        error_message="Remote install is disabled.",
        details={"host": "example.com"},
        created_at="2026-03-28T11:00:00+08:00",
        updated_at="2026-03-28T11:00:01+08:00",
        finished_at="2026-03-28T11:00:01+08:00",
    )
    db = FakeSession(results=[FakeScalarResult(task)])

    response = await skill_service.get_install_task(db, 7)

    assert response.id == 7
    assert response.package_url == "https://example.com/demo.zip"
    assert response.status == "rejected"


@pytest.mark.asyncio
async def test_retry_install_task_creates_new_attempt_when_remote_install_is_disabled():
    original_flag = settings.ENABLE_REMOTE_SKILL_INSTALL
    settings.ENABLE_REMOTE_SKILL_INSTALL = False
    task = SimpleNamespace(
        id=8,
        source_type="remote",
        package_name=None,
        package_url="https://example.com/demo.zip",
        package_checksum="abc123",
        package_signature=None,
        signature_algorithm=None,
        requested_by_user_id=1,
        requested_by_username="admin",
        status="rejected",
        installed_skill_slug=None,
        installed_skill_version=None,
        error_message="Remote install is disabled.",
        details={},
        created_at="2026-03-28T11:00:00+08:00",
        updated_at="2026-03-28T11:00:01+08:00",
        finished_at="2026-03-28T11:00:01+08:00",
    )
    try:
        db = FakeSession(results=[FakeScalarResult(task)])
        response = await skill_service.retry_install_task(
            db,
            task_id=8,
            current_user=SimpleNamespace(id=1, username="admin", role="admin"),
        )
    finally:
        settings.ENABLE_REMOTE_SKILL_INSTALL = original_flag

    assert response.task.status == "rejected"
    assert response.task.details["retry_of_task_id"] == 8
    assert task.details["latest_retry_task_id"] == response.task.id
    assert any(isinstance(item, SkillInstallTask) and item.id == response.task.id for item in db.added)
    assert any(isinstance(item, SkillAuditLog) and item.action == "skill.retry_install" for item in db.added)


@pytest.mark.asyncio
async def test_cancel_install_task_marks_pending_remote_task_as_cancelled():
    task = SimpleNamespace(
        id=9,
        source_type="remote",
        package_name=None,
        package_url="https://example.com/demo.zip",
        package_checksum="abc123",
        package_signature=None,
        signature_algorithm=None,
        requested_by_user_id=1,
        requested_by_username="admin",
        status="pending",
        installed_skill_slug=None,
        installed_skill_version=None,
        error_message=None,
        details={},
        created_at="2026-03-28T11:00:00+08:00",
        updated_at="2026-03-28T11:00:00+08:00",
        finished_at=None,
    )
    db = FakeSession(results=[FakeScalarResult(task)])

    response = await skill_service.cancel_install_task(
        db,
        task_id=9,
        current_user=SimpleNamespace(id=1, username="admin", role="admin"),
    )

    assert response.task.status == "cancelled"
    assert response.task.error_message == "Install task was cancelled by an operator."
    assert task.details["cancelled_by"] == "admin"
    assert any(isinstance(item, SkillAuditLog) and item.action == "skill.cancel_install" for item in db.added)


@pytest.mark.asyncio
async def test_list_install_tasks_applies_filters_to_query():
    task = SimpleNamespace(
        id=1,
        source_type="local",
        package_name="demo.zip",
        package_url=None,
        package_checksum="abc",
        package_signature=None,
        signature_algorithm=None,
        requested_by_user_id=1,
        requested_by_username="admin",
        status="installed",
        installed_skill_slug="demo-skill",
        installed_skill_version="0.2.0",
        error_message=None,
        details={"archive_name": "demo.zip"},
        created_at="2026-03-28T10:00:00+08:00",
        updated_at="2026-03-28T10:05:00+08:00",
        finished_at="2026-03-28T10:05:00+08:00",
    )
    db = FakeSession(results=[FakeCountResult(1), FakeScalarListResult([task])])

    response = await skill_service.list_install_tasks(
        db,
        status_filter="installed",
        source_type="local",
        skill_slug="demo-skill",
        requested_by_username="admin",
    )

    assert response.total == 1
    assert response.items[0].installed_skill_slug == "demo-skill"
    combined_sql = "\n".join(db.statements)
    assert "rag_skill_install_task.status" in combined_sql
    assert "rag_skill_install_task.source_type" in combined_sql
    assert "rag_skill_install_task.installed_skill_slug" in combined_sql
    assert "rag_skill_install_task.requested_by_username" in combined_sql


@pytest.mark.asyncio
async def test_list_audit_logs_applies_filters_to_query():
    audit_log = SimpleNamespace(
        id=9,
        action="skill.bind",
        target_type="robot_skill_binding",
        status="success",
        actor_user_id=1,
        actor_username="admin",
        actor_role="admin",
        robot_id=7,
        skill_slug="demo-skill",
        skill_version="0.2.0",
        install_task_id=None,
        message="Bound successfully.",
        details={"priority": 100},
        created_at="2026-03-28T10:10:00+08:00",
    )
    db = FakeSession(results=[FakeCountResult(1), FakeScalarListResult([audit_log])])

    response = await skill_service.list_audit_logs(
        db,
        action_filter="skill.bind",
        status_filter="success",
        actor_username="admin",
        skill_slug="demo-skill",
        robot_id=7,
    )

    assert response.total == 1
    assert response.items[0].skill_slug == "demo-skill"
    combined_sql = "\n".join(db.statements)
    assert "rag_skill_audit_log.action" in combined_sql
    assert "rag_skill_audit_log.status" in combined_sql
    assert "rag_skill_audit_log.actor_username" in combined_sql
    assert "rag_skill_audit_log.skill_slug" in combined_sql
    assert "rag_skill_audit_log.robot_id" in combined_sql
