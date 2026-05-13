"""行动模块 (Action Module)

提供 Agent 的行动能力：
- 工具调用：执行具体动作，通过函数调用实现
- 输出生成：生成最终返回给用户的文本、操作指令或界面响应
"""

from .models import (
    ActionType,
    Action,
    ActionResult,
    ToolCall,
    OutputType,
    OutputResult,
    ExecutionContext,
    ToolInfo,
)

from .tool_registry import ToolRegistry, get_tool_registry
from .executor import ActionExecutor, get_action_executor

# 延迟导入 OutputGenerator，避免循环依赖
# from .output_generator import OutputGenerator
from .action_manager import ActionManager, get_action_manager

__all__ = [
    # 数据模型
    "ActionType",
    "Action",
    "ActionResult",
    "ToolCall",
    "OutputType",
    "OutputResult",
    "ExecutionContext",
    "ToolInfo",

    # 工具注册表
    "ToolRegistry",
    "get_tool_registry",

    # 动作执行器
    "ActionExecutor",
    "get_action_executor",

    # 行动管理器
    "ActionManager",
    "get_action_manager",
]