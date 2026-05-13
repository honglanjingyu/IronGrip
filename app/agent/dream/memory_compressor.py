# app/dream/memory_compressor.py
"""记忆压缩提炼 - 将对话提炼为实体记忆"""

import uuid
from typing import List, Dict, Any, Optional
from loguru import logger

from .models import EntityMemory, EntityType, MemoryCompressionLevel
from .config import dream_config


class MemoryCompressor:
    """
    记忆压缩器
    将对话历史提炼为精炼的实体记忆
    """

    def __init__(self):
        self._llm = None
        logger.info("MemoryCompressor 初始化完成")

    def _get_llm(self):
        """延迟获取 LLM"""
        if self._llm is None:
            from app.agent.brain.llm_client import get_llm_client
            self._llm = get_llm_client()
        return self._llm

    async def compress_conversations(
            self,
            conversations: List[Dict[str, Any]],
            session_id: str,
            level: MemoryCompressionLevel = MemoryCompressionLevel.MEDIUM
    ) -> List[EntityMemory]:
        """
        压缩对话为实体记忆

        Args:
            conversations: 对话列表 [{role, content, timestamp}, ...]
            session_id: 来源会话ID
            level: 压缩级别

        Returns:
            List[EntityMemory]: 提炼出的实体记忆
        """
        if not conversations:
            return []

        logger.info(f"开始压缩 {len(conversations)} 条对话, 级别={level.value}")

        # 构建对话文本
        conversation_text = self._format_conversations(conversations)

        # 使用 LLM 提炼记忆
        memories = await self._extract_memories_with_llm(
            conversation_text, session_id, level
        )

        # 过滤低重要性记忆
        filtered = [m for m in memories if m.importance_score >= dream_config.IMPORTANCE_THRESHOLD]

        logger.info(f"压缩完成: 提炼 {len(memories)} 条, 过滤后 {len(filtered)} 条")
        return filtered

    async def _extract_memories_with_llm(
            self,
            conversation_text: str,
            session_id: str,
            level: MemoryCompressionLevel
    ) -> List[EntityMemory]:
        """使用 LLM 提取记忆"""

        # 根据压缩级别调整提示词
        if level == MemoryCompressionLevel.LIGHT:
            instruction = "提取关键信息点，每个点一句话"
            max_memories = 10
        elif level == MemoryCompressionLevel.MEDIUM:
            instruction = "提炼有价值的洞察和用户偏好，每个记忆用几句话描述"
            max_memories = 15
        else:  # DEEP
            instruction = "深度分析，提取抽象模式、用户特质、知识关联，形成结构化的记忆"
            max_memories = 20

        prompt = f"""
你是一个智能记忆压缩系统。请分析以下对话，提炼出有价值的实体记忆。

## 对话内容
{conversation_text[:8000]}

## 提取规则

### 需要提取的记忆类型：
1. **user_preference** - 用户偏好（用户喜欢什么、不喜欢什么）
2. **user_fact** - 用户事实（用户的身份、背景、需求）
3. **knowledge_insight** - 知识洞察（对话中产生的有价值知识）
4. **pattern** - 行为模式（用户的提问方式、关注点模式）
5. **correction** - 纠正信息（用户纠正过的错误理解）

### 重要性评分标准：
- 0.8-1.0: 非常重要，应该长期记住
- 0.5-0.7: 一般重要，可能需要用到
- 0.2-0.4: 轻度重要，短期参考

### {instruction}

## 输出格式 (JSON数组)
[
  {{
    "entity_type": "user_preference",
    "title": "简短标题",
    "content": "详细内容描述",
    "importance_score": 0.85,
    "confidence": 0.9,
    "tags": ["标签1", "标签2"]
  }}
]

请严格按照 JSON 数组格式输出，不要有其他文字。
"""

        try:
            from langchain_core.messages import SystemMessage, HumanMessage

            messages = [
                SystemMessage(content="你是一个智能记忆压缩系统，只输出 JSON 数组。"),
                HumanMessage(content=prompt)
            ]

            llm = self._get_llm()
            response = await llm.invoke(messages)

            # 解析 JSON
            import json
            # 提取 JSON 部分
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            data = json.loads(response.strip())

            memories = []
            for item in data[:max_memories]:
                memory = EntityMemory(
                    id=str(uuid.uuid4()),
                    entity_type=EntityType(item["entity_type"]),
                    title=item["title"][:100],
                    content=item["content"],
                    source_session_id=session_id,
                    source_conversations=[],
                    importance_score=float(item.get("importance_score", 0.5)),
                    confidence=float(item.get("confidence", 0.7)),
                    tags=item.get("tags", [])
                )
                memories.append(memory)

            return memories

        except Exception as e:
            logger.error(f"LLM 提取记忆失败: {e}")
            # 降级：简单的关键词提取
            return self._fallback_extract(conversation_text, session_id)

    def _fallback_extract(
            self,
            conversation_text: str,
            session_id: str
    ) -> List[EntityMemory]:
        """降级提取（简单关键词匹配）"""
        memories = []

        # 简单的关键词模式
        patterns = [
            ("user_preference", ["喜欢", "爱好", "感兴趣", "偏好"], 0.5),
            ("user_fact", ["我是", "我叫", "我在", "我的"], 0.6),
            ("knowledge_insight", ["原来", "我知道了", "学到了"], 0.4),
        ]

        for entity_type, keywords, base_score in patterns:
            for keyword in keywords:
                if keyword in conversation_text:
                    # 简单提取包含关键词的句子
                    sentences = conversation_text.split('。')
                    for sent in sentences:
                        if keyword in sent and len(sent) < 200:
                            memory = EntityMemory(
                                id=str(uuid.uuid4()),
                                entity_type=EntityType(entity_type),
                                title=f"关于{keyword}的记录",
                                content=sent.strip(),
                                source_session_id=session_id,
                                source_conversations=[],
                                importance_score=base_score
                            )
                            memories.append(memory)
                            break

        return memories

    def _format_conversations(self, conversations: List[Dict]) -> str:
        """格式化对话"""
        lines = []
        for conv in conversations:
            role = conv.get("role", "unknown")
            content = conv.get("content", "")
            if role == "user":
                lines.append(f"用户: {content}")
            elif role == "assistant":
                lines.append(f"助手: {content}")
            else:
                lines.append(f"{role}: {content}")
        return "\n".join(lines)


# 全局单例
_compressor: Optional[MemoryCompressor] = None


def get_memory_compressor() -> MemoryCompressor:
    global _compressor
    if _compressor is None:
        _compressor = MemoryCompressor()
    return _compressor