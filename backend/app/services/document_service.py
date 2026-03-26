"""
Async document management service.
"""

from __future__ import annotations

import io
import logging
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional

from fastapi import HTTPException, UploadFile, status
from PIL import Image
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.kafka.producer import producer
from app.models.document import Document
from app.models.knowledge import Knowledge
from app.models.user import User
from app.schemas.document import (
    DocumentDetail,
    DocumentListResponse,
    DocumentUploadResponse,
)
from app.utils.es_client import es_client
from app.utils.milvus_client import milvus_client
from app.utils.pipeline_storage import clear_pipeline_artifacts, pipeline_storage
from app.utils.storage import FileStorage

try:
    import magic
except ImportError:
    magic = None


logger = logging.getLogger(__name__)


class DocumentService:
    """Document management workflows."""

    def __init__(self):
        self.file_storage = FileStorage()

    def _get_mime_type(self, file_content: bytes, filename: str) -> str:
        mime_type = None
        if magic:
            try:
                mime_type = magic.from_buffer(file_content, mime=True)
            except Exception as exc:
                logger.warning(f"magic failed to detect MIME type: {exc}")

        if not mime_type:
            mime_type, _ = mimetypes.guess_type(filename)

        return mime_type or "application/octet-stream"

    def _get_image_dimensions(
        self,
        file_content: bytes,
    ) -> tuple[Optional[int], Optional[int]]:
        try:
            with Image.open(io.BytesIO(file_content)) as img:
                return img.width, img.height
        except Exception:
            return None, None

    async def _queue_document_task(
        self,
        document_id: int,
        file_path: str,
        knowledge_id: int,
        file_name: str,
        trigger: str,
    ) -> None:
        queued = await producer.send(
            "rag.document.upload",
            {
                "document_id": document_id,
                "file_path": file_path,
                "task_metadata": {
                    "knowledge_id": knowledge_id,
                    "file_name": file_name,
                    "trigger": trigger,
                },
            },
        )
        if not queued:
            raise RuntimeError(
                f"Failed to publish rag.document.upload for document_id={document_id}"
            )

    async def upload_document(
        self,
        db: AsyncSession,
        knowledge_id: int,
        file: UploadFile,
        current_user: User,
    ) -> DocumentUploadResponse:
        result = await db.execute(select(Knowledge).where(Knowledge.id == knowledge_id))
        knowledge = result.scalar_one_or_none()

        if not knowledge:
            logger.warning(f"Knowledge not found in upload_document: ID={knowledge_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库 [ID={knowledge_id}] 不存在",
            )

        if knowledge.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此知识库",
            )

        file_ext = Path(file.filename).suffix.lower()
        allowed_extensions = [".pdf", ".docx", ".txt", ".md", ".html"]
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"不支持的文件类型: {file_ext}。"
                    f"支持的类型: {', '.join(allowed_extensions)}"
                ),
            )

        file_content = await file.read()
        file_size = len(file_content)
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"文件大小超过限制（最大"
                    f"{settings.MAX_FILE_SIZE / 1024 / 1024:.0f}MB）"
                ),
            )

        mime_type = self._get_mime_type(file_content, file.filename)
        width, height = (None, None)
        if mime_type.startswith("image/"):
            width, height = self._get_image_dimensions(file_content)

        try:
            file_obj = io.BytesIO(file_content)
            relative_path, _ = self.file_storage.save_file(
                file=file_obj,
                original_filename=file.filename,
                knowledge_id=knowledge_id,
            )
        except Exception as exc:
            logger.error(f"Failed to save uploaded document: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="文件保存失败",
            )

        document = Document(
            knowledge_id=knowledge_id,
            file_name=file.filename,
            file_extension=file_ext[1:],
            file_path=relative_path,
            file_size=file_size,
            mime_type=mime_type,
            width=width,
            height=height,
            status="uploading",
            chunk_count=0,
            meta_data={},
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)

        queue_error: str | None = None
        try:
            await self._queue_document_task(
                document_id=document.id,
                file_path=str(relative_path),
                knowledge_id=knowledge_id,
                file_name=file.filename,
                trigger="upload",
            )
            logger.info(f"Queued document upload task: {file.filename} (ID: {document.id})")
        except Exception as exc:
            logger.error(f"Failed to publish upload task to Kafka: {exc}")
            queue_error = str(exc)
            await db.execute(
                update(Document)
                .where(Document.id == document.id)
                .values(
                    status="failed",
                    error_msg=f"Upload queue dispatch failed: {exc}",
                    meta_data=clear_pipeline_artifacts(document.meta_data),
                    updated_at=datetime.now(),
                )
            )
            await db.commit()

        return DocumentUploadResponse(
            document_id=document.id,
            filename=file.filename,
            file_size=file_size,
            preview_url=f"/api/v1/documents/{document.id}/preview",
            mime_type=mime_type,
            width=width,
            height=height,
            task_id=None,
            message=(
                "文档上传成功，正在后台处理中"
                if not queue_error
                else "文档已上传，但任务投递失败，可在文档列表中重试"
            ),
        )

    async def retry_document(
        self,
        db: AsyncSession,
        document_id: int,
        current_user: User,
    ) -> None:
        document = await self.get_document_by_id(db, document_id, current_user)

        if document.status != "failed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"当前文档状态为 {document.status}，无需重试",
            )

        pipeline_storage.delete_document_artifacts(document.id)
        cleaned_meta_data = clear_pipeline_artifacts(document.meta_data)

        await db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(
                status="uploading",
                error_msg=None,
                meta_data=cleaned_meta_data,
                updated_at=datetime.now(),
            )
        )
        await db.commit()
        await db.refresh(document)

        try:
            await self._queue_document_task(
                document_id=document.id,
                file_path=str(document.file_path),
                knowledge_id=document.knowledge_id,
                file_name=document.file_name,
                trigger="retry",
            )
            logger.info(f"Queued retry task for document: {document.file_name} (ID: {document.id})")
        except Exception as exc:
            logger.error(f"Failed to publish retry task to Kafka: {exc}")
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(
                    status="failed",
                    error_msg=f"Retry queue dispatch failed: {exc}",
                    updated_at=datetime.now(),
                )
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="重试任务启动失败",
            )

    async def get_document_by_id(
        self,
        db: AsyncSession,
        document_id: int,
        current_user: User,
    ) -> Document:
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在",
            )

        result = await db.execute(select(Knowledge).where(Knowledge.id == document.knowledge_id))
        knowledge = result.scalar_one_or_none()
        if not knowledge:
            logger.warning(
                f"Knowledge not found for document {document_id}: KB_ID={document.knowledge_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"所属知识库 [ID={document.knowledge_id}] 不存在",
            )

        if knowledge.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此文档",
            )

        return document

    async def get_documents(
        self,
        db: AsyncSession,
        knowledge_id: int,
        current_user: User,
        skip: int = 0,
        limit: int = 20,
        keyword: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> DocumentListResponse:
        logger.info(f"Querying documents for knowledge_id={knowledge_id}, user={current_user.id}")

        knowledge = await db.get(Knowledge, knowledge_id)
        if not knowledge:
            logger.warning(f"Knowledge not found in get_documents: ID={knowledge_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库 [ID={knowledge_id}] 不存在",
            )

        if knowledge.user_id != current_user.id and current_user.role != "admin":
            logger.warning(
                f"Permission denied in get_documents for knowledge_id={knowledge_id}, user={current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此知识库",
            )

        query = select(Document).where(Document.knowledge_id == knowledge_id)
        if keyword:
            query = query.where(Document.file_name.ilike(f"%{keyword}%"))
        if status_filter:
            query = query.where(Document.status == status_filter)

        try:
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar()
        except Exception as exc:
            logger.error(f"Failed to count documents: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="获取文档总数失败",
            )

        try:
            paged_query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
            result = await db.execute(paged_query)
            documents = result.scalars().all()
        except Exception as exc:
            logger.error(f"Failed to query documents: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="查询文档列表失败",
            )

        return DocumentListResponse(
            total=total,
            items=[DocumentDetail.model_validate(doc) for doc in documents],
        )

    async def delete_document(
        self,
        db: AsyncSession,
        document_id: int,
        current_user: User,
    ) -> None:
        document = await self.get_document_by_id(db, document_id, current_user)
        knowledge_id = document.knowledge_id

        try:
            file_path = Path(settings.FILE_STORAGE_PATH) / document.file_path
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted stored file: {file_path}")
        except Exception as exc:
            logger.warning(f"Failed to delete document files for {document_id}: {exc}")

        try:
            pipeline_storage.delete_document_artifacts(document.id)
        except Exception as exc:
            logger.warning(f"Failed to delete pipeline artifacts for {document_id}: {exc}")

        try:
            result = await db.execute(select(Knowledge).where(Knowledge.id == knowledge_id))
            knowledge = result.scalar_one_or_none()
            if knowledge:
                await milvus_client.delete_by_document(knowledge.vector_collection_name, document_id)
                await es_client.delete_by_document(document_id)
                logger.info(f"Deleted vector and search indexes for document_id={document_id}")
        except Exception as exc:
            logger.error(f"Failed to delete vector or search index for {document_id}: {exc}")

        await db.delete(document)
        await db.commit()

        try:
            doc_count_result = await db.execute(
                select(func.count(Document.id)).where(
                    Document.knowledge_id == knowledge_id,
                    Document.status == "completed",
                )
            )
            doc_count = doc_count_result.scalar()

            total_chunks_result = await db.execute(
                select(func.sum(Document.chunk_count)).where(
                    Document.knowledge_id == knowledge_id,
                    Document.status == "completed",
                )
            )
            total_chunks = total_chunks_result.scalar() or 0

            await db.execute(
                update(Knowledge)
                .where(Knowledge.id == knowledge_id)
                .values(document_count=doc_count, total_chunks=total_chunks)
            )
            await db.commit()
            logger.info(f"Updated knowledge statistics for knowledge_id={knowledge_id}")
        except Exception as exc:
            logger.error(f"Failed to update knowledge statistics for {knowledge_id}: {exc}")

        logger.info(f"Deleted document: {document.file_name} (ID: {document.id})")


document_service = DocumentService()
