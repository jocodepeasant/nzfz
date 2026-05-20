from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from td_executor.script.load import load_script_file
from td_executor.script.validate import validate_script_data


class ScriptTab(ttk.Frame):

    def __init__(self, parent: tk.Widget, app) -> None:
        super().__init__(parent)
        self.app = app
        self._script_data: dict | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        file_frame = ttk.LabelFrame(self, text="脚本文件")
        file_frame.pack(fill=tk.X, padx=5, pady=5)

        self._path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self._path_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0), pady=5
        )
        ttk.Button(file_frame, text="浏览...", command=self._on_browse).pack(
            side=tk.LEFT, padx=5, pady=5
        )
        ttk.Button(file_frame, text="校验", command=self._on_validate).pack(
            side=tk.LEFT, padx=5, pady=5
        )

        preview_frame = ttk.LabelFrame(self, text="脚本预览")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._preview_text = tk.Text(preview_frame, height=10, state=tk.DISABLED)
        self._preview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        param_frame = ttk.LabelFrame(self, text="运行参数")
        param_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(param_frame, text="窗口标题关键字:").pack(side=tk.LEFT, padx=(5, 0), pady=5)
        self._title_var = tk.StringVar(value="逆战")
        ttk.Entry(param_frame, textvariable=self._title_var, width=15).pack(
            side=tk.LEFT, padx=5, pady=5
        )

        self._connect_btn = ttk.Button(
            param_frame, text="连接窗口", command=self._on_connect_window
        )
        self._connect_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self._dry_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(param_frame, text="试运行(dry-run)", variable=self._dry_run_var).pack(
            side=tk.LEFT, padx=5, pady=5
        )

        self._debug_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(param_frame, text="调试模式", variable=self._debug_var).pack(
            side=tk.LEFT, padx=5, pady=5
        )

        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(fill=tk.X, padx=5, pady=5)

        style = ttk.Style()
        style.configure("Green.TButton", foreground="green")
        style.configure("Red.TButton", foreground="red")
        style.configure("Gray.TButton", foreground="gray")

        self._start_btn = ttk.Button(
            ctrl_frame, text="启动", style="Green.TButton", command=self._on_start
        )
        self._start_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self._stop_btn = ttk.Button(
            ctrl_frame, text="停止", style="Red.TButton", command=self._on_stop, state=tk.DISABLED
        )
        self._stop_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self._reset_btn = ttk.Button(
            ctrl_frame, text="重置", style="Gray.TButton", command=self._on_reset
        )
        self._reset_btn.pack(side=tk.LEFT, padx=5, pady=5)

    def _on_browse(self) -> None:
        path = filedialog.askopenfilename(
            title="选择脚本文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self._path_var.set(path)
            # 选择文件后自动加载脚本数据并显示预览，免去手动点击校验的步骤
            try:
                self._script_data = load_script_file(Path(path))
                self._show_preview(self._script_data)
            except Exception as e:
                self._script_data = None
                messagebox.showerror("加载失败", str(e))

    def _on_validate(self) -> None:
        path = self._path_var.get().strip()
        if not path:
            messagebox.showerror("错误", "请先选择脚本文件")
            return
        try:
            data = load_script_file(Path(path))
        except Exception as e:
            messagebox.showerror("加载失败", str(e))
            return
        self._script_data = data
        self._show_preview(data)
        errors = validate_script_data(data)
        if errors:
            first = errors[0]
            messagebox.showwarning("校验未通过", f"{first['path']}: {first['message']}")
        else:
            messagebox.showinfo("校验成功", "脚本校验通过")

    def _show_preview(self, data: dict) -> None:
        map_name = data.get("map_name", "未知")
        waves = data.get("waves", [])
        wave_count = len(waves)
        total_actions = sum(len(w.get("actions", [])) for w in waves)
        traps = data.get("traps", [])
        if not traps:
            trap_list = "无"
        else:
            trap_names = []
            for t in traps:
                if isinstance(t, dict):
                    trap_names.append(t.get("trap_name") or t.get("trap_id") or str(t))
                else:
                    trap_names.append(str(t))
            trap_list = ", ".join(trap_names)
        summary = (
            f"地图: {map_name}\n"
            f"波次: {wave_count}\n"
            f"总操作数: {total_actions}\n"
            f"陷阱列表: {trap_list}"
        )
        self._preview_text.config(state=tk.NORMAL)
        self._preview_text.delete("1.0", tk.END)
        self._preview_text.insert("1.0", summary)
        self._preview_text.config(state=tk.DISABLED)

    def _on_connect_window(self) -> None:
        if self.app.window_rect is not None:
            self.app.disconnect_window()
            self._connect_btn.config(text="连接窗口", state=tk.NORMAL)
            return
        title_keyword = self._title_var.get().strip()
        if not title_keyword:
            messagebox.showerror("错误", "请输入窗口标题关键字")
            return
        from td_executor.runtime.window import list_windows
        windows = list_windows(title_keyword)
        if not windows:
            messagebox.showinfo("提示", "未找到匹配的窗口进程")
            return
        from td_executor.ui.window_select_dialog import WindowSelectDialog
        dialog = WindowSelectDialog(self.app, windows)
        self.app.wait_window(dialog)
        if dialog.selected_hwnd is None:
            return
        ok = self.app.connect_window_by_hwnd(dialog.selected_hwnd)
        if ok:
            self._connect_btn.config(text="断开连接")
        else:
            self._connect_btn.config(text="连接窗口")
            messagebox.showerror("连接失败", "无法获取窗口信息")

    def _on_start(self) -> None:
        if self._script_data is None:
            # 允许未校验时自动从路径加载脚本，提升操作便捷性
            path = self._path_var.get().strip()
            if not path:
                messagebox.showerror("错误", "请先选择脚本文件")
                return
            try:
                self._script_data = load_script_file(Path(path))
                self._show_preview(self._script_data)
            except Exception as e:
                messagebox.showerror("加载失败", str(e))
                return
        title_keyword = self._title_var.get().strip()
        if not title_keyword:
            messagebox.showerror("错误", "请输入窗口标题关键字")
            return
        dry_run = self._dry_run_var.get()
        try:
            self.app.bridge.start_execution(
                self._script_data, title_keyword, dry_run,
                window_rect=self.app.window_rect,
                debug=self._debug_var.get(),
                on_done=self._on_run_done,
            )
        except Exception as e:
            messagebox.showerror("启动失败", str(e))
            return
        self.app.bridge.set_overlay(self.app.overlay if self._debug_var.get() else None)
        self._start_btn.config(state=tk.DISABLED)
        self._stop_btn.config(state=tk.NORMAL)
        self._connect_btn.config(state=tk.DISABLED)
        self.app.notebook.select(0)
        self.app.set_status("运行中")
        self.app.monitor_tab.reset()
        if self._script_data:
            self.app.preview_tab.set_script_data(self._script_data)

    def _on_stop(self) -> None:
        self.app.bridge.request_stop()
        self.app.set_status("正在停止...")

    def _on_reset(self) -> None:
        self._path_var.set("")
        self._title_var.set("逆战")
        self._dry_run_var.set(False)
        self._preview_text.config(state=tk.NORMAL)
        self._preview_text.delete("1.0", tk.END)
        self._preview_text.config(state=tk.DISABLED)
        self._script_data = None
        self._start_btn.config(state=tk.NORMAL)
        self._stop_btn.config(state=tk.DISABLED)
        self._connect_btn.config(text="连接窗口", state=tk.NORMAL)
        self.app.bridge.reset()
        self.app.disconnect_window()
        self.app.set_status("就绪")

    def _on_run_done(self) -> None:
        self.after(0, self._on_execution_done)

    def _on_execution_done(self) -> None:
        self._start_btn.config(state=tk.NORMAL)
        self._stop_btn.config(state=tk.DISABLED)
        if self.app.window_rect is not None:
            self._connect_btn.config(state=tk.NORMAL, text="断开连接")
        else:
            self._connect_btn.config(state=tk.NORMAL, text="连接窗口")

    def on_execution_done(self, event=None) -> None:
        self._start_btn.config(state=tk.NORMAL)
        self._stop_btn.config(state=tk.DISABLED)
        if self.app.window_rect is not None:
            self._connect_btn.config(state=tk.NORMAL, text="断开连接")
        else:
            self._connect_btn.config(state=tk.NORMAL, text="连接窗口")
