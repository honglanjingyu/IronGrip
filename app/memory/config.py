# app/memory/config.py
"""记忆模块配置 - 适配你的环境"""

import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger


def load_config():
    """加载环境配置"""
    env_paths = [
        Path.cwd() / ".env",
        Path(__file__).parent.parent.parent / ".env",
        Path(__file__).parent.parent / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"加载配置文件: {env_path}")
            return
    logger.warning("未找到 .env 配置文件，使用默认配置")


load_config()


class MemoryConfig:
    """记忆模块配置"""

    # ========== Embedding 配置 ==========
    EMBEDDING_TYPE: str = os.getenv("EMBEDDING_TYPE", "remote")

    # 远程 API 配置
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
    EMBEDDING_DIMENSIONS: int = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))

    # DashScope 专用
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "") or os.getenv("LLM_API_KEY", "")

    # 本地模型配置
    LOCAL_EMBEDDING_MODEL: str = os.getenv("LOCAL_EMBEDDING_MODEL", "bge-small-zh")
    LOCAL_EMBEDDING_PATH: Optional[str] = os.getenv("LOCAL_EMBEDDING_PATH")

    # 运行设备
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cpu")

    # 批量处理大小
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))

    # ========== 向量存储配置 ==========
    ENABLE_STORAGE: bool = os.getenv("ENABLE_STORAGE", "true").lower() == "true"
    VECTOR_STORE_TYPE: str = os.getenv("VECTOR_STORE_TYPE", "milvus")

    # Milvus 配置
    MILVUS_HOST: str = os.getenv("VECTOR_STORE_HOST", "localhost")
    MILVUS_PORT: str = os.getenv("VECTOR_STORE_PORT", "19530")
    MILVUS_USER: str = os.getenv("VECTOR_STORE_USER", "")
    MILVUS_PASSWORD: str = os.getenv("VECTOR_STORE_PASSWORD", "")

    # ========== 检索配置 ==========
    HYBRID_VECTOR_WEIGHT: float = float(os.getenv("HYBRID_VECTOR_WEIGHT", "0.6"))
    HYBRID_KEYWORD_WEIGHT: float = float(os.getenv("HYBRID_KEYWORD_WEIGHT", "0.4"))
    SIMILARITY_TOP_K: int = int(os.getenv("SIMILARITY_TOP_K", "5"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))

    # Rerank 配置
    RERANK_TYPE: str = os.getenv("RERANK_TYPE", "none")
    RERANK_MODEL: str = os.getenv("RERANK_MODEL", "gte-rerank-v2")
    RERANK_API_URL: str = os.getenv("RERANK_API_URL",
                                    "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank")

    # ========== 短期记忆配置 ==========
    SHORT_TERM_MAX_SIZE: int = int(os.getenv("SHORT_TERM_MAX_SIZE", "20"))

    # ========== 工作记忆配置 ==========
    WORKING_MAX_ITEMS: int = int(os.getenv("WORKING_MAX_ITEMS", "50"))
    WORKING_TTL_SECONDS: int = int(os.getenv("WORKING_TTL_SECONDS", "3600"))


memory_config = MemoryConfig()