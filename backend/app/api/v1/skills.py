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
    SkillInstallTaskActionResponse,
    SkillInstallTaskInfo,
    SkillInstallTaskListResponse,
    SkillListResponse,
    SkillRemoteInstallRequest,
    SkillRemoteInstallResponse,
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


@router.post(
    "/install-remote",
    response_model=SkillRemoteInstallResponse,
    summary="Install a remote skill package",
)
async def install_remote_skill(
    request: SkillRemoteInstallRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    task = await skill_service.install_remote_skill(
        db,
        package_url=request.package_url,
        checksum=request.checksum,
        signature=request.signature,
        signature_algorithm=request.signature_algorithm,
        current_user=current_user,
    )
    return {
        "message": "Remote install request completed",
        "install_task_id": getattr(task, "id", None),
        "status": getattr(task, "status", None),
        "installed_skill_slug": getattr(task, "installed_skill_slug", None),
        "installed_skill_version": getattr(task, "installed_skill_version", None),
    }


@router.get("/install-tasks", response_model=SkillInstallTaskListResponse, summary="List skill install tasks")
async def list_install_tasks(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    status_filter: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    skill_slug: str | None = Query(default=None),
    requested_by_username: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    _ = current_user
    return await skill_service.list_install_tasks(
        db,
        skip=skip,
        limit=limit,
        status_filter=status_filter,
        source_type=source_type,
        skill_slug=skill_slug,
        requested_by_username=requested_by_username,
    )


@router.get("/install-tasks/{task_id}", response_model=SkillInstallTaskInfo, summary="Get a skill install task")
async def get_install_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    _ = current_user
    return await skill_service.get_install_task(db, task_id)


@router.post(
    "/install-tasks/{task_id}/retry",
    response_model=SkillInstallTaskActionResponse,
    summary="Retry a remote skill install task",
)
async def retry_install_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return await skill_service.retry_install_task(db, task_id, current_user)


@router.post(
    "/install-tasks/{task_id}/cancel",
    response_model=SkillInstallTaskActionResponse,
    summary="Cancel a remote skill install task",
)
async def cancel_install_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return await skill_service.cancel_install_task(db, task_id, current_user)


@router.get("/audit-logs", response_model=SkillAuditLogListResponse, summary="List skill audit logs")
async def list_audit_logs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    action_filter: str | None = Query(default=None),
    status_filter: str | None = Query(default=None),
    actor_username: str | None = Query(default=None),
    skill_slug: str | None = Query(default=None),
    robot_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    _ = current_user
    return await skill_service.list_audit_logs(
        db,
        skip=skip,
        limit=limit,
        action_filter=action_filter,
        status_filter=status_filter,
        actor_username=actor_username,
        skill_slug=skill_slug,
        robot_id=robot_id,
    )


@router.get("/{skill_slug}", summary="Get installed skill detail")
async def get_skill_detail(
    skill_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await skill_service.get_skill_detail(db, skill_slug)
