# nexus/app/action/tools/rag_tool.py
"""
RAG 检索工具 - 通过 A2A 调用 PaperReadingRAG
"""

import os
from typing import Optional, Dict, Any
from loguru import logger

from app.a2a.client import get_a2a_client, A2ARAGResponse


async def search_knowledge_base(
        query: str,
        top_k: int = 5,
        session_id: str = ""
) -> str:
    """
    从知识库检索信息（通过 A2A 调用 PaperReadingRAG）

    当用户询问关于文档内容（如财报、研究报告、技术文档等）的问题时，
    使用此工具从 RAG 知识库中检索相关信息。

    Args:
        query: 搜索问题或关键词
        top_k: 返回结果数量，默认5条
        session_id: 会话ID（自动传递）

    Returns:
        str: 检索结果和生成的答案
    """
    logger.info(f"[会话 {session_id}] 调用知识库检索: query='{query}'")

    # 获取 A2A 服务地址（可从环境变量配置）
    a2a_url = os.getenv("A2A_RAG_URL", "http://localhost:8001")

    try:
        client = get_a2a_client(base_url=a2a_url)

        # 检查服务健康状态
        health = await client.health_check()
        if health.get("status") != "healthy":
            return f"⚠️ RAG 知识库服务不可用: {health.get('error', '未知错误')}"

        # 调用 RAG 检索
        result = await client.rag_ask(
            query=query,
            session_id=session_id,
            top_k=top_k
        )

        if result.get("success") and result.get("answer"):
            answer = result.get("answer", "")
            # 添加来源信息
            return f"📚 知识库检索结果：\n\n{answer}"
        else:
            error = result.get("error", "未找到相关信息")
            return f"❌ 知识库检索失败: {error}"

    except Exception as e:
        logger.error(f"知识库检索失败: {e}")
        return f"❌ 知识库检索失败: {str(e)}"


async def search_documents(
        query: str,
        top_k: int = 5,
        session_id: str = ""
) -> str:
    """
    从已上传文档中搜索相关内容（仅返回文档片段，不生成答案）

    适用于只需要查看相关文档片段，不需要 AI 生成总结的场景。

    Args:
        query: 搜索关键词
        top_k: 返回文档片段数量，默认5条
        session_id: 会话ID（自动传递）

    Returns:
        str: 相关文档片段列表
    """
    logger.info(f"[会话 {session_id}] 调用文档搜索: query='{query}'")

    a2a_url = os.getenv("A2A_RAG_URL", "http://localhost:8001")

    try:
        client = get_a2a_client(base_url=a2a_url)

        health = await client.health_check()
        if health.get("status") != "healthy":
            return f"⚠️ 文档搜索服务不可用"

        # 调用 RAG 检索（只需要文档，不需要答案）
        result = await client.rag_search(
            query=query,
            session_id=session_id,
            top_k=top_k,
            need_answer=False,
            include_documents=True
        )

        if result.success and result.documents:
            output = [f"📄 找到 {len(result.documents)} 个相关文档片段：\n"]
            for i, doc in enumerate(result.documents, 1):
                content = doc.get("content", "")[:300]
                score = doc.get("score", 0)
                output.append(f"\n【片段 {i}】相关度: {score:.2%}")
                output.append(f"{content}...")
            return "\n".join(output)
        else:
            return f"未找到与 '{query}' 相关的文档内容"

    except Exception as e:
        logger.error(f"文档搜索失败: {e}")
        return f"文档搜索失败: {str(e)}"