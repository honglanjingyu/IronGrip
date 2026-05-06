# app/mcp/mcp_server.py - 完整修复版本

import asyncio
import json
from typing import Dict, Any, List, Optional
from loguru import logger
from datetime import datetime

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types


class MCPServer:
    """MCP 服务器 - 管理工具并提供服务"""

    def __init__(self, name: str = "agent-mcp-server"):
        self.name = name
        self.server = Server(name)
        self._tools: Dict[str, Any] = {}
        self._running = False

        self._setup_handlers()
        logger.info(f"MCP Server 初始化: {name}")

    def _setup_handlers(self):
        """设置 MCP 协议处理器"""

        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            tools = []
            for name, tool in self._tools.items():
                input_schema = tool.get("input_schema", {
                    "type": "object",
                    "properties": {},
                    "required": []
                })
                tools.append(types.Tool(
                    name=name,
                    description=tool.get("description", f"Tool: {name}"),
                    inputSchema=input_schema
                ))
            logger.info(f"列出 {len(tools)} 个工具")
            return tools

        @self.server.call_tool()
        async def handle_call_tool(
                name: str,
                arguments: Dict[str, Any]
        ) -> List[types.TextContent]:
            """调用工具"""
            logger.info(f"调用工具: {name}, 参数类型: {type(arguments)}, 参数: {arguments}")

            if name not in self._tools:
                return [types.TextContent(
                    type="text",
                    text=f"错误: 工具 '{name}' 不存在"
                )]

            tool = self._tools[name]
            handler = tool.get("handler")

            if not handler:
                return [types.TextContent(
                    type="text",
                    text=f"错误: 工具 '{name}' 没有处理器"
                )]

            try:
                # 复制参数，避免修改原字典
                clean_arguments = dict(arguments)
                # 提取 session_id（如果存在）
                session_id = clean_arguments.pop("session_id", "")

                # 调试日志
                logger.info(f"调用工具 {name}，清理后参数: {clean_arguments}, session_id: {session_id}")

                # 调用工具
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(**clean_arguments, session_id=session_id)
                else:
                    result = handler(**clean_arguments, session_id=session_id)

                return [types.TextContent(
                    type="text",
                    text=str(result)
                )]

            except TypeError as e:
                # 参数类型错误
                logger.error(f"工具 {name} 参数错误: {e}")
                logger.info(f"工具签名: {handler.__signature__ if hasattr(handler, '__signature__') else 'unknown'}")
                return [types.TextContent(
                    type="text",
                    text=f"参数错误: {str(e)}"
                )]
            except Exception as e:
                logger.error(f"工具调用失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return [types.TextContent(
                    type="text",
                    text=f"工具执行失败: {str(e)}"
                )]

    def register_tool(
            self,
            name: str,
            handler: Any,
            description: str = "",
            input_schema: Optional[Dict[str, Any]] = None
    ):
        """注册工具"""
        if input_schema is None:
            input_schema = self._infer_schema(handler)

        self._tools[name] = {
            "name": name,
            "handler": handler,
            "description": description,
            "input_schema": input_schema
        }
        logger.info(f"注册工具到 MCP: {name}")

    def _infer_schema(self, handler) -> Dict[str, Any]:
        """从函数签名推断输入 schema"""
        import inspect

        sig = inspect.signature(handler)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name == "session_id":
                continue

            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == list:
                    param_type = "array"
                elif param.annotation == dict:
                    param_type = "object"

            properties[param_name] = {
                "type": param_type,
                "description": f"参数: {param_name}"
            }

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """直接调用工具（用于本地模式）"""
        logger.info(f"直接调用工具: {tool_name}, 参数: {arguments}")

        if tool_name not in self._tools:
            return [types.TextContent(
                type="text",
                text=f"错误: 工具 '{tool_name}' 不存在"
            )]

        tool = self._tools[tool_name]
        handler = tool.get("handler")

        if not handler:
            return [types.TextContent(
                type="text",
                text=f"错误: 工具 '{tool_name}' 没有处理器"
            )]

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)

            return [types.TextContent(
                type="text",
                text=str(result)
            )]
        except Exception as e:
            logger.error(f"工具调用失败: {e}")
            return [types.TextContent(
                type="text",
                text=f"工具执行失败: {str(e)}"
            )]

    async def run_stdio(self):
        """通过 stdio 运行 MCP 服务器"""
        self._running = True
        logger.info("MCP Server 启动 (stdio 模式)")

        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=self.name,
                    server_version="1.0.0",
                    capabilities={}
                ),
            )

    async def run_http(self, host: str = "127.0.0.1", port: int = 8001):
        """通过 HTTP/SSE 运行 MCP 服务器"""
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import JSONResponse
        import uvicorn

        sse = SseServerTransport("/messages")

        async def handle_sse(request):
            async with sse.connect_sse(
                    request.scope, request.receive, request._send
            ) as streams:
                await self.server.run(
                    streams[0], streams[1],
                    InitializationOptions(
                        server_name=self.name,
                        server_version="1.0.0",
                        capabilities={}
                    )
                )

        async def handle_messages(request):
            await sse.handle_post_message(request.scope, request.receive, request._send)

        async def health_check(request):
            return JSONResponse({"status": "ok", "server": self.name, "tools": len(self._tools)})

        app = Starlette(routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages", endpoint=handle_messages, methods=["POST"]),
            Route("/health", endpoint=health_check),
        ])

        logger.info(f"MCP Server 启动 (HTTP 模式): http://{host}:{port}")
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()


_mcp_server: Optional[MCPServer] = None


def get_mcp_server() -> MCPServer:
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServer()
    return _mcp_server