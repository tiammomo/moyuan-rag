import asyncio
import os
import sys
from typing import Any, Dict, List

import numpy as np
from sqlalchemy import func, select, update

sys.path.append(os.getcwd())

from app.core.exceptions import VectorizationFailedException
from app.core.llm.factory import LLMFactory
from app.core.security import api_key_crypto
from app.core.worker_logger import get_worker_logger
from app.db.session import AsyncSessionLocal
from app.kafka.consumer import KafkaConsumer
from app.models.apikey import APIKey
from app.models.document import Document
from app.models.knowledge import Knowledge
from app.models.llm import LLM
from app.utils.embedding import get_embedding_model
from app.utils.es_client import es_client
from app.utils.milvus_client import milvus_client
from app.utils.pipeline_storage import (
    clear_pipeline_artifacts,
    get_pipeline_artifact,
    pipeline_storage,
)

logger = get_worker_logger("vectorizer")
VECTORIZER_REPLAYABLE_STATUSES = {"splitting", "embedding"}


def _normalize_chunks(raw_chunks: List[Any], file_name: str) -> List[Dict[str, Any]]:
    normalized_chunks: List[Dict[str, Any]] = []

    for default_index, item in enumerate(raw_chunks or []):
        if isinstance(item, dict):
            content = str(item.get("content", "")).strip()
            metadata = dict(item.get("metadata") or {})
            chunk_index = int(item.get("chunk_index", default_index))
            char_count = int(item.get("char_count") or len(content))
        else:
            content = str(item).strip()
            metadata = {}
            chunk_index = default_index
            char_count = len(content)

        if not content:
            continue

        metadata.setdefault("file_name", file_name)
        normalized_chunks.append(
            {
                "content": content,
                "metadata": metadata,
                "chunk_index": chunk_index,
                "char_count": char_count,
            }
        )

    return normalized_chunks


async def _cleanup_failed_document(knowledge_id: int | None, doc_id: int) -> None:
    try:
        async with AsyncSessionLocal() as db:
            if knowledge_id is None:
                return

            result = await db.execute(select(Knowledge).where(Knowledge.id == knowledge_id))
            knowledge = result.scalar_one_or_none()
            if not knowledge:
                return

            await milvus_client.delete_by_document(knowledge.vector_collection_name, doc_id)
            await es_client.delete_by_document(doc_id)
    except Exception as cleanup_err:
        logger.error(f"Failed to clean partial index data for document_id={doc_id}: {cleanup_err}")


async def process_chunks(data: dict) -> None:
    doc_id = data.get("document_id")
    file_path = data.get("file_path")
    task_metadata = data.get("task_metadata") or {}
    knowledge_id = task_metadata.get("knowledge_id", data.get("knowledge_id"))
    file_name = task_metadata.get("file_name", data.get("file_name"))

    logger.info(
        f"Starting vectorization task for document_id={doc_id}, file_name={file_name}, file_path={file_path}"
    )

    try:
        async with AsyncSessionLocal() as db:
            doc_result = await db.execute(select(Document).where(Document.id == doc_id))
            document = doc_result.scalar_one_or_none()
            if not document:
                logger.warning(
                    f"Document not found, skipping vectorization task: document_id={doc_id}"
                )
                return
            if document.status not in VECTORIZER_REPLAYABLE_STATUSES:
                logger.info(
                    f"Skipping vectorization task for document_id={doc_id} because status={document.status}"
                )
                return

            chunks_artifact = get_pipeline_artifact(document.meta_data, "chunks")
            chunks_file_path = file_path or (chunks_artifact or {}).get("file_path")
            if not chunks_file_path:
                raise ValueError("Missing chunk artifact path")

            await db.execute(
                update(Document)
                .where(Document.id == doc_id)
                .values(status="embedding", error_msg=None)
            )
            await db.commit()

        raw_chunks = await asyncio.to_thread(pipeline_storage.read_json, chunks_file_path)
        logger.info(
            f"Loaded chunk artifact for document_id={doc_id}, chunk_count={len(raw_chunks or [])}"
        )

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Knowledge).where(Knowledge.id == knowledge_id))
            knowledge = result.scalar_one_or_none()

            if not knowledge:
                raise ValueError(f"Knowledge base not found: knowledge_id={knowledge_id}")

            collection_name = knowledge.vector_collection_name
            llm = None
            if knowledge.embed_llm_id:
                llm_result = await db.execute(select(LLM).where(LLM.id == knowledge.embed_llm_id))
                llm = llm_result.scalar_one_or_none()

            chunks = _normalize_chunks(raw_chunks, file_name)
            if not chunks:
                raise ValueError("No usable chunks were found in chunk artifact")

            chunk_texts = [chunk["content"] for chunk in chunks]

            if llm and llm.base_url:
                logger.info(f"Using remote embedding model {llm.model_name}")
                ak_stmt = select(APIKey).where(APIKey.llm_id == llm.id, APIKey.status == 1)
                ak_result = await db.execute(ak_stmt)
                apikey = ak_result.scalar_one_or_none()
                api_key = api_key_crypto.decrypt(apikey.api_key_encrypted) if apikey else ""

                provider = LLMFactory.get_provider(
                    provider_name=llm.provider,
                    api_key=api_key,
                    base_url=llm.base_url,
                    api_version=llm.api_version,
                )

                vectors_list = await provider.embed(chunk_texts, llm.model_name)
                vectors = [np.array(vector) for vector in vectors_list]
            else:
                logger.info("Using local embedding model")
                embedding_model = get_embedding_model()
                loop = asyncio.get_running_loop()
                vectors = await loop.run_in_executor(
                    None,
                    lambda: embedding_model.batch_encode(
                        chunk_texts,
                        show_progress=False,
                    ),
                )

        chunk_data = []
        for storage_index, (chunk, vector) in enumerate(zip(chunks, vectors)):
            chunk_index = chunk.get("chunk_index", storage_index)
            metadata = dict(chunk.get("metadata") or {})
            metadata.setdefault("file_name", file_name)
            chunk_data.append(
                {
                    "chunk_id": f"{doc_id}_{storage_index}",
                    "document_id": doc_id,
                    "knowledge_id": knowledge_id,
                    "content": chunk["content"],
                    "vector": vector.tolist(),
                    "chunk_index": chunk_index,
                    "char_count": chunk.get("char_count", len(chunk["content"])),
                    "metadata": metadata,
                    "filename": metadata.get("file_name", file_name),
                }
            )

        # Make stage replays safe when Kafka redelivers after a worker restart.
        await milvus_client.delete_by_document(collection_name, doc_id)
        await es_client.delete_by_document(doc_id)

        milvus_ok = await milvus_client.insert_vectors(collection_name=collection_name, data=chunk_data)
        if not milvus_ok:
            raise RuntimeError(f"Failed to insert Milvus vectors for document_id={doc_id}")

        es_ok = await es_client.batch_index_chunks(chunk_data)
        if not es_ok:
            raise RuntimeError(f"Failed to index Elasticsearch chunks for document_id={doc_id}")

        async with AsyncSessionLocal() as db:
            doc_result = await db.execute(select(Document).where(Document.id == doc_id))
            document = doc_result.scalar_one_or_none()
            if not document:
                logger.warning(
                    f"Document was deleted during vectorization, cleaning up index data: document_id={doc_id}"
                )
                await milvus_client.delete_by_document(collection_name, doc_id)
                await es_client.delete_by_document(doc_id)
                return

            await db.execute(
                update(Document)
                .where(Document.id == doc_id)
                .values(
                    status="completed",
                    chunk_count=len(chunk_data),
                    error_msg=None,
                    meta_data=clear_pipeline_artifacts(document.meta_data),
                )
            )

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

        await asyncio.to_thread(pipeline_storage.delete_document_artifacts, doc_id)

        logger.info(
            f"Vectorization completed for document_id={doc_id}, chunk_count={len(chunk_data)}"
        )

    except VectorizationFailedException as exc:
        logger.error(
            f"Vectorization failed for document_id={doc_id}, message={exc.message}, detail={exc.detail}, trace_id={exc.trace_id}"
        )
        await asyncio.to_thread(pipeline_storage.delete_document_artifacts, doc_id)
        await _cleanup_failed_document(knowledge_id, doc_id)

        error_msg = exc.message
        if exc.detail:
            error_msg += f" (detail: {exc.detail})"

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Document).where(Document.id == doc_id))
            document = result.scalar_one_or_none()
            meta_data = clear_pipeline_artifacts(document.meta_data if document else None)
            await db.execute(
                update(Document)
                .where(Document.id == doc_id)
                .values(status="failed", error_msg=error_msg, meta_data=meta_data)
            )
            await db.commit()

    except Exception as exc:
        logger.exception(
            f"Unexpected error during vectorization for document_id={doc_id}: {exc}"
        )
        await asyncio.to_thread(pipeline_storage.delete_document_artifacts, doc_id)
        await _cleanup_failed_document(knowledge_id, doc_id)

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Document).where(Document.id == doc_id))
            document = result.scalar_one_or_none()
            meta_data = clear_pipeline_artifacts(document.meta_data if document else None)
            await db.execute(
                update(Document)
                .where(Document.id == doc_id)
                .values(
                    status="failed",
                    error_msg=f"Vectorization failed: {exc}",
                    meta_data=meta_data,
                )
            )
            await db.commit()


async def heartbeat() -> None:
    while True:
        logger.info("Vectorizer worker heartbeat")
        await asyncio.sleep(60)


async def main() -> None:
    logger.info("Starting vectorizer worker")
    consumer = KafkaConsumer("rag.document.chunks", "vectorizer_group", process_chunks)
    try:
        await asyncio.gather(consumer.start(), heartbeat())
    except Exception as exc:
        logger.critical(f"Vectorizer worker exited unexpectedly: {exc}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
