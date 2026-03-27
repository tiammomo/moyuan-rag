import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.core.config import settings
from app.services.skill_service import skill_service


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
        response = await skill_service.install_local_skill(
            db=SimpleNamespace(execute=None),
            package=upload,
            current_user=SimpleNamespace(username="admin"),
        )
        registry = json.loads((tmp_path / "registry" / "installed.json").read_text(encoding="utf-8"))
    finally:
        settings.SKILL_INSTALL_ROOT = original_root

    assert response.skill.slug == "local-demo"
    assert registry["skills"][0]["slug"] == "local-demo"


@pytest.mark.asyncio
async def test_remote_install_rejected_when_disabled():
    original_flag = settings.ENABLE_REMOTE_SKILL_INSTALL
    settings.ENABLE_REMOTE_SKILL_INSTALL = False
    try:
        with pytest.raises(HTTPException) as exc_info:
            await skill_service.install_remote_skill("https://example.com/demo.zip", None)
    finally:
        settings.ENABLE_REMOTE_SKILL_INSTALL = original_flag

    assert exc_info.value.status_code == 403
