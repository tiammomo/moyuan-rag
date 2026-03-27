"""Skill install task persistence model."""

from sqlalchemy import BigInteger, Column, DateTime, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func

from app.db.session import Base


class SkillInstallTask(Base):
    __tablename__ = "rag_skill_install_task"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source_type = Column(String(20), nullable=False, default="local")
    package_name = Column(String(255), nullable=True)
    package_url = Column(String(500), nullable=True)
    package_checksum = Column(String(128), nullable=True)
    package_signature = Column(Text, nullable=True)
    signature_algorithm = Column(String(50), nullable=True)
    requested_by_user_id = Column(BigInteger, nullable=True, index=True)
    requested_by_username = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    installed_skill_slug = Column(String(100), nullable=True, index=True)
    installed_skill_version = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    finished_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<SkillInstallTask(id={self.id}, source_type={self.source_type}, status={self.status})>"
