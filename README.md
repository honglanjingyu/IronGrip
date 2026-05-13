# IronGrip

## 📖 简介

IronGrip 是一个功能完善的 AI Agent 系统，采用模块化架构设计，具备**感知、记忆、规划、行动**四大核心能力。系统支持多轮对话、长期记忆存储、工具调用、流式响应，并集成了用户认证与会话管理。

### 核心特性

- 🧠 **智能大脑** - Plan-Execute-Replan 执行模式，支持复杂任务分解与动态调整
- 💭 **实体记忆** - 自动提炼对话中的用户偏好、事实和知识洞察，持久化存储
- 🔌 **MCP 协议** - 统一工具注册与调用接口，易于扩展
- 🗄️ **多级记忆** - 短期记忆（Redis）+ 长期记忆（Milvus）+ 工作记忆
- 🔐 **用户认证** - JWT 认证 + PostgreSQL 用户/会话管理
- 🌊 **流式响应** - 支持 Server-Sent Events 实时输出
- 🔍 **混合检索** - 向量检索 + 关键词检索 + Rerank 重排序
- 🌐 **联网搜索** - 集成 SerpAPI，支持网络搜索
- 🧹 **遗忘机制** - 支持关键词遗忘和时间范围遗忘

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer (FastAPI)                   │
├─────────────────────────────────────────────────────────────┤
│  Perception │   Brain   │   Action   │   Memory   │   MCP   │
├─────────────┴───────────┴────────────┴────────────┴─────────┤
│  • Input Handler        • Planner        • Short-term (Redis)│
│  • Environment Sensor   • Executor       • Long-term (Milvus)│
│  • Memory Retriever     • Replanner      • Working (Memory)  │
│                          • Intent Router • Entity (File)     │
├─────────────────────────────────────────────────────────────┤
│                    Tools & Extensions                        │
│  • Web Search (SerpAPI)  • RAG (A2A)  • Time  • Forget      │
└─────────────────────────────────────────────────────────────┘
```

## 📁 项目结构

```
IronGrip/
├── run_api.py              # API 服务入口
├── run_mcp_server.py       # MCP 独立服务器
├── stop_api.py             # 停止服务脚本
├── app/
│   ├── agent/              # Agent 核心模块
│   │   ├── action/         # 行动模块（工具调用）
│   │   ├── brain/          # 大脑模块（规划/执行/重规划）
│   │   ├── dream/          # 做梦模块（实体记忆提炼）
│   │   ├── forget/         # 遗忘模块
│   │   ├── memory/         # 记忆模块（Redis/Milvus）
│   │   └── perception/     # 感知模块
│   ├── api/                # API 路由
│   ├── auth/               # JWT 认证
│   ├── db/                 # PostgreSQL 数据库
│   ├── mcp/                # MCP 协议实现
│   └── core/               # 核心类（Agent/SessionManager）
├── web/                    # Web 前端界面
├── entity_memory/          # 实体记忆存储目录
└── logs/                   # 日志目录
```

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Redis
- PostgreSQL
- Milvus（可选，用于长期记忆向量存储）

### 安装依赖

```bash
# 克隆项目
git clone https://github.com/yourusername/IronGrip.git
cd IronGrip

# 安装依赖
pip install -r requirements.txt
```

### 环境配置

配置 `.env` 文件

### 启动服务

```bash
# 启动 API 服务
python run_api.py --host 0.0.0.0 --port 8002 --reload

# 启动 MCP 服务器（可选，HTTP 模式）
python run_mcp_server.py --mode http --port 8003
```

## 📡 API 接口

### 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/auth/verify` | 验证 Token |

### 对话接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat` | 同步对话 |
| POST | `/api/v1/chat/stream` | 流式对话 |
| GET | `/api/v1/session/create` | 创建会话 |
| GET | `/api/v1/session/{id}/history` | 获取会话历史 |
| DELETE | `/api/v1/session/{id}` | 清除会话 |

### 知识库接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/knowledge` | 添加知识 |
| POST | `/api/v1/knowledge/search` | 搜索知识 |
| GET | `/api/v1/knowledge/stats` | 知识统计 |

### 工具接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/tools` | 列出所有工具 |
| GET | `/mcp/health` | MCP 健康检查 |

## 🔧 内置工具

| 工具名称 | 功能 | 示例 |
|---------|------|------|
| `web_search` | 联网搜索 | 搜索最新科技新闻 |
| `search_knowledge_base` | RAG 知识库检索 | 查询文档内容 |
| `get_current_time` | 获取当前时间 | 现在几点了？ |
| `query_entity_memory` | 查询实体记忆 | 我之前说过什么？ |
| `forget_memory` | 遗忘记忆 | 忘掉:python |
| `trigger_dream_now` | 立即整理记忆 | 整理记忆 |
| `get_dream_stats` | 查看记忆统计 | 记忆统计 |

## 💡 使用示例

### 同步对话

```bash
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，请介绍一下你自己",
    "session_id": "test-session"
  }'
```

### 流式对话

```javascript
const eventSource = new EventSource('/api/v1/chat/stream?message=你好');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'chunk') {
    console.log(data.data);
  }
};
```

### 遗忘指定内容

```
用户: 忘掉:python
助手: 🧹 已遗忘关于「python」的记忆：短期记忆 2 条，会话记忆 3 条，实体记忆 1 条
```

### 时间范围遗忘

```
用户: 忘掉:8小时内,python
助手: 🧹 已清除 3 条关于「python」的记忆（其中 2 条来自指定时间范围）
```

## ⚙️ 配置说明

### 意图路由配置 (`app/agent/brain/intent_rules.py`)

```python
# 快速匹配规则
FAST_RULES = {
    IntentType.SIMPLE: ["你好", "谢谢", "再见"],
    IntentType.HISTORY: ["问过什么", "之前问了"],
    IntentType.KNOWLEDGE: ["是什么", "解释一下"],
}

# 超短输入阈值
SHORT_INPUT_MAX_LENGTH = 5
```

### 做梦模块配置 (`app/agent/dream/config.py`)

```python
DREAM_INTERVAL_SECONDS = 600      # 10分钟检查一次
DREAM_IDLE_THRESHOLD_SECONDS = 30 # 空闲30秒后触发
DREAM_ON_STARTUP = False          # 启动时不做梦
```

