# app/agent/action/tools/__init__.py (修改)
"""内置行动工具 - 自动发现和注册到 MCP"""

import importlib
import inspect
from pathlib import Path
from typing import List, Callable, Any
from loguru import logger

EXCLUDE_FILES = {"__init__.py", "__pycache__"}
EXCLUDE_FUNCTIONS = {"get_long_term_memory"}

# 新增：工具分类
INDUSTRY_TOOLS = {
    "search_company_info",
    "search_financing_events",
    "compare_companies",
    "fetch_industry_report",
    "get_regulation_updates",
    "search_executive_moves",
    "extract_timeline"
}


def discover_tools() -> List[Callable]:
    """自动发现 tools 目录下的所有工具函数"""
    tools = []
    tools_dir = Path(__file__).parent  # 当前目录

    for py_file in tools_dir.glob("*.py"):
        if py_file.name in EXCLUDE_FILES:
            continue

        module_name = f"app.agent.action.tools.{py_file.stem}"

        try:
            module = importlib.import_module(module_name)

            for name, obj in inspect.getmembers(module):
                if name in EXCLUDE_FUNCTIONS:
                    continue
                if name.startswith("_"):
                    continue
                # 允许同步函数也可以作为工具
                if not callable(obj):
                    continue

                # 对于同步函数，包装为异步
                if not inspect.iscoroutinefunction(obj):
                    async def async_wrapper(**kwargs):
                        return obj(**kwargs)
                    tools.append(async_wrapper)
                    logger.debug(f"发现同步工具（已包装）: {name} from {py_file.name}")
                else:
                    tools.append(obj)
                    logger.debug(f"发现异步工具: {name} from {py_file.name}")

        except Exception as e:
            logger.error(f"加载模块 {module_name} 失败: {e}")

    return tools


def get_industry_tools() -> List[Callable]:
    """获取行业研究专用工具"""
    all_tools = discover_tools()
    return [t for t in all_tools if t.__name__ in INDUSTRY_TOOLS]


def get_general_tools() -> List[Callable]:
    """获取通用工具"""
    all_tools = discover_tools()
    return [t for t in all_tools if t.__name__ not in INDUSTRY_TOOLS]