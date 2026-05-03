# app/perception/config.py
"""感知模块配置管理"""

import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger


# 加载 .env 文件
def load_config():
    """加载环境配置"""
    # 查找 .env 文件
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


class VectorStoreConfig:
    """向量存储配置"""

    # 是否启用存储
    ENABLE_STORAGE: bool = os.getenv("ENABLE_STORAGE", "true").lower() == "true"

    # 向量存储类型
    VECTOR_STORE_TYPE: str = os.getenv("VECTOR_STORE_TYPE", "milvus")

    # Milvus 配置
    MILVUS_HOST: str = os.getenv("VECTOR_STORE_HOST", "localhost")
    MILVUS_PORT: str = os.getenv("VECTOR_STORE_PORT", "19530")
    MILVUS_USER: str = os.getenv("VECTOR_STORE_USER", "")
    MILVUS_PASSWORD: str = os.getenv("VECTOR_STORE_PASSWORD", "")

    # Elasticsearch 配置（备用）
    ES_HOST: str = os.getenv("VECTOR_STORE_HOST", "localhost")
    ES_PORT: str = os.getenv("VECTOR_STORE_PORT", "9200")
    ES_USER: str = os.getenv("VECTOR_STORE_USER", "")
    ES_PASSWORD: str = os.getenv("VECTOR_STORE_PASSWORD", "")

    # 集合名称
    COLLECTION_NAME: str = os.getenv("VECTOR_STORE_COLLECTION", "agent_long_term_memory")

class EmbeddingConfig:
    """Embedding 模型配置"""

    # Embedding 类型: remote, dashscope, local
    EMBEDDING_TYPE: str = os.getenv("EMBEDDING_TYPE", "remote")

    # 远程 API 配置
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
    EMBEDDING_DIMENSIONS: int = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))

    # DashScope 专用配置
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "") or os.getenv("LLM_API_KEY", "")

    # 本地模型配置
    LOCAL_EMBEDDING_MODEL: str = os.getenv("LOCAL_EMBEDDING_MODEL", "bge-small-zh")
    LOCAL_EMBEDDING_PATH: Optional[str] = os.getenv("LOCAL_EMBEDDING_PATH")

    # 运行设备
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cpu")

    # 批量处理大小
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))


class RetrievalConfig:
    """检索配置"""

    # 混合检索权重
    HYBRID_VECTOR_WEIGHT: float = float(os.getenv("HYBRID_VECTOR_WEIGHT", "0.6"))
    HYBRID_KEYWORD_WEIGHT: float = float(os.getenv("HYBRID_KEYWORD_WEIGHT", "0.4"))

    # Top-K 召回数量
    SIMILARITY_TOP_K: int = int(os.getenv("SIMILARITY_TOP_K", "5"))

    # 相似度阈值
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))

    # Rerank 配置
    RERANK_TYPE: str = os.getenv("RERANK_TYPE", "none")  # none, remote, local
    RERANK_MODEL: str = os.getenv("RERANK_MODEL", "gte-rerank-v2")
    RERANK_API_URL: str = os.getenv("RERANK_API_URL", "")


def validate_config() -> bool:
    """验证配置是否有效"""
    valid = True

    if EmbeddingConfig.EMBEDDING_TYPE == "remote":
        if not EmbeddingConfig.LLM_API_KEY:
            logger.warning("远程 Embedding 需要配置 LLM_API_KEY")
            valid = False

    if not VectorStoreConfig.ENABLE_STORAGE:
        logger.info("向量存储已禁用（ENABLE_STORAGE=false）")

    return valid


# 导出配置实例
vector_store_config = VectorStoreConfig()
embedding_config = EmbeddingConfig()
retrieval_config = RetrievalConfig()