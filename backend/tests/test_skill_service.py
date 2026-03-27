import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
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


class FakeSession:
    def __init__(self, results=None):
        self._results = list(results or [])
        self.added = []
        self.deleted = []
        self.commits = 0
        self.rollbacks = 0
        self._next_id = 1

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
        return None

    async def rollback(self):
        self.rollbacks += 1

    async def execute(self, _stmt):
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
