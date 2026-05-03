# app/tools/builtin_tools.py
"""内置工具 - 供大脑模块调用"""

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from loguru import logger

# 导入 Milvus 相关模块
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.perception import MilvusVectorStore
from app.perception.config import vector_store_config, embedding_config

# 全局 Milvus 客户端（延迟初始化）
_milvus_store: Optional[MilvusVectorStore] = None


def get_milvus_store() -> MilvusVectorStore:
    """获取 Milvus 向量存储实例（单例）"""
    global _milvus_store
    if _milvus_store is None:
        try:
            logger.info("初始化 Milvus 向量存储...")
            _milvus_store = MilvusVectorStore(
                collection_name=vector_store_config.COLLECTION_NAME
            )
            logger.info(f"Milvus 向量存储初始化成功，集合: {vector_store_config.COLLECTION_NAME}")
        except Exception as e:
            logger.error(f"Milvus 向量存储初始化失败: {e}")
            _milvus_store = None
    return _milvus_store


@tool
def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    """
    获取当前时间

    Args:
        timezone: 时区，默认为 Asia/Shanghai（北京时间）

    Returns:
        str: 格式化的当前时间
    """
    try:
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        return now.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logger.error(f"获取时间失败: {e}")
        return f"获取时间失败: {str(e)}"


@tool
def search_knowledge(query: str, top_k: int = 3) -> str:
    """
    从 Milvus 知识库中搜索相关信息

    当用户的问题涉及专业知识、文档内容或需要参考资料时，使用此工具。

    Args:
        query: 搜索查询词或问题
        top_k: 返回结果数量，默认 3 条

    Returns:
        str: 格式化的搜索结果
    """
    logger.info(f"知识库搜索: query='{query}', top_k={top_k}")

    try:
        # 获取 Milvus 向量存储
        milvus_store = get_milvus_store()

        if milvus_store is None:
            return "知识库服务不可用，请检查 Milvus 连接配置。"

        # 检查集合是否有数据
        stats = milvus_store.get_collection_stats()
        if not stats.get('exists', False):
            return "知识库尚未初始化，请先上传文档。"

        entity_count = stats.get('num_entities', 0)
        if entity_count == 0:
            return "知识库为空，请先上传文档。"

        logger.info(f"知识库共有 {entity_count} 条记录")

        # 执行相似度搜索
        results = milvus_store.similarity_search_with_score(query, k=top_k)

        if not results:
            return f"未找到与 '{query}' 相关的知识。"

        # 格式化搜索结果
        formatted_results = []
        for i, (doc, score) in enumerate(results, 1):
            # 计算相似度百分比（余弦相似度范围 [0,1]）
            similarity_percent = score * 100

            # 提取元数据信息
            metadata = doc.metadata
            source = metadata.get('_file_name', metadata.get('source', '未知来源'))
            category = metadata.get('category', '未分类')

            # 格式化每条结果
            result_text = f"""
【结果 {i}】(相似度: {similarity_percent:.1f}%)
来源: {source}
分类: {category}
内容: {doc.page_content}
"""
            formatted_results.append(result_text.strip())

        # 添加搜索摘要
        summary = f"找到 {len(results)} 条相关知识：\n\n"
        return summary + "\n\n".join(formatted_results)

    except Exception as e:
        logger.error(f"知识库搜索失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return f"知识库搜索出错: {str(e)}"


@tool
def search_knowledge_with_filter(
        query: str,
        category: Optional[str] = None,
        top_k: int = 3
) -> str:
    """
    从 Milvus 知识库中搜索相关信息（支持分类过滤）

    Args:
        query: 搜索查询词或问题
        category: 分类过滤（如: troubleshooting, memory, alert, database, milvus, data-sync）
        top_k: 返回结果数量，默认 3 条

    Returns:
        str: 格式化的搜索结果
    """
    logger.info(f"知识库搜索: query='{query}', category='{category}', top_k={top_k}")

    try:
        milvus_store = get_milvus_store()

        if milvus_store is None:
            return "知识库服务不可用，请检查 Milvus 连接配置。"

        # 获取所有结果
        results = milvus_store.similarity_search_with_score(query, k=top_k * 2)

        # 按分类过滤（如果有指定）
        if category:
            filtered_results = [
                (doc, score) for doc, score in results
                if doc.metadata.get('category') == category
            ]
            results = filtered_results[:top_k]
        else:
            results = results[:top_k]

        if not results:
            filter_msg = f"且分类为 '{category}'" if category else ""
            return f"未找到与 '{query}'{filter_msg} 相关的知识。"

        # 格式化结果
        formatted_results = []
        for i, (doc, score) in enumerate(results, 1):
            similarity_percent = score * 100
            metadata = doc.metadata

            result_text = f"""
【结果 {i}】(相似度: {similarity_percent:.1f}%)
来源: {metadata.get('_file_name', metadata.get('source', '未知'))}
分类: {metadata.get('category', '未分类')}
内容: {doc.page_content}
"""
            formatted_results.append(result_text.strip())

        summary = f"找到 {len(results)} 条相关知识：\n\n"
        return summary + "\n\n".join(formatted_results)

    except Exception as e:
        logger.error(f"知识库搜索失败: {e}")
        return f"知识库搜索出错: {str(e)}"


@tool
def get_knowledge_stats() -> str:
    """
    获取知识库统计信息

    Returns:
        str: 知识库统计信息
    """
    try:
        milvus_store = get_milvus_store()

        if milvus_store is None:
            return "知识库服务不可用，请检查 Milvus 连接配置。"

        stats = milvus_store.get_collection_stats()

        if not stats.get('exists', False):
            return "知识库尚未初始化。"

        entity_count = stats.get('num_entities', 0)

        # 尝试获取分类统计
        category_stats = {}
        try:
            # 查询所有文档来统计分类（简单实现）
            results = milvus_store.similarity_search_with_score("", k=100)
            for doc, _ in results:
                category = doc.metadata.get('category', '未分类')
                category_stats[category] = category_stats.get(category, 0) + 1
        except:
            pass

        info = f"""
知识库统计信息:
- 集合名称: {vector_store_config.COLLECTION_NAME}
- 文档总数: {entity_count}
- 向量维度: {embedding_config.EMBEDDING_DIMENSIONS}
- Milvus 地址: {vector_store_config.MILVUS_HOST}:{vector_store_config.MILVUS_PORT}
"""

        if category_stats:
            info += "\n分类统计:\n"
            for cat, count in category_stats.items():
                info += f"  - {cat}: {count} 条\n"

        return info.strip()

    except Exception as e:
        logger.error(f"获取知识库统计失败: {e}")
        return f"获取知识库统计出错: {str(e)}"


@tool
def add_to_knowledge(content: str, category: str = "general", source: str = "user") -> str:
    """
    添加知识到 Milvus 知识库

    Args:
        content: 要添加的知识内容
        category: 分类（如: general, troubleshooting, faq 等）
        source: 来源（如: user, system, document 等）

    Returns:
        str: 操作结果
    """
    logger.info(f"添加知识: category='{category}', source='{source}', 内容长度={len(content)}")

    try:
        from langchain_core.documents import Document

        milvus_store = get_milvus_store()

        if milvus_store is None:
            return "知识库服务不可用，请检查 Milvus 连接配置。"

        # 创建文档
        doc = Document(
            page_content=content,
            metadata={
                "source": source,
                "category": category,
                "timestamp": datetime.now().isoformat()
            }
        )

        # 添加到向量存储
        ids = milvus_store.add_documents([doc])

        if ids:
            return f"✅ 知识已成功添加到知识库 (ID: {ids[0]})"
        else:
            return "❌ 添加知识失败"

    except Exception as e:
        logger.error(f"添加知识失败: {e}")
        return f"添加知识出错: {str(e)}"