# app/mcp/mcp_manager.py
"""MCP 管理器 - 统一管理 MCP 集成"""

from typing import Dict, Any, List, Optional, Callable
from loguru import logger

from .mcp_server import MCPServer, get_mcp_server
from .mcp_client import MCPClient, get_mcp_client


class MCPManager:
    """
    MCP 管理器 - 统一管理 MCP 服务器和客户端

    职责：
    1. 注册工具到 MCP 服务器
    2. 通过 MCP 客户端调用工具
    3. 兼容旧的工具调用方式
    """

    def __init__(self, server_url: Optional[str] = None, use_local: bool = True):
        self.server_url = server_url
        self.use_local = use_local

        self._server: Optional[MCPServer] = None
        self._client: Optional[MCPClient] = None

        if use_local:
            self._server = get_mcp_server()

        self._client = get_mcp_client(server_url=server_url, use_local=use_local)

        # 工具映射（用于快速查找）
        self._tools: Dict[str, Dict[str, Any]] = {}

        logger.info(f"MCP Manager 初始化: use_local={use_local}, server_url={server_url}")

    @property
    def server(self) -> Optional[MCPServer]:
        """获取 MCP 服务器"""
        return self._server

    @property
    def client(self) -> MCPClient:
        """获取 MCP 客户端"""
        return self._client

    def register_tool(
            self,
            name: str,
            handler: Callable,
            description: str = "",
            input_schema: Optional[Dict[str, Any]] = None
    ):
        """
        注册工具到 MCP 服务器

        Args:
            name: 工具名称
            handler: 工具处理函数
            description: 工具描述
            input_schema: 输入参数 Schema
        """
        if self._server:
            self._server.register_tool(name, handler, description, input_schema)

        # 保存工具信息
        self._tools[name] = {
            "name": name,
            "handler": handler,
            "description": description,
            "input_schema": input_schema
        }

        logger.info(f"MCP 注册工具: {name}")

    def register_tools(self, tools: List[Any]):
        """批量注册工具"""
        for tool in tools:
            if hasattr(tool, '__name__'):
                self.register_tool(
                    name=tool.__name__,
                    handler=tool,
                    description=tool.__doc__ or f"Tool: {tool.__name__}"
                )
            else:
                self.register_tool(
                    name=tool.get("name", "unknown"),
                    handler=tool.get("handler"),
                    description=tool.get("description", "")
                )

    # app/mcp/mcp_manager.py - 修复 call_tool 函数

    async def call_tool(
            self,
            tool_name: str,
            arguments: Dict[str, Any],
            session_id: str = ""
    ) -> str:
        """
        通过 MCP 调用工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数
            session_id: 会话ID

        Returns:
            str: 执行结果
        """
        logger.info(f"MCP 调用工具: {tool_name}")

        # 优先使用客户端调用
        if self._client:
            return await self._client.call_tool(tool_name, arguments, session_id)

        # 回退到直接调用
        if tool_name in self._tools:
            handler = self._tools[tool_name]["handler"]
            try:
                # 关键修复：只传递 arguments，不要传递 tool_name
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(**arguments, session_id=session_id)
                else:
                    result = handler(**arguments, session_id=session_id)
                return str(result)
            except Exception as e:
                logger.error(f"工具调用失败: {e}")
                return f"执行失败: {str(e)}"

        return f"工具 '{tool_name}' 未注册"

    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取所有可用工具"""
        if self._client:
            return await self._client.list_tools()

        # 回退到本地列表
        return [
            {
                "name": name,
                "description": info.get("description", ""),
                "inputSchema": info.get("input_schema", {})
            }
            for name, info in self._tools.items()
        ]

    def get_tools_description(self) -> str:
        """获取工具描述（用于 LLM Prompt）"""
        tools = self._tools
        if not tools:
            return "无可用工具"

        lines = []
        for name, info in tools.items():
            desc = info.get("description", "无描述")
            lines.append(f"- {name}: {desc}")

        return "\n".join(lines)


# 全局单例
_mcp_manager: Optional[MCPManager] = None


def get_mcp_manager(server_url: Optional[str] = None, use_local: bool = True) -> MCPManager:
    """获取全局 MCP 管理器单例"""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager(server_url=server_url, use_local=use_local)
    return _mcp_manager