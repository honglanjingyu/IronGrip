"""输入处理模块 - 接收并标准化多模态输入"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from loguru import logger

from .models import InputData, InputType, EnvironmentContext


class InputHandler:
    """
    输入处理器

    功能：
    1. 接收用户的多模态输入（文本、文件、系统请求）
    2. 验证和清洗输入
    3. 标准化为统一的 InputData 格式
    """

    def __init__(self):
        self.max_text_length = 10000
        self.supported_extensions = [".txt", ".md", ".json"]
        logger.info("InputHandler 初始化完成")

    async def process_text(
        self,
        text: str,
        session_id: str,
        metadata: Optional[Dict] = None
    ) -> InputData:
        """处理文本输入"""
        if not text or not text.strip():
            raise ValueError("文本内容不能为空")

        if len(text) > self.max_text_length:
            logger.warning(f"输入文本过长: {len(text)} 字符，将截断")
            text = text[:self.max_text_length]

        cleaned_text = " ".join(text.strip().split())

        logger.info(f"处理文本输入: session={session_id}, 长度={len(cleaned_text)}")

        return InputData(
            type=InputType.TEXT,
            content=cleaned_text,
            session_id=session_id,
            metadata=metadata or {
                "original_length": len(text),
                "processed_at": datetime.now().isoformat()
            }
        )

    async def process_file(
        self,
        file_path: Union[str, Path],
        session_id: str,
        metadata: Optional[Dict] = None
    ) -> InputData:
        """处理文件输入"""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        if path.suffix not in self.supported_extensions:
            raise ValueError(f"不支持的文件类型: {path.suffix}")

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="gbk")

        logger.info(f"处理文件输入: session={session_id}, file={path.name}, 大小={len(content)}")

        return InputData(
            type=InputType.FILE,
            content=content,
            session_id=session_id,
            metadata=metadata or {
                "file_name": path.name,
                "file_size": len(content),
                "file_extension": path.suffix,
                "processed_at": datetime.now().isoformat()
            }
        )

    async def process_system_request(
        self,
        request: str,
        session_id: str,
        context: Optional[Dict] = None
    ) -> InputData:
        """处理系统请求"""
        logger.info(f"处理系统请求: session={session_id}")

        return InputData(
            type=InputType.SYSTEM,
            content=request,
            session_id=session_id,
            metadata=context or {
                "request_type": "system_diagnosis",
                "processed_at": datetime.now().isoformat()
            }
        )