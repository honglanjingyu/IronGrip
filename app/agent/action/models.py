"""行动模块数据模型"""

from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """动作类型"""
    TOOL_CALL = "tool_call"      # 工具调用
    DIRECT_OUTPUT = "direct_output"  # 直接输出
    DEFER = "defer"              # 延迟处理


class OutputType(str, Enum):
    """输出类型"""
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    COMMAND = "command"          # 操作指令

class ToolCall(BaseModel):
    """工具调用"""
    name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="工具参数")
    timestamp: datetime = Field(default_factory=datetime.now)


class Action(BaseModel):
    """决策动作"""
    type: ActionType = Field(..., description="动作类型")
    tool_call: Optional[ToolCall] = Field(None, description="工具调用（如果是 tool_call）")
    content: Optional[str] = Field(None, description="直接输出内容")
    content_type: OutputType = Field(default=OutputType.TEXT, description="输出类型")
    reasoning: str = Field(default="", description="决策推理过程")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ActionResult(BaseModel):
    """动作执行结果"""
    action: Action = Field(..., description="原始动作")
    success: bool = Field(default=False, description="是否成功")
    result: Optional[str] = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time_ms: float = Field(default=0.0, description="执行耗时（毫秒）")
    timestamp: datetime = Field(default_factory=datetime.now)


class OutputResult(BaseModel):
    """输出结果"""
    type: OutputType = Field(..., description="输出类型")
    content: str = Field(..., description="输出内容")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionContext(BaseModel):
    """执行上下文"""
    session_id: str = Field(..., description="会话ID")
    user_input: str = Field(..., description="原始用户输入")
    current_step: Optional[str] = Field(None, description="当前步骤")
    available_tools: List[Dict[str, Any]] = Field(default_factory=list)
    perception_context: Dict[str, Any] = Field(default_factory=dict)
    brain_state: Optional[Dict[str, Any]] = Field(None, description="大脑状态")


class ToolInfo(BaseModel):
    """工具信息"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    input_schema: Optional[Dict[str, Any]] = Field(None, description="输入参数 schema")
    is_async: bool = Field(default=True, description="是否异步工具")