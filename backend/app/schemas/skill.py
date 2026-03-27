"""
Pydantic schemas for the skills bootstrap slice.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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
    skill_version: str
    priority: int
    status: str
    binding_config: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class SkillDetail(SkillListItem):
    manifest: Dict[str, Any] = Field(default_factory=dict)
    readme_content: Optional[str] = None
    prompts: List[SkillPromptFile] = Field(default_factory=list)
    bound_robots: List[SkillRobotBindingDetail] = Field(default_factory=list)


class SkillInstallResponse(BaseModel):
    message: str
    skill: SkillDetail


class SkillRemoteInstallRequest(BaseModel):
    package_url: str = Field(..., min_length=1)
    checksum: Optional[str] = None


class SkillBindingCreate(BaseModel):
    priority: Optional[int] = Field(default=None, ge=1, le=9999)
    status: str = Field(default="active")
    binding_config: Dict[str, Any] = Field(default_factory=dict)


class SkillBindingUpdate(BaseModel):
    priority: Optional[int] = Field(default=None, ge=1, le=9999)
    status: Optional[str] = None
    binding_config: Optional[Dict[str, Any]] = None
