"""事件总线：解耦组件间通信，支持注册、发射、移除事件处理器。"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger(__name__)

EventHandler = Callable[[Any], None]


class EventBus:
    """事件总线，支持 on / emit / off 操作。"""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def on(self, event_type: str, handler: EventHandler) -> None:
        """注册事件处理器。"""
        self._handlers[event_type].append(handler)

    def off(self, event_type: str, handler: EventHandler) -> None:
        """移除指定事件处理器。"""
        handlers = self._handlers.get(event_type)
        if handlers is None:
            return
        try:
            handlers.remove(handler)
        except ValueError:
            pass

    def emit(self, event_type: str, data: Any = None) -> None:
        """发射事件，通知所有已注册的处理器。"""
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception:
                logger.exception("事件处理器异常: event_type=%s", event_type)

    def clear(self) -> None:
        """清空所有已注册的处理器。"""
        self._handlers.clear()