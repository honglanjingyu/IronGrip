# app/action/tools/knowledge_tool.py
"""知识库工具 - 支持会话隔离"""

from typing import Optional
from datetime import datetime
from loguru import logger


# 这些函数需要根据你的实际实现来定义
def get_long_term_memory():
    """获取长期记忆实例 - 根据你的项目实现"""
    from app.memory import get_memory_manager
    return get_memory_manager().long_term


async def search_knowledge(query: str, top_k: int = 3, session_id: str = "") -> str:
    """从知识库中搜索相关信息（支持会话隔离）"""
    logger.info(f"[会话 {session_id}] 知识库搜索: query='{query}', top_k={top_k}")

    long_memory = get_long_term_memory()
    if long_memory is None:
        return "知识库服务不可用，请检查 Milvus 连接配置。"

    try:
        stats = long_memory.get_stats()
        if not stats.get('available', False) or stats.get('num_entities', 0) == 0:
            return "知识库为空，请先上传文档。"

        # 使用会话ID进行过滤
        results = await long_memory.retrieve(
            query,
            session_id=session_id if session_id else None,
            top_k=top_k,
            enable_rerank=False
        )

        if not results:
            return f"未找到与 '{query}' 相关的知识。"

        formatted = []
        for i, item in enumerate(results, 1):
            similarity = item.score * 100
            metadata = item.metadata
            source = metadata.get('_file_name', metadata.get('source', '未知来源'))
            category = metadata.get('category', '未分类')

            formatted.append(
                f"\n【结果 {i}】(相似度: {similarity:.1f}%)\n"
                f"来源: {source}\n"
                f"分类: {category}\n"
                f"内容: {item.content}"
            )

        return f"找到 {len(results)} 条相关知识：\n" + "\n".join(formatted)

    except Exception as e:
        logger.error(f"知识库搜索失败: {e}")
        return f"知识库搜索出错: {str(e)}"


async def search_knowledge_with_filter(
        query: str,
        category: Optional[str] = None,
        top_k: int = 3,
        session_id: str = ""
) -> str:
    """从知识库中搜索（支持分类过滤和会话隔离）"""
    logger.info(f"[会话 {session_id}] 知识库过滤搜索: query='{query}', category={category}, top_k={top_k}")

    long_memory = get_long_term_memory()

    if long_memory is None:
        return "知识库服务不可用"

    try:
        results = await long_memory.retrieve(
            query,
            session_id=session_id if session_id else None,
            top_k=top_k * 2,
            enable_rerank=False
        )

        if category:
            results = [item for item in results if item.metadata.get('category') == category]
            results = results[:top_k]
        else:
            results = results[:top_k]

        if not results:
            filter_msg = f"且分类为 '{category}'" if category else ""
            return f"未找到与 '{query}'{filter_msg} 相关的知识。"

        formatted = []
        for i, item in enumerate(results, 1):
            similarity = item.score * 100
            metadata = item.metadata

            formatted.append(
                f"【结果 {i}】(相似度: {similarity:.1f}%)\n"
                f"来源: {metadata.get('_file_name', metadata.get('source', '未知'))}\n"
                f"分类: {metadata.get('category', '未分类')}\n"
                f"内容: {item.content}"
            )

        return f"找到 {len(results)} 条相关知识：\n\n" + "\n\n".join(formatted)

    except Exception as e:
        logger.error(f"知识库搜索失败: {e}")
        return f"知识库搜索出错: {str(e)}"


async def add_to_knowledge(content: str, category: str = "general", source: str = "user", session_id: str = "") -> str:
    """添加知识到知识库（自动关联会话）"""
    logger.info(f"[会话 {session_id}] 添加知识: category={category}, source={source}")

    long_memory = get_long_term_memory()

    if long_memory is None:
        return "知识库服务不可用"

    try:
        success = await long_memory.add_knowledge(
            content=content,
            session_id=session_id if session_id else None,
            metadata={
                "source": source,
                "category": category,
                "timestamp": datetime.now().isoformat()
            }
        )

        if success:
            return f"✅ 知识已成功添加到知识库"
        else:
            return "❌ 添加知识失败"

    except Exception as e:
        logger.error(f"添加知识失败: {e}")
        return f"添加知识出错: {str(e)}"


async def get_knowledge_stats(session_id: str = "") -> str:
    """获取知识库统计信息"""
    logger.info(f"[会话 {session_id}] 获取知识库统计")

    long_memory = get_long_term_memory()

    if long_memory is None:
        return "知识库服务不可用"

    try:
        stats = long_memory.get_stats(session_id=session_id if session_id else None)

        if not stats.get('available', False):
            return "知识库未初始化，请检查配置"

        num_entities = stats.get('num_entities', 0)

        return f"📊 知识库统计:\n- 总条目数: {num_entities}\n- 会话隔离: {'是' if session_id else '否'}\n- 存储类型: {stats.get('type', 'unknown')}"

    except Exception as e:
        logger.error(f"获取知识库统计失败: {e}")
        return f"获取统计失败: {str(e)}"