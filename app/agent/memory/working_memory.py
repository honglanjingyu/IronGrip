# app/memory/working_memory.py
"""工作记忆 - 暂存当前任务中间结果"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from .models import MemoryItem, MemoryType, WorkingMemoryConfig


class WorkingMemory:
    """
    工作记忆

    特点：
    - 存储当前任务的中间结果
    - 支持键值对存储
    - 支持过期时间
    - 支持自动清理
    """

    def __init__(self, config: Optional[WorkingMemoryConfig] = None):
        """
        初始化工作记忆

        Args:
            config: 配置，默认使用 WorkingMemoryConfig()
        """
        self.config = config or WorkingMemoryConfig()
        self._data: Dict[str, Dict[str, Any]] = {}

        logger.info(f"WorkingMemory 初始化: max_items={self.config.max_items}")

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> MemoryItem:
        """
        设置工作记忆

        Args:
            key: 键
            value: 值
            ttl_seconds: 过期时间（秒），默认使用配置值

        Returns:
            MemoryItem: 创建的记忆条目
        """
        ttl = ttl_seconds or self.config.ttl_seconds
        expires_at = datetime.now() + timedelta(seconds=ttl)

        self._data[key] = {
            "value": value,
            "created_at": datetime.now(),
            "expires_at": expires_at,
            "access_count": 0
        }

        # 如果超过最大条目数，清理最旧的
        if len(self._data) > self.config.max_items:
            self._cleanup_oldest()

        logger.debug(f"工作记忆更新: {key}={str(value)[:50]}...")

        return MemoryItem(
            id=key,
            type=MemoryType.WORKING,
            content=str(value),
            metadata={"key": key, "expires_at": expires_at.isoformat()},
            timestamp=datetime.now()
        )

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取工作记忆

        Args:
            key: 键
            default: 默认值

        Returns:
            Any: 值，如果不存在或已过期返回默认值
        """
        if key not in self._data:
            return default

        item = self._data[key]

        # 检查是否过期
        if datetime.now() > item["expires_at"]:
            del self._data[key]
            logger.debug(f"工作记忆已过期: {key}")
            return default

        item["access_count"] += 1
        return item["value"]

    def get_with_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """获取工作记忆及元数据"""
        if key not in self._data:
            return None

        item = self._data[key]
        if datetime.now() > item["expires_at"]:
            del self._data[key]
            return None

        item["access_count"] += 1
        return item

    def delete(self, key: str) -> bool:
        """删除工作记忆"""
        if key in self._data:
            del self._data[key]
            logger.debug(f"删除工作记忆: {key}")
            return True
        return False

    def exists(self, key: str) -> bool:
        """检查键是否存在且未过期"""
        if key not in self._data:
            return False

        if datetime.now() > self._data[key]["expires_at"]:
            del self._data[key]
            return False

        return True

    def get_all(self) -> Dict[str, Any]:
        """获取所有有效的工作记忆"""
        result = {}
        expired_keys = []

        for key, item in self._data.items():
            if datetime.now() > item["expires_at"]:
                expired_keys.append(key)
            else:
                result[key] = item["value"]

        # 清理过期项
        for key in expired_keys:
            del self._data[key]

        return result

    def get_summary(self) -> str:
        """获取工作记忆摘要（用于LLM Prompt）"""
        items = self.get_all()

        if not items:
            return "无工作记忆"

        lines = []
        for key, value in items.items():
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:100] + "..."
            lines.append(f"- {key}: {value_str}")

        return "\n".join(lines)

    def clear(self):
        """清空工作记忆"""
        self._data.clear()
        logger.info("WorkingMemory 已清空")

    def _cleanup_oldest(self):
        """清理最旧的工作记忆"""
        if not self._data:
            return

        oldest_key = min(
            self._data.items(),
            key=lambda x: x[1]["created_at"]
        )[0]
        del self._data[oldest_key]
        logger.debug(f"清理最旧工作记忆: {oldest_key}")

    def cleanup_expired(self) -> int:
        """清理过期的记忆"""
        expired_keys = [
            key for key, item in self._data.items()
            if datetime.now() > item["expires_at"]
        ]

        for key in expired_keys:
            del self._data[key]

        if expired_keys:
            logger.debug(f"清理过期记忆: {len(expired_keys)} 条")

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        self.cleanup_expired()

        return {
            "item_count": len(self._data),
            "max_items": self.config.max_items,
            "ttl_seconds": self.config.ttl_seconds,
            "keys": list(self._data.keys())
        }