# app/memory/models.py
"""记忆模块数据模型"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """记忆类型"""
    SHORT_TERM = "short_term"  # 短期记忆（对话上下文）
    LONG_TERM = "long_term"  # 长期记忆（向量知识库）
    WORKING = "working"  # 工作记忆（当前任务中间结果）


class MemoryItem(BaseModel):
    """记忆条目"""
    id: str = Field(..., description="记忆ID")
    type: MemoryType = Field(..., description="记忆类型")
    content: str = Field(..., description="记忆内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    score: float = Field(default=0.0, description="相关性分数")
    timestamp: datetime = Field(default_factory=datetime.now, description="创建时间")


class ShortTermConfig(BaseModel):
    """短期记忆配置"""
    max_size: int = Field(default=20, description="最大消息数量")
    max_tokens: int = Field(default=4000, description="最大Token数（估算）")
    trim_strategy: str = Field(default="recent", description="裁剪策略: recent, sliding_window")

    class Config:
        json_schema_extra = {
            "example": {
                "max_size": 20,
                "max_tokens": 4000,
                "trim_strategy": "recent"
            }
        }


class LongTermConfig(BaseModel):
    """长期记忆配置"""
    top_k: int = Field(default=5, description="默认检索数量")
    similarity_threshold: float = Field(default=0.3, description="相似度阈值")
    enable_hybrid_search: bool = Field(default=True, description="是否启用混合检索")
    vector_weight: float = Field(default=0.7, description="向量检索权重")
    keyword_weight: float = Field(default=0.3, description="关键词检索权重")

    class Config:
        json_schema_extra = {
            "example": {
                "top_k": 5,
                "similarity_threshold": 0.3,
                "enable_hybrid_search": True,
                "vector_weight": 0.7,
                "keyword_weight": 0.3
            }
        }


class WorkingMemoryConfig(BaseModel):
    """工作记忆配置"""
    max_items: int = Field(default=50, description="最大条目数量")
    ttl_seconds: int = Field(default=3600, description="过期时间（秒）")

    class Config:
        json_schema_extra = {
            "example": {
                "max_items": 50,
                "ttl_seconds": 3600
            }
        }


class MemoryStats(BaseModel):
    """记忆统计信息"""
    short_term_count: int = Field(default=0, description="短期记忆条目数")
    long_term_count: int = Field(default=0, description="长期记忆条目数")
    working_count: int = Field(default=0, description="工作记忆条目数")
    total_count: int = Field(default=0, description="总记忆条目数")
    timestamp: datetime = Field(default_factory=datetime.now)