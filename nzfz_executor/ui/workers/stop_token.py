"""协作式停止令牌（P2-05）。"""

from __future__ import annotations

import threading


class StopToken:
    """基于 threading.Event 的协作式停止标记。"""

    def __init__(self) -> None:
        self._event = threading.Event()

    def request_stop(self) -> None:
        self._event.set()

    def is_stop_requested(self) -> bool:
        return self._event.is_set()

    def reset(self) -> None:
        self._event.clear()
