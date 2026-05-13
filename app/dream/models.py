# app/dream/models.py
"""做梦模块数据模型 - 实体记忆系统"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import json
from pydantic import BaseModel


class EntityType(str, Enum):
    """实体类型"""
    USER_PREFERENCE = "user_preference"      # 用户偏好
    USER_FACT = "user_fact"                  # 用户相关事实
    KNOWLEDGE_INSIGHT = "knowledge_insight"  # 知识洞察
    PATTERN = "pattern"                      # 行为模式
    CONTEXT = "context"                      # 重要上下文
    CORRECTION = "correction"                # 纠正信息


class MemoryCompressionLevel(str, Enum):
    """压缩级别"""
    LIGHT = "light"      # 轻度压缩：提取关键点
    MEDIUM = "medium"    # 中度压缩：总结+提炼
    DEEP = "deep"        # 深度压缩：抽象化+关联


@dataclass
class EntityMemory:
    """实体记忆"""
    id: str                                    # 唯一ID
    entity_type: EntityType                    # 实体类型
    title: str                                 # 标题
    content: str                               # 内容
    source_session_id: str                     # 来源会话
    source_conversations: List[str]            # 来源对话引用
    importance_score: float = 0.5              # 重要性评分 0-1
    confidence: float = 0.7                    # 置信度 0-1
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_type": self.entity_type.value,
            "title": self.title,
            "content": self.content,
            "source_session_id": self.source_session_id,
            "source_conversations": self.source_conversations,
            "importance_score": self.importance_score,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "tags": self.tags,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityMemory":
        return cls(
            id=data["id"],
            entity_type=EntityType(data["entity_type"]),
            title=data["title"],
            content=data["content"],
            source_session_id=data["source_session_id"],
            source_conversations=data.get("source_conversations", []),
            importance_score=data.get("importance_score", 0.5),
            confidence=data.get("confidence", 0.7),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if "last_accessed" in data else datetime.now(),
            access_count=data.get("access_count", 0),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )


@dataclass
class DreamSession:
    """做梦会话"""
    id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    sessions_processed: List[str] = field(default_factory=list)
    memories_created: List[str] = field(default_factory=list)
    status: str = "running"  # running, completed, failed


@dataclass
class DreamResult:
    """做梦结果"""
    success: bool
    dream_session_id: str
    memories_created: List[EntityMemory]
    sessions_processed: int
    duration_seconds: float
    message: str = ""


class MemoryQuery(BaseModel):
    """记忆查询"""
    query: str
    entity_type: Optional[EntityType] = None
    tags: List[str] = field(default_factory=list)
    min_importance: float = 0.3
    limit: int = 10
    include_content: bool = True