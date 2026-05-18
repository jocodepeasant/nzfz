from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from tkinter import ttk, filedialog

import tkinter as tk


class ReportTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: object) -> None:
        super().__init__(parent)
        self.app = app
        self._reports_data: list[dict] = []
        self._build_ui()

    def _build_ui(self) -> None:
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_frame = ttk.Frame(self.paned)
        self.paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="报告列表").pack(anchor=tk.W, padx=5, pady=(5, 2))

        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.report_tree = ttk.Treeview(
            list_frame,
            columns=("时间", "脚本名", "结果", "时长"),
            show="headings",
            selectmode="browse",
        )
        self.report_tree.heading("时间", text="时间")
        self.report_tree.heading("脚本名", text="脚本名")
        self.report_tree.heading("结果", text="结果")
        self.report_tree.heading("时长", text="时长")
        self.report_tree.column("时间", width=140, minwidth=100)
        self.report_tree.column("脚本名", width=120, minwidth=80)
        self.report_tree.column("结果", width=70, minwidth=50)
        self.report_tree.column("时长", width=70, minwidth=50)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.report_tree.yview)
        self.report_tree.configure(yscrollcommand=scrollbar.set)
        self.report_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.report_tree.bind("<<TreeviewSelect>>", self._on_report_select)

        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame, weight=2)

        stats_frame = ttk.LabelFrame(right_frame, text="统计摘要")
        stats_frame.pack(fill=tk.X, padx=5, pady=(5, 2))

        self.label_total = ttk.Label(stats_frame, text="总动作数: -")
        self.label_total.pack(anchor=tk.W, padx=10, pady=2)
        self.label_success = ttk.Label(stats_frame, text="成功数: -")
        self.label_success.pack(anchor=tk.W, padx=10, pady=2)
        self.label_fail = ttk.Label(stats_frame, text="失败数: -")
        self.label_fail.pack(anchor=tk.W, padx=10, pady=2)
        self.label_duration = ttk.Label(stats_frame, text="运行时长: -")
        self.label_duration.pack(anchor=tk.W, padx=10, pady=2)

        detail_frame = ttk.LabelFrame(right_frame, text="动作日志")
        detail_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        detail_inner = ttk.Frame(detail_frame)
        detail_inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.action_tree = ttk.Treeview(
            detail_inner,
            columns=("波次", "类型", "名称", "状态", "重试次数", "错误信息"),
            show="headings",
            selectmode="browse",
        )
        self.action_tree.heading("波次", text="波次")
        self.action_tree.heading("类型", text="类型")
        self.action_tree.heading("名称", text="名称")
        self.action_tree.heading("状态", text="状态")
        self.action_tree.heading("重试次数", text="重试次数")
        self.action_tree.heading("错误信息", text="错误信息")
        self.action_tree.column("波次", width=50, minwidth=40)
        self.action_tree.column("类型", width=80, minwidth=60)
        self.action_tree.column("名称", width=120, minwidth=80)
        self.action_tree.column("状态", width=60, minwidth=50)
        self.action_tree.column("重试次数", width=70, minwidth=50)
        self.action_tree.column("错误信息", width=200, minwidth=100)

        action_scroll = ttk.Scrollbar(detail_inner, orient=tk.VERTICAL, command=self.action_tree.yview)
        self.action_tree.configure(yscrollcommand=action_scroll.set)
        self.action_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        action_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.export_btn = ttk.Button(btn_frame, text="导出", command=self._export_report)
        self.export_btn.pack(side=tk.RIGHT, padx=5)

    def refresh_reports(self) -> None:
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)
        self._reports_data.clear()

        reports_dir = Path("reports")
        if not reports_dir.is_dir():
            return

        report_files = sorted(reports_dir.glob("report_*.json"), reverse=True)
        for report_file in report_files:
            try:
                data = json.loads(report_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue

            self._reports_data.append(data)

            started_at = data.get("started_at", "")
            try:
                dt = datetime.fromisoformat(started_at)
                display_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                display_time = started_at

            script_name = data.get("script_name", "-")
            result = data.get("result", "-")

            duration_text = "-"
            finished_at = data.get("finished_at")
            if started_at and finished_at:
                try:
                    start_dt = datetime.fromisoformat(started_at)
                    finish_dt = datetime.fromisoformat(finished_at)
                    secs = (finish_dt - start_dt).total_seconds()
                    duration_text = f"{secs:.1f}s"
                except (ValueError, TypeError):
                    pass

            self.report_tree.insert("", tk.END, values=(display_time, script_name, result, duration_text))

    def _on_report_select(self, event: object = None) -> None:
        selection = self.report_tree.selection()
        if not selection:
            return

        index = self.report_tree.index(selection[0])
        if index >= len(self._reports_data):
            return

        data = self._reports_data[index]
        self._display_detail(data)

    def _display_detail(self, data: dict) -> None:
        actions = data.get("actions", [])
        total = len(actions)
        success = sum(1 for a in actions if a.get("success") is True)
        fail = sum(1 for a in actions if a.get("success") is False)

        self.label_total.config(text=f"总动作数: {total}")
        self.label_success.config(text=f"成功数: {success}")
        self.label_fail.config(text=f"失败数: {fail}")

        started_at = data.get("started_at", "")
        finished_at = data.get("finished_at", "")
        duration_text = "-"
        if started_at and finished_at:
            try:
                start_dt = datetime.fromisoformat(started_at)
                finish_dt = datetime.fromisoformat(finished_at)
                secs = (finish_dt - start_dt).total_seconds()
                duration_text = f"{secs:.1f}s"
            except (ValueError, TypeError):
                pass
        self.label_duration.config(text=f"运行时长: {duration_text}")

        for item in self.action_tree.get_children():
            self.action_tree.delete(item)

        for action in actions:
            wave = action.get("wave", "-")
            action_type = action.get("action_type", "-")
            action_name = action.get("action_name", "-")
            success_val = action.get("success")
            status = "成功" if success_val is True else ("失败" if success_val is False else "-")
            retry_count = action.get("retry_count", 0)
            error_message = action.get("error_message") or ""
            self.action_tree.insert(
                "", tk.END, values=(wave, action_type, action_name, status, retry_count, error_message)
            )

    def _export_report(self) -> None:
        selection = self.report_tree.selection()
        if not selection:
            return

        index = self.report_tree.index(selection[0])
        if index >= len(self._reports_data):
            return

        data = self._reports_data[index]

        started_at = data.get("started_at", "")
        try:
            dt = datetime.fromisoformat(started_at)
            default_name = f"report_{dt.strftime('%Y%m%d_%H%M%S')}.json"
        except (ValueError, TypeError):
            default_name = "report.json"

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
            initialfile=default_name,
        )
        if not path:
            return

        try:
            content = json.dumps(data, ensure_ascii=False, indent=2)
            Path(path).write_text(content, encoding="utf-8")
        except OSError:
            pass
