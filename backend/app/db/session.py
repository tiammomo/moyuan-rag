"""
Database session management and optional bootstrap seed data.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)


engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)


AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


Base = declarative_base()


async def init_db() -> None:
    """Seed optional bootstrap data after migrations have been applied."""
    from app.core.security import get_password_hash
    from app.models.knowledge import Knowledge
    from app.models.llm import LLM
    from app.models.user import User

    if not settings.CREATE_DEFAULT_ADMIN:
        logger.info("Skipping bootstrap seed data because CREATE_DEFAULT_ADMIN is disabled")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.username == settings.DEFAULT_ADMIN_USERNAME)
        )
        admin = result.scalar_one_or_none()
        if not admin:
            admin = User(
                username=settings.DEFAULT_ADMIN_USERNAME,
                email=settings.DEFAULT_ADMIN_EMAIL,
                password_hash=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                role="admin",
                status=1,
            )
            session.add(admin)
            await session.flush()
            logger.info(f"Created default admin user: {admin.username} (ID: {admin.id})")

        result = await session.execute(
            select(LLM).where(
                LLM.user_id == admin.id,
                LLM.provider == "local",
                LLM.model_type == "embedding",
                LLM.model_name == "qwen-v1",
            )
        )
        llm = result.scalar_one_or_none()
        if not llm:
            llm = LLM(
                user_id=admin.id,
                name="Default Embedding",
                provider="local",
                model_name="qwen-v1",
                model_type="embedding",
                status=1,
            )
            session.add(llm)
            await session.flush()
            logger.info(f"Created default embedding model (ID: {llm.id})")

        result = await session.execute(
            select(Knowledge).where(
                Knowledge.user_id == admin.id,
                Knowledge.name == "Sample Knowledge Base",
            )
        )
        kb = result.scalar_one_or_none()
        if not kb:
            kb = Knowledge(
                user_id=admin.id,
                name="Sample Knowledge Base",
                description="Automatically created bootstrap knowledge base",
                embed_llm_id=llm.id,
                vector_collection_name=f"kb_{admin.id}_default",
                status=1,
            )
            session.add(kb)
            logger.info("Created default knowledge base for bootstrap")

        await session.commit()

    logger.info("Bootstrap seed data check completed")


async def get_db() -> AsyncSession:
    """FastAPI dependency for an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as exc:
            logger.error(f"Database session error: {exc}")
            raise
        finally:
            await session.close()
