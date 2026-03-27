"""
Robot skill binding routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.skill import SkillBindingCreate, SkillBindingUpdate, SkillRobotBindingDetail
from app.services.skill_service import skill_service


router = APIRouter()


@router.get("/{robot_id}/skills", response_model=list[SkillRobotBindingDetail], summary="List robot skill bindings")
async def get_robot_skills(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await skill_service.get_robot_skill_bindings(db, robot_id, current_user)


@router.post("/{robot_id}/skills/{skill_slug}", response_model=SkillRobotBindingDetail, summary="Bind a skill to a robot")
async def bind_robot_skill(
    robot_id: int,
    skill_slug: str,
    payload: SkillBindingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await skill_service.bind_skill_to_robot(db, robot_id, skill_slug, payload, current_user)


@router.put("/{robot_id}/skills/{skill_slug}", response_model=SkillRobotBindingDetail, summary="Update a robot skill binding")
async def update_robot_skill(
    robot_id: int,
    skill_slug: str,
    payload: SkillBindingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await skill_service.update_robot_skill_binding(db, robot_id, skill_slug, payload, current_user)


@router.delete("/{robot_id}/skills/{skill_slug}", summary="Remove a skill from a robot")
async def delete_robot_skill(
    robot_id: int,
    skill_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await skill_service.unbind_skill_from_robot(db, robot_id, skill_slug, current_user)
    return {"message": "Skill binding removed"}
