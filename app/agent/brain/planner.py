# app/brain/planner.py
"""规划器 - 将复杂任务拆解为可执行步骤"""

from typing import List, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from loguru import logger

from .llm_client import get_llm_client
from .models import Plan, BrainState


class PlannerOutput(BaseModel):
    """规划器输出格式"""
    steps: List[str] = Field(description="任务步骤列表，按顺序执行")
    reasoning: str = Field(description="制定计划的推理过程")


# 规划器系统提示词
PLANNER_SYSTEM_PROMPT = """你是一个专业的任务规划专家。你的职责是将用户的复杂任务分解为清晰、可执行的步骤。

## 规划原则
1. **步骤独立性**：每个步骤应该是独立的、可执行的单元
2. **逻辑顺序**：步骤之间应有清晰的依赖关系，按正确顺序排列
3. **具体可操作**：步骤描述要具体，明确指出需要做什么
4. **工具导向**：如果步骤需要获取信息，明确指出需要调用什么工具
5. **适度粒度**：步骤不要太细（如"打开文件"）也不要太粗（如"解决问题"）

## 输出格式
- steps: 步骤列表，每个步骤是一个字符串
- reasoning: 解释你的规划思路

## 示例
用户输入: "帮我分析 CPU 使用率过高的原因"

输出:
{
  "steps": [
    "查询当前 CPU 使用率监控数据",
    "检查是否有异常进程占用 CPU",
    "分析相关服务的日志",
    "根据收集的信息定位根因",
    "生成分析报告"
  ],
  "reasoning": "首先需要获取当前状态，然后排查进程和日志，最后综合得出结论"
}
"""


class Planner:
    """规划器"""

    def __init__(self):
        self.llm = get_llm_client()
        logger.info("Planner 初始化完成")

    async def plan(
            self,
            user_input: str,
            perception_context: Dict[str, Any],
            available_tools: List[Dict[str, Any]],
            session_id: str = ""
    ) -> Plan:
        """
        根据用户输入和感知上下文制定执行计划

        Args:
            user_input: 用户输入
            perception_context: 感知上下文（环境信息、记忆等）
            available_tools: 可用工具列表
            session_id: 会话ID

        Returns:
            Plan: 执行计划
        """
        logger.info(f"[会话 {session_id}] 开始制定计划")

        # 构建上下文信息
        tools_desc = self._format_tools(available_tools)

        # 构建环境信息摘要
        env_summary = self._format_perception_context(perception_context)

        # 构建提示词
        user_prompt = f"""
## 用户输入
{user_input}

## 环境信息（仅供参考）
{env_summary}

## 可用工具
{tools_desc}

## 任务
请根据用户输入制定详细的执行计划。如果用户问题简单且不需要工具，可以制定一个简短的计划（1-2步）。
"""

        # 调用 LLM
        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]

        try:
            output = await self.llm.invoke_structured(messages, PlannerOutput)

            plan = Plan(
                steps=output.steps,
                reasoning=output.reasoning
            )

            logger.info(f"[会话 {session_id}] 计划制定完成: {len(plan.steps)} 个步骤")
            for i, step in enumerate(plan.steps, 1):
                logger.info(f"  步骤{i}: {step}")

            return plan

        except Exception as e:
            logger.error(f"[会话 {session_id}] 规划失败: {e}")
            # 返回一个默认计划
            return Plan(
                steps=["理解用户需求", "收集信息", "生成回答"],
                reasoning=f"规划失败，使用默认计划: {str(e)}"
            )

    def _format_tools(self, tools: List[Dict[str, Any]]) -> str:
        """格式化工具列表"""
        if not tools:
            return "无可用工具"

        lines = []
        for tool in tools:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "无描述")
            lines.append(f"- {name}: {desc}")

        return "\n".join(lines)

    def _format_perception_context(self, context: Dict[str, Any]) -> str:
        """格式化感知上下文"""
        parts = []

        # 环境信息
        env = context.get("environment", {})
        if env:
            parts.append(f"当前时间: {env.get('current_time', '未知')}")
            sys_status = env.get("system_status", {})
            if sys_status:
                parts.append(f"系统状态: CPU {sys_status.get('cpu_percent', 'N/A')}%, "
                             f"内存 {sys_status.get('memory_percent', 'N/A')}%")

        # 告警信息
        alerts = env.get("active_alerts", [])
        if alerts:
            parts.append(f"活动告警: {len(alerts)} 个")

        # 长期记忆
        long_term = context.get("long_term_memory", [])
        if long_term:
            parts.append(f"相关知识: {len(long_term)} 条")

        return "\n".join(parts) if parts else "无特殊环境信息"