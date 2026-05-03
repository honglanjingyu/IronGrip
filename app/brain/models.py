# app/brain/models.py
"""大脑模块数据模型"""

from typing import List, Dict, Any, Optional, Literal, Annotated
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import operator


class BrainPhase(str, Enum):
    """大脑工作阶段"""
    INIT = "init"
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    RESPONDING = "responding"
    COMPLETED = "completed"


class ActionType(str, Enum):
    """动作类型"""
    TOOL_CALL = "tool_call"  # 调用工具
    DIRECT_ANSWER = "direct_answer"  # 直接回答
    DEFER = "defer"  # 暂不处理，等待更多信息


class Plan(BaseModel):
    """执行计划"""
    steps: List[str] = Field(default_factory=list, description="执行步骤列表")
    reasoning: str = Field(default="", description="制定计划的推理过程")
    created_at: datetime = Field(default_factory=datetime.now)


class Action(BaseModel):
    """决策动作"""
    type: ActionType = Field(..., description="动作类型")
    tool_name: Optional[str] = Field(None, description="工具名称（如果是工具调用）")
    tool_input: Optional[Dict[str, Any]] = Field(None, description="工具参数")
    answer: Optional[str] = Field(None, description="直接回答内容")
    reasoning: str = Field(default="", description="决策推理过程")


class ExecutionStep(BaseModel):
    """执行步骤记录"""
    step: str = Field(..., description="步骤描述")
    action: Action = Field(..., description="执行的动作")
    result: Optional[str] = Field(None, description="执行结果")
    success: bool = Field(default=False, description="是否成功")
    error: Optional[str] = Field(None, description="错误信息")
    timestamp: datetime = Field(default_factory=datetime.now)


class BrainResponse(BaseModel):
    """大脑最终响应"""
    answer: str = Field(..., description="最终回答")
    plan: Plan = Field(..., description="执行的计划")
    execution_history: List[ExecutionStep] = Field(default_factory=list, description="执行历史")
    confidence: float = Field(default=0.0, description="置信度")
    needs_more_info: bool = Field(default=False, description="是否需要更多信息")


class BrainState(BaseModel):
    """大脑状态（工作记忆）"""
    # 用户输入
    input: str = Field(default="", description="原始用户输入")
    session_id: str = Field(default="", description="会话ID")

    # 感知上下文（来自感知模块）
    perception_context: Dict[str, Any] = Field(default_factory=dict, description="感知上下文")

    # 计划和执行
    plan: List[str] = Field(default_factory=list, description="当前计划步骤")
    past_steps: Annotated[List[ExecutionStep], operator.add] = Field(
        default_factory=list,
        description="已执行的步骤历史"
    )

    # 工具相关
    available_tools: List[Dict[str, Any]] = Field(default_factory=list, description="可用工具列表")

    # 最终输出
    response: Optional[str] = Field(None, description="最终响应")

    # 状态控制
    phase: BrainPhase = Field(default=BrainPhase.INIT, description="当前阶段")
    max_iterations: int = Field(default=10, description="最大迭代次数")
    current_iteration: int = Field(default=0, description="当前迭代次数")

    def should_continue(self) -> bool:
        """判断是否应该继续执行"""
        # 已有响应
        if self.response:
            return False
        # 超过最大迭代次数
        if self.current_iteration >= self.max_iterations:
            return False
        # 计划为空
        if not self.plan and self.current_iteration > 0:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump(exclude={"available_tools"})