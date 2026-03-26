import asyncio
import os
import sys

from sqlalchemy import select, update

sys.path.append(os.getcwd())

from app.core.worker_logger import get_worker_logger
from app.db.session import AsyncSessionLocal
from app.kafka.consumer import KafkaConsumer
from app.kafka.producer import producer
from app.models.document import Document
from app.utils.file_parser import file_parser
from app.utils.pipeline_storage import (
    clear_pipeline_artifacts,
    pipeline_storage,
    set_pipeline_artifact,
)

logger = get_worker_logger("parser")
PARSER_REPLAYABLE_STATUSES = {"uploading", "parsing"}


async def process_upload(data: dict) -> None:
    doc_id = data.get("document_id")
    file_path = data.get("file_path")
    task_metadata = data.get("task_metadata") or {}
    knowledge_id = task_metadata.get("knowledge_id", data.get("knowledge_id"))
    file_name = task_metadata.get("file_name", data.get("file_name"))

    logger.info(
        f"Starting parse task for document_id={doc_id}, file_name={file_name}, file_path={file_path}"
    )

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Document).where(Document.id == doc_id))
            document = result.scalar_one_or_none()
            if not document:
                logger.warning(f"Document not found, skipping parse task: document_id={doc_id}")
                return
            if document.status not in PARSER_REPLAYABLE_STATUSES:
                logger.info(
                    f"Skipping parse task for document_id={doc_id} because status={document.status}"
                )
                return

            document.meta_data = clear_pipeline_artifacts(document.meta_data)
            await db.execute(
                update(Document)
                .where(Document.id == doc_id)
                .values(status="parsing", error_msg=None, meta_data=document.meta_data)
            )
            await db.commit()

        full_path = pipeline_storage.resolve(file_path)
        loop = asyncio.get_running_loop()
        content = await loop.run_in_executor(None, file_parser.parse_file, full_path)

        if not content:
            raise ValueError("Parsed document content is empty")

        parsed_artifact_path = await asyncio.to_thread(
            pipeline_storage.save_text,
            doc_id,
            "parsed_content",
            content,
        )

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Document).where(Document.id == doc_id))
            document = result.scalar_one_or_none()
            if not document:
                logger.warning(
                    f"Document deleted before parsed artifact metadata could be stored: document_id={doc_id}"
                )
                await asyncio.to_thread(pipeline_storage.delete_document_artifacts, doc_id)
                return

            meta_data = set_pipeline_artifact(
                document.meta_data,
                "parsed_content",
                parsed_artifact_path,
                stage="parsing",
                source_file_path=file_path,
            )
            await db.execute(
                update(Document)
                .where(Document.id == doc_id)
                .values(meta_data=meta_data, error_msg=None)
            )
            await db.commit()

        queued = await producer.send(
            "rag.document.parsed",
            {
                "document_id": doc_id,
                "file_path": parsed_artifact_path,
                "task_metadata": {
                    "knowledge_id": knowledge_id,
                    "file_name": file_name,
                    "artifact_type": "parsed_content",
                    "source_file_path": file_path,
                },
            },
        )
        if not queued:
            raise RuntimeError(
                f"Failed to publish rag.document.parsed for document_id={doc_id}"
            )

        logger.info(
            f"Parse task completed for document_id={doc_id}, parsed_artifact_path={parsed_artifact_path}"
        )

    except Exception as exc:
        logger.exception(f"Failed to parse document_id={doc_id}: {exc}")
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
                    error_msg=f"Parse failed: {exc}",
                    meta_data=meta_data,
                )
            )
            await db.commit()


async def heartbeat() -> None:
    while True:
        logger.info("Parser worker heartbeat")
        await asyncio.sleep(60)


async def main() -> None:
    logger.info("Starting parser worker")
    consumer = KafkaConsumer("rag.document.upload", "parser_group", process_upload)
    try:
        await asyncio.gather(consumer.start(), producer.start(), heartbeat())
    except Exception as exc:
        logger.critical(f"Parser worker exited unexpectedly: {exc}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
