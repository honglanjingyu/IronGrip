# app/action/tools/dream_tool.py
"""做梦模块工具 - 供 Agent 调用"""

from typing import Optional
from loguru import logger


async def query_entity_memory(
        query: str,
        entity_type: Optional[str] = None,
        min_importance: float = 0.3,
        limit: int = 10,
        session_id: str = ""
) -> str:
    """
    查询实体记忆

    当你需要回忆之前学到的用户偏好、重要事实或知识洞察时使用此工具。
    这些记忆是从过去的对话中提炼出来的精华。

    Args:
        query: 查询关键词或问题
        entity_type: 记忆类型，可选: user_preference, user_fact, knowledge_insight, pattern, correction
        min_importance: 最低重要性(0-1)，默认0.3
        limit: 返回数量，默认10
        session_id: 会话ID（自动传递）

    Returns:
        str: 相关的实体记忆
    """
    logger.info(f"[会话 {session_id}] 查询实体记忆: query='{query}'")

    try:
        from app.agent.dream import get_dream_manager

        dream_manager = get_dream_manager()
        memories = await dream_manager.query_memories(
            query=query,
            entity_type=entity_type,
            min_importance=min_importance,
            limit=limit
        )

        if not memories:
            return "📭 没有找到相关的实体记忆。"

        # 格式化输出
        lines = ["🧠 **实体记忆查询结果**\n"]

        for i, mem in enumerate(memories, 1):
            type_icon = {
                "user_preference": "❤️",
                "user_fact": "👤",
                "knowledge_insight": "💡",
                "pattern": "🔄",
                "correction": "✏️"
            }.get(mem.entity_type.value, "📝")

            importance_star = "⭐" * int(mem.importance_score * 3) + "☆" * (3 - int(mem.importance_score * 3))

            lines.append(f"{type_icon} **{mem.title}**")
            lines.append(f"   {mem.content[:200]}")
            lines.append(f"   重要性: {importance_star} | 置信度: {mem.confidence:.0%}")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"查询实体记忆失败: {e}")
        return f"查询实体记忆失败: {str(e)}"


async def get_all_entity_memories(
        entity_type: Optional[str] = None,
        session_id: str = ""
) -> str:
    """
    获取所有实体记忆

    Args:
        entity_type: 可选，按类型过滤
        session_id: 会话ID

    Returns:
        str: 所有实体记忆的摘要
    """
    logger.info(f"[会话 {session_id}] 获取所有实体记忆, type={entity_type}")

    try:
        from app.agent.dream import get_dream_manager

        dream_manager = get_dream_manager()

        if entity_type:
            memories = dream_manager.get_memories_by_type(entity_type)
        else:
            memories = dream_manager.get_all_memories()

        if not memories:
            return "📭 目前没有存储任何实体记忆。"

        # 按类型分组
        by_type = {}
        for mem in memories:
            t = mem.entity_type.value
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(mem)

        lines = ["🧠 **实体记忆库**\n"]

        type_names = {
            "user_preference": "用户偏好",
            "user_fact": "用户事实",
            "knowledge_insight": "知识洞察",
            "pattern": "行为模式",
            "correction": "纠正信息"
        }

        for t, mems in by_type.items():
            lines.append(f"### {type_names.get(t, t)} ({len(mems)})")
            for mem in mems[:5]:  # 每种类型最多显示5条
                lines.append(f"- {mem.title}")
            if len(mems) > 5:
                lines.append(f"  ... 还有 {len(mems) - 5} 条")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"获取实体记忆失败: {e}")
        return f"获取失败: {str(e)}"


async def get_dream_stats(session_id: str = "") -> str:
    """
    获取做梦模块统计信息

    Returns:
        str: 统计信息
    """
    try:
        from app.agent.dream import get_dream_manager

        dream_manager = get_dream_manager()
        stats = dream_manager.get_stats()

        return f"""
🧠 **做梦模块统计**

- 实体记忆总数: {stats.get('total_count', 0)}
- 按类型分布: {stats.get('by_type', {})}
- 已处理会话数: {stats.get('processed_sessions', 0)}
- 存储路径: {stats.get('storage_path', 'unknown')}
- 上次做梦时间: {stats.get('last_dream_time', '从未')}
- 是否正在做梦: {'是' if stats.get('is_dreaming') else '否'}
"""
    except Exception as e:
        return f"获取统计失败: {str(e)}"


async def trigger_dream_now(session_id: str = "") -> str:
    """
    立即触发一次做梦（手动整理记忆）

    Returns:
        str: 执行结果
    """
    try:
        from app.agent.dream import get_dream_scheduler

        scheduler = get_dream_scheduler()
        result = await scheduler.dream_now()

        if result["success"]:
            return f"""
🌙 做梦完成！

- 处理会话数: {result['sessions_processed']}
- 提炼记忆数: {result['memories_created']}
- 耗时: {result['duration_seconds']:.2f} 秒

新记忆已保存到 entity_memory 目录。
"""
        else:
            return f"做梦失败: {result.get('message', '未知错误')}"

    except Exception as e:
        return f"触发做梦失败: {str(e)}"