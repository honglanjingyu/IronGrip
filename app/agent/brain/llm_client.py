# app/agent/brain/llm_client.py

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
        self.timeout = timeout

        self._client: Optional[ChatOpenAI] = None
        self._init_client()

    def _init_client(self):
        """初始化 ChatOpenAI 客户端"""
        if not self.api_key:
            logger.warning("LLM_API_KEY 未配置，LLM 客户端将无法正常工作")
            return

        # 注意：不设置 response_format，让 LangChain 自动处理
        self._client = ChatOpenAI(
            model=self.model_name,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=self.temperature,
            streaming=self.streaming,
            timeout=self.timeout,
            max_retries=1,
            request_timeout=self.timeout,
            # 不设置 response_format，避免 API 约束
        )
        logger.info(f"LLM 客户端初始化完成: model={self.model_name}, streaming={self.streaming}")

    @property
    def client(self) -> ChatOpenAI:
        if self._client is None:
            self._init_client()
        return self._client

    async def invoke(self, messages: List[BaseMessage], **kwargs) -> str:
        """同步调用 LLM"""
        try:
            response = await asyncio.wait_for(
                self.client.ainvoke(messages, **kwargs),
                timeout=self.timeout
            )
            content = response.content if hasattr(response, 'content') else str(response)
            return content
        except asyncio.TimeoutError:
            raise TimeoutError("LLM 调用超时")
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise

    async def invoke_structured(self, messages: List[BaseMessage], structure_type: Any, **kwargs) -> Any:
        """
        调用 LLM 并返回结构化输出

        阿里云 DashScope 要求：
        - 使用 response_format 为 json_object 时，messages 中必须包含 "json" 字样
        - 因此需要在 system prompt 中添加 "json" 关键词
        """
        try:
            # 检查并修复消息列表，确保包含 "json" 关键词
            fixed_messages = self._ensure_json_keyword_in_messages(messages)

            # 使用 with_structured_output，它会自动设置 response_format
            structured_llm = self.client.with_structured_output(structure_type)

            result = await asyncio.wait_for(
                structured_llm.ainvoke(fixed_messages, **kwargs),
                timeout=self.timeout
            )
            return result
        except asyncio.TimeoutError:
            raise TimeoutError("LLM 调用超时")
        except Exception as e:
            logger.error(f"结构化 LLM 调用失败: {e}")
            # 打印错误详情以便调试
            if hasattr(e, 'response'):
                logger.error(f"API 响应: {e.response}")
            raise

    def _ensure_json_keyword_in_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        确保消息中包含 "json" 关键词（阿里云 DashScope 要求）

        当使用 response_format: json_object 时，messages 中必须包含 "json" 字样
        """
        fixed_messages = []

        for msg in messages:
            content = msg.content if isinstance(msg.content, str) else str(msg.content)

            # 如果内容中已经包含 "json"，直接使用原消息
            if 'json' in content.lower():
                fixed_messages.append(msg)
                continue

            # 否则在 system message 中添加提示
            if isinstance(msg, SystemMessage):
                new_content = f"请以 JSON 格式输出。{content}"
                fixed_messages.append(SystemMessage(content=new_content))
            elif isinstance(msg, HumanMessage):
                # 在用户消息中添加 json 关键词
                new_content = f"请返回 JSON 格式。{content}"
                fixed_messages.append(HumanMessage(content=new_content))
            else:
                fixed_messages.append(msg)

        # 如果没有 SystemMessage，添加一个
        has_system = any(isinstance(m, SystemMessage) for m in fixed_messages)
        if not has_system:
            fixed_messages.insert(0, SystemMessage(content="请以 JSON 格式输出所有结果。"))

        return fixed_messages

    async def stream(self, messages: List[BaseMessage], **kwargs) -> AsyncGenerator[str, None]:
        """流式调用 LLM"""
        if not self._client:
            logger.error("LLM 客户端未初始化")
            yield "LLM 服务不可用，请检查配置"
            return

        try:
            logger.debug(f"开始流式调用 LLM, 消息数量: {len(messages)}")

            async for chunk in self._client.astream(messages, **kwargs):
                if hasattr(chunk, 'content') and chunk.content:
                    content = chunk.content
                    if isinstance(content, str) and content:
                        yield content
                elif isinstance(chunk, str) and chunk:
                    yield chunk

            logger.debug("流式调用完成")

        except asyncio.TimeoutError:
            logger.error("流式 LLM 调用超时")
            yield "抱歉，处理超时，请稍后重试。"
        except Exception as e:
            logger.error(f"流式 LLM 调用失败: {e}")
            yield f"处理出错: {str(e)}"


# 全局单例
_llm_client: Optional[LLMClient] = None


def get_llm_client(timeout: int = 30) -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient(timeout=timeout)
    return _llm_client