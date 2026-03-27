"""Chat and session related schemas."""

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.skill import SkillRobotBindingDetail


class SessionStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


ALLOWED_SESSION_STATUS = {"active", "archived", "deleted"}


class ChatRequest(BaseModel):
    robot_id: int = Field(..., description="Robot ID")
    question: str = Field(..., min_length=1, max_length=2000, description="User question")
    session_id: Optional[str] = Field(None, description="Session ID")
    stream: bool = Field(default=False, description="Whether to stream the response")


class RetrievedContext(BaseModel):
    chunk_id: str = Field(..., description="Chunk ID")
    document_id: int = Field(..., description="Document ID")
    filename: str = Field(..., description="Filename")
    content: str = Field(..., description="Chunk content")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    source: str = Field(..., description="Retrieval source")


class ChatResponse(BaseModel):
    session_id: str = Field(..., description="Session ID")
    question: str = Field(..., description="User question")
    answer: str = Field(..., description="Assistant answer")
    contexts: List[RetrievedContext] = Field(default_factory=list, description="Retrieved contexts")
    active_skills: List[SkillRobotBindingDetail] = Field(default_factory=list, description="Active robot skills")
    token_usage: dict = Field(default_factory=dict, description="Token usage")
    response_time: float = Field(..., description="Response time in seconds")


class ChatStreamChunk(BaseModel):
    session_id: str = Field(..., description="Session ID")
    content: str = Field(..., description="Delta content")
    is_finished: bool = Field(default=False, description="Whether the stream is finished")
    reasoning_content: Optional[str] = Field(None, description="Reasoning delta")
    contexts: Optional[List[RetrievedContext]] = Field(None, description="Retrieved contexts")
    active_skills: Optional[List[SkillRobotBindingDetail]] = Field(None, description="Active robot skills")
    token_usage: Optional[dict] = Field(None, description="Token usage")


class ConversationMessage(BaseModel):
    role: str = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="Timestamp")


class ConversationHistory(BaseModel):
    session_id: str = Field(..., description="Session ID")
    robot_id: int = Field(..., description="Robot ID")
    messages: List[ConversationMessage] = Field(default_factory=list, description="Messages")
    created_at: str = Field(..., description="Created at")


class SessionCreate(BaseModel):
    robot_id: int = Field(..., description="Robot ID")
    title: Optional[str] = Field(None, max_length=200, description="Session title")


class SessionUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200, description="Session title")
    is_pinned: Optional[bool] = Field(None, description="Whether the session is pinned")
    status: Optional[Literal["active", "archived", "deleted"]] = Field(
        None,
        description="Session status",
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, value):
        if value is not None and value not in ALLOWED_SESSION_STATUS:
            raise ValueError(f"Invalid session status. Expected one of {list(ALLOWED_SESSION_STATUS)}")
        return value


class SessionInfo(BaseModel):
    session_id: str = Field(..., description="Session UUID")
    robot_id: int = Field(..., description="Robot ID")
    title: Optional[str] = Field(None, description="Session title")
    summary: Optional[str] = Field(None, description="Session summary")
    message_count: int = Field(default=0, description="Message count")
    status: str = Field(default="active", description="Session status")
    is_pinned: bool = Field(default=False, description="Whether the session is pinned")
    last_message_at: Optional[datetime] = Field(None, description="Last message time")
    created_at: datetime = Field(..., description="Created at")

    model_config = ConfigDict(from_attributes=True)


class SessionListResponse(BaseModel):
    total: int = Field(..., description="Total count")
    sessions: List[SessionInfo] = Field(default_factory=list, description="Sessions")


class ChatHistoryItem(BaseModel):
    message_id: str = Field(..., description="Message ID")
    role: str = Field(..., description="Role")
    content: str = Field(..., description="Content")
    contexts: Optional[List[RetrievedContext]] = Field(None, description="Retrieved contexts")
    token_usage: Optional[dict] = Field(None, description="Token usage")
    feedback: Optional[int] = Field(None, description="User feedback")
    created_at: datetime = Field(..., description="Created at")

    model_config = ConfigDict(from_attributes=True)


class SessionDetailResponse(BaseModel):
    session: SessionInfo = Field(..., description="Session info")
    messages: List[ChatHistoryItem] = Field(default_factory=list, description="History messages")


class FeedbackRequest(BaseModel):
    message_id: str = Field(..., description="Message ID")
    feedback: int = Field(..., ge=-1, le=1, description="Feedback score")
    comment: Optional[str] = Field(None, max_length=500, description="Feedback comment")


class KnowledgeTestRequest(BaseModel):
    knowledge_id: int = Field(..., description="Knowledge ID")
    query: str = Field(..., min_length=1, max_length=500, description="Test query")
    top_k: int = Field(default=5, ge=1, le=20, description="Top-k")
    retrieval_mode: str = Field(default="hybrid", description="Retrieval mode")


class KnowledgeTestResponse(BaseModel):
    query: str = Field(..., description="Query")
    retrieval_mode: str = Field(..., description="Retrieval mode")
    results: List[RetrievedContext] = Field(default_factory=list, description="Results")
    retrieval_time: float = Field(..., description="Retrieval time in seconds")
