"""Chat and session API routes."""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.llm.base import LLMMessage, LLMRequest
from app.core.llm.factory import LLMFactory
from app.core.security import api_key_crypto
from app.db.session import get_db
from app.models.apikey import APIKey
from app.models.llm import LLM
from app.models.user import User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    KnowledgeTestRequest,
    KnowledgeTestResponse,
    RetrievedContext,
    SessionCreate,
    SessionDetailResponse,
    SessionInfo,
    SessionListResponse,
    SessionUpdate,
)
from app.services.context_manager import context_manager
from app.services.rag_service import rag_service
from app.services.robot_service import robot_service
from app.services.session_service import session_service
from app.utils.es_client import es_client
from app.utils.redis_client import redis_client


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ask", response_model=ChatResponse, summary="Chat with a robot")
async def chat(
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session, _ = await session_service.get_or_create_session(
        db=db,
        user=current_user,
        robot_id=chat_request.robot_id,
        session_id=chat_request.session_id,
    )

    robot = await robot_service.get_robot_by_id(db, chat_request.robot_id, current_user)
    knowledge_ids = await robot_service.get_robot_knowledge_ids(db, chat_request.robot_id)

    if not knowledge_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The robot is not associated with any knowledge base.",
        )

    start_time = time.time()
    response = await rag_service.chat_with_context(
        db=db,
        robot=robot,
        knowledge_ids=knowledge_ids,
        session_id=session.session_id,
        question=chat_request.question,
        user_id=current_user.id,
    )
    total_time_ms = int((time.time() - start_time) * 1000)

    await session_service.save_chat_message(
        db=db,
        session_id=session.session_id,
        role="user",
        content=chat_request.question,
    )
    await session_service.save_chat_message(
        db=db,
        session_id=session.session_id,
        role="assistant",
        content=response.answer,
        contexts=[ctx.model_dump() for ctx in response.contexts],
        token_usage=response.token_usage,
        time_metrics={"total_time_ms": total_time_ms},
    )

    return response


@router.post("/ask/stream", summary="Stream chat with a robot")
async def chat_stream(
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session, _ = await session_service.get_or_create_session(
        db=db,
        user=current_user,
        robot_id=chat_request.robot_id,
        session_id=chat_request.session_id,
    )

    robot = await robot_service.get_robot_by_id(db, chat_request.robot_id, current_user)
    knowledge_ids = await robot_service.get_robot_knowledge_ids(db, chat_request.robot_id)

    if not knowledge_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The robot is not associated with any knowledge base.",
        )

    request_start = time.time()
    runtime_bundle = await rag_service.build_runtime_skill_bundle(db, robot)

    retrieval_query = chat_request.question
    try:
        retrieval_query = await context_manager.rewrite_query_with_context(
            session_id=session.session_id,
            current_query=chat_request.question,
        )
    except Exception as exc:
        logger.warning("Query rewrite failed, falling back to the raw question: %s", exc)
        retrieval_query = chat_request.question

    retrieval_query = rag_service.apply_retrieval_skill_guidance(retrieval_query, runtime_bundle)

    retrieval_start = time.time()
    contexts = await rag_service.hybrid_retrieve(
        db=db,
        robot=robot,
        knowledge_ids=knowledge_ids,
        query=retrieval_query,
        top_k=robot.top_k,
    )
    retrieval_time = time.time() - retrieval_start

    history_messages = await redis_client.get_context_messages(session.session_id)
    llm_history = [
        {"role": message["role"], "content": message["content"]}
        for message in history_messages
    ]

    await session_service.save_chat_message(
        db=db,
        session_id=session.session_id,
        role="user",
        content=chat_request.question,
    )
    await context_manager.add_user_message(
        session_id=session.session_id,
        content=chat_request.question,
        tokens=0,
    )

    llm_result = await db.execute(select(LLM).where(LLM.id == robot.chat_llm_id, LLM.status == 1))
    llm = llm_result.scalar_one_or_none()
    if not llm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The chat LLM does not exist or is disabled.",
        )

    apikey_result = await db.execute(
        select(APIKey).where(APIKey.llm_id == robot.chat_llm_id, APIKey.status == 1)
    )
    apikey = apikey_result.scalar_one_or_none()
    if not apikey:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM {llm.name} has no available API key.",
        )

    api_key = api_key_crypto.decrypt(apikey.api_key_encrypted)
    provider = LLMFactory.get_provider(
        provider_name=llm.provider,
        api_key=api_key,
        base_url=llm.base_url,
        api_version=llm.api_version,
    )

    request = LLMRequest(
        messages=[
            LLMMessage(role=item["role"], content=item["content"])
            for item in rag_service.build_chat_messages(
                robot=robot,
                question=chat_request.question,
                contexts=contexts,
                history_messages=llm_history,
                runtime_bundle=runtime_bundle,
            )
        ],
        model=llm.model_name,
        temperature=getattr(robot, "temperature", 0.7),
        max_tokens=getattr(robot, "max_tokens", 2000),
        stream=True,
    )
    generation_start = time.time()

    state = {
        "full_answer": "",
        "full_reasoning_content": "",
        "has_reasoning_started": False,
        "has_text_started": False,
        "usage": {},
    }

    current_session_id = session.session_id
    contexts_data = [ctx.model_dump() for ctx in contexts]
    active_skills_data = [skill.model_dump() for skill in runtime_bundle.get("active_skills", [])]

    def format_sse_event(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def generate_stream():
        if contexts_data:
            yield format_sse_event(
                "speech_type",
                {"type": "searchGuid", "title": f"引用 {len(contexts_data)} 篇资料作为参考"},
            )
            for idx, ctx in enumerate(contexts_data):
                yield format_sse_event(
                    "speech_type",
                    {
                        "type": "context",
                        "index": idx + 1,
                        "docId": ctx.get("chunk_id", ""),
                        "title": ctx.get("filename", "unknown"),
                        "url": "",
                        "sourceType": "knowledge_base",
                        "quote": ctx.get("content", "")[:500],
                        "publish_time": "",
                        "icon_url": "",
                        "web_site_name": "知识库",
                        "ref_source_weight": int(ctx.get("score", 0) * 5),
                        "content": ctx.get("content", ""),
                    },
                )

        try:
            async for chunk in provider.chat_stream(request):
                if chunk.reasoning_delta:
                    state["full_reasoning_content"] += chunk.reasoning_delta
                    state["has_reasoning_started"] = True
                    if not state["has_text_started"]:
                        yield format_sse_event("speech_type", {"type": "reasoner"})
                        state["has_text_started"] = True
                    yield format_sse_event(
                        "speech_type",
                        {
                            "type": "think",
                            "title": "思考中...",
                            "iconType": 9,
                            "content": chunk.reasoning_delta,
                            "status": 1,
                        },
                    )

                if chunk.content_delta:
                    state["full_answer"] += chunk.content_delta
                    if state["full_reasoning_content"] and not state["has_text_started"]:
                        yield format_sse_event("speech_type", {"type": "reasoner"})
                        state["has_text_started"] = True
                    elif not state["has_text_started"] and not state["full_reasoning_content"]:
                        yield format_sse_event("speech_type", {"type": "text"})
                        state["has_text_started"] = True
                    yield format_sse_event(
                        "speech_type",
                        {
                            "type": "text",
                            "msg": chunk.content_delta,
                        },
                    )

                if chunk.usage:
                    state["usage"] = chunk.usage

                if chunk.finish_reason:
                    state["finished_at"] = time.time()
                    if state["full_reasoning_content"]:
                        think_time = int(time.time() - retrieval_start)
                        yield format_sse_event(
                            "speech_type",
                            {
                                "type": "think",
                                "title": f"已深度思考，用时 {think_time} 秒",
                                "iconType": 7,
                                "content": "",
                                "status": 2,
                            },
                        )

                    yield format_sse_event(
                        "speech_type",
                        {
                            "type": "finished",
                            "session_id": current_session_id,
                            "token_usage": state["usage"],
                            "full_answer": state["full_answer"],
                            "full_reasoning_content": state["full_reasoning_content"],
                            "active_skills": active_skills_data,
                        },
                    )
        except Exception as exc:
            logger.error("Streaming provider call failed: %s", exc)
            yield format_sse_event("speech_type", {"type": "text", "msg": f"错误: {exc}"})

    async def finally_save():
        try:
            await session_service.save_chat_message(
                db=db,
                session_id=current_session_id,
                role="assistant",
                content=state["full_answer"],
                contexts=contexts_data,
                token_usage=state.get("usage", {}),
                time_metrics={
                    "retrieval_time_ms": int(retrieval_time * 1000),
                    "generation_time_ms": int(
                        (state.get("finished_at", time.time()) - generation_start) * 1000
                    ),
                    "total_time_ms": int(
                        (state.get("finished_at", time.time()) - request_start) * 1000
                    ),
                },
            )

            await context_manager.add_assistant_message(
                session_id=current_session_id,
                content=state["full_answer"],
                tokens=0,
            )
            await redis_client.update_active_session(current_user.id, current_session_id)
        except Exception as exc:
            logger.error("Failed to persist streaming conversation: %s", exc)

    async def generate_stream_with_save():
        try:
            async for chunk in generate_stream():
                yield chunk
        finally:
            await finally_save()

    return StreamingResponse(
        generate_stream_with_save(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/test", response_model=KnowledgeTestResponse, summary="Test knowledge retrieval")
async def test_knowledge(
    test_request: KnowledgeTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.robot import Robot
    from app.services.knowledge_service import knowledge_service

    await knowledge_service.get_knowledge_by_id(db, test_request.knowledge_id, current_user)
    start_time = time.time()

    temp_robot = Robot(
        id=0,
        user_id=current_user.id,
        name="temp",
        chat_llm_id=1,
        system_prompt="",
        top_k=test_request.top_k,
        temperature=0.7,
        max_tokens=2000,
    )

    if test_request.retrieval_mode == "vector":
        raw_results = await rag_service._vector_retrieve_async(
            db=db,
            knowledge_ids=[test_request.knowledge_id],
            query=test_request.query,
            top_k=test_request.top_k,
        )
        contexts = await _convert_to_retrieved_contexts_async(raw_results)
    elif test_request.retrieval_mode == "keyword":
        raw_results = await rag_service._keyword_retrieve_async(
            knowledge_ids=[test_request.knowledge_id],
            query=test_request.query,
            top_k=test_request.top_k,
        )
        contexts = await _convert_to_retrieved_contexts_async(raw_results)
    else:
        contexts = await rag_service.hybrid_retrieve(
            db=db,
            robot=temp_robot,
            knowledge_ids=[test_request.knowledge_id],
            query=test_request.query,
            top_k=test_request.top_k,
        )

    retrieval_time = time.time() - start_time
    return KnowledgeTestResponse(
        query=test_request.query,
        retrieval_mode=test_request.retrieval_mode,
        results=contexts,
        retrieval_time=retrieval_time,
    )


async def _convert_to_retrieved_contexts_async(raw_results: list) -> list:
    contexts = []

    for result in raw_results:
        try:
            chunk_data = await es_client.get_chunk_by_id(result["chunk_id"])
            if chunk_data:
                contexts.append(
                    RetrievedContext(
                        chunk_id=result["chunk_id"],
                        document_id=result["document_id"],
                        filename=chunk_data.get("filename", "unknown"),
                        content=chunk_data.get("content", ""),
                        score=min(result.get("score", 0.0), 1.0),
                        source=result.get("source", "unknown"),
                    )
                )
        except Exception:
            contexts.append(
                RetrievedContext(
                    chunk_id=result["chunk_id"],
                    document_id=result["document_id"],
                    filename="unknown",
                    content="内容获取失败",
                    score=min(result.get("score", 0.0), 1.0),
                    source=result.get("source", "unknown"),
                )
            )

    return contexts


@router.get("/history/{session_id}", response_model=SessionDetailResponse, summary="Get conversation history")
async def get_conversation_history(
    session_id: str,
    message_limit: int = Query(default=50, ge=1, le=200, description="Message limit"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await session_service.get_session_detail(
        db=db,
        session_id=session_id,
        user=current_user,
        message_limit=message_limit,
    )


@router.post("/sessions", response_model=SessionInfo, summary="Create a new session")
async def create_session(
    session_create: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await session_service.create_session(
        db=db,
        user=current_user,
        robot_id=session_create.robot_id,
        title=session_create.title,
    )

    return SessionInfo(
        session_id=session.session_id,
        robot_id=session.robot_id,
        title=session.title,
        summary=session.summary,
        message_count=session.message_count,
        status=session.status,
        is_pinned=bool(session.is_pinned),
        last_message_at=session.last_message_at,
        created_at=session.created_at,
    )


@router.get("/sessions", response_model=SessionListResponse, summary="List sessions")
async def list_sessions(
    robot_id: Optional[int] = Query(default=None, description="Robot ID filter"),
    status_filter: str = Query(default="active", description="Status filter"),
    skip: int = Query(default=0, ge=0, description="Skip count"),
    limit: int = Query(default=20, ge=1, le=100, description="Limit"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await session_service.get_user_sessions(
        db=db,
        user=current_user,
        robot_id=robot_id,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse, summary="Get session detail")
async def get_session(
    session_id: str,
    message_limit: int = Query(default=50, ge=1, le=200, description="Message limit"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await session_service.get_session_detail(
        db=db,
        session_id=session_id,
        user=current_user,
        message_limit=message_limit,
    )


@router.put("/sessions/{session_id}", response_model=SessionInfo, summary="Update a session")
async def update_session(
    session_id: str,
    update_data: SessionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await session_service.update_session(
        db=db,
        session_id=session_id,
        user=current_user,
        update_data=update_data,
    )

    return SessionInfo(
        session_id=session.session_id,
        robot_id=session.robot_id,
        title=session.title,
        summary=session.summary,
        message_count=session.message_count,
        status=session.status,
        is_pinned=bool(session.is_pinned),
        last_message_at=session.last_message_at,
        created_at=session.created_at,
    )


@router.delete("/sessions/{session_id}", summary="Delete a session")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await session_service.delete_session(
        db=db,
        session_id=session_id,
        user=current_user,
    )
    return {"message": "Session deleted"}


@router.post("/feedback", summary="Submit message feedback")
async def submit_feedback(
    feedback_request: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await session_service.update_feedback(
        db=db,
        user=current_user,
        feedback_request=feedback_request,
    )
    return {"message": "Feedback submitted"}
