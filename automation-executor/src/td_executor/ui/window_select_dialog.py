from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class WindowSelectDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, windows: list[dict]) -> None:
        super().__init__(parent)
        self.selected_hwnd: int | None = None

        self.title("选择游戏窗口")
        self.geometry("500x400")

        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        x = parent_x + (parent_w - 500) // 2
        y = parent_y + (parent_h - 400) // 2
        self.geometry(f"+{x}+{y}")

        self.transient(parent)
        self.grab_set()

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(
            tree_frame, columns=("title", "hwnd"), show="headings"
        )
        self.tree.heading("title", text="窗口标题")
        self.tree.heading("hwnd", text="句柄")
        self.tree.column("title", width=350)
        self.tree.column("hwnd", width=100)

        scrollbar = ttk.Scrollbar(
            tree_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for index, win in enumerate(windows):
            self.tree.insert(
                "",
                tk.END,
                iid=str(index),
                values=(win.get("title", ""), win.get("hwnd", "")),
            )

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_double_click)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.connect_btn = ttk.Button(
            btn_frame, text="连接", command=self._on_connect, state=tk.DISABLED
        )
        self.connect_btn.pack(side=tk.RIGHT, padx=(5, 0))

        cancel_btn = ttk.Button(btn_frame, text="取消", command=self._on_cancel)
        cancel_btn.pack(side=tk.RIGHT)

    def _on_select(self, _event: tk.Event) -> None:
        selected = self.tree.selection()
        if selected:
            self.connect_btn.config(state=tk.NORMAL)
        else:
            self.connect_btn.config(state=tk.DISABLED)

    def _on_double_click(self, _event: tk.Event) -> None:
        self._on_connect()

    def _on_connect(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected[0])
        self.selected_hwnd = int(item["values"][1])
        self.destroy()

    def _on_cancel(self) -> None:
        self.selected_hwnd = None
        self.destroy()
