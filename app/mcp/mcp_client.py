# app/mcp/mcp_client.py - 修复 call_tool 方法
"""MCP 客户端 - 调用 MCP 服务器"""

import json
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from contextlib import asynccontextmanager
from loguru import logger

import httpx
import aiohttp


class MCPClient:
    """
    MCP 客户端 - 连接 MCP 服务器并调用工具

    支持两种模式：
    1. HTTP/SSE 模式：通过 HTTP 请求调用
    2. 本地模式：直接调用注册的工具（开发模式）
    """

    def __init__(
            self,
            server_url: Optional[str] = None,
            use_local: bool = True,
            local_server: Optional[Any] = None
    ):
        """
        初始化 MCP 客户端

        Args:
            server_url: MCP 服务器 URL (SSE endpoint)
            use_local: 是否使用本地模式（直接调用）
            local_server: 本地 MCP Server 实例
        """
        self.server_url = server_url
        self.use_local = use_local
        self.local_server = local_server
        self._tools_cache: Optional[List[Dict[str, Any]]] = None
        self._http_client: Optional[httpx.AsyncClient] = None

        logger.info(f"MCP Client 初始化: server_url={server_url}, use_local={use_local}")

    async def _get_http_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        获取所有可用工具列表

        Returns:
            List[Dict]: 工具列表，每个工具包含 name, description, inputSchema
        """
        if self._tools_cache is not None:
            return self._tools_cache

        if self.use_local and self.local_server:
            # 本地模式：从服务器获取
            tools = []
            for name, tool in self.local_server._tools.items():
                tools.append({
                    "name": name,
                    "description": tool.get("description", ""),
                    "inputSchema": tool.get("input_schema", {})
                })
            self._tools_cache = tools
            logger.info(f"从本地 MCP 获取到 {len(tools)} 个工具")
            return tools

        if self.server_url:
            # HTTP 模式：通过 SSE 获取
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                            f"{self.server_url.rstrip('/')}/health"
                    ) as health_resp:
                        if health_resp.status == 200:
                            data = await health_resp.json()
                            logger.info(f"从远程 MCP 获取服务器状态: {data}")
            except Exception as e:
                logger.warning(f"连接远程 MCP 服务器失败: {e}")

        # 回退到空列表
        return []

    # app/mcp/mcp_client.py - 修复 call_tool 函数

    async def call_tool(
            self,
            tool_name: str,
            arguments: Dict[str, Any],
            session_id: str = ""
    ) -> str:
        """
        调用工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数
            session_id: 会话ID

        Returns:
            str: 工具执行结果
        """
        logger.info(f"MCP 调用工具: {tool_name}, session={session_id}")

        # 关键修复：不要在这里添加 tool_name 到参数中
        # 只合并 session_id
        args_with_session = dict(arguments)  # 复制原始参数
        if session_id:
            args_with_session["session_id"] = session_id

        if self.use_local and self.local_server:
            # 本地模式：直接调用服务器的 call_tool 方法
            result = await self.local_server.call_tool(tool_name, args_with_session)
            if result and len(result) > 0:
                return result[0].text
            return "工具执行完成"

        if self.server_url:
            try:
                async with aiohttp.ClientSession() as session:
                    request = {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {
                            "name": tool_name,
                            "arguments": args_with_session
                        },
                        "id": 1
                    }

                    async with session.post(
                            f"{self.server_url.rstrip('/')}/messages",
                            json=request
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            if "result" in data and "content" in data["result"]:
                                content = data["result"]["content"]
                                if content and len(content) > 0:
                                    return content[0].get("text", "")
                        return f"工具调用失败: HTTP {response.status}"

            except Exception as e:
                logger.error(f"MCP 工具调用失败: {e}")
                return f"工具调用失败: {str(e)}"

        return "MCP 客户端未配置"

    async def close(self):
        """关闭客户端"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# 全局单例
_mcp_client: Optional[MCPClient] = None


def get_mcp_client(server_url: Optional[str] = None, use_local: bool = True) -> MCPClient:
    """获取全局 MCP Client 实例"""
    global _mcp_client
    if _mcp_client is None:
        from .mcp_server import get_mcp_server
        local_server = get_mcp_server() if use_local else None
        _mcp_client = MCPClient(
            server_url=server_url,
            use_local=use_local,
            local_server=local_server
        )
    return _mcp_client