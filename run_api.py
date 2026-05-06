# run_api.py - 修改日志配置
"""FastAPI 服务启动入口 - 支持 MCP"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from loguru import logger

# ============================================================
# 日志配置：只输出到文件，控制台只显示用户交互
# ============================================================

# 创建日志目录
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 移除所有默认处理器
logger.remove()

logger.add(
    LOG_DIR / "debug_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    level="DEBUG",
    encoding="utf-8"
)


# 控制台输出函数（用于用户交互）
def cout(*args, **kwargs):
    """纯用户交互输出，不加任何颜色/格式控制"""
    kwargs.setdefault('flush', True)
    print(*args, **kwargs)


# 导入 MCP
from app.mcp import get_mcp_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("正在初始化 Agent 系统...")

    # 初始化 MCP 管理器
    try:
        mcp_manager = get_mcp_manager(use_local=True)

        # 注册内置工具
        from app.action.tools import discover_tools
        tools = discover_tools()
        for tool in tools:
            mcp_manager.register_tool(
                name=tool.__name__,
                handler=tool,
                description=tool.__doc__ or f"Tool: {tool.__name__}"
            )
        logger.info(f"MCP 已注册 {len(tools)} 个工具")
    except Exception as e:
        logger.error(f"MCP 初始化失败: {e}")

    from app.api.dependencies import get_agent

    try:
        agent = await get_agent()
        logger.info("Agent 系统初始化完成")
    except Exception as e:
        logger.error(f"Agent 初始化失败: {e}")

    yield

    logger.info("正在关闭 Agent 系统...")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    app = FastAPI(
        title="Agent API",
        description="AI Agent 系统 API 接口 (MCP 协议)",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册 API 路由
    from app.api.routes import router
    app.include_router(router)

    # MCP 健康检查端点
    @app.get("/mcp/health")
    async def mcp_health():
        from app.mcp import get_mcp_manager
        mcp_manager = get_mcp_manager(use_local=True)
        return {
            "status": "ok",
            "tools": list(mcp_manager._tools.keys()),
            "tool_count": len(mcp_manager._tools)
        }

    # 静态文件服务
    web_dir = Path(__file__).parent / "web"
    if web_dir.exists():
        app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

        from fastapi.responses import FileResponse

        @app.get("/")
        async def serve_index():
            index_path = web_dir / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
            return {"message": "Web frontend not found"}

        logger.info(f"Web 前端已加载: {web_dir}")
    else:
        @app.get("/")
        async def root():
            return {
                "name": "Agent API (MCP)",
                "version": "1.0.0",
                "docs": "/docs",
                "health": "/api/v1/health",
                "mcp_health": "/mcp/health"
            }

        logger.warning(f"Web 前端目录不存在: {web_dir}")

    return app


def main():
    """启动服务"""
    import argparse

    parser = argparse.ArgumentParser(description="启动 Agent API 服务")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--reload", action="store_true", help="热重载模式")
    parser.add_argument("--mcp-port", type=int, default=8001, help="MCP 服务器端口")
    parser.add_argument("--mcp-mode", choices=["stdio", "http", "embedded"],
                        default="embedded", help="MCP 运行模式")
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

    # 如果指定了独立 MCP 模式，需要单独启动
    if args.mcp_mode == "http":
        cout(f"\n⚠️  请单独运行: python run_mcp_server.py --mode http --port {args.mcp_port}")
    elif args.mcp_mode == "stdio":
        cout(f"\n⚠️  请单独运行: python run_mcp_server.py --mode stdio")

    app = create_app()

    cout(f"\n{'=' * 50}")
    cout(f"🚀 Agent API 服务已启动 (MCP 模式)")
    cout(f"{'=' * 50}")
    cout(f"📍 地址: http://{args.host}:{args.port}")
    cout(f"📖 API 文档: http://{args.host}:{args.port}/docs")
    cout(f"🎨 Web 界面: http://{args.host}:{args.port}/")
    cout(f"🔧 MCP 状态: http://{args.host}:{args.port}/mcp/health")
    cout(f"🛠️  MCP 模式: {args.mcp_mode}")
    cout(f"📁 日志目录: logs/")
    cout(f"{'=' * 50}\n")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()