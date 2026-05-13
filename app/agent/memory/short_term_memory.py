# app/memory/short_term_memory.py
"""短期记忆 - 保存当前对话上下文"""

from typing import List, Dict, Any, Optional
from collections import deque
from datetime import datetime
import uuid
from loguru import logger

from .models import MemoryItem, MemoryType, ShortTermConfig


class ShortTermMemory:
    """
    短期记忆

    特点：
    - 容量有限（默认20条消息）
    - 自动裁剪过期或过长的消息
    - 支持获取最近N条消息
    - 支持清空
    """

    def __init__(self, config: Optional[ShortTermConfig] = None):
        """
        初始化短期记忆

        Args:
            config: 配置，默认使用 ShortTermConfig()
        """
        self.config = config or ShortTermConfig()
        self._messages: deque = deque(maxlen=self.config.max_size)
        self._message_ids: List[str] = []

        logger.info(f"ShortTermMemory 初始化: max_size={self.config.max_size}")

    def add_message(
            self,
            role: str,
            content: str,
            metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryItem:
        """
        添加消息到短期记忆

        Args:
            role: 角色 (user, assistant, system)
            content: 消息内容
            metadata: 元数据

        Returns:
            MemoryItem: 创建的记忆条目
        """
        message_id = str(uuid.uuid4())

        message = {
            "id": message_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }

        self._messages.append(message)
        self._message_ids.append(message_id)

        # 裁剪如果超过最大数量
        if len(self._message_ids) > self.config.max_size:
            removed = self._message_ids.pop(0)
            logger.debug(f"裁剪消息: {removed}")

        logger.debug(f"添加消息: role={role}, content_len={len(content)}")

        return MemoryItem(
            id=message_id,
            type=MemoryType.SHORT_TERM,
            content=content,
            metadata={"role": role, **message["metadata"]},
            timestamp=datetime.now()
        )

    def _add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> MemoryItem:
        """内部添加消息方法（用于自定义角色）"""
        return self.add_message(role, content, metadata)

    def add_user_message(self, content: str, metadata: Optional[Dict] = None) -> MemoryItem:
        """添加用户消息"""
        return self.add_message("user", content, metadata)

    def add_assistant_message(self, content: str, metadata: Optional[Dict] = None) -> MemoryItem:
        """添加助手消息"""
        return self.add_message("assistant", content, metadata)

    def add_system_message(self, content: str, metadata: Optional[Dict] = None) -> MemoryItem:
        """添加系统消息"""
        return self.add_message("system", content, metadata)

    def get_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近N条消息

        Args:
            n: 消息数量

        Returns:
            List[Dict]: 消息列表
        """
        messages = list(self._messages)
        return messages[-n:] if n > 0 else messages

    def get_all(self) -> List[Dict[str, Any]]:
        """获取所有消息"""
        return list(self._messages)

    def get_formatted_context(self, max_messages: Optional[int] = None) -> str:
        """
        获取格式化的对话上下文（用于LLM Prompt）

        Args:
            max_messages: 最大消息数量

        Returns:
            str: 格式化的上下文
        """
        messages = self.get_recent(max_messages) if max_messages else self.get_all()

        if not messages:
            return ""

        lines = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                lines.append(f"用户: {content}")
            elif role == "assistant":
                lines.append(f"助手: {content}")
            else:
                lines.append(f"系统: {content}")

        return "\n".join(lines)

    def estimate_tokens(self) -> int:
        """
        估算当前消息的总Token数

        Returns:
            int: 估算的Token数（按字符数/3粗略估算）
        """
        total_chars = sum(len(msg["content"]) for msg in self._messages)
        return total_chars // 3

    def is_full(self) -> bool:
        """检查是否已满"""
        return len(self._messages) >= self.config.max_size

    def clear(self):
        """清空短期记忆"""
        self._messages.clear()
        self._message_ids.clear()
        logger.info("ShortTermMemory 已清空")

    def get_size(self) -> int:
        """获取消息数量"""
        return len(self._messages)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        roles = {}
        for msg in self._messages:
            role = msg["role"]
            roles[role] = roles.get(role, 0) + 1

        return {
            "message_count": len(self._messages),
            "max_size": self.config.max_size,
            "estimated_tokens": self.estimate_tokens(),
            "roles": roles
        }