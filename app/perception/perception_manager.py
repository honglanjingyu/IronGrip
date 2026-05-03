# app/perception/perception_manager.py
"""感知管理器 - 统一管理感知模块的所有组件"""

from typing import Optional, Dict, Any
from loguru import logger

from .models import PerceptionResult, InputData
from .input_handler import InputHandler
from .environment_sensor import EnvironmentSensor
from .memory_retriever import MemoryRetriever
from .config import vector_store_config, validate_config


class PerceptionManager:
    """
    感知管理器

    统一管理：
    1. 输入处理
    2. 环境感知
    3. 记忆检索
    """

    def __init__(self, vector_store_manager=None):
        """
        初始化感知管理器

        Args:
            vector_store_manager: 向量存储管理器（用于长期记忆）
        """
        # 验证配置
        validate_config()

        self.input_handler = InputHandler()
        self.environment_sensor = EnvironmentSensor()

        # 如果没有传入向量存储管理器且启用了存储，则自动创建
        if vector_store_manager is None and vector_store_config.ENABLE_STORAGE:
            vector_store_manager = self._create_vector_store()

        self.memory_retriever = MemoryRetriever(vector_store_manager)

        # 会话状态缓存
        self._session_cache: Dict[str, Dict] = {}

        logger.info("PerceptionManager 初始化完成")

    def _create_vector_store(self):
        """根据配置创建向量存储实例"""
        if vector_store_config.VECTOR_STORE_TYPE == "milvus":
            try:
                from .milvus_store import MilvusVectorStore
                logger.info("创建 Milvus 向量存储实例")
                return MilvusVectorStore()
            except Exception as e:
                logger.error(f"创建 Milvus 向量存储失败: {e}")
                return None
        else:
            logger.warning(f"不支持的向量存储类型: {vector_store_config.VECTOR_STORE_TYPE}")
            return None

    async def perceive(
            self,
            input_text: str,
            session_id: str,
            include_long_term: bool = True,
            top_k: Optional[int] = None,
            metadata: Optional[Dict] = None
    ) -> PerceptionResult:
        """
        执行完整的感知流程

        Args:
            input_text: 用户输入文本
            session_id: 会话ID
            include_long_term: 是否包含长期记忆检索
            top_k: 长期记忆返回数量
            metadata: 附加元数据

        Returns:
            PerceptionResult: 完整的感知结果
        """
        logger.info(f"开始感知流程: session={session_id}, input='{input_text[:100]}...'")

        # 1. 输入处理
        input_data = await self.input_handler.process_text(
            text=input_text,
            session_id=session_id,
            metadata=metadata
        )

        # 2. 环境感知
        environment_context = await self.environment_sensor.scan_environment(session_id)

        # 3. 记忆检索
        short_term, long_term, working_memory = await self.memory_retriever.retrieve_all(
            query=input_text,
            session_id=session_id,
            include_long_term=include_long_term,
            top_k=top_k
        )

        # 4. 生成摘要
        summary = self._generate_summary(
            input_data=input_data,
            environment=environment_context,
            short_term_count=len(short_term),
            long_term_count=len(long_term)
        )

        result = PerceptionResult(
            input_data=input_data,
            environment_context=environment_context,
            short_term_memory=short_term,
            long_term_memory=long_term,
            working_memory=working_memory,
            summary=summary
        )

        # 缓存结果
        self._session_cache[session_id] = {
            "last_input": input_text,
            "last_perception": result,
            "timestamp": input_data.timestamp
        }

        logger.info(f"感知流程完成: session={session_id}")
        return result

    def _generate_summary(
            self,
            input_data: InputData,
            environment: Any,
            short_term_count: int,
            long_term_count: int
    ) -> str:
        """生成感知结果摘要"""
        return f"""
感知摘要:
- 输入类型: {input_data.type.value}
- 输入长度: {len(str(input_data.content))} 字符
- 当前时间: {environment.current_time}
- 环境状态: CPU {environment.system_status.get('cpu_percent', 'N/A')}%, 内存 {environment.system_status.get('memory_percent', 'N/A')}%
- 活动告警: {len(environment.active_alerts)} 个
- 短期记忆: {short_term_count} 条
- 长期记忆: {long_term_count} 条
        """.strip()

    async def perceive_with_file(
            self,
            file_path: str,
            session_id: str,
            include_long_term: bool = True,
            top_k: Optional[int] = None
    ) -> PerceptionResult:
        """
        带文件的感知流程

        Args:
            file_path: 文件路径
            session_id: 会话ID
            include_long_term: 是否包含长期记忆
            top_k: 长期记忆返回数量

        Returns:
            PerceptionResult: 感知结果
        """
        logger.info(f"开始文件感知流程: session={session_id}, file={file_path}")

        # 1. 处理文件输入
        input_data = await self.input_handler.process_file(file_path, session_id)

        # 2. 环境感知
        environment_context = await self.environment_sensor.scan_environment(session_id)

        # 3. 记忆检索（使用文件内容作为查询）
        short_term, long_term, working_memory = await self.memory_retriever.retrieve_all(
            query=input_data.content[:500],
            session_id=session_id,
            include_long_term=include_long_term,
            top_k=top_k
        )

        summary = f"文件感知: {input_data.metadata.get('file_name', 'unknown')}, 大小={input_data.metadata.get('file_size', 0)} 字符"

        return PerceptionResult(
            input_data=input_data,
            environment_context=environment_context,
            short_term_memory=short_term,
            long_term_memory=long_term,
            working_memory=working_memory,
            summary=summary
        )

    def add_conversation_to_memory(
            self,
            user_input: str,
            assistant_output: str
    ):
        """将对话添加到短期记忆"""
        self.memory_retriever.add_to_short_term(user_input, assistant_output)

    def add_to_working_memory(self, key: str, value: Any):
        """添加到工作记忆"""
        self.memory_retriever.add_to_working(key, value)

    def clear_session(self, session_id: str):
        """清空会话"""
        self.memory_retriever.clear_session()
        if session_id in self._session_cache:
            del self._session_cache[session_id]
        logger.info(f"清空会话: {session_id}")

    def _create_vector_store(self):
        """根据配置创建向量存储实例"""
        if vector_store_config.VECTOR_STORE_TYPE == "milvus":
            try:
                from .milvus_store import MilvusVectorStore
                logger.info("创建 Milvus 向量存储实例")
                # 使用配置中的集合名称
                return MilvusVectorStore(
                    collection_name=vector_store_config.COLLECTION_NAME
                )
            except Exception as e:
                logger.error(f"创建 Milvus 向量存储失败: {e}")
                return None
        else:
            logger.warning(f"不支持的向量存储类型: {vector_store_config.VECTOR_STORE_TYPE}")
            return None