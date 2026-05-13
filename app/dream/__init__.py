# app/dream/__init__.py
"""做梦模块 - 实体记忆系统"""

from .models import (
    EntityMemory,
    EntityType,
    DreamSession,
    DreamResult,
    MemoryQuery,
    MemoryCompressionLevel
)
from .entity_memory import EntityMemoryStore, get_entity_memory_store
from .memory_compressor import MemoryCompressor, get_memory_compressor
from .dream_manager import DreamManager, get_dream_manager
from .scheduler import DreamScheduler, get_dream_scheduler
from .config import dream_config, DreamConfig


async def init_dream_module():
    """初始化做梦模块"""
    from .scheduler import get_dream_scheduler
    from .config import dream_config

    scheduler = get_dream_scheduler()

    if dream_config.DREAM_ON_STARTUP:
        # 启动时执行一次做梦
        dream_manager = get_dream_manager()
        await dream_manager.dream()

    if dream_config.ENABLE_SCHEDULER:
        await scheduler.start()

    return scheduler


async def shutdown_dream_module():
    """关闭做梦模块"""
    from .scheduler import get_dream_scheduler

    scheduler = get_dream_scheduler()
    await scheduler.stop()


__all__ = [
    "EntityMemory",
    "EntityType",
    "DreamSession",
    "DreamResult",
    "MemoryQuery",
    "MemoryCompressionLevel",
    "EntityMemoryStore",
    "get_entity_memory_store",
    "MemoryCompressor",
    "get_memory_compressor",
    "DreamManager",
    "get_dream_manager",
    "DreamScheduler",
    "get_dream_scheduler",
    "dream_config",
    "DreamConfig",
    "init_dream_module",
    "shutdown_dream_module",
]