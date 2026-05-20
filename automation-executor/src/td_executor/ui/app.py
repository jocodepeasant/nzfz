"""GUI 主窗口。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from td_executor.ui.executor_bridge import ExecutorBridge


class ExecutorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("TD Executor - 塔防自动化执行器")
        self.geometry("1100x750")
        self.minsize(800, 500)

        self.bridge = ExecutorBridge()
        self._poll_id: str | None = None
        self._window_rect = None
        self._overlay = None

        self._build_ui()
        self._start_status_clock()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._init_tabs()

        self.status_frame = ttk.Frame(self, relief=tk.SUNKEN)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=(0, 5))

        self.status_label = ttk.Label(self.status_frame, text="状态: 空闲", width=20, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, padx=5)

        ttk.Separator(self.status_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=2)

        self.window_label = ttk.Label(self.status_frame, text="窗口: 未连接", width=30, anchor=tk.W)
        self.window_label.pack(side=tk.LEFT, padx=5)

        ttk.Separator(self.status_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=2)

        self.clock_label = ttk.Label(self.status_frame, text="", width=20, anchor=tk.E)
        self.clock_label.pack(side=tk.RIGHT, padx=5)

    def _init_tabs(self) -> None:
        from td_executor.ui.monitor_tab import MonitorTab
        from td_executor.ui.script_tab import ScriptTab
        from td_executor.ui.report_tab import ReportTab
        from td_executor.ui.preview_tab import PreviewTab

        self.monitor_tab = MonitorTab(self.notebook, self)
        self.notebook.add(self.monitor_tab, text=" 监控 ")

        self.script_tab = ScriptTab(self.notebook, self)
        self.notebook.add(self.script_tab, text=" 脚本 ")

        self.report_tab = ReportTab(self.notebook, self)
        self.notebook.add(self.report_tab, text=" 报告 ")

        self.preview_tab = PreviewTab(self.notebook, self)
        self.notebook.add(self.preview_tab, text=" 画面 ")

    def _start_status_clock(self) -> None:
        self._update_clock()

    def _update_clock(self) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        self.clock_label.config(text=now)
        self.after(1000, self._update_clock)

    def set_status(self, status: str) -> None:
        self.status_label.config(text=f"状态: {status}")

    def set_window_info(self, info: str) -> None:
        self.window_label.config(text=f"窗口: {info}")

    @property
    def window_rect(self):
        return self._window_rect

    @property
    def overlay(self):
        return self._overlay

    def connect_window(self, title_keyword: str) -> bool:
        from td_executor.runtime.window import find_game_window

        rect = find_game_window(title_keyword)
        if rect is None:
            self.set_window_info("未找到")
            return False
        self._window_rect = rect
        info = f"{rect.width}x{rect.height}"
        if rect.title:
            info = f"{rect.title} ({info})"
        self.set_window_info(info)
        self.preview_tab.set_window_rect(rect)
        self.focus_force()
        from td_executor.runtime.overlay import WindowOverlay
        self._overlay = WindowOverlay()
        self._overlay.show(rect.hwnd, window_info=info)
        return True

    def connect_window_by_hwnd(self, hwnd: int) -> bool:
        from td_executor.runtime.window import get_window_rect

        rect = get_window_rect(hwnd)
        if rect is None:
            self.set_window_info("未找到")
            return False
        self._window_rect = rect
        info = f"{rect.width}x{rect.height}"
        if rect.title:
            info = f"{rect.title} ({info})"
        self.set_window_info(info)
        self.preview_tab.set_window_rect(rect)
        self.focus_force()
        from td_executor.runtime.overlay import WindowOverlay
        self._overlay = WindowOverlay()
        self._overlay.show(rect.hwnd, window_info=info)
        return True

    def disconnect_window(self) -> None:
        if self._overlay is not None:
            self._overlay.hide()
            self._overlay = None
        self._window_rect = None
        self.set_window_info("未连接")
        self.preview_tab.set_window_rect(None)

    def start_polling(self) -> None:
        self._poll_queue()

    def _poll_queue(self) -> None:
        event = self.bridge.get_event()
        if event is not None:
            self._handle_event(event)
        self._poll_id = self.after(100, self._poll_queue)

    def _handle_event(self, event: object) -> None:
        from td_executor.ui.events import (
            ActionStartEvent,
            ActionCompleteEvent,
            WaveChangeEvent,
            ExecutionDoneEvent,
        )

        if isinstance(event, ActionStartEvent):
            self.monitor_tab.on_action_start(event)
        elif isinstance(event, ActionCompleteEvent):
            self.monitor_tab.on_action_complete(event)
        elif isinstance(event, WaveChangeEvent):
            self.monitor_tab.on_wave_change(event)
        elif isinstance(event, ExecutionDoneEvent):
            self.monitor_tab.on_execution_done(event)
            self.script_tab.on_execution_done(event)
            self.preview_tab.on_execution_done(event)
            self.set_status("已停止")
            if event.result == "completed":
                self.report_tab.refresh_reports()

    def _on_close(self) -> None:
        if self.bridge.running:
            if not messagebox.askyesno("确认退出", "执行器正在运行，确认退出？"):
                return
            self.bridge.request_stop()
        if self._poll_id:
            self.after_cancel(self._poll_id)
        self.destroy()


def launch() -> None:
    try:
        app = ExecutorApp()
        app.start_polling()
        app.mainloop()
    except tk.TclError:
        print("无法启动 GUI：未检测到显示环境")
        raise SystemExit(1)
