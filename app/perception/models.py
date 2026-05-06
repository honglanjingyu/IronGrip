# app/perception/models.py
"""感知模块数据模型"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class InputType(str, Enum):
    """输入类型枚举"""
    TEXT = "text"
    FILE = "file"
    SYSTEM = "system"  # 系统诊断请求


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class InputData(BaseModel):
    """标准化的输入数据"""
    type: InputType
    content: Any
    session_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class EnvironmentContext(BaseModel):
    """环境上下文"""
    current_time: str
    timezone: str
    system_status: Dict[str, Any] = Field(default_factory=dict)
    api_results: List[Dict[str, Any]] = Field(default_factory=list)
    active_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    custom_context: Dict[str, Any] = Field(default_factory=dict)


# 添加 EnvironmentState 类（被 environment_sensor.py 使用）
class EnvironmentState(BaseModel):
    """环境状态（用于 EnvironmentPerceiver）"""
    current_time: str
    system_info: Dict[str, Any] = Field(default_factory=dict)
    api_results: Dict[str, Any] = Field(default_factory=dict)
    active_alerts: List[Dict[str, Any]] = Field(default_factory=list)


class MemoryType(str, Enum):
    """记忆类型"""
    SHORT_TERM = "short_term"   # 短期记忆（对话上下文）
    LONG_TERM = "long_term"     # 长期记忆（知识库）
    WORKING = "working"          # 工作记忆（当前任务中间结果）


class MemoryItem(BaseModel):
    """记忆条目"""
    id: str
    type: MemoryType
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0  # 相关性分数
    timestamp: datetime = Field(default_factory=datetime.now)


class PerceptionResult(BaseModel):
    """感知模块输出结果"""
    input_data: InputData
    environment_context: EnvironmentContext
    short_term_memory: List[MemoryItem]
    long_term_memory: List[MemoryItem]
    working_memory: Dict[str, Any] = Field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 - 使用 model_dump() 替代 dict()"""
        return {
            "input": {
                "type": self.input_data.type,
                "content": self.input_data.content,
                "session_id": self.input_data.session_id
            },
            "environment": self.environment_context.model_dump(),
            "short_term_memory": [m.model_dump() for m in self.short_term_memory],
            "long_term_memory": [m.model_dump() for m in self.long_term_memory],
            "working_memory": self.working_memory,
            "summary": self.summary
        }