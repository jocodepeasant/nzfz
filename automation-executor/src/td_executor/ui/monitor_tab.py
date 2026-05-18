from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk

from td_executor.ui.events import (
    ActionCompleteEvent,
    ActionStartEvent,
    ExecutionDoneEvent,
    WaveChangeEvent,
)


class MonitorTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: object) -> None:
        super().__init__(parent)
        self.app = app
        self._start_time: float | None = None
        self._total_waves: int = 0
        self._success_count: int = 0
        self._fail_count: int = 0
        self._skip_count: int = 0
        self._row_map: dict[int, str] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        progress_frame = ttk.LabelFrame(self, text="波次进度")
        progress_frame.pack(fill=tk.X, padx=5, pady=(5, 2))

        self._wave_label = ttk.Label(progress_frame, text="波次 0/0")
        self._wave_label.pack(side=tk.LEFT, padx=5, pady=3)

        self._wave_progress = ttk.Progressbar(progress_frame, mode="determinate", maximum=100)
        self._wave_progress.pack(fill=tk.X, padx=5, pady=3, expand=True)

        content_frame = ttk.Frame(self)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        tree_frame = ttk.Frame(content_frame)
        tree_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        columns = ("序号", "类型", "名称", "状态", "重试次数", "耗时(ms)")
        self._tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=80, anchor=tk.CENTER)
        self._tree.column("名称", width=160, anchor=tk.W)
        self._tree.column("耗时(ms)", width=90, anchor=tk.E)

        self._tree.tag_configure("pending", foreground="gray")
        self._tree.tag_configure("running", foreground="blue")
        self._tree.tag_configure("success", foreground="green")
        self._tree.tag_configure("fail", foreground="red")
        self._tree.tag_configure("skip", foreground="goldenrod")

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        stats_frame = ttk.LabelFrame(content_frame, text="统计")
        stats_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))

        self._stat_total_label = ttk.Label(stats_frame, text="总动作数: 0")
        self._stat_total_label.pack(anchor=tk.W, padx=8, pady=2)

        self._stat_success_label = ttk.Label(stats_frame, text="成功数: 0")
        self._stat_success_label.pack(anchor=tk.W, padx=8, pady=2)

        self._stat_fail_label = ttk.Label(stats_frame, text="失败数: 0")
        self._stat_fail_label.pack(anchor=tk.W, padx=8, pady=2)

        self._stat_skip_label = ttk.Label(stats_frame, text="跳过数: 0")
        self._stat_skip_label.pack(anchor=tk.W, padx=8, pady=2)

        self._stat_duration_label = ttk.Label(stats_frame, text="运行时长: 0.0s")
        self._stat_duration_label.pack(anchor=tk.W, padx=8, pady=2)

    def on_action_start(self, event: ActionStartEvent) -> None:
        if self._start_time is None:
            self._start_time = time.time()

        iid = self._tree.insert("", tk.END, values=(
            event.action_index + 1,
            event.action_type,
            event.action_name,
            "执行中",
            0,
            "",
        ), tags=("running",))
        self._row_map[event.action_index] = iid
        self._tree.see(iid)

    def on_action_complete(self, event: ActionCompleteEvent) -> None:
        iid = self._row_map.get(event.action_index)
        if iid is None:
            return

        if event.skipped:
            status = "⊘ 跳过"
            tag = "skip"
            self._skip_count += 1
        elif event.success:
            status = "✓ 成功"
            tag = "success"
            self._success_count += 1
        else:
            status = "✗ 失败"
            tag = "fail"
            self._fail_count += 1

        self._tree.item(iid, values=(
            event.action_index + 1,
            event.action_type,
            event.action_name,
            status,
            event.retry_count,
            f"{event.duration_ms:.0f}",
        ), tags=(tag,))

        self._update_stats()

    def on_wave_change(self, event: WaveChangeEvent) -> None:
        self._total_waves = event.total_waves
        self._wave_label.config(text=f"波次 {event.wave}/{event.total_waves}")
        if event.total_waves > 0:
            self._wave_progress["value"] = (event.wave / event.total_waves) * 100

    def on_execution_done(self, event: ExecutionDoneEvent) -> None:
        self._success_count = event.success_count
        self._fail_count = event.fail_count
        self._skip_count = event.skip_count
        self._update_stats(duration=event.duration_seconds)

    def _update_stats(self, duration: float | None = None) -> None:
        total = self._success_count + self._fail_count + self._skip_count
        self._stat_total_label.config(text=f"总动作数: {total}")
        self._stat_success_label.config(text=f"成功数: {self._success_count}")
        self._stat_fail_label.config(text=f"失败数: {self._fail_count}")
        self._stat_skip_label.config(text=f"跳过数: {self._skip_count}")

        if duration is not None:
            self._stat_duration_label.config(text=f"运行时长: {duration:.1f}s")
        elif self._start_time is not None:
            elapsed = time.time() - self._start_time
            self._stat_duration_label.config(text=f"运行时长: {elapsed:.1f}s")

    def reset(self) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._row_map.clear()
        self._start_time = None
        self._total_waves = 0
        self._success_count = 0
        self._fail_count = 0
        self._skip_count = 0
        self._wave_label.config(text="波次 0/0")
        self._wave_progress["value"] = 0
        self._stat_total_label.config(text="总动作数: 0")
        self._stat_success_label.config(text="成功数: 0")
        self._stat_fail_label.config(text="失败数: 0")
        self._stat_skip_label.config(text="跳过数: 0")
        self._stat_duration_label.config(text="运行时长: 0.0s")
