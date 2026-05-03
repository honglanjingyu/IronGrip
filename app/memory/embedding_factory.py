# app/memory/embedding_factory.py
"""Embedding 工厂 - 支持远程和本地模型"""

from typing import List, Optional
from loguru import logger

from .config import memory_config


class EmbeddingFactory:
    """Embedding 模型工厂 - 单例模式"""

    _instance = None
    _embeddings = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._embeddings = None
        logger.info("EmbeddingFactory 初始化完成")

    def get_embeddings(self):
        """获取 embedding 实例"""
        if self._embeddings is None:
            self._embeddings = self._create_embeddings()
        return self._embeddings

    def _create_embeddings(self):
        """根据配置创建 embedding 模型"""
        if memory_config.EMBEDDING_TYPE == "remote":
            return self._create_remote_embeddings()
        else:
            return self._create_local_embeddings()

    def _create_remote_embeddings(self):
        """创建远程 Embedding（DashScope）"""
        try:
            # 方案1: 使用 DashScope 专用 SDK
            try:
                from langchain_community.embeddings import DashScopeEmbeddings

                logger.info(f"使用 DashScope Embedding: model={memory_config.EMBEDDING_MODEL}")

                embeddings = DashScopeEmbeddings(
                    model=memory_config.EMBEDDING_MODEL,
                    dashscope_api_key=memory_config.DASHSCOPE_API_KEY or memory_config.LLM_API_KEY,
                )

                # 测试 embedding
                test_result = embeddings.embed_query("test")
                logger.info(f"DashScope Embedding 测试成功，向量维度: {len(test_result)}")
                return embeddings

            except ImportError:
                logger.warning("DashScopeEmbeddings 不可用，尝试使用 OpenAI 兼容接口")

            # 方案2: 使用 OpenAI 兼容接口
            from langchain_openai import OpenAIEmbeddings

            api_key = memory_config.DASHSCOPE_API_KEY or memory_config.LLM_API_KEY
            if not api_key:
                logger.warning("未配置 API Key，远程 Embedding 将不可用")
                return None

            logger.info(f"使用 OpenAI 兼容接口: model={memory_config.EMBEDDING_MODEL}")

            embeddings = OpenAIEmbeddings(
                model=memory_config.EMBEDDING_MODEL,
                openai_api_key=api_key,
                openai_api_base=memory_config.LLM_BASE_URL,
                chunk_size=memory_config.EMBEDDING_BATCH_SIZE,
            )

            # 测试 embedding
            test_result = embeddings.embed_query("测试文本")
            logger.info(f"OpenAI 兼容接口 Embedding 测试成功，向量维度: {len(test_result)}")
            return embeddings

        except Exception as e:
            logger.error(f"创建远程 Embedding 失败: {e}")
            if memory_config.EMBEDDING_TYPE == "remote":
                logger.warning("远程 Embedding 失败，回退到本地 Embedding")
                return self._create_local_embeddings()
            raise

    def _create_local_embeddings(self):
        """创建本地 Embedding（HuggingFace）"""
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings

            model_kwargs = {'device': memory_config.EMBEDDING_DEVICE}
            encode_kwargs = {'normalize_embeddings': True}

            # 模型名称映射
            model_mapping = {
                "bge-small-zh": "BAAI/bge-small-zh-v1.5",
                "bge-base-zh": "BAAI/bge-base-zh-v1.5",
                "bge-large-zh": "BAAI/bge-large-zh-v1.5",
                "m3e-base": "m3e-base",
                "text2vec-base": "shibing624/text2vec-base-chinese",
            }

            model_name = memory_config.LOCAL_EMBEDDING_MODEL
            hf_model_name = model_mapping.get(model_name, model_name)

            # 优先使用本地路径
            if memory_config.LOCAL_EMBEDDING_PATH:
                model_path = memory_config.LOCAL_EMBEDDING_PATH
                logger.info(f"使用本地模型路径: {model_path}")
            else:
                model_path = hf_model_name
                logger.info(f"使用 HuggingFace 模型: {model_path}")

            embeddings = HuggingFaceEmbeddings(
                model_name=model_path,
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs,
            )

            # 测试 embedding
            test_result = embeddings.embed_query("测试文本")
            logger.info(f"本地 Embedding 创建成功，向量维度: {len(test_result)}")
            return embeddings

        except Exception as e:
            logger.error(f"创建本地 Embedding 失败: {e}")
            raise


# 全局单例
_embedding_factory = None


def get_embeddings():
    """获取全局 Embedding 实例"""
    global _embedding_factory
    if _embedding_factory is None:
        _embedding_factory = EmbeddingFactory()
    return _embedding_factory.get_embeddings()