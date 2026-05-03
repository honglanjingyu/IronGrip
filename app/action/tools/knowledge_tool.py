"""知识库工具 - 从 Milvus 知识库检索信息"""

from typing import Optional
from loguru import logger

# 导入感知模块的向量存储
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from app.perception import MilvusVectorStore
    from app.perception.config import vector_store_config, embedding_config
except ImportError:
    logger.warning("无法导入感知模块，知识库工具将不可用")
    MilvusVectorStore = None
    vector_store_config = None
    embedding_config = None


_milvus_store = None


def get_milvus_store():
    """获取 Milvus 向量存储实例（单例）"""
    global _milvus_store

    if MilvusVectorStore is None:
        logger.error("感知模块不可用")
        return None

    if _milvus_store is None:
        try:
            _milvus_store = MilvusVectorStore(
                collection_name=vector_store_config.COLLECTION_NAME if vector_store_config else "agent_long_term_memory"
            )
            logger.info(f"Milvus 向量存储初始化成功")
        except Exception as e:
            logger.error(f"Milvus 向量存储初始化失败: {e}")
            _milvus_store = None
    return _milvus_store


async def search_knowledge(query: str, top_k: int = 3) -> str:
    """
    从知识库中搜索相关信息

    Args:
        query: 搜索查询词
        top_k: 返回结果数量，默认 3 条

    Returns:
        str: 格式化的搜索结果
    """
    logger.info(f"知识库搜索: query='{query}', top_k={top_k}")

    milvus_store = get_milvus_store()

    if milvus_store is None:
        return "知识库服务不可用，请检查 Milvus 连接配置。"

    try:
        stats = milvus_store.get_collection_stats()
        if not stats.get('exists', False) or stats.get('num_entities', 0) == 0:
            return "知识库为空，请先上传文档。"

        results = milvus_store.similarity_search_with_score(query, k=top_k)

        if not results:
            return f"未找到与 '{query}' 相关的知识。"

        formatted = []
        for i, (doc, score) in enumerate(results, 1):
            similarity = score * 100
            metadata = doc.metadata
            source = metadata.get('_file_name', metadata.get('source', '未知来源'))
            category = metadata.get('category', '未分类')

            formatted.append(
                f"【结果 {i}】(相似度: {similarity:.1f}%)\n"
                f"来源: {source}\n"
                f"分类: {category}\n"
                f"内容: {doc.page_content}"
            )

        return f"找到 {len(results)} 条相关知识：\n\n" + "\n\n".join(formatted)

    except Exception as e:
        logger.error(f"知识库搜索失败: {e}")
        return f"知识库搜索出错: {str(e)}"


async def search_knowledge_with_filter(
    query: str,
    category: Optional[str] = None,
    top_k: int = 3
) -> str:
    """
    从知识库中搜索（支持分类过滤）

    Args:
        query: 搜索查询词
        category: 分类过滤
        top_k: 返回结果数量

    Returns:
        str: 格式化的搜索结果
    """
    milvus_store = get_milvus_store()

    if milvus_store is None:
        return "知识库服务不可用"

    try:
        results = milvus_store.similarity_search_with_score(query, k=top_k * 2)

        if category:
            results = [(doc, score) for doc, score in results
                       if doc.metadata.get('category') == category]
            results = results[:top_k]
        else:
            results = results[:top_k]

        if not results:
            filter_msg = f"且分类为 '{category}'" if category else ""
            return f"未找到与 '{query}'{filter_msg} 相关的知识。"

        formatted = []
        for i, (doc, score) in enumerate(results, 1):
            similarity = score * 100
            metadata = doc.metadata

            formatted.append(
                f"【结果 {i}】(相似度: {similarity:.1f}%)\n"
                f"来源: {metadata.get('_file_name', metadata.get('source', '未知'))}\n"
                f"分类: {metadata.get('category', '未分类')}\n"
                f"内容: {doc.page_content}"
            )

        return f"找到 {len(results)} 条相关知识：\n\n" + "\n\n".join(formatted)

    except Exception as e:
        logger.error(f"知识库搜索失败: {e}")
        return f"知识库搜索出错: {str(e)}"


async def get_knowledge_stats() -> str:
    """获取知识库统计信息"""
    milvus_store = get_milvus_store()

    if milvus_store is None:
        return "知识库服务不可用"

    try:
        stats = milvus_store.get_collection_stats()

        if not stats.get('exists', False):
            return "知识库尚未初始化。"

        result = f"""
知识库统计信息:
- 集合名称: {vector_store_config.COLLECTION_NAME if vector_store_config else 'N/A'}
- 文档总数: {stats.get('num_entities', 0)}
- Milvus 地址: {vector_store_config.MILVUS_HOST}:{vector_store_config.MILVUS_PORT if vector_store_config else 'N/A'}
""".strip()

        return result

    except Exception as e:
        logger.error(f"获取知识库统计失败: {e}")
        return f"获取知识库统计出错: {str(e)}"


async def add_to_knowledge(content: str, category: str = "general", source: str = "user") -> str:
    """
    添加知识到知识库

    Args:
        content: 知识内容
        category: 分类
        source: 来源

    Returns:
        str: 操作结果
    """
    from langchain_core.documents import Document
    from datetime import datetime

    milvus_store = get_milvus_store()

    if milvus_store is None:
        return "知识库服务不可用"

    try:
        doc = Document(
            page_content=content,
            metadata={
                "source": source,
                "category": category,
                "timestamp": datetime.now().isoformat()
            }
        )

        ids = milvus_store.add_documents([doc])

        if ids:
            return f"✅ 知识已成功添加到知识库 (ID: {ids[0]})"
        else:
            return "❌ 添加知识失败"

    except Exception as e:
        logger.error(f"添加知识失败: {e}")
        return f"添加知识出错: {str(e)}"