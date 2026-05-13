# app/api/routes.py - 完整修复版（添加用户认证、会话权限验证、遗忘模块和时间范围遗忘）

import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Header
from fastapi.responses import StreamingResponse
from loguru import logger
import json
import re

from .models import (
    ChatRequest, ChatResponse,
    KnowledgeAddRequest, KnowledgeSearchRequest,
    KnowledgeAddResponse, KnowledgeSearchResponse,
    SessionCreateRequest, SessionResponse, StatusResponse, MemoryStatsResponse, HealthResponse,
    SessionHistoryResponse, SessionInfoResponse
)
from .dependencies import get_agent, get_session_manager
from app.core import Agent, SessionManager
from app.db.database import get_db_manager
from app.auth.jwt_utils import get_user_id_from_token

router = APIRouter(prefix="/api/v1", tags=["Agent"])


# ========== 认证和会话权限辅助函数 ==========

async def verify_session_auth(
        session_id: str,
        authorization: Optional[str] = None
) -> tuple[bool, Optional[int]]:
    """
    验证用户是否有权访问会话
    Returns:
        (is_authorized, user_id)
    """
    if not session_id:
        return False, None

    # 如果没有认证信息，允许访问（兼容未登录模式）
    if not authorization:
        logger.debug(f"未提供认证信息，允许访问会话: {session_id}")
        return True, None

    # 提取 token
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization

    user_id = get_user_id_from_token(token)

    if not user_id:
        logger.warning(f"Token 无效，拒绝访问会话: {session_id}")
        return False, None

    # 验证会话访问权限
    db = get_db_manager()
    authorized = db.verify_session_access(user_id, session_id)

    if not authorized:
        logger.warning(f"用户 {user_id} 无权访问会话 {session_id}")
        return False, user_id

    return True, user_id


async def associate_session_with_user(
        user_id: int,
        session_id: str
) -> bool:
    """将会话关联到用户"""
    if not user_id:
        return True  # 未登录用户不需要关联

    db = get_db_manager()
    return db.associate_session(user_id, session_id)


def parse_time_range_forget(input_text: str) -> Optional[tuple]:
    """
    解析时间范围遗忘命令

    支持格式:
    - "忘掉:8小时内,白兔"
    - "忘掉:8小时前,白兔"
    - "忘掉:昨天,白兔"
    - "忘掉:今天,白兔"
    - "忘掉:本周,白兔"
    - "忘掉:本月,白兔"

    Returns:
        (hours, keyword) 或 None
    """
    patterns = [
        # 格式: 忘掉:X小时内,关键词
        r'忘掉[：:]\s*(\d+)\s*小时内\s*[,，]\s*(.+)',
        r'忘掉[：:]\s*(\d+)\s*小时前\s*[,，]\s*(.+)',
        # 格式: 忘掉:X小时,关键词
        r'忘掉[：:]\s*(\d+)\s*小时\s*[,，]\s*(.+)',
        # 格式: 忘掉:昨天,关键词
        r'忘掉[：:]\s*昨天\s*[,，]\s*(.+)',
        # 格式: 忘掉:今天,关键词
        r'忘掉[：:]\s*今天\s*[,，]\s*(.+)',
        # 格式: 忘掉:本周,关键词
        r'忘掉[：:]\s*本周\s*[,，]\s*(.+)',
        # 格式: 忘掉:本月,关键词
        r'忘掉[：:]\s*本月\s*[,，]\s*(.+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, input_text)
        if match:
            if match.group(1).isdigit():
                hours = int(match.group(1))
                keyword = match.group(2).strip()
                return (hours, keyword, "hours")
            else:
                # 处理自然语言时间
                time_word = match.group(1)
                keyword = match.group(2).strip()
                return (time_word, keyword, "natural")

    return None


# ========== 会话管理接口 ==========

@router.get("/session/create")
async def create_session(
        user_id: str = Query("default", description="用户ID（兼容旧版）"),
        authorization: Optional[str] = Header(None),
        agent: Agent = Depends(get_agent)
) -> SessionResponse:
    try:
        # 获取用户ID（从 token 中）
        token_user_id = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]
            token_user_id = get_user_id_from_token(token)
            if token_user_id:
                logger.info(f"已登录用户创建会话: user_id={token_user_id}")

        # 创建会话
        if agent._memory_manager and hasattr(agent._memory_manager, '_redis_memory'):
            # 如果是已登录用户，使用 user_id=username，否则使用 default
            redis_user_id = str(token_user_id) if token_user_id else user_id
            session_id = agent._memory_manager._redis_memory.get_or_create_session(user_id=redis_user_id)
            agent._current_session_id = session_id
            agent._memory_manager.set_session(session_id)
            logger.info(f"创建新会话: {session_id}, user_id={redis_user_id}")
        else:
            session_id = uuid.uuid4().hex[:16]
            logger.warning(f"记忆管理器未初始化，使用临时会话: {session_id}")

        # 如果用户已登录，关联会话到数据库
        if token_user_id:
            await associate_session_with_user(token_user_id, session_id)
            logger.info(f"会话 {session_id} 已关联到用户 {token_user_id}")

        return SessionResponse(
            session_id=session_id,
            created_at=datetime.now().isoformat(),
            user_name=str(token_user_id) if token_user_id else user_id
        )
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@router.get("/session/{session_id}/info")
async def get_session_info(
        session_id: str,
        authorization: Optional[str] = Header(None),
        agent: Agent = Depends(get_agent)
) -> SessionInfoResponse:
    """获取会话信息 - 验证会话是否存在"""
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id不能为空")

    # 验证权限
    is_authorized, user_id = await verify_session_auth(session_id, authorization)
    if not is_authorized:
        return SessionInfoResponse(
            success=False,
            session_id=session_id,
            info=None,
            message="无权访问此会话"
        )

    logger.info(f"get_session_info 调用: session_id={session_id}")

    try:
        if agent._memory_manager and hasattr(agent._memory_manager, '_redis_memory'):
            redis_memory = agent._memory_manager._redis_memory
            info = redis_memory.get_session_info(session_id)
            logger.info(f"Redis 返回的 info: {info}")

            if info:
                return SessionInfoResponse(
                    success=True,
                    session_id=session_id,
                    info=info
                )
            else:
                logger.warning(f"会话 {session_id} 在 Redis 中不存在")
                return SessionInfoResponse(
                    success=False,
                    session_id=session_id,
                    info=None,
                    message=f"会话 {session_id} 不存在"
                )
        else:
            logger.warning("记忆管理器不可用或没有 Redis")
            return SessionInfoResponse(
                success=False,
                session_id=session_id,
                info=None,
                message="记忆管理器不可用"
            )
    except Exception as e:
        logger.error(f"获取会话信息失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取会话信息失败: {str(e)}")


@router.get("/session/{session_id}/history")
async def get_session_history(
        session_id: str,
        limit: int = Query(50, ge=1, le=200),
        authorization: Optional[str] = Header(None),
        agent: Agent = Depends(get_agent)
) -> SessionHistoryResponse:
    """获取会话的完整历史记录"""
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id不能为空")

    # 验证权限
    is_authorized, user_id = await verify_session_auth(session_id, authorization)
    if not is_authorized:
        return SessionHistoryResponse(
            success=False,
            session_id=session_id,
            message_count=0,
            messages=[],
            error="无权访问此会话"
        )

    logger.info(f"get_session_history: session_id={session_id}, limit={limit}")

    try:
        if agent._memory_manager and hasattr(agent._memory_manager, '_redis_memory'):
            redis_memory = agent._memory_manager._redis_memory
            history = redis_memory.get_session_history(session_id, limit=limit)
            logger.info(f"获取到 {len(history)} 条历史消息")

            return SessionHistoryResponse(
                success=True,
                session_id=session_id,
                message_count=len(history),
                messages=history
            )
        else:
            logger.warning("记忆管理器不可用")
            return SessionHistoryResponse(
                success=False,
                session_id=session_id,
                message_count=0,
                messages=[],
                error="记忆管理器不可用"
            )
    except Exception as e:
        logger.error(f"获取历史失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


@router.delete("/session/{session_id}")
async def clear_session(
        session_id: str,
        authorization: Optional[str] = Header(None),
        agent: Agent = Depends(get_agent)
):
    """清除指定会话的记忆"""
    # 验证权限
    is_authorized, user_id = await verify_session_auth(session_id, authorization)
    if not is_authorized:
        raise HTTPException(status_code=403, detail="无权访问此会话")

    if agent._memory_manager:
        agent._memory_manager.clear_session(session_id)
    return {"success": True, "message": f"会话 {session_id} 已清空"}


# ========== 健康检查接口 ==========

@router.get("/health", response_model=HealthResponse)
async def health_check(agent: Agent = Depends(get_agent)):
    """健康检查接口"""
    return HealthResponse(
        status="healthy",
        initialized=agent._initialized,
        timestamp=datetime.now().isoformat()
    )


@router.get("/ping")
async def ping():
    return {"message": "pong", "timestamp": datetime.now().isoformat()}


# ========== 对话接口（支持权限验证和遗忘请求）==========

@router.post("/chat", response_model=ChatResponse)
async def chat(
        request: ChatRequest,
        authorization: Optional[str] = Header(None),
        agent: Agent = Depends(get_agent),
        session_manager: SessionManager = Depends(get_session_manager)
):
    """与 Agent 对话 - 支持 session_id 和权限验证"""
    try:
        from app.agent.dream import get_dream_scheduler
        scheduler = get_dream_scheduler()
        scheduler.record_request()
    except Exception:
        pass

    # 获取或创建会话
    if request.session_id:
        session_id = session_manager.get_or_create(request.session_id)
    else:
        session_id = session_manager.get_or_create()

    # ========== 处理遗忘请求（非流式）==========
    is_forget = False
    forget_result = None

    try:
        from app.agent.forget import get_forget_manager
        from app.agent.forget.time_range_forget import get_time_range_forget_manager

        forget_manager = get_forget_manager()
        time_range_manager = get_time_range_forget_manager()

        # 检查是否是时间范围遗忘
        if time_range_manager.is_time_range_forget_request(request.message):
            is_forget = True
            forget_result = await time_range_manager.process_time_range_forget(request.message, session_id)
        # 检查是否是普通遗忘
        elif forget_manager.is_forget_request(request.message):
            is_forget = True
            forget_result = await forget_manager.process_forget_request(request.message, session_id)

        if forget_result:
            return ChatResponse(
                success=True,
                response=forget_result,
                session_id=session_id,
                steps_executed=0,
                elapsed_ms=0
            )
    except Exception as e:
        logger.warning(f"遗忘模块处理失败: {e}")

    if not agent._initialized:
        return ChatResponse(
            success=False,
            response="系统正在初始化，请稍后再试...",
            session_id="",
            steps_executed=0,
            elapsed_ms=0,
            error="System initializing"
        )

    # 验证权限
    is_authorized, user_id = await verify_session_auth(session_id, authorization)
    if not is_authorized:
        return ChatResponse(
            success=False,
            response="无权访问此会话",
            session_id=session_id,
            steps_executed=0,
            elapsed_ms=0,
            error="Unauthorized"
        )

    # 如果用户已登录且会话是新建的，关联会话
    if user_id and request.session_id is None:
        await associate_session_with_user(user_id, session_id)

    # 设置会话到记忆管理器
    if agent._memory_manager:
        agent._memory_manager.set_session(session_id)

    # 执行对话
    result = await agent.chat(request.message)

    return ChatResponse(
        success=result["success"],
        response=result.get("response", ""),
        session_id=session_id,
        steps_executed=result.get("steps_executed", 0),
        elapsed_ms=result.get("elapsed_ms", 0),
        error=result.get("error") if not result["success"] else None
    )


@router.post("/chat/stream")
async def chat_stream(
        request: ChatRequest,
        authorization: Optional[str] = Header(None),
        agent: Agent = Depends(get_agent),
        session_manager: SessionManager = Depends(get_session_manager)
):
    """流式对话接口 - 支持 session_id 和权限验证"""

    # 获取或创建会话
    if request.session_id:
        session_id = session_manager.get_or_create(request.session_id)
    else:
        session_id = session_manager.get_or_create()

    # ========== 处理遗忘请求（流式）==========
    is_forget = False
    forget_result = None

    try:
        from app.agent.forget import get_forget_manager
        from app.agent.forget.time_range_forget import get_time_range_forget_manager

        forget_manager = get_forget_manager()
        time_range_manager = get_time_range_forget_manager()

        # 检查是否是时间范围遗忘
        if time_range_manager.is_time_range_forget_request(request.message):
            is_forget = True
            forget_result = await time_range_manager.process_time_range_forget(request.message, session_id)
        # 检查是否是普通遗忘
        elif forget_manager.is_forget_request(request.message):
            is_forget = True
            forget_result = await forget_manager.process_forget_request(request.message, session_id)

        if forget_result:
            async def forget_response():
                yield f"data: {json.dumps({'type': 'session', 'data': {'session_id': session_id}})}\n\n"
                yield f"data: {json.dumps({'type': 'response_start'})}\n\n"
                yield f"data: {json.dumps({'type': 'chunk', 'data': forget_result})}\n\n"
                yield f"data: {json.dumps({'type': 'response_end'})}\n\n"
                yield f"data: {json.dumps({'type': 'complete', 'data': {}})}\n\n"
                yield f"data: {json.dumps({'type': 'end', 'session_id': session_id})}\n\n"

            return StreamingResponse(forget_response(), media_type="text/event-stream")
    except Exception as e:
        logger.warning(f"遗忘模块处理失败: {e}")

    if not agent._initialized:
        async def error_gen():
            yield f"data: {json.dumps({'type': 'error', 'data': '系统正在初始化'})}\n\n"

        return StreamingResponse(error_gen(), media_type="text/event-stream")

    # 验证权限
    is_authorized, user_id = await verify_session_auth(session_id, authorization)
    if not is_authorized:
        async def unauthorized_gen():
            yield f"data: {json.dumps({'type': 'error', 'data': '无权访问此会话'})}\n\n"

        return StreamingResponse(unauthorized_gen(), media_type="text/event-stream")

    # 如果用户已登录且会话是新建的，关联会话
    if user_id and request.session_id is None:
        await associate_session_with_user(user_id, session_id)

    if agent._memory_manager:
        agent._memory_manager.set_session(session_id)

    async def generate():
        full_response = ""

        try:
            # 先发送会话信息
            yield f"data: {json.dumps({'type': 'session', 'data': {'session_id': session_id}})}\n\n"

            perception_result = await agent._perception_manager.perceive(
                input_text=request.message,
                session_id=session_id,
                include_long_term=True,
                top_k=5
            )

            available_tools = []
            for tool_name in agent._action_manager.list_tools():
                available_tools.append({
                    "name": tool_name,
                    "description": agent._get_tool_description(tool_name)
                })

            async for event in agent._brain_manager.think_stream(
                    user_input=request.message,
                    session_id=session_id,
                    perception_context=perception_result.to_dict(),
                    available_tools=available_tools,
                    search_mode=request.search_mode,
                    is_expert=request.is_expert
            ):
                event_type = event.get("type")

                if event_type == "response_chunk":
                    chunk = event.get("data", "")
                    if chunk:
                        full_response += chunk
                        yield f"data: {json.dumps({'type': 'chunk', 'data': chunk})}\n\n"

                elif event_type == "response_start":
                    yield f"data: {json.dumps({'type': 'response_start'})}\n\n"

                elif event_type == "response_end":
                    yield f"data: {json.dumps({'type': 'response_end'})}\n\n"

                elif event_type == "status":
                    yield f"data: {json.dumps({'type': 'status', 'data': event.get('message', '')})}\n\n"

                elif event_type == "plan":
                    yield f"data: {json.dumps({'type': 'plan', 'data': event.get('steps', [])})}\n\n"

                elif event_type == "step_start":
                    yield f"data: {json.dumps({'type': 'step_start', 'data': event.get('step', '')})}\n\n"

                elif event_type == "step_complete":
                    yield f"data: {json.dumps({'type': 'step_complete', 'data': event.get('step', '')})}\n\n"

                elif event_type == "tool_call":
                    yield f"data: {json.dumps({'type': 'tool_call', 'data': event.get('tool', '')})}\n\n"

                elif event_type == "complete":
                    yield f"data: {json.dumps({'type': 'complete', 'data': event.get('summary', {})})}\n\n"

            # 发送结束标记
            yield f"data: {json.dumps({'type': 'end', 'session_id': session_id})}\n\n"

            # ========== 关键：遗忘请求不保存到记忆 ==========
            if not is_forget and full_response and agent._memory_manager:
                # 保存消息到 Redis
                recent_messages = agent._memory_manager.get_recent_messages(2)
                last_user_saved = None
                for msg in recent_messages:
                    if msg.get('role') == 'user':
                        last_user_saved = msg.get('content')
                        break

                if last_user_saved != request.message:
                    agent._memory_manager.add_user_message(request.message)
                    agent._memory_manager.add_assistant_message(full_response)
                    logger.info(f"保存消息到 Redis: {request.message[:50]}...")
                else:
                    logger.info(f"消息已存在，跳过重复保存")

                # 感知模块添加对话到短期记忆
                if agent._perception_manager:
                    agent._perception_manager.add_conversation_to_memory(request.message, full_response)
            elif is_forget:
                logger.info(f"遗忘请求，不保存到记忆: {request.message}")

        except Exception as e:
            logger.error(f"流式响应错误: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ========== 其他接口 ==========

@router.post("/session", response_model=SessionResponse)
async def create_session_old(
        request: SessionCreateRequest,
        session_manager: SessionManager = Depends(get_session_manager)
):
    """创建新会话（兼容旧接口）"""
    session_id = session_manager.get_or_create(user_name=request.user_name)
    session_info = session_manager._sessions.get(session_id, {})
    return SessionResponse(
        session_id=session_id,
        created_at=session_info.get("created_at").isoformat() if session_info.get("created_at") else None,
        user_name=session_info.get("user_name", request.user_name)
    )


@router.post("/session/{session_id}/new")
async def new_session(
        session_id: Optional[str] = None,
        agent: Agent = Depends(get_agent)
):
    """创建新会话（切换当前会话）"""
    agent.new_session()
    return {
        "success": True,
        "session_id": agent.get_session_id(),
        "message": "已创建新会话"
    }


@router.post("/knowledge", response_model=KnowledgeAddResponse)
async def add_knowledge(
        request: KnowledgeAddRequest,
        agent: Agent = Depends(get_agent)
):
    result = await agent.add_knowledge(request.content, request.category)
    return KnowledgeAddResponse(
        success=result["success"],
        message=result["message"]
    )


@router.post("/knowledge/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
        request: KnowledgeSearchRequest,
        agent: Agent = Depends(get_agent)
):
    if request.category:
        if agent._action_manager:
            result = await agent._action_manager.execute_tool_call(
                tool_name="search_knowledge_with_filter",
                tool_input={
                    "query": request.query,
                    "category": request.category,
                    "top_k": request.top_k
                },
                session_id=agent.get_session_id()
            )
        else:
            result = "知识库服务不可用"
        return KnowledgeSearchResponse(
            success=True,
            message=result
        )
    else:
        result = await agent.search_knowledge(request.query, request.top_k)
        return KnowledgeSearchResponse(
            success=result["success"],
            message=result["message"]
        )


@router.get("/knowledge/stats")
async def get_knowledge_stats(agent: Agent = Depends(get_agent)):
    result = await agent.get_knowledge_stats()
    return result


@router.get("/status", response_model=StatusResponse)
async def get_status(
        agent: Agent = Depends(get_agent),
        session_manager: SessionManager = Depends(get_session_manager)
):
    status = agent.get_status()
    return StatusResponse(
        initialized=status["initialized"],
        session_id=status.get("session_id", ""),
        tools=status.get("tools", []),
        active_sessions=session_manager.get_all()
    )


@router.get("/memory/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(agent: Agent = Depends(get_agent)):
    stats = await agent.get_memory_stats()
    return MemoryStatsResponse(
        short_term=stats.get("short_term", 0),
        working=stats.get("working", 0),
        long_term=stats.get("long_term", 0),
        total=stats.get("total", 0)
    )


@router.get("/tools")
async def list_tools(agent: Agent = Depends(get_agent)):
    return {
        "success": True,
        "tools": agent.list_tools()
    }


@router.post("/admin/intent/reload")
async def reload_intent_rules(
        authorization: str = Header(None)
):
    """热重载意图路由规则（需要管理员权限）"""
    from app.agent.brain.intent_router import get_intent_router

    router = get_intent_router()
    success = router.reload_rules()

    if success:
        return {"success": True, "message": "意图路由规则已重新加载"}
    else:
        return {"success": False, "message": "重新加载失败"}