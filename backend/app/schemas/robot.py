"""
Pydantic schemas for robot configuration and retrieval tests.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RobotCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="机器人名称")
    avatar: Optional[str] = Field(None, description="机器人头像 URL")
    chat_llm_id: int = Field(..., description="对话 LLM 模型 ID")
    rerank_llm_id: Optional[int] = Field(None, description="重排序模型 ID")
    knowledge_ids: List[int] = Field(..., min_length=1, description="关联的知识库 ID 列表")
    system_prompt: str = Field(
        default="你是一个智能助手，请基于提供的知识库内容回答用户问题。",
        max_length=2000,
        description="系统提示词",
    )
    welcome_message: Optional[str] = Field(None, max_length=500, description="欢迎语")
    top_k: int = Field(default=5, ge=1, le=20, description="检索 Top-K")
    similarity_threshold: float = Field(
        default=0.3, ge=0.0, le=1.0, description="召回结果相似度阈值"
    )
    enable_rerank: bool = Field(default=False, description="是否启用重排序")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="生成温度")
    max_tokens: int = Field(
        default=2000, ge=100, le=8000, description="最大生成 token 数"
    )
    description: Optional[str] = Field(None, max_length=500, description="机器人描述")


class RobotBase(BaseModel):
    name: str = Field(..., description="机器人名称")
    avatar: Optional[str] = Field(None, description="机器人头像 URL")
    chat_llm_id: int = Field(..., description="对话 LLM 模型 ID")
    rerank_llm_id: Optional[int] = Field(None, description="重排序模型 ID")
    system_prompt: str = Field(..., description="系统提示词")
    welcome_message: Optional[str] = Field(None, description="欢迎语")
    top_k: int = Field(..., description="检索 Top-K")
    similarity_threshold: float = Field(..., description="召回结果相似度阈值")
    enable_rerank: bool = Field(..., description="是否启用重排序")
    temperature: float = Field(..., description="生成温度")
    max_tokens: int = Field(..., description="最大生成 token 数")
    description: Optional[str] = Field(None, description="机器人描述")
    status: int = Field(..., description="状态：0-禁用，1-启用")


class RobotDetail(RobotBase):
    id: int = Field(..., description="机器人 ID")
    user_id: int = Field(..., description="创建者用户 ID")
    knowledge_ids: List[int] = Field(default_factory=list, description="关联的知识库 ID 列表")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

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
    query: str = Field(..., min_length=1, max_length=500, description="查询文本")
    top_k: int = Field(default=5, ge=1, le=20, description="检索数量")
    threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="分数阈值")


class RetrievalTestResultItem(BaseModel):
    id: str = Field(..., description="切片 ID")
    score: float = Field(..., description="得分")
    content: str = Field(..., description="内容片段")
    document_id: int = Field(..., description="所属文档 ID")
    filename: str = Field(..., description="所属文件名")


class RetrievalTestResponse(BaseModel):
    results: List[RetrievalTestResultItem] = Field(..., description="检索结果列表")


class RobotUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="机器人名称")
    avatar: Optional[str] = Field(None, description="机器人头像 URL")
    chat_llm_id: Optional[int] = Field(None, description="对话 LLM 模型 ID")
    rerank_llm_id: Optional[int] = Field(None, description="重排序模型 ID")
    knowledge_ids: Optional[List[int]] = Field(
        None, min_length=1, description="关联的知识库 ID 列表"
    )
    system_prompt: Optional[str] = Field(None, max_length=2000, description="系统提示词")
    welcome_message: Optional[str] = Field(None, max_length=500, description="欢迎语")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="检索 Top-K")
    similarity_threshold: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="召回结果相似度阈值"
    )
    enable_rerank: Optional[bool] = Field(None, description="是否启用重排序")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="生成温度")
    max_tokens: Optional[int] = Field(
        None, ge=100, le=8000, description="最大生成 token 数"
    )
    description: Optional[str] = Field(None, max_length=500, description="机器人描述")
    status: Optional[int] = Field(None, description="状态：0-禁用，1-启用")


class RobotListResponse(BaseModel):
    total: int = Field(..., description="总数")
    items: List[RobotDetail] = Field(..., description="机器人列表")


class RobotBrief(BaseModel):
    id: int = Field(..., description="机器人 ID")
    name: str = Field(..., description="机器人名称")
    description: Optional[str] = Field(None, description="机器人描述")

    model_config = ConfigDict(from_attributes=True)
