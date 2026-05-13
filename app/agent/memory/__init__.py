# app/agent/memory/__init__.py
"""记忆模块 (Memory Module)

提供 Agent 的记忆能力：
- 短期记忆：当前对话轮次内的上下文窗口
- 长期记忆：历史会话记录和向量知识库
- 工作记忆：暂存当前任务中间结果
"""

from .models import (
    MemoryType,
    MemoryItem,
    ShortTermConfig,
    LongTermConfig,
    WorkingMemoryConfig,
    MemoryStats,
)
from .short_term_memory import ShortTermMemory
from .long_term_memory import LongTermMemory
from .working_memory import WorkingMemory
from .memory_manager import MemoryManager, get_memory_manager

# 添加这一行 - 导出 Redis 会话记忆管理器
from .redis_session_memory import RedisSessionMemory, get_redis_memory_manager

__all__ = [
    # 数据模型
    "MemoryType",
    "MemoryItem",
    "ShortTermConfig",
    "LongTermConfig",
    "WorkingMemoryConfig",
    "MemoryStats",
    # 核心组件
    "ShortTermMemory",
    "LongTermMemory",
    "WorkingMemory",
    "MemoryManager",
    "get_memory_manager",
    # Redis 会话记忆
    "RedisSessionMemory",
    "get_redis_memory_manager",
]