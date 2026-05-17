# app/agent/action/tools/industry_tools.py
"""
行业研究工具 - 公司研究、竞品对比、融资追踪
使用 PaperReadingRAG 的 GraphRAG 知识图谱增强检索
"""

import os
import json
import re
from typing import Optional, List, Dict, Any
from loguru import logger
from datetime import datetime, timedelta

from app.a2a.graph_client import get_graph_client


async def _call_graphrag(
        query: str,
        session_id: str,
        top_k: int = 8
) -> Optional[Dict[str, Any]]:
    """
    内部方法：调用 GraphRAG 接口

    Returns:
        GraphRAG 返回结果，失败返回 None
    """
    client = get_graph_client()

    try:
        # 检查服务健康状态
        if not await client.health_check():
            logger.warning("GraphRAG 服务不可用")
            return None

        # 调用 GraphRAG 问答
        result = await client.graph_ask(
            question=query,
            session_id=session_id,
            top_k=top_k,
            enable_memory=True
        )

        if result.get("success"):
            return result
        else:
            logger.warning(f"GraphRAG 返回失败: {result.get('error')}")
            return None

    except Exception as e:
        logger.error(f"GraphRAG 调用失败: {e}")
        return None


async def _fallback_web_search(query: str, num_results: int = 5, session_id: str = "") -> str:
    """回退到普通联网搜索"""
    from .search_tool import web_search
    return await web_search(query=query, num_results=num_results, session_id=session_id)


def _format_graphrag_response(
        title: str,
        result: Dict[str, Any],
        include_entities: bool = True
) -> str:
    """格式化 GraphRAG 响应"""
    answer = result.get("answer", "")
    reasoning_path = result.get("reasoning_path", "")

    output_parts = [f"{title}\n"]

    if reasoning_path:
        output_parts.append(f"### 🔗 推理路径\n{reasoning_path}\n")

    output_parts.append(f"### 📝 分析结果\n{answer}")

    if include_entities:
        graph_info = result.get("graph_info", {})
        entities = graph_info.get("entities_extracted", [])
        if entities:
            output_parts.append(f"\n### 🏷️ 识别实体\n{', '.join(entities)}")

    return "\n".join(output_parts)


async def search_company_info(
        company_name: str,
        info_type: str = "basic",
        session_id: str = ""
) -> str:
    """
    搜索公司基本信息：成立时间、业务范围、融资情况、核心产品
    优先使用 GraphRAG 知识图谱，失败时回退到联网搜索

    Args:
        company_name: 公司名称，如 "字节跳动"、"月之暗面"
        info_type: 信息类型，可选: basic(基本信息), finance(融资情况), products(核心产品), team(团队)
        session_id: 会话ID

    Returns:
        str: 公司信息
    """
    logger.info(f"[会话 {session_id}] 搜索公司信息: company={company_name}, type={info_type}")

    # 构建 GraphRAG 查询
    query_map = {
        "basic": f"请介绍 {company_name} 公司的基本信息，包括成立时间、业务范围、核心产品和融资情况",
        "finance": f"请分析 {company_name} 的融资历程、估值变化和主要投资方",
        "products": f"请介绍 {company_name} 的核心产品和技术优势",
        "team": f"请介绍 {company_name} 的创始团队、核心管理层和组织架构"
    }

    query = query_map.get(info_type, query_map["basic"])

    # 尝试 GraphRAG
    result = await _call_graphrag(query, session_id, top_k=8)

    if result:
        title = f"📊 **{company_name} ({info_type})**"
        return _format_graphrag_response(title, result)

    # 回退到联网搜索
    logger.info(f"回退到联网搜索: {company_name}")
    query_map_web = {
        "basic": f"{company_name} 公司简介 成立时间 业务范围 融资",
        "finance": f"{company_name} 融资 估值 投资方",
        "products": f"{company_name} 核心产品 产品线",
        "team": f"{company_name} 创始人 核心团队"
    }
    web_query = query_map_web.get(info_type, query_map_web["basic"])
    return await _fallback_web_search(web_query, 5, session_id)


async def search_financing_events(
        time_range: str = "last_month",
        sector: str = "AI",
        round: str = "",
        session_id: str = ""
) -> str:
    """
    搜索融资事件，可按时间、领域、轮次筛选
    优先使用 GraphRAG 分析投资关系网络

    Args:
        time_range: 时间范围: last_week, last_month, last_quarter, last_year
        sector: 行业领域: AI, 云计算, 电商, 游戏, 企业服务, 自动驾驶, 半导体
        round: 融资轮次: 种子轮, 天使轮, A轮, B轮, C轮, 战略投资
        session_id: 会话ID

    Returns:
        str: 融资事件列表（包含投资关系）
    """
    logger.info(f"[会话 {session_id}] 搜索融资事件: time={time_range}, sector={sector}, round={round}")

    # 时间范围映射
    time_map = {
        "last_week": "最近一周",
        "last_month": "最近一个月",
        "last_quarter": "最近三个月",
        "last_year": "最近一年"
    }
    time_desc = time_map.get(time_range, "最近一个月")

    # 构建 GraphRAG 查询
    query_parts = [f"{time_desc}"]
    if sector:
        query_parts.append(sector)
    query_parts.append("领域")
    if round:
        query_parts.append(round)
    query_parts.append("的融资事件，请分析投资方与创业公司的关系网络")

    query = " ".join(query_parts)

    # 尝试 GraphRAG
    result = await _call_graphrag(query, session_id, top_k=10)

    if result:
        title = f"💰 **融资事件追踪**\n时间: {time_desc} | 领域: {sector}"
        if round:
            title += f" | 轮次: {round}"
        return _format_graphrag_response(title, result)

    # 回退到联网搜索
    search_query = f"{time_desc} {sector} {round}融资 事件 汇总" if round else f"{time_desc} {sector} 融资事件"
    return await _fallback_web_search(search_query, 8, session_id)


async def compare_companies(
        companies: List[str],
        dimensions: List[str],
        session_id: str = ""
) -> str:
    """
    对比多家公司在指定维度上的差异
    优先使用 GraphRAG 分析公司间的竞争/合作关系

    Args:
        companies: 公司列表，如 ["字节跳动", "百度"]
        dimensions: 对比维度，可选: 业务范围, 营收规模, 用户数, 核心产品, 融资历史, 市场份额
        session_id: 会话ID

    Returns:
        str: 对比结果（包含关系推理）
    """
    logger.info(f"[会话 {session_id}] 竞品对比: companies={companies}, dimensions={dimensions}")

    if len(companies) < 2:
        return "请提供至少两家公司进行对比"

    companies_str = "、".join(companies)
    dimensions_str = "、".join(dimensions)

    # 构建 GraphRAG 查询
    query = f"""请对比分析以下公司：{companies_str}

对比维度：{dimensions_str}

请特别关注：
1. 公司间的竞争关系或合作关系
2. 在行业中的市场地位差异
3. 各公司的核心优势和劣势

请展示推理路径，并标注信息来源。"""

    # 尝试 GraphRAG
    result = await _call_graphrag(query, session_id, top_k=12)

    if result:
        title = f"📊 **竞品对比分析**\n\n**对比公司**: {companies_str}\n**对比维度**: {dimensions_str}"
        return _format_graphrag_response(title, result, include_entities=True)

    # 回退：分别搜索各公司信息
    from .search_tool import web_search
    from app.agent.brain.llm_client import get_llm_client
    from langchain_core.messages import SystemMessage, HumanMessage

    all_results = []
    for company in companies:
        search_query = f"{company} {' '.join(dimensions)}"
        result_text = await web_search(query=search_query, num_results=3, session_id=session_id)
        all_results.append(f"### {company}\n{result_text}")

    # 让 LLM 生成对比表格
    llm = get_llm_client()
    compare_prompt = f"""
请根据以下信息，生成一个 {dimensions_str} 的对比表格：

{chr(10).join(all_results)}

输出格式：Markdown 表格
"""

    try:
        response = await llm.invoke([HumanMessage(content=compare_prompt)])
        return f"📊 **竞品对比: {companies_str}**\n\n{response}"
    except Exception:
        return f"📊 **竞品对比: {companies_str}**\n\n" + "\n\n".join(all_results)


async def fetch_industry_report(
        topic: str,
        source: str = "auto",
        session_id: str = ""
) -> str:
    """
    获取行业研究报告摘要
    优先使用 GraphRAG 分析行业格局和玩家关系

    Args:
        topic: 研究主题，如 "AIGC 行业趋势"、"2025 年半导体市场"
        source: 来源: auto(自动), graph(知识图谱), web(联网搜索)
        session_id: 会话ID

    Returns:
        str: 研究报告摘要
    """
    logger.info(f"[会话 {session_id}] 获取行业报告: topic={topic}, source={source}")

    # 优先使用 GraphRAG
    if source in ["auto", "graph"]:
        query = f"""请分析 {topic} 的行业发展趋势，包括：
1. 行业主要玩家和竞争格局
2. 核心技术和产品发展
3. 投融资动态
4. 行业内的合作关系网络

请展示推理路径。"""

        result = await _call_graphrag(query, session_id, top_k=12)

        if result:
            title = f"📈 **行业研究报告: {topic}**"
            return _format_graphrag_response(title, result)

    # 联网搜索
    search_query = f"{topic} 行业研究报告 分析"
    return await _fallback_web_search(search_query, 6, session_id)


async def get_regulation_updates(
        sector: str = "",
        time_range: str = "last_month",
        session_id: str = ""
) -> str:
    """
    获取监管政策更新
    优先使用 GraphRAG 分析政策影响关系

    Args:
        sector: 行业领域: AI, 数据安全, 金融, 医疗, 互联网
        time_range: 时间范围: last_week, last_month, last_quarter
        session_id: 会话ID

    Returns:
        str: 监管政策更新列表
    """
    logger.info(f"[会话 {session_id}] 获取监管政策: sector={sector}, time={time_range}")

    time_map = {
        "last_week": "最近一周",
        "last_month": "最近一个月",
        "last_quarter": "最近三个月"
    }
    time_desc = time_map.get(time_range, "最近一个月")

    # 构建 GraphRAG 查询
    query_parts = [time_desc]
    if sector:
        query_parts.append(sector)
    query_parts.append("领域的监管政策和法规更新，以及这些政策对行业的影响")

    query = " ".join(query_parts)

    # 尝试 GraphRAG
    result = await _call_graphrag(query, session_id, top_k=8)

    if result:
        title = f"📋 **监管政策更新**\n时间范围: {time_desc}"
        if sector:
            title += f" | 领域: {sector}"
        return _format_graphrag_response(title, result)

    # 回退
    from .search_tool import web_search_advanced
    return await web_search_advanced(
        query=f"{time_desc} {sector} 监管政策 法规 更新",
        num_results=6,
        time_range=time_desc,
        session_id=session_id
    )


async def search_executive_moves(
        company_name: str = "",
        industry: str = "",
        time_range: str = "last_month",
        session_id: str = ""
) -> str:
    """
    搜索高管变动信息

    Args:
        company_name: 公司名称（可选）
        industry: 行业（可选）
        time_range: 时间范围
        session_id: 会话ID

    Returns:
        str: 高管变动信息
    """
    logger.info(f"[会话 {session_id}] 搜索高管变动: company={company_name}, industry={industry}")

    time_map = {
        "last_week": "最近一周",
        "last_month": "最近一个月",
        "last_quarter": "最近三个月"
    }
    time_desc = time_map.get(time_range, "最近一个月")

    if company_name:
        query = f"{company_name} 高管变动 人事调整 {time_desc}"
    elif industry:
        query = f"{industry} 行业 高管变动 CEO 离职 任命 {time_desc}"
    else:
        query = f"科技行业 高管变动 {time_desc}"

    return await _fallback_web_search(query, 5, session_id)


async def extract_timeline(
        event_topic: str,
        time_range: str = "",
        session_id: str = ""
) -> str:
    """
    提取事件时间线

    Args:
        event_topic: 事件主题，如 "OpenAI 发展历程"、"中国大模型发布"
        time_range: 时间范围（可选）
        session_id: 会话ID

    Returns:
        str: 格式化的时间线
    """
    logger.info(f"[会话 {session_id}] 提取时间线: topic={event_topic}")

    query = f"{event_topic} 时间线 发展历程 里程碑"
    if time_range:
        query += f" {time_range}"

    result = await _fallback_web_search(query, 8, session_id)

    # 让 LLM 格式化为时间线
    from app.agent.brain.llm_client import get_llm_client
    from langchain_core.messages import HumanMessage

    llm = get_llm_client()
    timeline_prompt = f"""
请将以下信息整理成时间线格式（按时间顺序，每行格式：YYYY-MM-DD：事件描述）：

{result}

输出格式：
- 2024-01-01：事件描述
- 2024-02-01：事件描述
"""

    try:
        response = await llm.invoke([HumanMessage(content=timeline_prompt)])
        return f"📅 **{event_topic} 时间线**\n\n{response}"
    except Exception:
        return f"📅 **{event_topic} 时间线**\n\n{result}"