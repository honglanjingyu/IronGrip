# app/action/action_manager.py (修改版)
"""行动管理器 - 统一管理行动模块，使用 MCP"""

from typing import List, Dict, Any, Optional, AsyncGenerator
from loguru import logger

from .models import (
    Action, ActionType, ActionResult, ExecutionContext,
    OutputResult, OutputType, ToolCall
)
from .executor import ActionExecutor, get_action_executor
# 移除旧的 tool_registry，使用 MCP
from app.mcp import get_mcp_manager, MCPManager


class ActionManager:
    """
    行动管理器 - 使用 MCP 协议
    """

    def __init__(self):
        self.executor: ActionExecutor = get_action_executor()
        # 使用 MCP 管理器
        self.mcp_manager: MCPManager = get_mcp_manager(use_local=True)
        self._output_generator = None
        logger.info("ActionManager 初始化完成 (MCP 模式)")

    @property
    def output_generator(self):
        """延迟获取输出生成器"""
        if self._output_generator is None:
            from .output_generator import OutputGenerator
            self._output_generator = OutputGenerator()
        return self._output_generator

    def register_tool(self, tool: Any) -> None:
        """注册单个工具到 MCP"""
        if hasattr(tool, 'name'):
            name = tool.name
            description = getattr(tool, 'description', tool.__doc__ or "")
        else:
            name = tool.__name__
            description = tool.__doc__ or f"Tool: {name}"

        self.mcp_manager.register_tool(
            name=name,
            handler=tool,
            description=description
        )

    def register_tools(self, tools: List[Any]) -> None:
        """批量注册工具"""
        for tool in tools:
            self.register_tool(tool)

    def register_builtin_tools(self) -> None:
        """注册内置工具 - 通过 MCP"""
        from app.action.tools import discover_tools

        tools = discover_tools()

        if not tools:
            logger.warning("未发现任何内置工具")
            return

        self.register_tools(tools)
        logger.info(f"已通过 MCP 注册 {len(tools)} 个内置工具")

    def list_tools(self) -> List[str]:
        """列出所有已注册的工具"""
        tools = self.mcp_manager._tools
        return list(tools.keys())

    def get_tools_description(self) -> str:
        """获取工具描述（用于 LLM Prompt）"""
        return self.mcp_manager.get_tools_description()

    # app/action/action_manager.py - 确保正确传递参数

    async def execute_tool_call(
            self,
            tool_name: str,
            tool_input: Dict[str, Any],
            session_id: str = ""
    ) -> str:
        """执行单个工具调用 - 通过 MCP"""
        # 关键：只传递 tool_input，不要添加额外的 tool_name
        return await self.mcp_manager.call_tool(
            tool_name=tool_name,
            arguments=tool_input,  # 直接传递 tool_input，不要修改
            session_id=session_id
        )

    async def execute_actions(
            self,
            actions: List[Action],
            context: ExecutionContext,
            session_id: str = ""
    ) -> List[ActionResult]:
        """执行动作列表"""
        return await self.executor.execute_actions(actions, context, session_id)

    async def generate_output(
            self,
            user_input: str,
            action_results: List[ActionResult],
            perception_context: Optional[Dict[str, Any]] = None,
            output_type: OutputType = OutputType.MARKDOWN,
            session_id: str = ""
    ) -> OutputResult:
        """生成最终输出"""
        return await self.executor.generate_output(
            user_input=user_input,
            action_results=action_results,
            perception_context=perception_context,
            output_type=output_type,
            session_id=session_id
        )

    async def generate_output_stream(
            self,
            user_input: str,
            action_results: List[ActionResult],
            perception_context: Optional[Dict[str, Any]] = None,
            session_id: str = ""
    ) -> AsyncGenerator[str, None]:
        """流式生成输出"""
        async for chunk in self.executor.generate_output_stream(
                user_input=user_input,
                action_results=action_results,
                perception_context=perception_context,
                session_id=session_id
        ):
            yield chunk

    async def run_single_action(
            self,
            action_type: ActionType,
            tool_name: Optional[str] = None,
            tool_input: Optional[Dict[str, Any]] = None,
            content: Optional[str] = None,
            context: Optional[ExecutionContext] = None,
            session_id: str = ""
    ) -> ActionResult:
        """执行单个动作"""
        if action_type == ActionType.TOOL_CALL and tool_name:
            action = Action(
                type=ActionType.TOOL_CALL,
                tool_call=ToolCall(name=tool_name, input=tool_input or {}),
                reasoning=f"调用工具 {tool_name}"
            )
        else:
            action = Action(
                type=ActionType.DIRECT_OUTPUT,
                content=content or "处理完成",
                reasoning="直接输出"
            )

        exec_context = context or ExecutionContext(
            session_id=session_id,
            user_input=""
        )

        return await self.executor.execute_action(action, exec_context, session_id)


# 全局单例
_action_manager: Optional[ActionManager] = None


def get_action_manager() -> ActionManager:
    """获取全局行动管理器单例"""
    global _action_manager
    if _action_manager is None:
        _action_manager = ActionManager()
    return _action_manager