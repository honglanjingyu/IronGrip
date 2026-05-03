# app/brain/llm_client.py
"""LLM 客户端 - 使用 OpenAI 兼容模式调用阿里云 DashScope/Qwen"""

from typing import Optional, List, Dict, Any, AsyncGenerator
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from loguru import logger

from .config import brain_config


class LLMClient:
    """LLM 客户端封装 - 使用 OpenAI 兼容模式"""

    def __init__(self, timeout: int = 30):
        self.model_name = brain_config.LLM_MODEL_NAME
        self.api_key = brain_config.LLM_API_KEY
        self.base_url = brain_config.LLM_BASE_URL
        self.temperature = brain_config.LLM_TEMPERATURE
        self.streaming = brain_config.STREAMING
        self.timeout = timeout  # 超时时间（秒）

        self._client: Optional[ChatOpenAI] = None
        self._init_client()

    def _init_client(self):
        """初始化 ChatOpenAI 客户端（OpenAI 兼容模式）"""
        if not self.api_key:
            logger.warning("LLM_API_KEY 未配置，LLM 客户端将无法正常工作")
            return

        # 使用 OpenAI 兼容模式调用阿里云 DashScope
        self._client = ChatOpenAI(
            model=self.model_name,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=self.temperature,
            streaming=self.streaming,
            timeout=self.timeout,
            max_retries=1,  # 减少重试次数
            request_timeout=self.timeout,
        )
        logger.info(
            f"LLM 客户端初始化完成: model={self.model_name}, base_url={self.base_url}, streaming={self.streaming}, timeout={self.timeout}s")

    @property
    def client(self) -> ChatOpenAI:
        """获取客户端实例"""
        if self._client is None:
            self._init_client()
        return self._client

    async def invoke(
            self,
            messages: List[BaseMessage],
            **kwargs
    ) -> str:
        """同步调用 LLM（非流式）"""
        try:
            # 添加超时控制
            response = await asyncio.wait_for(
                self.client.ainvoke(messages, **kwargs),
                timeout=self.timeout
            )
            content = response.content if hasattr(response, 'content') else str(response)
            logger.debug(f"LLM 调用成功，响应长度: {len(content)}")
            return content
        except asyncio.TimeoutError:
            logger.error(f"LLM 调用超时 (>{self.timeout}s)")
            raise TimeoutError(f"LLM 调用超时，请检查网络连接或稍后重试")
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise

    async def invoke_structured(
            self,
            messages: List[BaseMessage],
            structure_type: Any,
            **kwargs
    ) -> Any:
        """
        调用 LLM 并返回结构化输出

        Args:
            messages: 消息列表
            structure_type: Pydantic 模型类，用于约束输出格式
            **kwargs: 额外参数

        Returns:
            结构化输出对象
        """
        try:
            # ChatOpenAI 也支持 with_structured_output
            structured_llm = self.client.with_structured_output(structure_type)

            # 添加超时控制
            result = await asyncio.wait_for(
                structured_llm.ainvoke(messages, **kwargs),
                timeout=self.timeout
            )
            logger.debug(f"结构化 LLM 调用成功")
            return result
        except asyncio.TimeoutError:
            logger.error(f"结构化 LLM 调用超时 (>{self.timeout}s)")
            raise TimeoutError(f"LLM 调用超时，请检查网络连接或稍后重试")
        except Exception as e:
            logger.error(f"结构化 LLM 调用失败: {e}")
            raise

    async def stream(
            self,
            messages: List[BaseMessage],
            **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式调用 LLM"""
        try:
            async for chunk in self.client.astream(messages, **kwargs):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
        except asyncio.TimeoutError:
            logger.error(f"流式 LLM 调用超时")
            yield "抱歉，处理超时，请稍后重试。"
        except Exception as e:
            logger.error(f"流式 LLM 调用失败: {e}")
            yield f"处理出错: {str(e)}"


# 全局单例
_llm_client: Optional[LLMClient] = None


def get_llm_client(timeout: int = 30) -> LLMClient:
    """获取全局 LLM 客户端单例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient(timeout=timeout)
    return _llm_client