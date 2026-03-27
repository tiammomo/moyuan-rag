"""Robot management API routes."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.robot import (
    RetrievalTestRequest,
    RetrievalTestResponse,
    RetrievalTestResultItem,
    RobotBrief,
    RobotCreate,
    RobotDetail,
    RobotListResponse,
    RobotUpdate,
)
from app.services.rag_service import rag_service
from app.services.robot_service import robot_service


router = APIRouter()

rate_limiter = defaultdict(list)


def check_rate_limit(user_id: int):
    now = time.time()
    rate_limiter[user_id] = [stamp for stamp in rate_limiter[user_id] if now - stamp < 60]
    if len(rate_limiter[user_id]) >= 30:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Limit is 30 requests per minute.",
        )
    rate_limiter[user_id].append(now)


@router.post("/{robot_id}/retrieval-test", response_model=RetrievalTestResponse, summary="Robot retrieval test")
async def retrieval_test(
    robot_id: int,
    test_data: RetrievalTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_rate_limit(current_user.id)

    robot = await robot_service.get_robot_by_id(db, robot_id, current_user)
    knowledge_ids = await robot_service.get_robot_knowledge_ids(db, robot_id)

    if not knowledge_ids:
        return RetrievalTestResponse(results=[])

    contexts = await rag_service.hybrid_retrieve(
        db=db,
        robot=robot,
        knowledge_ids=knowledge_ids,
        query=test_data.query,
        top_k=test_data.top_k,
    )

    results = [
        RetrievalTestResultItem(
            id=context.chunk_id,
            score=context.score,
            content=context.content,
            document_id=context.document_id,
            filename=context.filename,
        )
        for context in contexts
        if context.score >= test_data.threshold
    ]
    return RetrievalTestResponse(results=results)


@router.post("", response_model=RobotDetail, summary="Create a robot")
async def create_robot(
    robot_data: RobotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    robot = await robot_service.create_robot(db, robot_data, current_user)
    return await robot_service.build_robot_detail(db, robot)


@router.get("", response_model=RobotListResponse, summary="List robots")
async def get_robots(
    skip: int = Query(0, ge=0, description="Skip count"),
    limit: int = Query(20, ge=1, le=100, description="Limit"),
    keyword: Optional[str] = Query(None, description="Keyword"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await robot_service.get_robots(db, current_user, skip, limit, keyword)


@router.get("/brief", response_model=list[RobotBrief], summary="List robot briefs")
async def get_robots_brief(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    robots = await robot_service.get_robots(db, current_user, skip=0, limit=100)
    return [RobotBrief.model_validate(robot) for robot in robots.items]


@router.get("/{robot_id}", response_model=RobotDetail, summary="Get robot detail")
async def get_robot(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    robot = await robot_service.get_robot_by_id(db, robot_id, current_user)
    return await robot_service.build_robot_detail(db, robot)


@router.put("/{robot_id}", response_model=RobotDetail, summary="Update a robot")
async def update_robot(
    robot_id: int,
    robot_data: RobotUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated_robot = await robot_service.update_robot(db, robot_id, robot_data, current_user)
    return await robot_service.build_robot_detail(db, updated_robot)


@router.delete("/{robot_id}", summary="Delete a robot")
async def delete_robot(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await robot_service.delete_robot(db, robot_id, current_user)
    return {"message": "Robot deleted successfully"}
