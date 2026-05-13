# app/agent/forget/memory_eraser.py
"""记忆清除器 - 清除指定关键词相关的所有记忆"""

import re
import json
from pathlib import Path
from typing import List, Optional
from loguru import logger


class MemoryEraser:
    """
    记忆清除器

    功能：
    1. 从短期记忆中清除包含关键词的消息
    2. 从 Redis 会话中删除相关消息（不清除整个会话）
    3. 从实体记忆（文件系统）中删除相关记忆文件
    """

    def __init__(self):
        self._memory_manager = None
        self._dream_manager = None
        self._redis_memory = None
        logger.info("MemoryEraser 初始化完成")

    def _get_memory_manager(self):
        """获取记忆管理器"""
        if self._memory_manager is None:
            try:
                from app.agent.memory import get_memory_manager
                self._memory_manager = get_memory_manager()
            except Exception as e:
                logger.error(f"获取记忆管理器失败: {e}")
        return self._memory_manager

    def _get_dream_manager(self):
        """获取做梦管理器（用于实体记忆）"""
        if self._dream_manager is None:
            try:
                from app.agent.dream import get_dream_manager
                self._dream_manager = get_dream_manager()
            except Exception as e:
                logger.error(f"获取做梦管理器失败: {e}")
        return self._dream_manager

    def _get_redis_memory(self):
        """获取 Redis 记忆管理器"""
        if self._redis_memory is None:
            try:
                from app.agent.memory import get_redis_memory_manager
                self._redis_memory = get_redis_memory_manager()
            except Exception as e:
                logger.error(f"获取 Redis 记忆管理器失败: {e}")
        return self._redis_memory

    def extract_keyword(self, user_input: str) -> Optional[str]:
        """
        从用户输入中提取要遗忘的关键词

        支持格式：
        - "忘掉:xxx"
        - "忘掉：xxx"
        - "忘记:xxx"
        - "遗忘:xxx"
        - "清除记忆:xxx"
        - "删除记忆:xxx"
        """
        patterns = [
            r'忘掉[：:]\s*(.+)',
            r'忘记[：:]\s*(.+)',
            r'遗忘[：:]\s*(.+)',
            r'清除记忆[：:]\s*(.+)',
            r'删除记忆[：:]\s*(.+)',
            r'忘掉\s+(.+)',
            r'忘记\s+(.+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, user_input)
            if match:
                keyword = match.group(1).strip()
                if keyword and len(keyword) > 0:
                    logger.info(f"提取到遗忘关键词: '{keyword}'")
                    return keyword
        return None

    async def clear_short_term_memory(self, keyword: str, session_id: str) -> int:
        """
        清除短期记忆中包含关键词的消息
        """
        count = 0
        memory_manager = self._get_memory_manager()

        if not memory_manager:
            logger.warning("记忆管理器不可用，无法清除短期记忆")
            return 0

        try:
            recent_messages = memory_manager.get_recent_messages(100)

            to_delete = []
            for i, msg in enumerate(recent_messages):
                content = msg.get("content", "")
                if keyword.lower() in content.lower():
                    to_delete.append(i)
                    count += 1

            logger.info(f"[会话 {session_id}] 短期记忆中匹配到 {count} 条包含 '{keyword}' 的消息")

            if to_delete and memory_manager._short_term:
                all_messages = list(memory_manager._short_term._messages)
                filtered_messages = []
                for msg in all_messages:
                    if keyword.lower() not in msg.get("content", "").lower():
                        filtered_messages.append(msg)

                memory_manager._short_term.clear()
                for msg in filtered_messages:
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role == "user":
                        memory_manager._short_term.add_user_message(content)
                    elif role == "assistant":
                        memory_manager._short_term.add_assistant_message(content)
                    else:
                        memory_manager._short_term._add_message(role, content)

                logger.info(f"[会话 {session_id}] 短期记忆中删除了 {len(all_messages) - len(filtered_messages)} 条消息")

        except Exception as e:
            logger.error(f"清除短期记忆失败: {e}")

        return count

    async def clear_redis_session_memory(self, keyword: str, session_id: str) -> int:
        """
        清除 Redis 会话记忆中包含关键词的消息
        只删除相关消息，保留其他消息
        """
        count = 0
        redis = self._get_redis_memory()

        if not redis:
            logger.warning("Redis 不可用，无法清除会话记忆")
            return 0

        try:
            history = redis.get_session_history(session_id, limit=200)

            if not history:
                return 0

            keep_messages = []
            for msg in history:
                content = msg.get("content", "")
                if keyword.lower() not in content.lower():
                    keep_messages.append(msg)
                else:
                    count += 1
                    logger.info(f"[会话 {session_id}] 删除消息: {content[:50]}...")

            if count > 0:
                key = redis._get_session_key(session_id)
                redis.redis_client.delete(key)

                for msg in keep_messages:
                    redis.redis_client.rpush(key, json.dumps(msg, ensure_ascii=False))

                meta_key = redis._get_meta_key(session_id)
                redis.redis_client.hset(meta_key, "message_count", len(keep_messages))

                logger.info(f"[会话 {session_id}] Redis 记忆中删除了 {count} 条包含 '{keyword}' 的消息")

        except Exception as e:
            logger.error(f"清除 Redis 会话记忆失败: {e}")

        return count

    async def clear_entity_memory(self, keyword: str, session_id: str) -> int:
        """
        清除实体记忆中包含关键词的记忆
        """
        count = 0
        dream_manager = self._get_dream_manager()

        if not dream_manager:
            logger.warning("做梦管理器不可用，无法清除实体记忆")
            return 0

        try:
            all_memories = dream_manager.get_all_memories()

            to_delete = []
            for memory in all_memories:
                if (keyword.lower() in memory.title.lower() or
                        keyword.lower() in memory.content.lower()):
                    to_delete.append(memory.id)
                    count += 1

            for memory_id in to_delete:
                dream_manager.delete_memory(memory_id)

            if count > 0:
                logger.info(f"[会话 {session_id}] 实体记忆中删除了 {count} 条包含 '{keyword}' 的记忆")

        except Exception as e:
            logger.error(f"清除实体记忆失败: {e}")

        return count

    async def forget(
            self,
            keyword: str,
            session_id: str,
            include_short_term: bool = True,
            include_redis: bool = True,
            include_entity: bool = True
    ) -> dict:
        """
        执行遗忘操作

        Args:
            keyword: 要遗忘的关键词
            session_id: 当前会话ID
            include_short_term: 是否清除短期记忆
            include_redis: 是否清除 Redis 会话记忆
            include_entity: 是否清除实体记忆

        Returns:
            统计结果
        """
        results = {
            "keyword": keyword,
            "short_term_cleared": 0,
            "redis_cleared": 0,
            "entity_cleared": 0,
            "total_cleared": 0,
            "success": True,
            "message": ""
        }

        logger.info(f"[会话 {session_id}] 开始遗忘关键词: '{keyword}'")

        try:
            if include_short_term:
                results["short_term_cleared"] = await self.clear_short_term_memory(keyword, session_id)

            if include_redis:
                results["redis_cleared"] = await self.clear_redis_session_memory(keyword, session_id)

            if include_entity:
                results["entity_cleared"] = await self.clear_entity_memory(keyword, session_id)

            results["total_cleared"] = (
                results["short_term_cleared"] +
                results["redis_cleared"] +
                results["entity_cleared"]
            )

            results["message"] = f"已清除 {results['total_cleared']} 条关于 '{keyword}' 的记忆"
            logger.info(f"[会话 {session_id}] 遗忘完成: {results['message']}")

        except Exception as e:
            results["success"] = False
            results["message"] = f"遗忘失败: {str(e)}"
            logger.error(f"[会话 {session_id}] 遗忘失败: {e}")

        return results


# 全局单例
_eraser: Optional[MemoryEraser] = None


def get_memory_eraser() -> MemoryEraser:
    """获取记忆清除器单例"""
    global _eraser
    if _eraser is None:
        _eraser = MemoryEraser()
    return _eraser