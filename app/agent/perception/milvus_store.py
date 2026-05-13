# app/perception/milvus_store.py
"""Milvus 向量存储管理器 - 直接使用 PyMilvus，避免 LangChain 连接问题"""

from typing import List, Optional, Dict, Any, Tuple
from loguru import logger
import numpy as np
from langchain_core.documents import Document

from .config import vector_store_config, embedding_config, retrieval_config


class EmbeddingFactory:
    """Embedding 模型工厂 - 根据配置创建"""

    _instance = None
    _embeddings = None

    @classmethod
    def get_embeddings(cls):
        """获取 embedding 模型实例（单例）"""
        if cls._embeddings is None:
            cls._embeddings = cls._create_embeddings()
        return cls._embeddings

    @classmethod
    def _create_embeddings(cls):
        """创建 embedding 模型"""
        if embedding_config.EMBEDDING_TYPE == "remote":
            return cls._create_remote_embeddings()
        else:
            return cls._create_local_embeddings()

    @classmethod
    def _create_remote_embeddings(cls):
        """创建远程 API Embedding（支持阿里云 DashScope）"""
        try:
            # 尝试使用 DashScope 专用 SDK
            try:
                from langchain_community.embeddings import DashScopeEmbeddings

                logger.info(f"使用 DashScope Embedding: model={embedding_config.EMBEDDING_MODEL}")

                embeddings = DashScopeEmbeddings(
                    model=embedding_config.EMBEDDING_MODEL,
                    dashscope_api_key=embedding_config.LLM_API_KEY,
                )

                # 测试 embedding
                test_result = embeddings.embed_query("test")
                logger.info(f"DashScope Embedding 测试成功，向量维度: {len(test_result)}")
                return embeddings

            except ImportError:
                logger.warning("DashScopeEmbeddings 不可用，尝试使用 OpenAI 兼容接口")

                # 使用 OpenAI 兼容接口
                from langchain_openai import OpenAIEmbeddings

                logger.info(f"使用 OpenAI 兼容接口 Embedding: model={embedding_config.EMBEDDING_MODEL}")

                embeddings = OpenAIEmbeddings(
                    model=embedding_config.EMBEDDING_MODEL,
                    openai_api_key=embedding_config.LLM_API_KEY,
                    openai_api_base=embedding_config.LLM_BASE_URL,
                    chunk_size=embedding_config.EMBEDDING_BATCH_SIZE,
                )

                # 测试 embedding
                test_result = embeddings.embed_query("测试文本")
                logger.info(f"OpenAI 兼容接口 Embedding 测试成功，向量维度: {len(test_result)}")
                return embeddings

        except Exception as e:
            logger.error(f"创建远程 Embedding 失败: {e}")
            logger.warning("回退到本地 Embedding")
            return cls._create_local_embeddings()

    @classmethod
    def _create_local_embeddings(cls):
        """创建本地 HuggingFace Embedding"""
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings

            model_name = embedding_config.LOCAL_EMBEDDING_MODEL
            model_kwargs = {'device': embedding_config.EMBEDDING_DEVICE}
            encode_kwargs = {'normalize_embeddings': True}

            # 映射模型名称到 HuggingFace 模型 ID
            model_mapping = {
                "bge-small-zh": "BAAI/bge-small-zh-v1.5",
                "bge-base-zh": "BAAI/bge-base-zh-v1.5",
                "bge-large-zh": "BAAI/bge-large-zh-v1.5",
                "m3e-base": "m3e-base",
                "text2vec-base": "shibing624/text2vec-base-chinese",
            }

            hf_model_name = model_mapping.get(model_name, model_name)

            # 如果指定了本地路径
            if embedding_config.LOCAL_EMBEDDING_PATH:
                model_kwargs['model_name'] = embedding_config.LOCAL_EMBEDDING_PATH
            else:
                model_kwargs['model_name'] = hf_model_name

            logger.info(f"创建本地 Embedding: model={hf_model_name}, device={embedding_config.EMBEDDING_DEVICE}")

            return HuggingFaceEmbeddings(
                model_name=model_kwargs['model_name'],
                model_kwargs={'device': embedding_config.EMBEDDING_DEVICE},
                encode_kwargs=encode_kwargs,
            )
        except Exception as e:
            logger.error(f"创建本地 Embedding 失败: {e}")
            raise


class MilvusVectorStore:
    """
    Milvus 向量存储管理器 - 直接使用 PyMilvus
    避免 LangChain 的连接冲突问题
    """

    def __init__(
            self,
            collection_name: Optional[str] = None,
            embeddings=None
    ):
        self.collection_name = collection_name or vector_store_config.COLLECTION_NAME
        self.host = vector_store_config.MILVUS_HOST
        self.port = vector_store_config.MILVUS_PORT
        self.user = vector_store_config.MILVUS_USER
        self.password = vector_store_config.MILVUS_PASSWORD
        self.dim = embedding_config.EMBEDDING_DIMENSIONS

        # 添加 alias 属性
        self.alias = "default"

        # 获取 embedding 模型
        self.embeddings = embeddings or EmbeddingFactory.get_embeddings()

        # 添加 logger 属性
        self.logger = logger

        # 连接和集合
        self._connected = False
        self.collection = None

        # 初始化
        self._connect()
        self._init_collection()

        logger.info(f"MilvusVectorStore 初始化完成: collection={self.collection_name}, host={self.host}:{self.port}")

    def _connect(self):
        """建立 Milvus 连接"""
        if self._connected:
            try:
                from pymilvus import connections
                if connections.has_connection(self.alias):
                    self.logger.debug(f"Milvus 连接已存在且有效: {self.alias}")
                    return
            except Exception as e:
                self.logger.warning(f"现有连接无效: {e}")
                self._connected = False

        # 重新建立连接
        try:
            from pymilvus import connections

            # 如果已有同名连接，先断开
            if connections.has_connection(self.alias):
                connections.disconnect(self.alias)

            # 创建新连接
            connections.connect(
                alias=self.alias,
                host=self.host,
                port=self.port,
                timeout=10
            )
            self._connected = True
            self.logger.info(f"成功连接到 Milvus: {self.host}:{self.port}")
        except Exception as e:
            self.logger.error(f"连接 Milvus 失败: {e}")
            self._connected = False

    def _init_collection(self):
        """初始化集合"""
        if not self._connected:
            return

        try:
            from pymilvus import Collection, CollectionSchema, FieldSchema, DataType, utility

            # 检查集合是否存在
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                logger.info(f"集合已存在: {self.collection_name}, 实体数: {self.collection.num_entities}")

                # 检查索引
                if not self.collection.has_index():
                    self._create_index()

                # 尝试加载集合（如果有数据）
                if self.collection.num_entities > 0:
                    try:
                        self.collection.load()
                        logger.info(f"集合已加载: {self.collection_name}")
                    except Exception as e:
                        logger.warning(f"加载集合失败: {e}")
                return

            # 创建新集合
            logger.info(f"创建新集合: {self.collection_name}")

            # 定义字段 - 注意字段顺序: id, text, embedding, metadata
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
                FieldSchema(name="metadata", dtype=DataType.JSON),
            ]

            schema = CollectionSchema(fields, description="Agent 长期记忆集合")
            self.collection = Collection(self.collection_name, schema)

            # 创建索引
            self._create_index()

            logger.info(f"集合创建成功: {self.collection_name}")

        except Exception as e:
            logger.error(f"初始化集合失败: {e}")
            self.collection = None

    def _create_index(self):
        """创建向量索引"""
        if self.collection is None:
            return

        try:
            index_params = {
                "metric_type": "COSINE",  # 改为余弦相似度
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            self.collection.create_index(
                field_name="embedding",
                index_params=index_params
            )
            logger.info(f"索引创建成功: {index_params}")
        except Exception as e:
            logger.error(f"创建索引失败: {e}")

    def _ensure_collection_loaded(self):
        """确保集合已加载到内存"""
        if self.collection is None:
            return False

        try:
            # 检查集合是否已加载
            if hasattr(self.collection, 'is_loaded'):
                if self.collection.is_loaded:
                    return True
            else:
                # 旧版本 PyMilvus，尝试加载，如果已加载会忽略
                pass

            # 尝试加载集合
            if self.collection.num_entities > 0:
                self.collection.load()
                logger.debug("集合已加载到内存")
            return True
        except Exception as e:
            logger.warning(f"加载集合失败: {e}")
            return False

    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """获取文本的向量表示"""
        try:
            # 使用 embedding 模型生成向量
            # LangChain embeddings 的 embed_documents 方法
            if hasattr(self.embeddings, 'embed_documents'):
                embeddings = self.embeddings.embed_documents(texts)
            else:
                # 回退到单个 embedding
                embeddings = [self.embeddings.embed_query(text) for text in texts]
            return embeddings
        except Exception as e:
            logger.error(f"生成向量失败: {e}")
            return []

    def add_documents(self, documents: List[Document]) -> List[str]:
        """添加文档到向量存储"""
        if not self._connected or self.collection is None:
            logger.warning("向量存储不可用，无法添加文档")
            return []

        if not vector_store_config.ENABLE_STORAGE:
            logger.warning("向量存储已禁用")
            return []

        try:
            # 准备数据
            texts = [doc.page_content for doc in documents]
            metadatas = [doc.metadata for doc in documents]

            # 生成向量
            embeddings = self._get_embeddings(texts)
            if not embeddings:
                logger.error("向量生成失败")
                return []

            # 字段顺序必须与定义时一致: text, embedding, metadata
            # id 是自动生成的，不需要传入
            entities = [
                texts,  # text 字段
                embeddings,  # embedding 字段
                metadatas,  # metadata 字段
            ]

            # 插入数据
            mr = self.collection.insert(entities)

            # 刷新数据
            self.collection.flush()

            # 确保集合已加载（如果是新添加的数据）
            self._ensure_collection_loaded()

            logger.info(f"成功添加 {len(documents)} 个文档到 Milvus")

            # 返回 ID 列表
            ids = [str(i) for i in mr.primary_keys] if mr.primary_keys else []
            return ids

        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def similarity_search(self, query: str, k: Optional[int] = None) -> List[Document]:
        """相似度搜索"""
        results = self.similarity_search_with_score(query, k)
        return [doc for doc, _ in results]

    def similarity_search_with_score(self, query: str, k: Optional[int] = None) -> List[Tuple[Document, float]]:
        """带分数的相似度搜索"""
        if not self._connected or self.collection is None:
            logger.warning("向量存储不可用，返回空结果")
            return []

        try:
            k = k or retrieval_config.SIMILARITY_TOP_K

            # 生成查询向量
            query_embedding = self._get_embeddings([query])
            if not query_embedding:
                logger.error("查询向量生成失败")
                return []

            # 确保集合已加载
            if not self._ensure_collection_loaded():
                logger.warning("集合无法加载，返回空结果")
                return []

            # 检查是否有数据
            if self.collection.num_entities == 0:
                logger.warning("集合为空，无法搜索")
                return []

            # 搜索参数 - 改为余弦相似度
            search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}

            # 执行搜索 - 指定输出字段
            results = self.collection.search(
                data=[query_embedding[0]],
                anns_field="embedding",
                param=search_params,
                limit=k,
                output_fields=["text", "metadata"]
            )

            # 转换结果
            documents = []
            threshold = retrieval_config.SIMILARITY_THRESHOLD

            for hits in results:
                for hit in hits:
                    score = hit.score

                    # 过滤低于阈值的结果（余弦相似度范围在[0,1]或[-1,1]之间）
                    if score < threshold:
                        continue

                    # 转换为 Document
                    doc = Document(
                        page_content=hit.entity.get('text', ''),
                        metadata=hit.entity.get('metadata', {})
                    )
                    documents.append((doc, score))

            logger.debug(f"相似度搜索: query='{query[:50]}...', 返回={len(documents)} 条")
            return documents

        except Exception as e:
            logger.error(f"相似度搜索失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def delete_collection(self):
        """删除集合"""
        if not self._connected:
            return

        try:
            from pymilvus import utility
            if utility.has_collection(self.collection_name):
                utility.drop_collection(self.collection_name)
                logger.info(f"删除集合: {self.collection_name}")
                self.collection = None
        except Exception as e:
            logger.error(f"删除集合失败: {e}")

    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            from pymilvus import utility

            if not utility.has_collection(self.collection_name):
                return {"error": f"集合 '{self.collection_name}' 不存在", "exists": False}

            if self.collection is None:
                from pymilvus import Collection
                self.collection = Collection(self.collection_name)

            # 确保统计信息是最新的
            self.collection.flush()

            return {
                "name": self.collection_name,
                "exists": True,
                "num_entities": self.collection.num_entities,
            }
        except Exception as e:
            return {"error": str(e), "exists": False}