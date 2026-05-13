# app/dream/entity_memory.py
"""实体记忆存储 - 文件系统持久化"""

import json
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger
import threading

from .models import EntityMemory, EntityType, MemoryQuery
from .config import dream_config


class EntityMemoryStore:
    """
    实体记忆存储 - 基于文件系统
    存储路径: {project_root}/entity_memory/
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.memory_dir = Path.cwd() / dream_config.ENTITY_MEMORY_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self._cache: Dict[str, EntityMemory] = {}
        self._cache_loaded = False
        self._cache_lock = threading.Lock()

        self._load_all()
        self._initialized = True

        logger.info(f"EntityMemoryStore 初始化: {self.memory_dir}, 已加载 {len(self._cache)} 条记忆")

    def _get_file_path(self, memory_id: str) -> Path:
        """获取记忆文件路径"""
        # 按 ID 前两位分目录，避免单目录文件过多
        sub_dir = memory_id[:2]
        dir_path = self.memory_dir / sub_dir
        dir_path.mkdir(exist_ok=True)
        return dir_path / f"{memory_id}.json"

    def _save_memory(self, memory: EntityMemory):
        """保存单条记忆"""
        file_path = self._get_file_path(memory.id)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(memory.to_dict(), f, ensure_ascii=False, indent=2)
            logger.debug(f"保存记忆: {memory.id} - {memory.title[:30]}")
        except Exception as e:
            logger.error(f"保存记忆失败 {memory.id}: {e}")

    def _load_memory(self, memory_id: str) -> Optional[EntityMemory]:
        """加载单条记忆"""
        file_path = self._get_file_path(memory_id)
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return EntityMemory.from_dict(data)
        except Exception as e:
            logger.error(f"加载记忆失败 {memory_id}: {e}")
            return None

    def _load_all(self):
        """加载所有记忆到缓存"""
        with self._cache_lock:
            self._cache.clear()

            if not self.memory_dir.exists():
                return

            for sub_dir in self.memory_dir.iterdir():
                if sub_dir.is_dir():
                    for file_path in sub_dir.glob("*.json"):
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            memory = EntityMemory.from_dict(data)
                            self._cache[memory.id] = memory
                        except Exception as e:
                            logger.warning(f"加载记忆文件失败 {file_path}: {e}")

            self._cache_loaded = True
            logger.info(f"加载了 {len(self._cache)} 条实体记忆")

    def save(self, memory: EntityMemory) -> str:
        """保存记忆"""
        with self._cache_lock:
            self._cache[memory.id] = memory
        self._save_memory(memory)
        logger.info(f"记忆已保存: {memory.entity_type.value} - {memory.title[:50]}")
        return memory.id

    def save_multi(self, memories: List[EntityMemory]) -> List[str]:
        """批量保存记忆"""
        ids = []
        for memory in memories:
            ids.append(self.save(memory))
        return ids

    def get(self, memory_id: str) -> Optional[EntityMemory]:
        """获取记忆"""
        with self._cache_lock:
            memory = self._cache.get(memory_id)

        if memory:
            # 更新访问统计
            memory.access_count += 1
            memory.last_accessed = datetime.now()
            self._save_memory(memory)

        return memory

    def get_all(self) -> List[EntityMemory]:
        """获取所有记忆"""
        with self._cache_lock:
            return list(self._cache.values())

    def query(self, query: MemoryQuery) -> List[EntityMemory]:
        """
        语义查询记忆（基于关键词匹配，后续可升级为向量检索）
        """
        results = []
        query_lower = query.query.lower()
        query_words = set(query_lower.split())

        with self._cache_lock:
            for memory in self._cache.values():
                # 类型过滤
                if query.entity_type and memory.entity_type != query.entity_type:
                    continue

                # 重要性过滤
                if memory.importance_score < query.min_importance:
                    continue

                # 标签过滤
                if query.tags and not any(tag in memory.tags for tag in query.tags):
                    continue

                # 关键词匹配
                score = 0.0
                title_lower = memory.title.lower()
                content_lower = memory.content.lower()

                for word in query_words:
                    if word in title_lower:
                        score += 0.5
                    if word in content_lower:
                        score += 0.3

                # 完全匹配
                if query_lower in title_lower:
                    score += 1.0
                if query_lower in content_lower:
                    score += 0.6

                if score > 0:
                    # 综合评分 = 关键词匹配 * 0.6 + 重要性 * 0.4
                    final_score = score * 0.6 + memory.importance_score * 0.4
                    results.append((memory, final_score))

        # 排序
        results.sort(key=lambda x: x[1], reverse=True)

        # 限制数量
        limited = [r[0] for r in results[:query.limit]]

        logger.info(f"记忆查询: '{query.query}' -> {len(limited)} 条结果")
        return limited

    def search_by_type(self, entity_type: EntityType) -> List[EntityMemory]:
        """按类型搜索"""
        with self._cache_lock:
            return [m for m in self._cache.values() if m.entity_type == entity_type]

    def search_by_tag(self, tag: str) -> List[EntityMemory]:
        """按标签搜索"""
        with self._cache_lock:
            return [m for m in self._cache.values() if tag in m.tags]

    def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        file_path = self._get_file_path(memory_id)
        with self._cache_lock:
            if memory_id in self._cache:
                del self._cache[memory_id]

        if file_path.exists():
            file_path.unlink()
            logger.info(f"删除记忆: {memory_id}")
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        type_counts = {}
        with self._cache_lock:
            for memory in self._cache.values():
                type_counts[memory.entity_type.value] = type_counts.get(memory.entity_type.value, 0) + 1

        return {
            "total_count": len(self._cache),
            "by_type": type_counts,
            "storage_path": str(self.memory_dir)
        }

    def clear_all(self):
        """清空所有记忆"""
        with self._cache_lock:
            self._cache.clear()

        if self.memory_dir.exists():
            import shutil
            shutil.rmtree(self.memory_dir)
            self.memory_dir.mkdir()

        logger.info("所有实体记忆已清空")


# 全局单例
_entity_memory_store: Optional[EntityMemoryStore] = None


def get_entity_memory_store() -> EntityMemoryStore:
    global _entity_memory_store
    if _entity_memory_store is None:
        _entity_memory_store = EntityMemoryStore()
    return _entity_memory_store