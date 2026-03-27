"""RAG service for retrieval and answer generation."""

from __future__ import annotations

import asyncio
import logging
import math
import time
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm.base import LLMMessage, LLMRequest
from app.core.llm.factory import LLMFactory
from app.core.security import api_key_crypto
from app.models.apikey import APIKey
from app.models.knowledge import Knowledge
from app.models.llm import LLM
from app.models.robot import Robot
from app.schemas.chat import ChatResponse, RetrievedContext
from app.services.context_manager import context_manager
from app.services.skill_service import skill_service
from app.utils.embedding import get_embedding_model
from app.utils.es_client import es_client
from app.utils.milvus_client import milvus_client
from app.utils.redis_client import redis_client
from app.utils.reranker import reranker


logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        self.es_client = es_client
        self.milvus_client = milvus_client

    async def hybrid_retrieve(
        self,
        db: AsyncSession,
        robot: Robot,
        knowledge_ids: List[int],
        query: str,
        top_k: int = 5,
    ) -> List[RetrievedContext]:
        recall_k = max(top_k, top_k * 4 if getattr(robot, "enable_rerank", False) else top_k * 2)

        vector_results, keyword_results = await asyncio.gather(
            self._vector_retrieve_async(db, knowledge_ids, query, recall_k),
            self._keyword_retrieve_async(knowledge_ids, query, recall_k),
        )

        merged_results = await self._merge_results_async(
            vector_results=vector_results,
            keyword_results=keyword_results,
            top_k=recall_k,
        )

        if getattr(robot, "enable_rerank", False) and merged_results:
            merged_results = await self._rerank_results(
                db=db,
                robot=robot,
                query=query,
                merged_results=merged_results,
                top_k=top_k,
            )

        similarity_threshold = float(getattr(robot, "similarity_threshold", 0.0) or 0.0)
        if similarity_threshold > 0:
            merged_results = [
                context for context in merged_results if context.score >= similarity_threshold
            ]

        return merged_results[:top_k]

    async def _vector_retrieve_async(
        self,
        db: AsyncSession,
        knowledge_ids: List[int],
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        try:
            knowledge_result = await db.execute(select(Knowledge).where(Knowledge.id.in_(knowledge_ids)))
            knowledges = knowledge_result.scalars().all()
            if not knowledges:
                return []

            grouped_knowledges: Dict[int, List[Knowledge]] = {}
            for knowledge in knowledges:
                grouped_knowledges.setdefault(knowledge.embed_llm_id or 0, []).append(knowledge)

            all_results: List[Dict[str, Any]] = []
            for embed_llm_id, grouped_items in grouped_knowledges.items():
                query_vector = await self._build_query_vector(db=db, embed_llm_id=embed_llm_id, query=query)
                if query_vector is None:
                    continue

                search_tasks = [
                    self.milvus_client.search_vectors(
                        collection_name=knowledge.vector_collection_name,
                        query_vector=query_vector,
                        top_k=top_k,
                    )
                    for knowledge in grouped_items
                ]
                task_results = await asyncio.gather(*search_tasks, return_exceptions=True)

                for index, result in enumerate(task_results):
                    if isinstance(result, Exception):
                        logger.error(
                            "Vector retrieval failed for knowledge %s: %s",
                            grouped_items[index].id,
                            result,
                        )
                        continue

                    for item in result:
                        all_results.append(
                            {
                                "chunk_id": item["chunk_id"],
                                "document_id": item["document_id"],
                                "score": float(item["score"]),
                                "source": "vector",
                                "knowledge_id": grouped_items[index].id,
                            }
                        )

            all_results.sort(key=lambda item: item["score"], reverse=True)
            return all_results[:top_k]
        except Exception as exc:
            logger.error("Async vector retrieval failed: %s", exc)
            return []

    async def _build_query_vector(
        self,
        db: AsyncSession,
        embed_llm_id: int,
        query: str,
    ) -> Optional[List[float]]:
        if embed_llm_id == 0:
            embedding_model = get_embedding_model()
            return embedding_model.encode(query)[0].tolist()

        llm_result = await db.execute(select(LLM).where(LLM.id == embed_llm_id))
        llm = llm_result.scalar_one_or_none()
        if llm and llm.base_url:
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
            embeddings = await provider.embed(texts=[query], model=llm.model_name)
            return embeddings[0]

        embedding_model = get_embedding_model()
        return embedding_model.encode(query)[0].tolist()

    async def _keyword_retrieve_async(
        self,
        knowledge_ids: List[int],
        query: str,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        try:
            results = await self.es_client.search_chunks(query, knowledge_ids, top_k)
            return [
                {
                    "chunk_id": item["chunk_id"],
                    "document_id": item["document_id"],
                    "score": float(item["score"]),
                    "source": "keyword",
                    "knowledge_id": item["knowledge_id"],
                }
                for item in results
            ]
        except Exception as exc:
            logger.error("Keyword retrieval failed: %s", exc)
            return []

    async def _merge_results_async(
        self,
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        top_k: int,
    ) -> List[RetrievedContext]:
        merged_scores: Dict[str, Dict[str, Any]] = {}

        for rank, result in enumerate(vector_results):
            chunk_id = result["chunk_id"]
            merged_scores.setdefault(
                chunk_id,
                {
                    "chunk_id": chunk_id,
                    "document_id": result["document_id"],
                    "knowledge_id": result["knowledge_id"],
                    "vector_score": 0.0,
                    "keyword_score": 0.0,
                    "rrf_score": 0.0,
                    "source": "vector",
                },
            )
            merged_scores[chunk_id]["vector_score"] = float(result["score"])
            merged_scores[chunk_id]["rrf_score"] += 1 / (60 + rank + 1)

        for rank, result in enumerate(keyword_results):
            chunk_id = result["chunk_id"]
            merged_scores.setdefault(
                chunk_id,
                {
                    "chunk_id": chunk_id,
                    "document_id": result["document_id"],
                    "knowledge_id": result["knowledge_id"],
                    "vector_score": 0.0,
                    "keyword_score": 0.0,
                    "rrf_score": 0.0,
                    "source": "keyword",
                },
            )
            merged_scores[chunk_id]["keyword_score"] = float(result["score"])
            merged_scores[chunk_id]["rrf_score"] += 1 / (60 + rank + 1)
            if merged_scores[chunk_id]["vector_score"] > 0:
                merged_scores[chunk_id]["source"] = "hybrid"

        sorted_items = sorted(
            merged_scores.values(),
            key=lambda item: (
                item["rrf_score"],
                self._blend_retrieval_score(item["vector_score"], item["keyword_score"]),
            ),
            reverse=True,
        )[:top_k]

        if not sorted_items:
            return []

        chunk_ids = [item["chunk_id"] for item in sorted_items]
        try:
            chunks_data_list = await self.es_client.get_chunks_by_ids(chunk_ids)
            chunk_map = {chunk["chunk_id"]: chunk for chunk in chunks_data_list}

            contexts: List[RetrievedContext] = []
            for item in sorted_items:
                chunk_data = chunk_map.get(item["chunk_id"])
                if not chunk_data:
                    continue

                contexts.append(
                    RetrievedContext(
                        chunk_id=item["chunk_id"],
                        document_id=item["document_id"],
                        filename=chunk_data.get("filename", "unknown"),
                        content=chunk_data.get("content", ""),
                        score=self._blend_retrieval_score(
                            item["vector_score"],
                            item["keyword_score"],
                        ),
                        source=item["source"],
                    )
                )
            return contexts
        except Exception as exc:
            logger.error("Failed to resolve merged retrieval chunks: %s", exc)
            return []

    async def _rerank_results(
        self,
        db: AsyncSession,
        robot: Robot,
        query: str,
        merged_results: List[RetrievedContext],
        top_k: int,
    ) -> List[RetrievedContext]:
        docs = [context.content for context in merged_results]
        rerank_llm = None
        if getattr(robot, "rerank_llm_id", None):
            llm_result = await db.execute(select(LLM).where(LLM.id == robot.rerank_llm_id))
            rerank_llm = llm_result.scalar_one_or_none()

        try:
            if rerank_llm and rerank_llm.base_url:
                ak_stmt = select(APIKey).where(APIKey.llm_id == rerank_llm.id, APIKey.status == 1)
                ak_result = await db.execute(ak_stmt)
                apikey = ak_result.scalar_one_or_none()
                api_key = api_key_crypto.decrypt(apikey.api_key_encrypted) if apikey else ""

                provider = LLMFactory.get_provider(
                    provider_name=rerank_llm.provider,
                    api_key=api_key,
                    base_url=rerank_llm.base_url,
                    api_version=rerank_llm.api_version,
                )
                rerank_results = await provider.rerank(
                    query=query,
                    texts=docs,
                    model=rerank_llm.model_name,
                    top_n=top_k,
                )

                final_results: List[RetrievedContext] = []
                for fallback_index, item in enumerate(rerank_results):
                    if isinstance(item, dict):
                        result_index = item.get("index", fallback_index)
                        raw_score = item.get("relevance_score", item.get("score"))
                    else:
                        result_index = fallback_index
                        raw_score = None

                    if result_index >= len(merged_results):
                        continue

                    context = merged_results[result_index].model_copy(deep=True)
                    if raw_score is not None:
                        context.score = self._normalize_score(raw_score)
                    context.source = f"{context.source}+remote_rerank"
                    final_results.append(context)

                return final_results or merged_results[:top_k]

            loop = asyncio.get_running_loop()
            rerank_pairs = await loop.run_in_executor(None, reranker.rerank, query, docs, top_k)

            final_results: List[RetrievedContext] = []
            for result_index, raw_score in rerank_pairs:
                if result_index >= len(merged_results):
                    continue
                context = merged_results[result_index].model_copy(deep=True)
                context.score = self._normalize_score(raw_score)
                context.source = f"{context.source}+local_rerank"
                final_results.append(context)

            return final_results or merged_results[:top_k]
        except Exception as exc:
            logger.error("Rerank failed, falling back to merged results: %s", exc)
            return merged_results[:top_k]

    def _blend_retrieval_score(self, vector_score: float, keyword_score: float) -> float:
        vector_score = self._clamp_score(vector_score)
        keyword_score = self._clamp_score(keyword_score)
        if vector_score > 0 and keyword_score > 0:
            return round((vector_score * 0.65) + (keyword_score * 0.35), 6)
        return round(max(vector_score, keyword_score), 6)

    def _normalize_score(self, raw_score: Any) -> float:
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            return 0.0

        if 0.0 <= score <= 1.0:
            return score

        if score >= 20:
            return 1.0
        if score <= -20:
            return 0.0
        return 1.0 / (1.0 + math.exp(-score))

    def _clamp_score(self, score: Any) -> float:
        try:
            score = float(score)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(score, 1.0))

    async def build_runtime_skill_bundle(self, db: AsyncSession, robot: Robot) -> dict[str, Any]:
        bundle = await skill_service.get_runtime_skill_bundle(db, robot.id)
        return {
            "active_skills": bundle.active_skills,
            "system_prompts": bundle.system_prompts,
            "retrieval_prompts": bundle.retrieval_prompts,
            "answer_prompts": bundle.answer_prompts,
        }

    def apply_retrieval_skill_guidance(
        self,
        query: str,
        runtime_bundle: dict[str, Any] | None = None,
    ) -> str:
        if not runtime_bundle:
            return query

        retrieval_prompts = runtime_bundle.get("retrieval_prompts") or []
        if not retrieval_prompts:
            return query

        return (
            f"{query}\n\n"
            "## Skill Retrieval Guidance\n"
            f"{chr(10).join(retrieval_prompts)}"
        )

    def build_chat_messages(
        self,
        robot: Robot,
        question: str,
        contexts: List[RetrievedContext],
        history_messages: List[Dict[str, str]] | None = None,
        runtime_bundle: dict[str, Any] | None = None,
    ) -> List[Dict[str, str]]:
        context_text = (
            "\n\n".join(
                [
                    f"[参考{i + 1}] {context.filename}\n{context.content}"
                    for i, context in enumerate(contexts)
                ]
            )
            if contexts
            else "未找到相关的知识库内容。"
        )

        system_sections = [robot.system_prompt or "You are a helpful assistant."]
        if runtime_bundle:
            system_sections.extend(runtime_bundle.get("system_prompts") or [])
            answer_prompts = runtime_bundle.get("answer_prompts") or []
            if answer_prompts:
                system_sections.append("## Skill Answer Guidance\n" + "\n\n".join(answer_prompts))

        messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": "\n\n".join(section for section in system_sections if section).strip(),
            }
        ]
        if history_messages:
            messages.extend(history_messages)

        user_content = (
            "## 知识库上下文\n"
            f"{context_text}\n\n"
            "## 用户问题\n"
            f"{question}\n\n"
            "请基于知识库内容回答用户问题。"
            "如果无法从知识库中找到依据，请明确说明。"
            "如果使用了上下文，请优先在句子末尾标注类似[参考1]的引用。"
        )
        messages.append({"role": "user", "content": user_content})
        return messages

    async def _call_llm_api(
        self,
        db: AsyncSession,
        llm_id: int,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        llm_result = await db.execute(select(LLM).where(LLM.id == llm_id, LLM.status == 1))
        llm = llm_result.scalar_one_or_none()
        if not llm:
            raise ValueError(f"LLM model does not exist or is disabled: {llm_id}")

        apikey_result = await db.execute(select(APIKey).where(APIKey.llm_id == llm_id, APIKey.status == 1))
        apikey = apikey_result.scalar_one_or_none()
        if not apikey:
            raise ValueError(f"LLM {llm.name} has no available API key")

        api_key = api_key_crypto.decrypt(apikey.api_key_encrypted)
        provider = LLMFactory.get_provider(
            provider_name=llm.provider,
            api_key=api_key,
            base_url=llm.base_url,
            api_version=llm.api_version,
        )

        request = LLMRequest(
            messages=[LLMMessage(role=item["role"], content=item["content"]) for item in messages],
            model=llm.model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        response = await provider.chat(request)
        return {
            "answer": response.content,
            "token_usage": {
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "total_tokens": response.total_tokens,
            },
        }

    async def generate_answer(
        self,
        db: AsyncSession,
        robot: Robot,
        question: str,
        contexts: List[RetrievedContext],
        session_id: str | None = None,
        history_messages: List[Dict[str, str]] | None = None,
        runtime_bundle: dict[str, Any] | None = None,
    ) -> ChatResponse:
        start_time = time.time()
        messages = self.build_chat_messages(
            robot=robot,
            question=question,
            contexts=contexts,
            history_messages=history_messages,
            runtime_bundle=runtime_bundle,
        )

        try:
            llm_result = await self._call_llm_api(
                db=db,
                llm_id=robot.chat_llm_id,
                messages=messages,
                temperature=robot.temperature,
                max_tokens=robot.max_tokens,
            )
            answer = llm_result["answer"]
            token_usage = llm_result["token_usage"]
        except Exception as exc:
            logger.error("LLM invocation failed: %s", exc)
            answer = f"抱歉，生成回答时出错: {exc}"
            token_usage = {}

        response_time = time.time() - start_time
        if not session_id:
            session_id = str(uuid.uuid4())

        return ChatResponse(
            session_id=session_id,
            question=question,
            answer=answer,
            contexts=contexts,
            active_skills=(runtime_bundle or {}).get("active_skills", []),
            token_usage=token_usage,
            response_time=response_time,
        )

    async def chat_with_context(
        self,
        db: AsyncSession,
        robot: Robot,
        knowledge_ids: List[int],
        question: str,
        session_id: str | None = None,
        user_id: int | None = None,
    ) -> ChatResponse:
        runtime_bundle = await self.build_runtime_skill_bundle(db, robot)

        retrieval_query = question
        if session_id:
            try:
                retrieval_query = await context_manager.rewrite_query_with_context(
                    session_id=session_id,
                    current_query=question,
                )
            except Exception as exc:
                logger.warning("Query rewrite failed, falling back to the raw question: %s", exc)
                retrieval_query = question

        retrieval_query = self.apply_retrieval_skill_guidance(retrieval_query, runtime_bundle)

        contexts = await self.hybrid_retrieve(
            db=db,
            robot=robot,
            knowledge_ids=knowledge_ids,
            query=retrieval_query,
            top_k=robot.top_k,
        )

        history_messages = []
        if session_id:
            try:
                history_messages = await redis_client.get_context_messages(session_id)
            except Exception:
                history_messages = []

        response = await self.generate_answer(
            db=db,
            robot=robot,
            question=question,
            contexts=contexts,
            session_id=session_id,
            history_messages=[
                {"role": message["role"], "content": message["content"]}
                for message in history_messages
            ],
            runtime_bundle=runtime_bundle,
        )

        if session_id:
            await context_manager.add_user_message(session_id, question)
            await context_manager.add_assistant_message(session_id, response.answer)
            await redis_client.update_active_session(user_id, session_id)

        return response


rag_service = RAGService()
