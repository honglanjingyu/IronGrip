# app/perception/__init__.py
"""感知模块 (Perception Module)

提供 Agent 的感知能力：
- 输入处理：接收并标准化多模态输入
- 环境感知：获取当前状态信息
- 记忆检索：从短期/长期记忆检索相关信息
"""

from .models import (
    InputData, InputType, EnvironmentContext,
    MemoryItem, MemoryType, PerceptionResult
)
from .input_handler import InputHandler
from .environment_sensor import EnvironmentSensor
from .memory_retriever import MemoryRetriever, ShortTermMemory, LongTermMemory, WorkingMemory
from .perception_manager import PerceptionManager
from .config import (
    vector_store_config, embedding_config, retrieval_config,
    validate_config
)

# 尝试导入 Milvus 存储（如果可用）
try:
    from .milvus_store import MilvusVectorStore, EmbeddingFactory
    __all___ext = ["MilvusVectorStore", "EmbeddingFactory"]
except ImportError:
    __all___ext = []

__all__ = [
    "InputData",
    "InputType",
    "EnvironmentContext",
    "MemoryItem",
    "MemoryType",
    "PerceptionResult",
    "InputHandler",
    "EnvironmentSensor",
    "MemoryRetriever",
    "ShortTermMemory",
    "LongTermMemory",
    "WorkingMemory",
    "PerceptionManager",
    "vector_store_config",
    "embedding_config",
    "retrieval_config",
    "validate_config",
] + __all___ext