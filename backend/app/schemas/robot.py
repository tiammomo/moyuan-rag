"""Pydantic schemas for robot configuration and retrieval tests."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.skill import SkillRobotBindingDetail


class RobotCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Robot name")
    avatar: Optional[str] = Field(None, description="Robot avatar URL")
    chat_llm_id: int = Field(..., description="Chat LLM model ID")
    rerank_llm_id: Optional[int] = Field(None, description="Rerank model ID")
    knowledge_ids: List[int] = Field(..., min_length=1, description="Associated knowledge IDs")
    system_prompt: str = Field(
        default="你是一个智能助手，请基于提供的知识库内容回答用户问题。",
        max_length=2000,
        description="System prompt",
    )
    welcome_message: Optional[str] = Field(None, max_length=500, description="Welcome message")
    top_k: int = Field(default=5, ge=1, le=20, description="Retrieval top-k")
    similarity_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Similarity threshold")
    enable_rerank: bool = Field(default=False, description="Whether rerank is enabled")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Generation temperature")
    max_tokens: int = Field(default=2000, ge=100, le=8000, description="Max generation tokens")
    description: Optional[str] = Field(None, max_length=500, description="Robot description")


class RobotBase(BaseModel):
    name: str = Field(..., description="Robot name")
    avatar: Optional[str] = Field(None, description="Robot avatar URL")
    chat_llm_id: int = Field(..., description="Chat LLM model ID")
    rerank_llm_id: Optional[int] = Field(None, description="Rerank model ID")
    system_prompt: str = Field(..., description="System prompt")
    welcome_message: Optional[str] = Field(None, description="Welcome message")
    top_k: int = Field(..., description="Retrieval top-k")
    similarity_threshold: float = Field(..., description="Similarity threshold")
    enable_rerank: bool = Field(..., description="Whether rerank is enabled")
    temperature: float = Field(..., description="Generation temperature")
    max_tokens: int = Field(..., description="Max generation tokens")
    description: Optional[str] = Field(None, description="Robot description")
    status: int = Field(..., description="Status: 0 disabled, 1 enabled")


class RobotDetail(RobotBase):
    id: int = Field(..., description="Robot ID")
    user_id: int = Field(..., description="Owner user ID")
    knowledge_ids: List[int] = Field(default_factory=list, description="Associated knowledge IDs")
    skills: List[SkillRobotBindingDetail] = Field(default_factory=list, description="Bound skills")
    created_at: datetime = Field(..., description="Created at")
    updated_at: datetime = Field(..., description="Updated at")

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def map_welcome_msg(cls, data):
        if hasattr(data, "welcome_msg") and not hasattr(data, "welcome_message"):
            data.welcome_message = data.welcome_msg
        elif (
            isinstance(data, dict)
            and "welcome_msg" in data
            and "welcome_message" not in data
        ):
            data["welcome_message"] = data["welcome_msg"]
        return data


class RetrievalTestRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Query text")
    top_k: int = Field(default=5, ge=1, le=20, description="Retrieval result count")
    threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="Score threshold")


class RetrievalTestResultItem(BaseModel):
    id: str = Field(..., description="Chunk ID")
    score: float = Field(..., description="Score")
    content: str = Field(..., description="Chunk content")
    document_id: int = Field(..., description="Document ID")
    filename: str = Field(..., description="Filename")


class RetrievalTestResponse(BaseModel):
    results: List[RetrievalTestResultItem] = Field(..., description="Retrieval results")


class RobotUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Robot name")
    avatar: Optional[str] = Field(None, description="Robot avatar URL")
    chat_llm_id: Optional[int] = Field(None, description="Chat LLM model ID")
    rerank_llm_id: Optional[int] = Field(None, description="Rerank model ID")
    knowledge_ids: Optional[List[int]] = Field(None, min_length=1, description="Associated knowledge IDs")
    system_prompt: Optional[str] = Field(None, max_length=2000, description="System prompt")
    welcome_message: Optional[str] = Field(None, max_length=500, description="Welcome message")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Retrieval top-k")
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Similarity threshold")
    enable_rerank: Optional[bool] = Field(None, description="Whether rerank is enabled")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Generation temperature")
    max_tokens: Optional[int] = Field(None, ge=100, le=8000, description="Max generation tokens")
    description: Optional[str] = Field(None, max_length=500, description="Robot description")
    status: Optional[int] = Field(None, description="Status: 0 disabled, 1 enabled")


class RobotListResponse(BaseModel):
    total: int = Field(..., description="Total count")
    items: List[RobotDetail] = Field(..., description="Robot list")


class RobotBrief(BaseModel):
    id: int = Field(..., description="Robot ID")
    name: str = Field(..., description="Robot name")
    description: Optional[str] = Field(None, description="Robot description")

    model_config = ConfigDict(from_attributes=True)
