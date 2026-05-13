# run_mcp_server.py
#!/usr/bin/env python
"""独立运行 MCP 服务器"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import asyncio
import argparse
from loguru import logger

# ============================================================
# 日志配置：只输出到文件，控制台只显示关键信息
# ============================================================

# 创建日志目录
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 移除所有默认处理器
logger.remove()

# 添加文件处理器
logger.add(
    LOG_DIR / "mcp_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} | {message}",
    level="DEBUG",
    encoding="utf-8"
)


def cout(*args, **kwargs):
    """控制台输出"""
    kwargs.setdefault('flush', True)
    print(*args, **kwargs)


from app.mcp import get_mcp_server, get_mcp_manager
from app.agent.action.tools import discover_tools


async def main():
    parser = argparse.ArgumentParser(description="MCP 服务器")
    parser.add_argument("--mode", choices=["stdio", "http"], default="stdio", help="运行模式")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP 模式监听地址")
    parser.add_argument("--port", type=int, default=8003, help="HTTP 模式监听端口")
    parser.add_argument("--console-log", action="store_true", help="同时输出日志到控制台")
    args = parser.parse_args()

    # 如果需要控制台日志
    if args.console_log:
        logger.add(
            sys.stdout,
            format="{time:HH:mm:ss} | {level} | {message}",
            level="INFO",
            colorize=True
        )

    # 获取 MCP 服务器
    mcp_server = get_mcp_server()
    mcp_manager = get_mcp_manager(use_local=True)

    # 注册内置工具
    tools = discover_tools()
    for tool in tools:
        mcp_server.register_tool(
            name=tool.__name__,
            handler=tool,
            description=tool.__doc__ or f"Tool: {tool.__name__}"
        )

    cout(f"\n{'=' * 50}")
    cout(f"🔧 MCP 服务器已启动")
    cout(f"{'=' * 50}")
    cout(f"📁 日志目录: logs/")
    cout(f"🔧 已注册工具: {len(tools)} 个")
    cout(f"🛠️  运行模式: {args.mode}")
    cout(f"{'=' * 50}\n")

    if args.mode == "http":
        await mcp_server.run_http(host=args.host, port=args.port)
    else:
        await mcp_server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())