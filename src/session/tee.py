"""
TeeStream - 将终端输出同时写入原流和会话日志
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List


class TeeStream:
    """将 stdout/stderr 同时写入原流和会话日志，使会话日志包含终端全部输出"""

    def __init__(self, stream: Any, log_list: List[dict], role: str = "终端") -> None:
        self._stream = stream
        self._log_list = log_list
        self._role = role
        self._buffer = ""

    def write(self, data: str) -> int:
        n = self._stream.write(data)
        self._buffer += data
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._log_list.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "role": self._role,
                "content": line,
            })
        return n

    def flush(self) -> None:
        self._stream.flush()
        if self._buffer:
            self._log_list.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "role": self._role,
                "content": self._buffer.rstrip("\r"),
            })
            self._buffer = ""

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)
