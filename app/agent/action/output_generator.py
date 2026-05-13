"""输出生成器 - 生成最终返回给用户的响应"""

from typing import Dict, Any, List, Optional, AsyncGenerator
from langchain_core.messages import SystemMessage, HumanMessage
from loguru import logger

from .models import OutputResult, OutputType, ActionResult


class OutputGenerator:
    """输出生成器 - 生成最终响应"""

    def __init__(self):
        # 延迟导入 LLM 客户端，避免循环依赖
        self._llm = None
        logger.info("OutputGenerator 初始化完成")

    def _get_llm(self):
        """延迟获取 LLM 客户端"""
        if self._llm is None:
            from app.agent.brain.llm_client import get_llm_client
            self._llm = get_llm_client()
        return self._llm

    async def generate(
            self,
            user_input: str,
            action_results: List[ActionResult],
            perception_context: Optional[Dict[str, Any]] = None,
            output_type: OutputType = OutputType.MARKDOWN,
            session_id: str = ""
    ) -> OutputResult:
        """
        根据执行结果生成最终输出

        Args:
            user_input: 原始用户输入
            action_results: 动作执行结果列表
            perception_context: 感知上下文
            output_type: 输出类型
            session_id: 会话ID

        Returns:
            OutputResult: 输出结果
        """
        logger.info(f"[会话 {session_id}] 生成最终输出")

        if not action_results:
            # 没有执行结果，直接回答用户
            return await self._direct_response(user_input, session_id)

        # 构建执行结果摘要
        execution_summary = self._format_action_results(action_results)

        prompt = f"""
## 原始任务
{user_input}

## 执行过程和结果
{execution_summary}

## 任务
请根据以上执行结果，生成一个{self._get_output_type_desc(output_type)}的响应。
- 回答要清晰、结构化
- 基于实际数据，不要编造
- 如果某些步骤失败，要诚实说明
"""

        messages = [
            SystemMessage(content=(
                "你是一个专业的AI助手，请根据提供的信息生成清晰、准确的回答。"
                "使用 Markdown 格式使内容更易读。"
            )),
            HumanMessage(content=prompt)
        ]

        try:
            llm = self._get_llm()
            response = await llm.invoke(messages)

            return OutputResult(
                type=output_type,
                content=response,
                metadata={
                    "session_id": session_id,
                    "action_count": len(action_results),
                    "generated_at": "llm"
                }
            )
        except Exception as e:
            logger.error(f"生成输出失败: {e}")
            # 回退响应
            fallback = self._generate_fallback(user_input, action_results)
            return OutputResult(
                type=OutputType.TEXT,
                content=fallback,
                metadata={"error": str(e)}
            )

    async def generate_stream(
            self,
            user_input: str,
            action_results: List[ActionResult],
            perception_context: Optional[Dict[str, Any]] = None,
            session_id: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        流式生成输出

        Yields:
            str: 响应内容块
        """
        logger.info(f"[会话 {session_id}] 流式生成最终输出")

        if not action_results:
            async for chunk in self._direct_response_stream(user_input, session_id):
                if chunk:
                    yield chunk
            return

        execution_summary = self._format_action_results(action_results)

        prompt = f"""
## 原始任务
{user_input}

## 执行过程和结果
{execution_summary}

## 任务
请根据以上执行结果，生成一个清晰的响应。回答要基于实际数据。
"""

        messages = [
            SystemMessage(content="你是一个专业的AI助手，请根据提供的信息生成清晰、准确的回答。"),
            HumanMessage(content=prompt)
        ]

        try:
            llm = self._get_llm()
            async for chunk in llm.stream(messages):
                yield chunk
        except Exception as e:
            logger.error(f"流式生成输出失败: {e}")
            yield f"\n\n*生成响应时出错: {str(e)}*"

    async def _direct_response(self, user_input: str, session_id: str) -> OutputResult:
        """直接回答（无需工具调用）"""
        messages = [
            SystemMessage(content="你是一个专业的AI助手，请友好、简洁地回答用户的问题。"),
            HumanMessage(content=user_input)
        ]

        try:
            llm = self._get_llm()
            response = await llm.invoke(messages)
            return OutputResult(
                type=OutputType.TEXT,
                content=response,
                metadata={"generated_at": "direct"}
            )
        except Exception as e:
            return OutputResult(
                type=OutputType.TEXT,
                content=f"抱歉，处理您的请求时出现错误: {str(e)}",
                metadata={"error": str(e)}
            )

    async def _direct_response_stream(
            self,
            user_input: str,
            session_id: str
    ) -> AsyncGenerator[str, None]:
        """流式直接回答"""
        messages = [
            SystemMessage(content="你是一个专业的AI助手，请友好、简洁地回答用户的问题。"),
            HumanMessage(content=user_input)
        ]

        try:
            llm = self._get_llm()
            async for chunk in llm.stream(messages):
                yield chunk
        except Exception as e:
            logger.error(f"流式直接回答失败: {e}")
            yield f"抱歉，处理出错: {str(e)}"

    def _format_action_results(self, results: List[ActionResult]) -> str:
        """格式化动作执行结果"""
        if not results:
            return "无执行结果"

        lines = []
        for i, result in enumerate(results, 1):
            lines.append(f"### 步骤 {i}: {result.action.reasoning or '执行动作'}")

            if result.action.type.value == "tool_call" and result.action.tool_call:
                lines.append(f"- 调用工具: {result.action.tool_call.name}")
                lines.append(f"- 参数: {result.action.tool_call.input}")

            if result.success:
                result_preview = result.result[:500] if result.result and len(result.result) > 500 else result.result
                lines.append(f"- 结果: {result_preview}")
            else:
                lines.append(f"- 错误: {result.error}")
            lines.append("")

        return "\n".join(lines)

    def _get_output_type_desc(self, output_type: OutputType) -> str:
        """获取输出类型描述"""
        desc_map = {
            OutputType.TEXT: "纯文本",
            OutputType.MARKDOWN: "Markdown 格式",
            OutputType.JSON: "JSON 格式",
            OutputType.HTML: "HTML 格式",
            OutputType.COMMAND: "操作指令",
        }
        return desc_map.get(output_type, "清晰易读")

    def _generate_fallback(self, user_input: str, results: List[ActionResult]) -> str:
        """生成回退响应"""
        lines = [f"# 任务执行结果\n\n## 原始任务\n{user_input}\n"]

        if results:
            lines.append("## 执行步骤\n")
            for i, result in enumerate(results, 1):
                status = "✅" if result.success else "❌"
                lines.append(f"{status} **步骤 {i}**: {result.action.reasoning or '执行动作'}")
                if result.result:
                    lines.append(f"   {result.result[:200]}...")

        lines.append("\n## 说明\n由于系统异常，部分信息可能不完整。")

        return "\n".join(lines)