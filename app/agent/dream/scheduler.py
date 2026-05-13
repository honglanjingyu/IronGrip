# app/dream/scheduler.py
"""做梦后台调度器 - 每10分钟检查一次"""

import asyncio
import time
from datetime import datetime
from typing import Optional
from loguru import logger

from .dream_manager import get_dream_manager, DreamManager
from .config import dream_config


class DreamScheduler:
    """
    做梦后台调度器

    每10分钟检查一次系统空闲状态，空闲时自动触发做梦
    启动时不做梦，关闭时做一次梦
    """

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.dream_manager: DreamManager = get_dream_manager()
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False
        self._last_request_time = datetime.now()  # 最后请求时间
        self._initialized = True

        logger.info("DreamScheduler 初始化完成")

    def record_request(self):
        """记录用户请求（用于判断空闲）"""
        self._last_request_time = datetime.now()
        logger.debug("记录用户请求时间")

    async def _scheduler_loop(self):
        """调度器主循环 - 每10分钟检查一次"""
        logger.info(f"做梦调度器已启动，检查间隔: {dream_config.DREAM_INTERVAL_SECONDS}秒")

        while self._running:
            try:
                # 等待指定间隔
                await asyncio.sleep(dream_config.DREAM_INTERVAL_SECONDS)

                if not self._running:
                    break

                # 检查是否空闲
                idle_seconds = (datetime.now() - self._last_request_time).total_seconds()

                if idle_seconds >= dream_config.DREAM_IDLE_THRESHOLD_SECONDS:
                    logger.info(f"系统空闲 {idle_seconds:.0f} 秒，检查是否需要做梦...")

                    # 获取未处理会话
                    unprocessed = await self.dream_manager.get_unprocessed_sessions()

                    if len(unprocessed) >= dream_config.MIN_SESSIONS_FOR_DREAM:
                        logger.info(f"发现 {len(unprocessed)} 个未处理会话，开始做梦...")
                        await self.dream_manager.dream()
                    else:
                        logger.debug(
                            f"未处理会话不足 ({len(unprocessed)} < {dream_config.MIN_SESSIONS_FOR_DREAM})，跳过")
                else:
                    logger.debug(
                        f"系统活跃中，空闲 {idle_seconds:.0f} 秒 < {dream_config.DREAM_IDLE_THRESHOLD_SECONDS} 秒")

            except asyncio.CancelledError:
                logger.info("调度器被取消")
                break
            except Exception as e:
                logger.error(f"调度器循环出错: {e}")
                await asyncio.sleep(60)

    async def start(self):
        """启动调度器（启动时不做梦）"""
        if self._running:
            logger.warning("调度器已在运行")
            return

        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("做梦调度器已启动（启动时不做梦，首次检查在10分钟后）")

    async def stop(self):
        """停止调度器"""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            self._scheduler_task = None
        logger.info("做梦调度器已停止")

    async def dream_now(self) -> dict:
        """立即执行一次做梦"""
        result = await self.dream_manager.dream()
        return {
            "success": result.success,
            "dream_session_id": result.dream_session_id,
            "memories_created": len(result.memories_created),
            "sessions_processed": result.sessions_processed,
            "duration_seconds": result.duration_seconds,
            "message": result.message
        }


# 全局单例
_scheduler: Optional[DreamScheduler] = None


def get_dream_scheduler() -> DreamScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = DreamScheduler()
    return _scheduler