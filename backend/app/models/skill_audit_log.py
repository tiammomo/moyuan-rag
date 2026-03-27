"""Audit trail model for skill operations."""

from sqlalchemy import BigInteger, Column, DateTime, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func

from app.db.session import Base


class SkillAuditLog(Base):
    __tablename__ = "rag_skill_audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    action = Column(String(50), nullable=False, index=True)
    target_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="success", index=True)
    actor_user_id = Column(BigInteger, nullable=True, index=True)
    actor_username = Column(String(50), nullable=True)
    actor_role = Column(String(20), nullable=True)
    robot_id = Column(BigInteger, nullable=True, index=True)
    skill_slug = Column(String(100), nullable=True, index=True)
    skill_version = Column(String(50), nullable=True)
    install_task_id = Column(BigInteger, nullable=True, index=True)
    message = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<SkillAuditLog(id={self.id}, action={self.action}, status={self.status})>"
