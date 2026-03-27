"""
Robot to skill binding model.
"""

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func

from app.db.session import Base


class RobotSkillBinding(Base):
    """Stores which skills are explicitly bound to a robot."""

    __tablename__ = "rag_robot_skill_binding"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    robot_id = Column(BigInteger, nullable=False, index=True)
    skill_slug = Column(String(100), nullable=False)
    skill_version = Column(String(50), nullable=False)
    binding_config = Column(JSON, nullable=True)
    priority = Column(Integer, default=100, nullable=False)
    status = Column(String(20), default="active", nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("robot_id", "skill_slug", name="uk_robot_skill"),
    )

    def __repr__(self) -> str:
        return f"<RobotSkillBinding(robot_id={self.robot_id}, skill_slug={self.skill_slug})>"
