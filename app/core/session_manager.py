# app/core/session_manager.py
"""会话管理器"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional


class SessionManager:
    """会话管理器 - 管理多个会话"""

    def __init__(self):
        self._sessions: Dict[str, dict] = {}

    def get_or_create(self, session_id: str = None, user_name: str = "user") -> str:
        if session_id and session_id in self._sessions:
            return session_id
        new_session_id = session_id or str(uuid.uuid4())[:8]
        self._sessions[new_session_id] = {
            "session_id": new_session_id,
            "created_at": datetime.now(),
            "user_name": user_name
        }
        return new_session_id

    def get_all(self) -> List[str]:
        return list(self._sessions.keys())

    def get_session_info(self, session_id: str) -> Optional[dict]:
        return self._sessions.get(session_id)