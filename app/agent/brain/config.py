# app/brain/config.py
"""大脑模块配置"""

import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger


# 加载环境变量
def load_config():
    env_paths = [
        Path.cwd() / ".env",
        Path(__file__).parent.parent.parent / ".env",
        Path(__file__).parent.parent / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"加载配置文件: {env_path}")
            return
    logger.warning("未找到 .env 配置文件")


load_config()


class BrainConfig:
    """大脑模块配置"""

    # LLM 配置
    LLM_TYPE: str = os.getenv("LLM_TYPE", "remote")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "qwen-plus")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))

    # Plan-Execute-Replan 配置
    MAX_PLAN_STEPS: int = int(os.getenv("MAX_PLAN_STEPS", "10"))
    MAX_EXECUTION_ITERATIONS: int = int(os.getenv("MAX_EXECUTION_ITERATIONS", "8"))

    # 提示词模板路径
    PROMPT_TEMPLATES: dict = {
        "planner": "brain/prompts/planner.txt",
        "executor": "brain/prompts/executor.txt",
        "replanner": "brain/prompts/replanner.txt",
    }

    # 是否启用流式输出
    STREAMING: bool = os.getenv("STREAMING", "true").lower() == "true"


# 全局配置实例
brain_config = BrainConfig()