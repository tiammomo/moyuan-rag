from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.models.robot_skill_binding import RobotSkillBinding
from app.models.skill_audit_log import SkillAuditLog
from app.schemas.chat import ChatResponse
from app.schemas.chat import RetrievedContext
from app.schemas.skill import SkillDetail
from app.schemas.skill import SkillRobotBindingDetail
from app.services.rag_service import rag_service
from app.services.skill_service import skill_service


def _write_skill(
    root: Path,
    *,
    slug: str,
    name: str,
    version: str = "0.1.0",
    allowed_robot_modes: list[str] | None = None,
) -> None:
    skill_root = root / "extracted" / slug / version
    skill_root.mkdir(parents=True, exist_ok=True)
    (skill_root / "prompts").mkdir(parents=True, exist_ok=True)
    (root / "registry").mkdir(parents=True, exist_ok=True)

    constraints = ""
    if allowed_robot_modes is not None:
        constraints_lines = "\n".join(f"    - {mode}" for mode in allowed_robot_modes)
        constraints = f"\nconstraints:\n  allowed_robot_modes:\n{constraints_lines}"

    (skill_root / "skill.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                f"slug: {slug}",
                f"name: {name}",
                f"version: {version}",
                "category: demo",
                f"description: {name} description",
                "entrypoints:",
                "  system_prompt: prompts/system.md",
                "  retrieval_prompt: prompts/retrieval.md",
                "  answer_prompt: prompts/answer.md",
            ]
        )
        + constraints,
        encoding="utf-8",
    )
    (skill_root / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
    (skill_root / "prompts" / "system.md").write_text(f"{name} system guidance", encoding="utf-8")
    (skill_root / "prompts" / "retrieval.md").write_text(f"{name} retrieval guidance", encoding="utf-8")
    (skill_root / "prompts" / "answer.md").write_text(f"{name} answer guidance", encoding="utf-8")


def _write_registry(root: Path, skills: list[dict[str, str]]) -> None:
    (root / "registry").mkdir(parents=True, exist_ok=True)
    (root / "registry" / "installed.json").write_text(
        json.dumps({"skills": skills}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class FakeRowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeScalarResult:
    def __init__(self, scalar):
        self._scalar = scalar

    def scalar_one_or_none(self):
        return self._scalar


class QueueDB:
    def __init__(self, results):
        self._results = list(results)

    async def execute(self, _stmt):
        return self._results.pop(0)


class FakeCountResult:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value


class PersistQueueDB(QueueDB):
    def __init__(self, results):
        super().__init__(results)
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


def _registry_record(slug: str, name: str, version: str = "0.1.0") -> dict[str, str]:
    return {
        "slug": slug,
        "name": name,
        "version": version,
        "description": f"{name} description",
        "category": "demo",
        "source_type": "local",
        "status": "active",
        "install_path": f"extracted/{slug}/{version}",
        "manifest_path": f"extracted/{slug}/{version}/skill.yaml",
        "readme_path": f"extracted/{slug}/{version}/SKILL.md",
        "installed_at": "2026-03-27T12:00:00+08:00",
    }


@pytest.mark.asyncio
async def test_runtime_bundle_collects_skill_prompts(tmp_path: Path):
    original_root = settings.SKILL_INSTALL_ROOT
    settings.SKILL_INSTALL_ROOT = str(tmp_path)
    try:
        _write_skill(tmp_path, slug="alpha-skill", name="Alpha Skill")
        _write_registry(tmp_path, [_registry_record("alpha-skill", "Alpha Skill")])
        binding = SimpleNamespace(
            robot_id=7,
            skill_slug="alpha-skill",
            skill_version="0.1.0",
            priority=100,
            status="active",
            binding_config={"_provenance": {"install_task_id": 12}},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db = QueueDB([FakeRowsResult([(binding, "Demo Robot")])])

        bundle = await skill_service.get_runtime_skill_bundle(db, robot_id=7)
    finally:
        settings.SKILL_INSTALL_ROOT = original_root

    assert [skill.skill_slug for skill in bundle.active_skills] == ["alpha-skill"]
    assert bundle.active_skills[0].provenance_install_task_id == 12
    assert "Alpha Skill::system_prompt" in bundle.system_prompts[0]
    assert "Alpha Skill::retrieval_prompt" in bundle.retrieval_prompts[0]
    assert "Alpha Skill::answer_prompt" in bundle.answer_prompts[0]


@pytest.mark.asyncio
async def test_bind_skill_rejects_incompatible_robot_mode(tmp_path: Path):
    original_root = settings.SKILL_INSTALL_ROOT
    settings.SKILL_INSTALL_ROOT = str(tmp_path)
    try:
        _write_skill(
            tmp_path,
            slug="workflow-only",
            name="Workflow Only",
            allowed_robot_modes=["workflow_runner"],
        )
        _write_registry(tmp_path, [_registry_record("workflow-only", "Workflow Only")])

        robot = SimpleNamespace(id=9, user_id=1, name="Demo Robot")
        db = QueueDB(
            [
                FakeScalarResult(robot),
                FakeRowsResult([]),
            ]
        )

        with pytest.raises(HTTPException) as exc_info:
            await skill_service.bind_skill_to_robot(
                db=db,
                robot_id=9,
                skill_slug="workflow-only",
                payload=SimpleNamespace(priority=None, status="active", binding_config={}),
                current_user=SimpleNamespace(id=1, role="user"),
            )
    finally:
        settings.SKILL_INSTALL_ROOT = original_root

    assert exc_info.value.status_code == 400
    assert "does not support this robot type" in exc_info.value.detail


@pytest.mark.asyncio
async def test_generate_answer_injects_skill_prompts_and_returns_active_skills(monkeypatch):
    captured: dict[str, object] = {}
    active_skills = [
        SkillRobotBindingDetail(
            robot_id=1,
            robot_name="Demo Robot",
            skill_slug="rag-citation-guide",
            skill_name="RAG Citation Guide",
            skill_version="0.1.0",
            category="answering",
            skill_description="Citations first",
            priority=100,
            status="active",
            prompt_keys=["system_prompt", "answer_prompt"],
            binding_config={"_provenance": {"install_task_id": 12}},
            provenance_install_task_id=12,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    ]

    async def fake_call_llm_api(*, db, llm_id, messages, temperature, max_tokens):
        captured["messages"] = messages
        return {
            "answer": "Mock answer",
            "token_usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

    monkeypatch.setattr(rag_service, "_call_llm_api", fake_call_llm_api)

    response = await rag_service.generate_answer(
        db=SimpleNamespace(),
        robot=SimpleNamespace(chat_llm_id=1, system_prompt="Base prompt", temperature=0.7, max_tokens=2000),
        question="What is hybrid retrieval?",
        contexts=[],
        runtime_bundle={
            "active_skills": active_skills,
            "system_prompts": ["[RAG Citation Guide::system_prompt]\nUse citations."],
            "retrieval_prompts": [],
            "answer_prompts": ["[RAG Citation Guide::answer_prompt]\nLead with the answer."],
        },
    )

    system_message = captured["messages"][0]["content"]
    assert "Base prompt" in system_message
    assert "Use citations." in system_message
    assert "Lead with the answer." in system_message
    assert response.active_skills[0].skill_slug == "rag-citation-guide"
    assert response.active_skills[0].provenance_install_task_id == 12


@pytest.mark.asyncio
async def test_chat_with_context_applies_retrieval_skill_guidance(monkeypatch):
    captured: dict[str, str] = {}

    async def fake_build_runtime_skill_bundle(_db, _robot):
        return {
            "active_skills": [],
            "system_prompts": [],
            "retrieval_prompts": ["[Skill::retrieval_prompt]\nFocus on policy names."],
            "answer_prompts": [],
        }

    async def fake_hybrid_retrieve(*, db, robot, knowledge_ids, query, top_k):
        captured["query"] = query
        return []

    async def fake_generate_answer(**kwargs):
        return ChatResponse(
            session_id="session-1",
            question=kwargs["question"],
            answer="ok",
            contexts=[],
            active_skills=[],
            token_usage={},
            response_time=0.01,
        )

    monkeypatch.setattr(rag_service, "build_runtime_skill_bundle", fake_build_runtime_skill_bundle)
    monkeypatch.setattr(rag_service, "hybrid_retrieve", fake_hybrid_retrieve)
    monkeypatch.setattr(rag_service, "generate_answer", fake_generate_answer)

    response = await rag_service.chat_with_context(
        db=SimpleNamespace(),
        robot=SimpleNamespace(id=1, top_k=5),
        knowledge_ids=[1],
        question="公司的报销制度是什么？",
        session_id=None,
        user_id=None,
    )

    assert "Skill Retrieval Guidance" in captured["query"]
    assert response.answer == "ok"


@pytest.mark.asyncio
async def test_bind_skill_writes_audit_log(monkeypatch):
    db = PersistQueueDB([FakeScalarResult(None), FakeCountResult(0)])

    async def fake_get_robot(_db, robot_id, current_user):
        return SimpleNamespace(id=robot_id, user_id=current_user.id, name="Demo Robot")

    async def fake_get_skill_detail(_db, _slug):
        return SkillDetail(
            slug="rag-citation-guide",
            name="RAG Citation Guide",
            version="0.1.0",
            description="Guide",
            category="answering",
            source_type="local",
            status="active",
            install_path="extracted/rag-citation-guide/0.1.0",
            installed_at="2026-03-27T12:00:00+08:00",
            readme_available=True,
        )

    async def fake_get_bindings(_db, robot_id, current_user):
        _ = current_user
        return [
            SkillRobotBindingDetail(
                robot_id=robot_id,
                robot_name="Demo Robot",
                skill_slug="rag-citation-guide",
                skill_name="RAG Citation Guide",
                skill_version="0.1.0",
                category="answering",
                skill_description="Guide",
                priority=100,
                status="active",
                prompt_keys=["system_prompt"],
                binding_config={"_provenance": {"install_task_id": 33}},
                provenance_install_task_id=33,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        ]

    async def fake_get_provenance_task(_db, *, install_task_id, skill_slug):
        _ = skill_slug
        return SimpleNamespace(id=install_task_id)

    monkeypatch.setattr(skill_service, "_get_robot_for_binding", fake_get_robot)
    monkeypatch.setattr(skill_service, "get_skill_detail", fake_get_skill_detail)
    monkeypatch.setattr(skill_service, "get_robot_skill_bindings", fake_get_bindings)
    monkeypatch.setattr(skill_service, "_get_binding_provenance_task", fake_get_provenance_task)

    await skill_service.bind_skill_to_robot(
        db=db,
        robot_id=1,
        skill_slug="rag-citation-guide",
        payload=SimpleNamespace(priority=None, status="active", binding_config={}, install_task_id=33),
        current_user=SimpleNamespace(id=1, username="alice", role="user"),
    )

    assert any(isinstance(item, RobotSkillBinding) for item in db.added)
    assert any(
        isinstance(item, SkillAuditLog)
        and item.action == "skill.bind"
        and item.status == "success"
        and item.install_task_id == 33
        for item in db.added
    )
    persisted_binding = next(item for item in db.added if isinstance(item, RobotSkillBinding))
    assert persisted_binding.binding_config["_provenance"]["install_task_id"] == 33


@pytest.mark.asyncio
async def test_update_and_unbind_write_audit_logs(monkeypatch):
    binding = RobotSkillBinding(
        robot_id=1,
        skill_slug="rag-citation-guide",
        skill_version="0.1.0",
        priority=100,
        status="active",
        binding_config={},
    )
    binding.id = 10

    async def fake_get_robot(_db, robot_id, current_user):
        return SimpleNamespace(id=robot_id, user_id=current_user.id, name="Demo Robot")

    async def fake_get_skill_detail(_db, _slug):
        return SkillDetail(
            slug="rag-citation-guide",
            name="RAG Citation Guide",
            version="0.1.0",
            description="Guide",
            category="answering",
            source_type="local",
            status="active",
            install_path="extracted/rag-citation-guide/0.1.0",
            installed_at="2026-03-27T12:00:00+08:00",
            readme_available=True,
        )

    async def fake_get_bindings(_db, robot_id, current_user):
        _ = current_user
        return [
            SkillRobotBindingDetail(
                robot_id=robot_id,
                robot_name="Demo Robot",
                skill_slug="rag-citation-guide",
                skill_name="RAG Citation Guide",
                skill_version="0.1.0",
                category="answering",
                skill_description="Guide",
                priority=50,
                status="disabled",
                prompt_keys=["system_prompt"],
                binding_config={"_provenance": {"install_task_id": 44}},
                provenance_install_task_id=44,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        ]

    async def fake_get_provenance_task(_db, *, install_task_id, skill_slug):
        _ = skill_slug
        return SimpleNamespace(id=install_task_id)

    monkeypatch.setattr(skill_service, "_get_robot_for_binding", fake_get_robot)
    monkeypatch.setattr(skill_service, "get_skill_detail", fake_get_skill_detail)
    monkeypatch.setattr(skill_service, "get_robot_skill_bindings", fake_get_bindings)
    monkeypatch.setattr(skill_service, "_get_binding_provenance_task", fake_get_provenance_task)

    update_db = PersistQueueDB([FakeScalarResult(binding)])
    await skill_service.update_robot_skill_binding(
        db=update_db,
        robot_id=1,
        skill_slug="rag-citation-guide",
        payload=SimpleNamespace(priority=50, status="disabled", binding_config={}, install_task_id=44),
        current_user=SimpleNamespace(id=1, username="alice", role="user"),
    )

    unbind_db = PersistQueueDB([FakeScalarResult(binding)])
    monkeypatch.setattr(skill_service, "_get_robot_for_binding", fake_get_robot)
    await skill_service.unbind_skill_from_robot(
        db=unbind_db,
        robot_id=1,
        skill_slug="rag-citation-guide",
        current_user=SimpleNamespace(id=1, username="alice", role="user"),
    )

    assert any(
        isinstance(item, SkillAuditLog)
        and item.action == "skill.update_binding"
        and item.status == "success"
        and item.install_task_id == 44
        for item in update_db.added
    )
    assert any(
        isinstance(item, SkillAuditLog) and item.action == "skill.unbind" and item.status == "success"
        for item in unbind_db.added
    )
