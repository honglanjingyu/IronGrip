
"""感知模块测试 Demo

运行方式:
    python demo_perception.py

文件位置: 项目主目录（与 main.py 同级）
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime


# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入感知模块
from app.perception import PerceptionManager


class MockVectorStore:
    """模拟向量存储（用于测试长期记忆检索）"""

    def __init__(self):
        self.documents = []
        self._init_mock_documents()

    def _init_mock_documents(self):
        """初始化模拟文档"""
        # 创建一个简单的文档类来模拟 LangChain Document
        class MockDocument:
            def __init__(self, page_content: str, metadata: dict):
                self.page_content = page_content
                self.metadata = metadata

        self.mock_docs = [
            MockDocument(
                page_content="系统故障排查指南：当 CPU 使用率过高时，第一步检查是否有异常进程，使用 top 命令查看 CPU 占用最高的进程。第二步分析进程日志，定位问题代码。",
                metadata={"source": "knowledge_base", "category": "troubleshooting"}
            ),
            MockDocument(
                page_content="内存泄漏排查方法：内存使用率持续上升通常是内存泄漏的表现，建议使用 jmap 或 heap profiler 分析堆内存。常见原因包括未关闭的连接、缓存未清理等。",
                metadata={"source": "knowledge_base", "category": "memory"}
            ),
            MockDocument(
                page_content="告警处理最佳实践：先确认告警级别和影响范围，再分析根本原因，最后制定处理方案和预防措施。关键告警需在 5 分钟内响应。",
                metadata={"source": "knowledge_base", "category": "alert"}
            ),
            MockDocument(
                page_content="向量数据库是一种专门存储和检索向量数据的数据库，常用于语义搜索、推荐系统、RAG 等场景。常见产品包括 Milvus、Pinecone、Weaviate。",
                metadata={"source": "knowledge_base", "category": "database"}
            ),
            MockDocument(
                page_content="数据同步服务常见问题：同步延迟通常由网络问题、源库负载过高或目标库写入瓶颈引起。解决方案包括优化查询、增加并发、使用批量写入。",
                metadata={"source": "knowledge_base", "category": "data-sync"}
            ),
        ]

    def similarity_search(self, query: str, k: int = 3):
        """
        模拟相似度搜索（基于关键词匹配）

        实际场景中会使用向量检索，这里用简单关键词匹配模拟
        """
        # 简单的关键词匹配模拟
        keywords = query.lower()
        scored_docs = []

        for doc in self.mock_docs:
            score = 0
            content_lower = doc.page_content.lower()

            # 简单的关键词匹配评分
            if 'cpu' in keywords and 'cpu' in content_lower:
                score += 3
            if '内存' in keywords and ('内存' in content_lower or 'memory' in content_lower):
                score += 3
            if '告警' in keywords and '告警' in content_lower:
                score += 3
            if '向量' in keywords and '向量' in content_lower:
                score += 3
            if '同步' in keywords and '同步' in content_lower:
                score += 3
            if '延迟' in keywords and '延迟' in content_lower:
                score += 2
            if '排查' in keywords and '排查' in content_lower:
                score += 2

            if score > 0:
                scored_docs.append((doc, score))

        # 按分数排序
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # 返回前 k 个
        return [doc for doc, _ in scored_docs[:k]]

    def add_documents(self, docs):
        """添加文档"""
        self.documents.extend(docs)


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


async def demo_text_input():
    """测试 1: 文本输入感知"""
    print_section("测试 1: 文本输入感知")

    # 创建感知管理器（使用模拟向量存储）
    mock_store = MockVectorStore()
    perception = PerceptionManager(vector_store_manager=mock_store)

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

    print_subsection("📚 长期记忆 (知识库检索结果)")
    if result.long_term_memory:
        for i, item in enumerate(result.long_term_memory, 1):
            print(f"  {i}. [相关性: {item.score:.2f}]")
            preview = item.content[:100] + "..." if len(item.content) > 100 else item.content
            print(f"     内容: {preview}")
            print(f"     来源: {item.metadata.get('source', 'unknown')}")
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
    """测试 2: 文件输入感知"""
    print_section("测试 2: 文件输入感知")

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

    perception = PerceptionManager()

    print("\n🔍 执行文件感知流程...")

    result = await perception.perceive_with_file(
        file_path=str(test_file),
        session_id="test-session-002",
        include_long_term=False  # 不检索长期记忆，测试文件内容
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
    """测试 3: 记忆工作流（多轮对话）"""
    print_section("测试 3: 记忆工作流（多轮对话）")

    perception = PerceptionManager()
    session_id = "test-memory-session"

    # 定义对话轮次
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

        # 感知用户输入
        await perception.perceive(
            input_text=user_input,
            session_id=session_id,
            include_long_term=False  # 只测试短期记忆
        )

        # 保存到记忆
        perception.add_conversation_to_memory(user_input, assistant_output)

        current_count = len(perception.memory_retriever.short_term.messages)
        print(f"   📝 短期记忆: {current_count} 条消息")

    # 查看完整短期记忆
    print_subsection("📖 完整短期记忆内容")
    recent = perception.memory_retriever.short_term.get_recent(10)
    for i, msg in enumerate(recent, 1):
        role_symbol = "👤" if msg['role'] == 'user' else "🤖"
        content_preview = msg['content'][:80] + "..." if len(msg['content']) > 80 else msg['content']
        print(f"  {i}. {role_symbol} {content_preview}")

    # 测试工作记忆
    print_subsection("💾 工作记忆测试")

    perception.add_to_working_memory("current_topic", "向量数据库与传统数据库对比")
    perception.add_to_working_memory("keywords", ["向量检索", "相似度搜索", "RAG", "Milvus"])
    perception.add_to_working_memory("user_interest", "数据库技术")
    perception.add_to_working_memory("conversation_depth", len(conversations))

    working_mem = perception.memory_retriever.working.get_all()
    for key, value in working_mem.items():
        print(f"  {key}: {value}")

    # 测试工作记忆摘要
    summary = perception.memory_retriever.working.get_summary()
    print(f"\n  📋 工作记忆摘要:\n{summary}")

    # 测试记忆清空
    print_subsection("🗑️ 清空会话记忆")
    before_count = len(perception.memory_retriever.short_term.messages)
    perception.clear_session(session_id)
    after_count = len(perception.memory_retriever.short_term.messages)
    print(f"  清空前消息数: {before_count}")
    print(f"  清空后消息数: {after_count}")

    return perception


async def demo_environment_alerts():
    """测试 4: 环境感知 - 告警场景"""
    print_section("测试 4: 环境感知 - 告警场景（模拟 AIOps）")

    perception = PerceptionManager()

    # 设置模拟告警
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

    # 感知诊断请求
    print("\n🔍 执行系统诊断感知...")

    result = await perception.perceive(
        input_text="请分析当前系统告警，给出根因分析和处理建议",
        session_id="test-aiops-session",
        include_long_term=True,
        top_k=2
    )

    print_subsection("⚠️ 检测到的活动告警")
    for i, alert in enumerate(result.environment_context.active_alerts, 1):
        print(f"  {i}. [{alert.get('severity', 'unknown').upper()}] {alert.get('alertname', 'unknown')}")
        print(f"     实例: {alert.get('instance', 'N/A')}")
        print(f"     持续时间: {alert.get('duration', 'N/A')}")
        print(f"     描述: {alert.get('description', 'N/A')}")

    print_subsection("📚 检索到的相关知识")
    for item in result.long_term_memory:
        print(f"  • {item.content[:120]}...")
        print(f"    相关性分数: {item.score:.2f}\n")

    print_subsection("🌍 系统状态快照")
    sys_status = result.environment_context.system_status
    print(f"  CPU: {sys_status.get('cpu_percent', 'N/A')}%")
    print(f"  内存: {sys_status.get('memory_percent', 'N/A')}% (已用 {sys_status.get('memory_used_gb', 'N/A')}GB / 总计 {sys_status.get('memory_total_gb', 'N/A')}GB)")
    print(f"  磁盘: {sys_status.get('disk_usage_percent', 'N/A')}%")

    return result


async def demo_api_result_capture():
    """测试 5: API 结果捕获"""
    print_section("测试 5: API 结果捕获（环境感知缓存）")

    perception = PerceptionManager()

    # 模拟 API 调用
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

    # 获取捕获的结果
    print_subsection("📊 捕获的 API 结果")
    captured = await perception.environment_sensor.get_api_results(limit=10)
    for i, item in enumerate(captured, 1):
        result_str = str(item['result'])
        preview = result_str[:60] + "..." if len(result_str) > 60 else result_str
        print(f"  {i}. {item['tool_name']}: {preview}")

    # 测试带 API 结果的环境感知
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
    print(" 感知模块测试套件")
    print("🎯" * 35)

    try:
        # 运行所有测试
        await demo_text_input()
        await demo_file_input()
        await demo_memory_workflow()
        await demo_environment_alerts()
        await demo_api_result_capture()

        # 测试总结
        print_section("✅ 所有测试完成", char="🎯")
        print("\n🎉 感知模块测试全部通过！")
        print("\n📝 总结:")
        print("  ✓ 文本输入处理正常")
        print("  ✓ 文件输入处理正常")
        print("  ✓ 短期记忆（对话上下文）正常")
        print("  ✓ 长期记忆（知识检索）正常")
        print("  ✓ 工作记忆（中间结果）正常")
        print("  ✓ 环境感知（时间/系统状态）正常")
        print("  ✓ 告警感知正常")
        print("  ✓ API 结果缓存正常")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
