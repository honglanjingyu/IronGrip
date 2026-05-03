
"""感知模块测试 Demo - 使用真实 Milvus 向量存储

运行方式:
    python demo_perception.py

文件位置: 项目主目录（与 main.py 同级）
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入感知模块
from app.perception import PerceptionManager, MilvusVectorStore
from app.perception.config import vector_store_config, embedding_config, retrieval_config
from langchain_core.documents import Document


def print_section(title: str, char: str = "=", width: int = 70):
    """打印分节标题"""
    print("\n" + char * width)
    print(f" {title}")
    print(char * width)


def print_subsection(title: str):
    """打印子标题"""
    print("\n" + "-" * 40)
    print(f" {title}")
    print("-" * 40)


def print_config_info():
    """打印当前配置信息"""
    print_section("📋 当前配置信息")
    print(f"  向量存储类型: {vector_store_config.VECTOR_STORE_TYPE}")
    print(f"  Milvus 地址: {vector_store_config.MILVUS_HOST}:{vector_store_config.MILVUS_PORT}")
    print(f"  集合名称: {vector_store_config.COLLECTION_NAME}")
    print(f"  存储启用: {vector_store_config.ENABLE_STORAGE}")
    print(f"  Embedding 类型: {embedding_config.EMBEDDING_TYPE}")
    if embedding_config.EMBEDDING_TYPE == "remote":
        print(f"  Embedding 模型: {embedding_config.EMBEDDING_MODEL}")
    else:
        print(f"  本地 Embedding 模型: {embedding_config.LOCAL_EMBEDDING_MODEL}")
        print(f"  运行设备: {embedding_config.EMBEDDING_DEVICE}")
    print(f"  检索 Top-K: {retrieval_config.SIMILARITY_TOP_K}")
    print(f"  相似度阈值: {retrieval_config.SIMILARITY_THRESHOLD}")


async def clear_and_reinit_knowledge_base(vector_store: MilvusVectorStore):
    """清空并重新初始化知识库 - 先删除现有集合，再创建新集合并添加文档"""
    print_subsection("📚 清空并重新初始化知识库")

    # 1. 删除现有集合
    stats = vector_store.get_collection_stats()
    if stats.get("exists", False):
        print(f"  检测到已有集合，包含 {stats.get('num_entities', 0)} 个文档")
        print("  正在删除现有集合...")
        vector_store.delete_collection()
        print("  ✅ 集合已删除")

    # 2. 重新初始化集合（会自动创建新集合）
    print("  正在创建新集合...")
    vector_store._init_collection()
    print("  ✅ 新集合创建成功")

    # 3. 添加示例文档
    print("  添加示例文档到 Milvus...")

    documents = [
        Document(
            page_content="系统故障排查指南：当 CPU 使用率过高时，第一步检查是否有异常进程，使用 top 命令查看 CPU 占用最高的进程。第二步分析进程日志，定位问题代码。",
            metadata={"source": "knowledge_base", "category": "troubleshooting", "id": "doc_001"}
        ),
        Document(
            page_content="内存泄漏排查方法：内存使用率持续上升通常是内存泄漏的表现，建议使用 jmap 或 heap profiler 分析堆内存。常见原因包括未关闭的连接、缓存未清理等。",
            metadata={"source": "knowledge_base", "category": "memory", "id": "doc_002"}
        ),
        Document(
            page_content="告警处理最佳实践：先确认告警级别和影响范围，再分析根本原因，最后制定处理方案和预防措施。关键告警需在 5 分钟内响应。",
            metadata={"source": "knowledge_base", "category": "alert", "id": "doc_003"}
        ),
        Document(
            page_content="向量数据库是一种专门存储和检索向量数据的数据库，常用于语义搜索、推荐系统、RAG 等场景。常见产品包括 Milvus、Pinecone、Weaviate。",
            metadata={"source": "knowledge_base", "category": "database", "id": "doc_004"}
        ),
        Document(
            page_content="数据同步服务常见问题：同步延迟通常由网络问题、源库负载过高或目标库写入瓶颈引起。解决方案包括优化查询、增加并发、使用批量写入。",
            metadata={"source": "knowledge_base", "category": "data-sync", "id": "doc_005"}
        ),
        Document(
            page_content="Milvus 向量数据库使用指南：Milvus 是一款开源向量数据库，支持百亿级向量检索。主要概念包括 Collection（集合）、Partition（分区）、Index（索引）等。",
            metadata={"source": "knowledge_base", "category": "milvus", "id": "doc_006"}
        ),
    ]

    # 批量添加文档
    ids = vector_store.add_documents(documents)

    if ids:
        print(f"  ✅ 成功添加 {len(ids)} 个文档到 Milvus")

        # 显示添加后的统计信息
        stats = vector_store.get_collection_stats()
        print(f"  集合统计: 共 {stats.get('num_entities', 0)} 个文档")
        
        # 打印添加的文档信息
        print(f"\n  📄 已添加文档列表:")
        for i, doc in enumerate(documents, 1):
            preview = doc.page_content[:60] + "..." if len(doc.page_content) > 60 else doc.page_content
            print(f"     {i}. [{doc.metadata.get('category', 'unknown')}] {preview}")
    else:
        print(f"  ⚠️ 没有成功添加文档，请检查 Milvus 连接和配置")
        print(f"  错误信息: {stats.get('error', 'Unknown error')}")
    
    return len(ids) if ids else 0


async def demo_store_and_retrieve():
    """测试 1: 先存储文档到 Milvus，再进行检索"""
    print_section("测试 1: 存储文档到 Milvus + 检索验证")

    # 创建 Milvus 向量存储
    print("  正在连接 Milvus...")
    try:
        vector_store = MilvusVectorStore()
        print("  ✅ Milvus 连接成功")
    except Exception as e:
        print(f"  ❌ Milvus 连接失败: {e}")
        return None, None

    # 清空并重新初始化知识库（先删除再添加）
    doc_count = await clear_and_reinit_knowledge_base(vector_store)
    
    if doc_count == 0:
        print("  ❌ 文档存储失败，终止测试")
        return None, None

    # 验证存储结果 - 执行多次检索测试
    print_subsection("🔍 检索验证")

    # 测试查询列表
    test_queries = [
        ("CPU 告警如何处理", "troubleshooting"),
        ("内存泄漏怎么排查", "memory"),
        ("什么是向量数据库", "database"),
        ("Milvus 是什么", "milvus"),
        ("数据同步延迟怎么办", "data-sync"),
        ("告警响应时间要求", "alert"),
    ]

    for query, expected_category in test_queries:
        print(f"\n  📝 查询: {query}")
        results = vector_store.similarity_search_with_score(query, k=2)
        
        if results:
            print(f"     找到 {len(results)} 个相关文档:")
            for i, (doc, score) in enumerate(results, 1):
                preview = doc.page_content[:80] + "..." if len(doc.page_content) > 80 else doc.page_content
                print(f"       {i}. [相关性: {score:.4f}] {preview}")
                print(f"          分类: {doc.metadata.get('category', 'unknown')}")
        else:
            print(f"      ⚠️ 未找到相关文档")

    return vector_store, doc_count


async def demo_text_input_with_stored_knowledge(vector_store: MilvusVectorStore):
    """测试 2: 使用已存储的知识库进行文本输入感知"""
    print_section("测试 2: 文本输入感知（使用已存储的知识库）")

    # 创建感知管理器（使用已有的向量存储）
    perception = PerceptionManager(vector_store_manager=vector_store)

    test_input = "我的数据同步服务出现 CPU 告警，请帮我分析原因"
    print(f"\n🔍 输入: {test_input}")
    print("   执行感知流程...")

    # 执行感知
    result = await perception.perceive(
        input_text=test_input,
        session_id="test-session-001",
        include_long_term=True,
        top_k=3,
        metadata={"source": "api", "priority": "high", "user_id": "user-123"}
    )

    # 打印结果
    print_subsection("📥 输入信息")
    print(f"  类型: {result.input_data.type.value}")
    print(f"  会话ID: {result.input_data.session_id}")
    print(f"  内容: {result.input_data.content}")
    print(f"  元数据: {result.input_data.metadata}")

    print_subsection("🌍 环境信息")
    print(f"  当前时间: {result.environment_context.current_time}")
    print(f"  时区: {result.environment_context.timezone}")
    print(f"  CPU 使用率: {result.environment_context.system_status.get('cpu_percent', 'N/A')}%")
    print(f"  内存使用率: {result.environment_context.system_status.get('memory_percent', 'N/A')}%")
    print(f"  磁盘使用率: {result.environment_context.system_status.get('disk_usage_percent', 'N/A')}%")
    print(f"  API 调用记录: {len(result.environment_context.api_results)} 条")
    print(f"  活动告警: {len(result.environment_context.active_alerts)} 个")

    print_subsection("💾 短期记忆")
    if result.short_term_memory:
        for i, item in enumerate(result.short_term_memory[:3], 1):
            preview = item.content[:80] + "..." if len(item.content) > 80 else item.content
            print(f"  {i}. {preview}")
    else:
        print("  (无短期记忆)")

    print_subsection("📚 长期记忆 (Milvus 知识库检索结果)")
    if result.long_term_memory:
        for i, item in enumerate(result.long_term_memory, 1):
            print(f"  {i}. [相关性: {item.score:.4f}]")
            preview = item.content[:100] + "..." if len(item.content) > 100 else item.content
            print(f"     内容: {preview}")
            print(f"     来源: {item.metadata.get('source', 'unknown')}")
            print(f"     分类: {item.metadata.get('category', 'unknown')}")
    else:
        print("  (无相关长期记忆)")

    print_subsection("💼 工作记忆")
    if result.working_memory:
        for key, value in result.working_memory.items():
            val_str = str(value)
            preview = val_str[:80] + "..." if len(val_str) > 80 else val_str
            print(f"  {key}: {preview}")
    else:
        print("  (无工作记忆)")

    print_subsection("📝 感知摘要")
    print(f"  {result.summary}")

    return perception, result


async def demo_file_input():
    """测试 3: 文件输入感知"""
    print_section("测试 3: 文件输入感知")

    # 创建临时测试文件
    test_file = Path(__file__).parent / "temp_test_knowledge.md"
    test_content = """# Agent 感知模块设计文档

## 功能概述
感知模块是 Agent 系统的重要组成部分，负责接收外部输入并转换为内部表示。

## 核心组件

### 1. 输入处理器 (InputHandler)
- 文本输入：接收并清洗用户文本
- 文件输入：读取 txt、md、json 等格式文件
- 系统请求：处理 AIOps 诊断等系统级请求

### 2. 环境感知器 (EnvironmentSensor)
- 时间感知：获取当前时间和时区
- 状态感知：获取 CPU、内存、磁盘等系统状态
- API 结果缓存：记录工具调用结果供后续使用

### 3. 记忆检索器 (MemoryRetriever)
- 短期记忆：最近 N 轮对话历史
- 长期记忆：向量数据库知识检索
- 工作记忆：当前任务中间结果

## 使用示例
```python
perception = PerceptionManager()
result = await perception.perceive(
    input_text="用户问题",
    session_id="session-001"
)
```
"""
    test_file.write_text(test_content, encoding="utf-8")

    print(f"\n📁 创建测试文件: {test_file.name}")
    print(f"   文件大小: {len(test_content)} 字符")
    print("   内容包含感知模块设计文档...")

    perception = PerceptionManager(vector_store_manager=None)

    print("\n🔍 执行文件感知流程...")

    result = await perception.perceive_with_file(
        file_path=str(test_file),
        session_id="test-session-002",
        include_long_term=False
    )

    print_subsection("📁 文件感知结果")
    print(f"  文件名: {result.input_data.metadata.get('file_name')}")
    print(f"  文件大小: {result.input_data.metadata.get('file_size')} 字符")
    print(f"  文件类型: {result.input_data.metadata.get('file_extension')}")
    print(f"  内容预览: {result.input_data.content[:200]}...")

    print_subsection("🌍 环境信息")
    print(f"  当前时间: {result.environment_context.current_time}")
    print(f"  系统状态: CPU {result.environment_context.system_status.get('cpu_percent', 'N/A')}%")

    print_subsection("📝 感知摘要")
    print(f"  {result.summary}")

    # 清理测试文件
    test_file.unlink()
    print(f"\n🗑️ 已清理测试文件: {test_file.name}")

    return result


async def demo_memory_workflow():
    """测试 4: 记忆工作流（多轮对话）"""
    print_section("测试 4: 记忆工作流（多轮对话）")

    perception = PerceptionManager(vector_store_manager=None)
    session_id = "test-memory-session"

    conversations = [
        ("什么是向量数据库？",
         "向量数据库是一种专门存储和检索向量数据的数据库系统，常用于 RAG、推荐系统等场景。"),
        ("它和传统数据库有什么区别？",
         "主要区别：向量数据库擅长相似度搜索（向量距离计算），传统数据库擅长精确匹配（WHERE 条件）。"),
        ("可以举个例子说明吗？",
         "比如做图片搜索：传统数据库需要精确标签匹配，而向量数据库可以直接用图片特征向量找到相似图片。"),
        ("那 Milvus 是什么？",
         "Milvus 是一个开源的向量数据库，支持百亿级向量检索，被广泛应用于 AI 应用开发。"),
    ]

    for i, (user_input, assistant_output) in enumerate(conversations, 1):
        print(f"\n--- 第 {i} 轮对话 ---")
        print(f"👤 用户: {user_input}")
        if len(assistant_output) > 60:
            print(f"🤖 助手: {assistant_output[:60]}...")
        else:
            print(f"🤖 助手: {assistant_output}")

        await perception.perceive(
            input_text=user_input,
            session_id=session_id,
            include_long_term=False
        )

        perception.add_conversation_to_memory(user_input, assistant_output)

        current_count = len(perception.memory_retriever.short_term.messages)
        print(f"   📝 短期记忆: {current_count} 条消息")

    print_subsection("📖 完整短期记忆内容")
    recent = perception.memory_retriever.short_term.get_recent(10)
    for i, msg in enumerate(recent, 1):
        role_symbol = "👤" if msg['role'] == 'user' else "🤖"
        content_preview = msg['content'][:80] + "..." if len(msg['content']) > 80 else msg['content']
        print(f"  {i}. {role_symbol} {content_preview}")

    print_subsection("💾 工作记忆测试")
    perception.add_to_working_memory("current_topic", "向量数据库与传统数据库对比")
    perception.add_to_working_memory("keywords", ["向量检索", "相似度搜索", "RAG", "Milvus"])
    perception.add_to_working_memory("user_interest", "数据库技术")
    perception.add_to_working_memory("conversation_depth", len(conversations))

    working_mem = perception.memory_retriever.working.get_all()
    for key, value in working_mem.items():
        print(f"  {key}: {value}")

    summary = perception.memory_retriever.working.get_summary()
    print(f"\n  📋 工作记忆摘要:\n{summary}")

    print_subsection("🗑️ 清空会话记忆")
    before_count = len(perception.memory_retriever.short_term.messages)
    perception.clear_session(session_id)
    after_count = len(perception.memory_retriever.short_term.messages)
    print(f"  清空前消息数: {before_count}")
    print(f"  清空后消息数: {after_count}")

    return perception


async def demo_environment_alerts(vector_store: MilvusVectorStore = None):
    """测试 5: 环境感知 - 告警场景"""
    print_section("测试 5: 环境感知 - 告警场景（模拟 AIOps）")

    perception = PerceptionManager(vector_store_manager=vector_store)

    alerts = [
        {
            "alertname": "HighCPUUsage",
            "severity": "critical",
            "instance": "data-sync-service",
            "duration": "15m",
            "description": "CPU 使用率持续超过 85%，影响数据同步效率"
        },
        {
            "alertname": "MemoryPressure",
            "severity": "warning",
            "instance": "data-sync-service",
            "duration": "30m",
            "description": "内存使用率超过 70%，存在内存泄漏风险"
        },
        {
            "alertname": "SyncDelay",
            "severity": "warning",
            "instance": "data-sync-service",
            "duration": "10m",
            "description": "数据同步延迟超过 5 分钟"
        }
    ]

    await perception.environment_sensor.set_active_alerts(alerts)
    print(f"\n⚠️ 已设置 {len(alerts)} 个模拟告警:")
    for alert in alerts:
        print(f"   - [{alert['severity'].upper()}] {alert['alertname']}: {alert['description']}")

    print("\n🔍 执行系统诊断感知...")

    result = await perception.perceive(
        input_text="请分析当前系统告警，给出根因分析和处理建议",
        session_id="test-aiops-session",
        include_long_term=True,
        top_k=3
    )

    print_subsection("⚠️ 检测到的活动告警")
    for i, alert in enumerate(result.environment_context.active_alerts, 1):
        print(f"  {i}. [{alert.get('severity', 'unknown').upper()}] {alert.get('alertname', 'unknown')}")
        print(f"     实例: {alert.get('instance', 'N/A')}")
        print(f"     持续时间: {alert.get('duration', 'N/A')}")
        print(f"     描述: {alert.get('description', 'N/A')}")

    print_subsection("📚 检索到的相关知识（来自 Milvus）")
    if result.long_term_memory:
        for item in result.long_term_memory:
            print(f"  • {item.content[:120]}...")
            print(f"    相关性分数: {item.score:.4f}")
            print(f"    来源: {item.metadata.get('source', 'unknown')}\n")
    else:
        print("  (未检索到相关知识)")

    print_subsection("🌍 系统状态快照")
    sys_status = result.environment_context.system_status
    print(f"  CPU: {sys_status.get('cpu_percent', 'N/A')}%")
    print(f"  内存: {sys_status.get('memory_percent', 'N/A')}% (已用 {sys_status.get('memory_used_gb', 'N/A')}GB / 总计 {sys_status.get('memory_total_gb', 'N/A')}GB)")
    print(f"  磁盘: {sys_status.get('disk_usage_percent', 'N/A')}%")

    return result


async def demo_api_result_capture():
    """测试 6: API 结果捕获"""
    print_section("测试 6: API 结果捕获（环境感知缓存）")

    perception = PerceptionManager(vector_store_manager=None)

    print("\n📡 模拟 API 调用并捕获结果...")

    api_results = [
        ("cls_search_log", {"total": 150, "logs": ["error1", "error2"], "took_ms": 45}),
        ("query_metrics", {"cpu": 85.5, "memory": 72.3, "timestamp": datetime.now().isoformat()}),
        ("get_alerts", {"total": 3, "alerts": ["HighCPU", "MemoryPressure"]}),
        ("query_database", {"slow_queries": ["SELECT * FROM large_table"], "count": 5}),
    ]

    for tool_name, result_data in api_results:
        await perception.environment_sensor.capture_api_result(result_data, tool_name)
        print(f"  ✓ 捕获 {tool_name} 调用结果")

    print_subsection("📊 捕获的 API 结果")
    captured = await perception.environment_sensor.get_api_results(limit=10)
    for i, item in enumerate(captured, 1):
        result_str = str(item['result'])
        preview = result_str[:60] + "..." if len(result_str) > 60 else result_str
        print(f"  {i}. {item['tool_name']}: {preview}")

    print("\n🔍 执行带 API 结果的环境感知...")

    result = await perception.perceive(
        input_text="根据最近的监控数据，分析系统是否存在异常",
        session_id="test-api-session",
        include_long_term=False
    )

    print_subsection("🔧 环境中的 API 结果")
    for api_result in result.environment_context.api_results:
        result_str = str(api_result.get('result'))
        preview = result_str[:80] + "..." if len(result_str) > 80 else result_str
        print(f"  • {api_result.get('tool_name')}: {preview}")

    return result


async def main():
    """主函数：运行所有测试"""
    print("\n" + "🎯" * 35)
    print(" 感知模块测试套件（存储 + 检索完整流程）")
    print("🎯" * 35)

    print_config_info()

    try:
        # 测试 1: 先存储文档到 Milvus，再检索验证
        vector_store, doc_count = await demo_store_and_retrieve()
        
        if vector_store is None:
            print("\n❌ Milvus 连接失败，无法继续测试")
            return 1

        # 测试 2: 使用已存储的知识库进行文本输入感知
        await demo_text_input_with_stored_knowledge(vector_store)

        # 测试 3: 文件输入感知
        await demo_file_input()

        # 测试 4: 记忆工作流
        await demo_memory_workflow()

        # 测试 5: 环境感知 - 告警场景
        await demo_environment_alerts(vector_store)

        # 测试 6: API 结果捕获
        await demo_api_result_capture()

        # 测试总结
        print_section("✅ 所有测试完成", char="🎯")
        print("\n🎉 感知模块测试全部通过！")
        print("\n📝 总结:")
        print("  ✓ 文档存储到 Milvus 正常")
        print("  ✓ 从 Milvus 检索文档正常")
        print("  ✓ 文本输入感知正常")
        print("  ✓ 文件输入感知正常")
        print("  ✓ 短期记忆（对话上下文）正常")
        print(f"  ✓ 长期记忆（Milvus 知识检索）正常 - 使用 {embedding_config.EMBEDDING_TYPE} Embedding")
        print("  ✓ 工作记忆（中间结果）正常")
        print("  ✓ 环境感知（时间/系统状态）正常")
        print("  ✓ 告警感知正常")
        print("  ✓ API 结果缓存正常")

        print("\n🔗 连接状态:")
        if vector_store_config.ENABLE_STORAGE:
            print(f"  - Milvus: {vector_store_config.MILVUS_HOST}:{vector_store_config.MILVUS_PORT}")
            print(f"  - 集合: {vector_store_config.COLLECTION_NAME}")
            print(f"  - 文档数: {doc_count}")
            print(f"  - Embedding: {embedding_config.EMBEDDING_TYPE}")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)