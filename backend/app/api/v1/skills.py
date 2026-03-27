"""
Skills API routes for the bootstrap slice.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.skill import SkillInstallResponse, SkillListResponse, SkillRemoteInstallRequest
from app.services.skill_service import skill_service


router = APIRouter()


@router.get("", response_model=SkillListResponse, summary="List installed skills")
async def list_skills(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = await skill_service.list_skills(db)
    return SkillListResponse(total=len(items), items=items)


@router.post("/install-local", response_model=SkillInstallResponse, summary="Install a local skill package")
async def install_local_skill(
    package: UploadFile = File(..., description="Local skill package zip file"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return await skill_service.install_local_skill(db, package, current_user)


@router.post("/install-remote", summary="Install a remote skill package")
async def install_remote_skill(
    request: SkillRemoteInstallRequest,
    current_user: User = Depends(require_admin),
):
    await skill_service.install_remote_skill(request.package_url, request.checksum)
    return {"message": "Remote install request accepted"}


@router.get("/{skill_slug}", summary="Get installed skill detail")
async def get_skill_detail(
    skill_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await skill_service.get_skill_detail(db, skill_slug)
