"""
Pydantic schemas for the skills bootstrap slice.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SkillListItem(BaseModel):
    slug: str
    name: str
    version: str
    description: Optional[str] = None
    category: Optional[str] = None
    source_type: str = "local"
    status: str = "active"
    install_path: str
    installed_at: Optional[str] = None
    readme_available: bool = False
    bound_robot_count: int = 0


class SkillListResponse(BaseModel):
    total: int
    items: List[SkillListItem]


class SkillPromptFile(BaseModel):
    key: str
    path: str
    content: str


class SkillRobotBindingDetail(BaseModel):
    robot_id: int
    robot_name: Optional[str] = None
    skill_slug: str
    skill_name: Optional[str] = None
    skill_version: str
    category: Optional[str] = None
    skill_description: Optional[str] = None
    priority: int
    status: str
    prompt_keys: List[str] = Field(default_factory=list)
    binding_config: Dict[str, Any] = Field(default_factory=dict)
    provenance_install_task_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class SkillInstalledVariantInfo(BaseModel):
    version: str
    install_path: str
    manifest_path: str
    readme_available: bool = False
    is_current: bool = False
    installed_at: Optional[str] = None
    prompt_keys: List[str] = Field(default_factory=list)
    bound_robot_count: int = 0
    bound_robot_ids: List[int] = Field(default_factory=list)


class SkillDetail(SkillListItem):
    manifest: Dict[str, Any] = Field(default_factory=dict)
    readme_content: Optional[str] = None
    prompts: List[SkillPromptFile] = Field(default_factory=list)
    bound_robots: List[SkillRobotBindingDetail] = Field(default_factory=list)
    installed_variants: List[SkillInstalledVariantInfo] = Field(default_factory=list)


class SkillInstallResponse(BaseModel):
    message: str
    skill: SkillDetail
    install_task_id: Optional[int] = None


class SkillRemoteInstallRequest(BaseModel):
    package_url: str = Field(..., min_length=1)
    checksum: Optional[str] = None
    signature: Optional[str] = None
    signature_algorithm: Optional[str] = None


class SkillRemoteInstallResponse(BaseModel):
    message: str
    install_task_id: Optional[int] = None
    status: Optional[str] = None
    installed_skill_slug: Optional[str] = None
    installed_skill_version: Optional[str] = None


class SkillBindingCreate(BaseModel):
    priority: Optional[int] = Field(default=None, ge=1, le=9999)
    status: str = Field(default="active")
    binding_config: Dict[str, Any] = Field(default_factory=dict)
    install_task_id: Optional[int] = Field(default=None, ge=1)


class SkillBindingUpdate(BaseModel):
    priority: Optional[int] = Field(default=None, ge=1, le=9999)
    status: Optional[str] = None
    binding_config: Optional[Dict[str, Any]] = None
    install_task_id: Optional[int] = Field(default=None, ge=1)


class RuntimeSkillPromptBundle(BaseModel):
    active_skills: List[SkillRobotBindingDetail] = Field(default_factory=list)
    system_prompts: List[str] = Field(default_factory=list)
    retrieval_prompts: List[str] = Field(default_factory=list)
    answer_prompts: List[str] = Field(default_factory=list)


class SkillInstallTaskInfo(BaseModel):
    id: int
    source_type: str
    package_name: Optional[str] = None
    package_url: Optional[str] = None
    package_checksum: Optional[str] = None
    package_signature: Optional[str] = None
    signature_algorithm: Optional[str] = None
    requested_by_user_id: Optional[int] = None
    requested_by_username: Optional[str] = None
    status: str
    installed_skill_slug: Optional[str] = None
    installed_skill_version: Optional[str] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    finished_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SkillInstallTaskListResponse(BaseModel):
    total: int
    items: List[SkillInstallTaskInfo]


class SkillInstallTaskActionResponse(BaseModel):
    message: str
    task: SkillInstallTaskInfo


class SkillAuditLogEntry(BaseModel):
    id: int
    action: str
    target_type: str
    status: str
    actor_user_id: Optional[int] = None
    actor_username: Optional[str] = None
    actor_role: Optional[str] = None
    robot_id: Optional[int] = None
    skill_slug: Optional[str] = None
    skill_version: Optional[str] = None
    install_task_id: Optional[int] = None
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SkillAuditLogListResponse(BaseModel):
    total: int
    items: List[SkillAuditLogEntry]
