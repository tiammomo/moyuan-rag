"""Robot management service."""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import Knowledge
from app.models.llm import LLM
from app.models.robot import Robot
from app.models.robot_knowledge import RobotKnowledge
from app.models.user import User
from app.schemas.robot import RobotCreate, RobotDetail, RobotListResponse, RobotUpdate
from app.services.skill_service import skill_service


logger = logging.getLogger(__name__)


class RobotService:
    """Robot management service."""

    @staticmethod
    async def build_robot_detail(db: AsyncSession, robot: Robot) -> RobotDetail:
        robot_detail = RobotDetail.model_validate(robot)
        robot_detail.knowledge_ids = await RobotService.get_robot_knowledge_ids(db, robot.id)
        robot_detail.skills = await skill_service.get_robot_bindings(db, robot_id=robot.id)
        return robot_detail

    @staticmethod
    async def create_robot(db: AsyncSession, robot_data: RobotCreate, current_user: User) -> Robot:
        result = await db.execute(
            select(LLM).where(LLM.id == robot_data.chat_llm_id, LLM.model_type == "chat")
        )
        chat_llm = result.scalar_one_or_none()
        if not chat_llm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat LLM model does not exist or has the wrong type.",
            )

        for kb_id in robot_data.knowledge_ids:
            result = await db.execute(select(Knowledge).where(Knowledge.id == kb_id))
            knowledge = result.scalar_one_or_none()
            if not knowledge:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Knowledge base {kb_id} does not exist.",
                )
            if knowledge.user_id != current_user.id and current_user.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You do not have access to knowledge base {kb_id}.",
                )

        new_robot = Robot(
            user_id=current_user.id,
            name=robot_data.name,
            avatar=robot_data.avatar,
            chat_llm_id=robot_data.chat_llm_id,
            rerank_llm_id=robot_data.rerank_llm_id,
            system_prompt=robot_data.system_prompt,
            welcome_msg=robot_data.welcome_message,
            top_k=robot_data.top_k,
            similarity_threshold=robot_data.similarity_threshold,
            enable_rerank=robot_data.enable_rerank if hasattr(robot_data, "enable_rerank") else False,
            temperature=robot_data.temperature,
            max_tokens=robot_data.max_tokens,
            description=robot_data.description,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db.add(new_robot)
        await db.flush()

        for kb_id in robot_data.knowledge_ids:
            db.add(RobotKnowledge(robot_id=new_robot.id, knowledge_id=kb_id))

        await db.commit()
        await db.refresh(new_robot)

        logger.info("Created robot %s (ID: %s)", new_robot.name, new_robot.id)
        return new_robot

    @staticmethod
    async def get_robot_by_id(db: AsyncSession, robot_id: int, current_user: User) -> Robot:
        result = await db.execute(select(Robot).where(Robot.id == robot_id))
        robot = result.scalar_one_or_none()

        if not robot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Robot not found.",
            )

        if robot.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this robot.",
            )

        return robot

    @staticmethod
    async def get_robot_knowledge_ids(db: AsyncSession, robot_id: int) -> List[int]:
        stmt = (
            select(RobotKnowledge.knowledge_id)
            .join(Knowledge, RobotKnowledge.knowledge_id == Knowledge.id)
            .where(RobotKnowledge.robot_id == robot_id)
            .where(Knowledge.status == 1)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_robots(
        db: AsyncSession,
        current_user: User,
        skip: int = 0,
        limit: int = 20,
        keyword: Optional[str] = None,
    ) -> RobotListResponse:
        query = select(Robot)

        if current_user.role != "admin":
            query = query.where(Robot.user_id == current_user.id)

        if keyword:
            query = query.where(Robot.name.ilike(f"%{keyword}%"))

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        robots = result.scalars().all()

        items = [await RobotService.build_robot_detail(db, robot) for robot in robots]
        return RobotListResponse(total=total, items=items)

    @staticmethod
    async def update_robot(
        db: AsyncSession,
        robot_id: int,
        robot_data: RobotUpdate,
        current_user: User,
    ) -> Robot:
        robot = await RobotService.get_robot_by_id(db, robot_id, current_user)

        if robot.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this robot.",
            )

        if robot_data.name is not None:
            robot.name = robot_data.name
        if robot_data.avatar is not None:
            robot.avatar = robot_data.avatar
        if robot_data.chat_llm_id is not None:
            robot.chat_llm_id = robot_data.chat_llm_id
        if robot_data.rerank_llm_id is not None:
            robot.rerank_llm_id = robot_data.rerank_llm_id
        if robot_data.system_prompt is not None:
            robot.system_prompt = robot_data.system_prompt
        if robot_data.welcome_message is not None:
            robot.welcome_msg = robot_data.welcome_message
        if robot_data.top_k is not None:
            robot.top_k = robot_data.top_k
        if robot_data.similarity_threshold is not None:
            robot.similarity_threshold = robot_data.similarity_threshold
        if robot_data.enable_rerank is not None:
            robot.enable_rerank = robot_data.enable_rerank
        if robot_data.temperature is not None:
            robot.temperature = robot_data.temperature
        if robot_data.max_tokens is not None:
            robot.max_tokens = robot_data.max_tokens
        if robot_data.description is not None:
            robot.description = robot_data.description
        if robot_data.status is not None:
            robot.status = robot_data.status

        if robot_data.knowledge_ids is not None:
            await db.execute(delete(RobotKnowledge).where(RobotKnowledge.robot_id == robot_id))
            for kb_id in robot_data.knowledge_ids:
                db.add(RobotKnowledge(robot_id=robot_id, knowledge_id=kb_id))

        robot.updated_at = datetime.now()
        await db.commit()
        await db.refresh(robot)

        logger.info("Updated robot %s (ID: %s)", robot.name, robot.id)
        return robot

    @staticmethod
    async def delete_robot(db: AsyncSession, robot_id: int, current_user: User) -> None:
        robot = await RobotService.get_robot_by_id(db, robot_id, current_user)

        if robot.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this robot.",
            )

        await db.execute(delete(RobotKnowledge).where(RobotKnowledge.robot_id == robot_id))
        await db.delete(robot)
        await db.commit()

        logger.info("Deleted robot %s (ID: %s)", robot.name, robot.id)


robot_service = RobotService()
