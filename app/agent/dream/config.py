# app/dream/config.py
"""做梦模块配置 - 启动后每10分钟做一次梦，关闭时做一次梦"""

import os
from pathlib import Path
from dataclasses import dataclass


@dataclass
class DreamConfig:
    """做梦配置"""

    # ========== 实体记忆存储配置 ==========
    # 实体记忆存储目录（项目根目录下）
    ENTITY_MEMORY_DIR: str = "entity_memory"

    # ========== 记忆压缩配置 ==========
    # 单次做梦最多提炼记忆数
    MAX_MEMORIES_PER_DREAM: int = 20

    # 保留记忆的最低重要性分数（低于此分数的不保存）
    IMPORTANCE_THRESHOLD: float = 0.4

    # 最少处理会话数（低于此数量不触发做梦）
    MIN_SESSIONS_FOR_DREAM: int = 1

    # 单次处理的最大会话数
    MAX_SESSIONS_PER_DREAM: int = 50

    # ========== 调度配置 ==========
    # 启动时是否执行做梦（False = 启动时不做梦）
    DREAM_ON_STARTUP: bool = False

    # 是否启用后台调度器（True = 启用）
    ENABLE_SCHEDULER: bool = True

    # 后台调度间隔（秒） - 10分钟 = 600秒
    DREAM_INTERVAL_SECONDS: int = 600

    # 空闲阈值（秒）- 系统空闲多久后触发做梦
    DREAM_IDLE_THRESHOLD_SECONDS: int = 30

    @classmethod
    def from_env(cls) -> "DreamConfig":
        """从环境变量加载配置"""
        return cls(
            ENTITY_MEMORY_DIR=os.getenv("ENTITY_MEMORY_DIR", "entity_memory"),
            MAX_MEMORIES_PER_DREAM=int(os.getenv("MAX_MEMORIES_PER_DREAM", "20")),
            IMPORTANCE_THRESHOLD=float(os.getenv("IMPORTANCE_THRESHOLD", "0.4")),
            MIN_SESSIONS_FOR_DREAM=int(os.getenv("MIN_SESSIONS_FOR_DREAM", "1")),
            MAX_SESSIONS_PER_DREAM=int(os.getenv("MAX_SESSIONS_PER_DREAM", "50")),
            DREAM_ON_STARTUP=os.getenv("DREAM_ON_STARTUP", "false").lower() == "true",
            ENABLE_SCHEDULER=os.getenv("ENABLE_DREAM_SCHEDULER", "true").lower() == "true",
            DREAM_INTERVAL_SECONDS=int(os.getenv("DREAM_INTERVAL_SECONDS", "600")),
            DREAM_IDLE_THRESHOLD_SECONDS=int(os.getenv("DREAM_IDLE_THRESHOLD_SECONDS", "30")),
        )


dream_config = DreamConfig.from_env()