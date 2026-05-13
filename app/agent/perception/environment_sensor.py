"""环境感知模块 - 获取当前状态信息"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from zoneinfo import ZoneInfo
from loguru import logger

from .models import EnvironmentContext


class EnvironmentSensor:
    """
    环境感知器

    功能：
    1. 获取当前时间、时区等基础信息
    2. 获取系统状态（CPU、内存等）
    3. 保存和检索 API 调用结果
    4. 管理活动告警
    """

    def __init__(self):
        self.default_timezone = "Asia/Shanghai"
        self._api_results_cache: List[Dict[str, Any]] = []
        self._active_alerts: List[Dict[str, Any]] = []
        logger.info("EnvironmentSensor 初始化完成")

    async def get_current_time(self, timezone: Optional[str] = None) -> str:
        """获取当前时间"""
        tz = timezone or self.default_timezone
        try:
            tz_info = ZoneInfo(tz)
            now = datetime.now(tz_info)
            return now.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.error(f"获取时间失败: {e}")
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            import psutil
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "memory_used_gb": round(psutil.virtual_memory().used / (1024 ** 3), 2),
                "memory_total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
                "disk_usage_percent": psutil.disk_usage('/').percent,
                "timestamp": datetime.now().isoformat()
            }
        except ImportError:
            logger.warning("psutil 未安装，返回模拟数据")
            return {
                "cpu_percent": 25.5,
                "memory_percent": 45.2,
                "memory_used_gb": 3.6,
                "memory_total_gb": 8.0,
                "disk_usage_percent": 60.0,
                "timestamp": datetime.now().isoformat()
            }

    async def capture_api_result(self, result: Dict[str, Any], tool_name: str) -> None:
        """记录 API 调用结果"""
        self._api_results_cache.append({
            "tool_name": tool_name,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        if len(self._api_results_cache) > 100:
            self._api_results_cache = self._api_results_cache[-50:]
        logger.debug(f"记录 API 结果: {tool_name}")

    async def get_api_results(self, tool_name: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """获取历史 API 调用结果"""
        results = self._api_results_cache
        if tool_name:
            results = [r for r in results if r.get("tool_name") == tool_name]
        return results[-limit:]

    async def set_active_alerts(self, alerts: List[Dict[str, Any]]) -> None:
        """设置活动告警"""
        self._active_alerts = alerts
        logger.info(f"更新活动告警: {len(alerts)} 个")

    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """获取活动告警"""
        return self._active_alerts

    async def scan_environment(self, session_id: str, timezone: Optional[str] = None) -> EnvironmentContext:
        """扫描完整环境信息"""
        logger.info(f"扫描环境信息: session={session_id}")

        current_time = await self.get_current_time(timezone)
        system_status = await self.get_system_status()
        active_alerts = await self.get_active_alerts()
        recent_api_results = await self.get_api_results(limit=5)

        return EnvironmentContext(
            current_time=current_time,
            timezone=timezone or self.default_timezone,
            system_status=system_status,
            api_results=recent_api_results,
            active_alerts=active_alerts
        )