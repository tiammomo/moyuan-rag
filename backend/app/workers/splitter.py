import asyncio
import os
import sys

from sqlalchemy import select, update

sys.path.append(os.getcwd())

from app.core.config import settings
from app.core.worker_logger import get_worker_logger
from app.db.session import AsyncSessionLocal
from app.kafka.consumer import KafkaConsumer
from app.kafka.producer import producer
from app.models.document import Document
from app.models.knowledge import Knowledge
from app.utils.pipeline_storage import (
    clear_pipeline_artifacts,
    get_pipeline_artifact,
    pipeline_storage,
    set_pipeline_artifact,
)
from app.utils.text_splitter import TextSplitter

logger = get_worker_logger("splitter")
SPLITTER_REPLAYABLE_STATUSES = {"parsing", "splitting"}


async def process_parsed(data: dict) -> None:
    doc_id = data.get("document_id")
    file_path = data.get("file_path")
    task_metadata = data.get("task_metadata") or {}
    knowledge_id = task_metadata.get("knowledge_id", data.get("knowledge_id"))
    file_name = task_metadata.get("file_name", data.get("file_name"))

    logger.info(
        f"Starting split task for document_id={doc_id}, file_name={file_name}, file_path={file_path}"
    )

    try:
        async with AsyncSessionLocal() as db:
            doc_result = await db.execute(select(Document).where(Document.id == doc_id))
            document = doc_result.scalar_one_or_none()
            if not document:
                logger.warning(f"Document not found, skipping split task: document_id={doc_id}")
                return
            if document.status not in SPLITTER_REPLAYABLE_STATUSES:
                logger.info(
                    f"Skipping split task for document_id={doc_id} because status={document.status}"
                )
                return

            knowledge_result = await db.execute(
                select(Knowledge).where(Knowledge.id == knowledge_id)
            )
            knowledge = knowledge_result.scalar_one_or_none()
            if not knowledge:
                raise ValueError(f"Knowledge base not found: knowledge_id={knowledge_id}")

            parsed_artifact = get_pipeline_artifact(document.meta_data, "parsed_content")
            parsed_file_path = file_path or (parsed_artifact or {}).get("file_path")
            if not parsed_file_path:
                raise ValueError("Missing parsed content artifact path")

            await db.execute(
                update(Document)
                .where(Document.id == doc_id)
                .values(status="splitting", error_msg=None)
            )
            await db.commit()

            chunk_size = knowledge.chunk_size or settings.DEFAULT_CHUNK_SIZE
            chunk_overlap = knowledge.chunk_overlap or settings.DEFAULT_CHUNK_OVERLAP

        content = await asyncio.to_thread(pipeline_storage.read_text, parsed_file_path)
        splitter = TextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = await asyncio.to_thread(splitter.split_documents, content)

        if not chunks:
            raise ValueError("No chunks were generated from parsed content")

        chunks_artifact_path = await asyncio.to_thread(
            pipeline_storage.save_json,
            doc_id,
            "chunks",
            chunks,
        )

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Document).where(Document.id == doc_id))
            document = result.scalar_one_or_none()
            if not document:
                logger.warning(
                    f"Document deleted before chunk artifact metadata could be stored: document_id={doc_id}"
                )
                await asyncio.to_thread(pipeline_storage.delete_document_artifacts, doc_id)
                return

            meta_data = set_pipeline_artifact(
                document.meta_data,
                "chunks",
                chunks_artifact_path,
                stage="splitting",
                chunk_count=len(chunks),
                source_file_path=task_metadata.get("source_file_path"),
            )
            await db.execute(
                update(Document)
                .where(Document.id == doc_id)
                .values(meta_data=meta_data, error_msg=None)
            )
            await db.commit()

        queued = await producer.send(
            "rag.document.chunks",
            {
                "document_id": doc_id,
                "file_path": chunks_artifact_path,
                "task_metadata": {
                    "knowledge_id": knowledge_id,
                    "file_name": file_name,
                    "artifact_type": "chunks",
                    "chunk_count": len(chunks),
                    "source_file_path": task_metadata.get("source_file_path"),
                },
            },
        )
        if not queued:
            raise RuntimeError(
                f"Failed to publish rag.document.chunks for document_id={doc_id}"
            )

        logger.info(
            f"Split task completed for document_id={doc_id}, chunk_count={len(chunks)}, chunks_artifact_path={chunks_artifact_path}"
        )

    except Exception as exc:
        logger.exception(f"Failed to split document_id={doc_id}: {exc}")
        await asyncio.to_thread(pipeline_storage.delete_document_artifacts, doc_id)
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Document).where(Document.id == doc_id))
            document = result.scalar_one_or_none()
            meta_data = clear_pipeline_artifacts(document.meta_data if document else None)
            await db.execute(
                update(Document)
                .where(Document.id == doc_id)
                .values(
                    status="failed",
                    error_msg=f"Split failed: {exc}",
                    meta_data=meta_data,
                )
            )
            await db.commit()


async def heartbeat() -> None:
    while True:
        logger.info("Splitter worker heartbeat")
        await asyncio.sleep(60)


async def main() -> None:
    logger.info("Starting splitter worker")
    consumer = KafkaConsumer("rag.document.parsed", "splitter_group", process_parsed)
    try:
        await asyncio.gather(consumer.start(), producer.start(), heartbeat())
    except Exception as exc:
        logger.critical(f"Splitter worker exited unexpectedly: {exc}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
