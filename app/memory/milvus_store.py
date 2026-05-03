# app/memory/milvus_store.py
"""Milvus 向量存储 - 适配你的配置"""

from typing import List, Optional, Dict, Any, Tuple
from loguru import logger
from langchain_core.documents import Document

from .config import memory_config
from .embedding_factory import get_embeddings


class MilvusVectorStore:
    """
    Milvus 向量存储管理器

    支持：
    - 文档添加和检索
    - 相似度搜索
    - 元数据过滤
    - 集合管理
    """

    def __init__(
            self,
            collection_name: str = "agent_long_term_memory",
            embeddings=None
    ):
        self.collection_name = collection_name
        self.host = memory_config.MILVUS_HOST
        self.port = memory_config.MILVUS_PORT
        self.user = memory_config.MILVUS_USER
        self.password = memory_config.MILVUS_PASSWORD
        self.dim = memory_config.EMBEDDING_DIMENSIONS

        # 获取 embedding 模型
        self.embeddings = embeddings or get_embeddings()

        # 连接状态
        self._connected = False
        self.collection = None

        # 初始化
        self._connect()
        self._init_collection()

        logger.info(f"MilvusVectorStore 初始化完成: collection={self.collection_name}, host={self.host}:{self.port}")

    def _connect(self):
        """建立 Milvus 连接"""
        try:
            from pymilvus import connections

            alias = "default"

            # 如果已有连接，先断开
            if connections.has_connection(alias):
                connections.disconnect(alias)

            # 创建新连接
            connection_args = {
                "alias": alias,
                "host": self.host,
                "port": self.port,
                "timeout": 10,
            }

            if self.user and self.password:
                connection_args["user"] = self.user
                connection_args["password"] = self.password

            connections.connect(**connection_args)
            self._connected = True
            logger.info(f"成功连接到 Milvus: {self.host}:{self.port}")

        except Exception as e:
            logger.error(f"连接 Milvus 失败: {e}")
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

                # 加载集合
                if self.collection.num_entities > 0:
                    try:
                        # 尝试加载，忽略已加载的错误
                        self.collection.load()
                        logger.info(f"集合已加载: {self.collection_name}")
                    except Exception as e:
                        error_msg = str(e).lower()
                        if "already loaded" in error_msg:
                            logger.debug(f"集合已加载: {self.collection_name}")
                        else:
                            logger.warning(f"加载集合失败: {e}")
                return

            # 创建新集合
            logger.info(f"创建新集合: {self.collection_name}")

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
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            self.collection.create_index(
                field_name="embedding",
                index_params=index_params
            )
            logger.info(f"索引创建成功")
        except Exception as e:
            logger.error(f"创建索引失败: {e}")

    def _ensure_collection_loaded(self):
        """确保集合已加载"""
        if self.collection is None:
            return False

        try:
            if self.collection.num_entities > 0:
                # 尝试加载，如果已加载会抛出异常，忽略即可
                try:
                    self.collection.load()
                except Exception as e:
                    error_msg = str(e).lower()
                    if "already loaded" not in error_msg:
                        logger.warning(f"加载集合: {e}")
            return True
        except Exception as e:
            logger.warning(f"加载集合失败: {e}")
            return False

    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """获取文本的向量表示"""
        if self.embeddings is None:
            logger.error("Embedding 模型未配置")
            return []

        try:
            if hasattr(self.embeddings, 'embed_documents'):
                embeddings = self.embeddings.embed_documents(texts)
            else:
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

        if not memory_config.ENABLE_STORAGE:
            logger.warning("向量存储已禁用")
            return []

        try:
            texts = [doc.page_content for doc in documents]
            metadatas = [doc.metadata for doc in documents]

            # 生成向量
            embeddings = self._get_embeddings(texts)
            if not embeddings:
                logger.error("向量生成失败")
                return []

            # 插入数据
            entities = [texts, embeddings, metadatas]
            mr = self.collection.insert(entities)

            # 刷新数据
            self.collection.flush()
            self._ensure_collection_loaded()

            logger.info(f"成功添加 {len(documents)} 个文档到 Milvus")

            ids = [str(i) for i in mr.primary_keys] if mr.primary_keys else []
            return ids

        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return []

    def similarity_search(
            self,
            query: str,
            k: Optional[int] = None,
            filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """相似度搜索"""
        results = self.similarity_search_with_score(query, k, filter_metadata)
        return [doc for doc, _ in results]

    def similarity_search_with_score(
            self,
            query: str,
            k: Optional[int] = None,
            filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, float]]:
        """带分数的相似度搜索"""
        if not self._connected or self.collection is None:
            logger.warning("向量存储不可用，返回空结果")
            return []

        try:
            k = k or memory_config.SIMILARITY_TOP_K

            # 生成查询向量
            query_embedding = self._get_embeddings([query])
            if not query_embedding:
                logger.error("查询向量生成失败")
                return []

            # 确保集合已加载
            if not self._ensure_collection_loaded():
                return []

            if self.collection.num_entities == 0:
                logger.warning("集合为空，无法搜索")
                return []

            # 搜索参数
            search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}

            # 构建过滤表达式
            expr = None
            if filter_metadata:
                expr = self._build_filter_expr(filter_metadata)

            # 执行搜索
            results = self.collection.search(
                data=[query_embedding[0]],
                anns_field="embedding",
                param=search_params,
                limit=k,
                expr=expr,
                output_fields=["text", "metadata"]
            )

            # 转换结果
            documents = []
            threshold = memory_config.SIMILARITY_THRESHOLD

            for hits in results:
                for hit in hits:
                    score = hit.score
                    if score < threshold:
                        continue

                    doc = Document(
                        page_content=hit.entity.get('text', ''),
                        metadata=hit.entity.get('metadata', {})
                    )
                    documents.append((doc, score))

            logger.debug(f"相似度搜索: query='{query[:50]}...', 返回={len(documents)} 条")
            return documents

        except Exception as e:
            logger.error(f"相似度搜索失败: {e}")
            return []

    def _build_filter_expr(self, filter_metadata: Dict[str, Any]) -> str:
        """构建 Milvus 过滤表达式"""
        conditions = []
        for key, value in filter_metadata.items():
            if isinstance(value, str):
                conditions.append(f'metadata["{key}"] == "{value}"')
            elif isinstance(value, (int, float)):
                conditions.append(f'metadata["{key}"] == {value}')
            else:
                conditions.append(f'metadata["{key}"] == "{str(value)}"')
        return " and ".join(conditions)

    def delete_by_source(self, source: str) -> int:
        """删除指定来源的文档"""
        if not self._connected or self.collection is None:
            return 0

        try:
            expr = f'metadata["_source"] == "{source}"'
            result = self.collection.delete(expr)
            deleted_count = result.delete_count if hasattr(result, "delete_count") else 0
            logger.info(f"删除文档: source={source}, 数量={deleted_count}")
            return deleted_count
        except Exception as e:
            logger.warning(f"删除文档失败: {e}")
            return 0

    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            from pymilvus import utility

            if not utility.has_collection(self.collection_name):
                return {"exists": False, "num_entities": 0}

            if self.collection is None:
                from pymilvus import Collection
                self.collection = Collection(self.collection_name)

            return {
                "exists": True,
                "name": self.collection_name,
                "num_entities": self.collection.num_entities,
            }
        except Exception as e:
            return {"exists": False, "num_entities": 0, "error": str(e)}

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