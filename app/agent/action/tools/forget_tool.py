# app/agent/action/tools/forget_tool.py
"""遗忘工具 - 供 Agent 调用"""

from typing import Optional
from loguru import logger


async def forget_memory(
        keyword: str,
        include_short_term: bool = True,
        include_redis: bool = True,
        include_entity: bool = True,
        session_id: str = ""
) -> str:
    """
    遗忘指定关键词相关的所有记忆

    当用户要求你忘记某些内容时，使用此工具清除相关的记忆。

    Args:
        keyword: 要遗忘的关键词（如 "白兔"、"Python" 等）
        include_short_term: 是否清除短期记忆，默认 True
        include_redis: 是否清除 Redis 会话记忆，默认 True
        include_entity: 是否清除实体记忆，默认 True
        session_id: 会话ID（自动传递）

    Returns:
        str: 操作结果
    """
    logger.info(f"[会话 {session_id}] 调用遗忘工具: keyword='{keyword}'")

    try:
        from app.agent.forget import get_memory_eraser

        eraser = get_memory_eraser()
        result = await eraser.forget(
            keyword=keyword,
            session_id=session_id,
            include_short_term=include_short_term,
            include_redis=include_redis,
            include_entity=include_entity
        )

        if result["success"]:
            parts = []
            if result["short_term_cleared"] > 0:
                parts.append(f"短期记忆 {result['short_term_cleared']} 条")
            if result["redis_cleared"] > 0:
                parts.append(f"会话记忆 {result['redis_cleared']} 条")
            if result["entity_cleared"] > 0:
                parts.append(f"实体记忆 {result['entity_cleared']} 条")

            if parts:
                return f"🧹 已遗忘关于「{keyword}」的记忆：{', '.join(parts)}"
            else:
                return f"📭 没有找到关于「{keyword}」的记忆"
        else:
            return f"❌ 遗忘失败: {result['message']}"

    except Exception as e:
        logger.error(f"遗忘工具调用失败: {e}")
        return f"❌ 遗忘失败: {str(e)}"


async def clear_all_entity_memories(session_id: str = "") -> str:
    """
    清除所有实体记忆（谨慎使用）

    警告：此操作不可逆，会删除所有已提炼的实体记忆。

    Returns:
        str: 操作结果
    """
    try:
        from app.agent.dream import get_dream_manager

        dream_manager = get_dream_manager()
        stats = dream_manager.get_stats()
        total = stats.get("total_count", 0)

        if total == 0:
            return "📭 没有实体记忆需要清除"

        # 确认操作（在实际使用中，Agent 会先询问用户确认）
        dream_manager._store.clear_all()

        return f"🧹 已清除全部 {total} 条实体记忆"

    except Exception as e:
        logger.error(f"清除所有实体记忆失败: {e}")
        return f"❌ 清除失败: {str(e)}"