# app/api/dependencies.py
"""依赖注入 - 管理全局 Agent 实例"""

from typing import Optional
import asyncio
from loguru import logger

from app.core import Agent, SessionManager


# 全局 Agent 实例
_agent: Optional[Agent] = None
_agent_lock = asyncio.Lock()

# 全局会话管理器
_session_manager: SessionManager = None


async def get_agent() -> Agent:
    """获取全局 Agent 实例（单例，懒加载）"""
    global _agent

    async with _agent_lock:
        if _agent is None:
            _agent = Agent()
            # 设置会话管理器
            _agent.set_session_manager(get_session_manager())
            await _agent.initialize()

        return _agent


async def reset_agent():
    """重置 Agent（用于测试或重新初始化）"""
    global _agent
    async with _agent_lock:
        _agent = None


def get_session_manager() -> SessionManager:
    """获取会话管理器（单例）"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager