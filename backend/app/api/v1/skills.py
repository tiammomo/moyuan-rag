"""
Skills API routes for the bootstrap slice.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.skill import (
    SkillAuditLogListResponse,
    SkillInstallResponse,
    SkillInstallTaskListResponse,
    SkillListResponse,
    SkillRemoteInstallRequest,
)
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    await skill_service.install_remote_skill(
        db,
        package_url=request.package_url,
        checksum=request.checksum,
        signature=request.signature,
        signature_algorithm=request.signature_algorithm,
        current_user=current_user,
    )
    return {"message": "Remote install request accepted"}


@router.get("/install-tasks", response_model=SkillInstallTaskListResponse, summary="List skill install tasks")
async def list_install_tasks(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    status_filter: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    _ = current_user
    return await skill_service.list_install_tasks(db, skip=skip, limit=limit, status_filter=status_filter)


@router.get("/audit-logs", response_model=SkillAuditLogListResponse, summary="List skill audit logs")
async def list_audit_logs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    action_filter: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    _ = current_user
    return await skill_service.list_audit_logs(db, skip=skip, limit=limit, action_filter=action_filter)


@router.get("/{skill_slug}", summary="Get installed skill detail")
async def get_skill_detail(
    skill_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await skill_service.get_skill_detail(db, skill_slug)
