from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog
from typing import TYPE_CHECKING

try:
    from PIL import Image, ImageTk, ImageDraw
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

if TYPE_CHECKING:
    from td_executor.ui.app import ExecutorApp


class PreviewTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: ExecutorApp) -> None:
        super().__init__(parent)
        self._app = app
        self._script_data: dict | None = None
        self._auto_refresh_id: str | None = None
        self._photo_image: ImageTk.PhotoImage | None = None
        self._show_slots = tk.BooleanVar(value=False)
        self._current_image: Image.Image | None = None
        self._rect = None

        if not _PIL_AVAILABLE:
            ttk.Label(
                self,
                text="需要安装 Pillow: pip install td-executor[ui]",
            ).pack(padx=20, pady=20)
            return

        self._build_ui()

    def _build_ui(self) -> None:
        control_bar = ttk.Frame(self)
        control_bar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(control_bar, text="刷新截图", command=self._on_refresh).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_bar, text="保存截图", command=self._on_save).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(
            control_bar, text="显示格子标注", variable=self._show_slots, command=self._on_refresh
        ).pack(side=tk.LEFT, padx=2)

        self._canvas = tk.Canvas(self, bg="black")
        self._canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def set_script_data(self, script_data: dict) -> None:
        self._script_data = script_data
        if self._rect is None:
            from td_executor.runtime.window import find_game_window
            self._rect = find_game_window()
        self._start_auto_refresh()

    def set_window_rect(self, rect) -> None:
        self._rect = rect
        if rect is not None:
            self._on_refresh()
        else:
            self._stop_auto_refresh()
            self._canvas.delete("all")

    def _start_auto_refresh(self) -> None:
        self._stop_auto_refresh()
        self._auto_refresh()

    def _auto_refresh(self) -> None:
        self._on_refresh()
        if self._app.bridge.running:
            self._auto_refresh_id = self.after(2000, self._auto_refresh)

    def _stop_auto_refresh(self) -> None:
        if self._auto_refresh_id is not None:
            self.after_cancel(self._auto_refresh_id)
            self._auto_refresh_id = None

    def _on_refresh(self) -> None:
        image = self._capture_screenshot()
        if image is None:
            return
        if self._show_slots.get():
            image = self._draw_slot_overlay(image)
        self._current_image = image
        self._display_image(image)

    def _on_save(self) -> None:
        if self._current_image is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")],
        )
        if path:
            self._current_image.save(path)

    def _capture_screenshot(self):
        from td_executor.runtime.capture import ScreenCapture
        from td_executor.runtime.window import find_game_window

        rect = self._rect or find_game_window()
        if rect is None:
            return None
        try:
            capture = ScreenCapture(
                region={
                    "left": rect.left,
                    "top": rect.top,
                    "width": rect.width,
                    "height": rect.height,
                }
            )
            with capture:
                frame = capture.capture_frame()
            rgb = frame[:, :, ::-1].copy()
            return Image.fromarray(rgb)
        except Exception:
            return None

    def _draw_slot_overlay(self, image):
        from td_executor.runtime.coordinates import ratio_to_pixel
        from td_executor.runtime.window import find_game_window

        if self._script_data is None:
            return image
        slots = self._script_data.get("slots", [])
        if not slots:
            return image
        rect = self._rect or find_game_window()
        if rect is None:
            return image
        draw = ImageDraw.Draw(image)
        for slot in slots:
            slot_id = slot.get("slot_id", "")
            position = slot.get("position", {})
            x_ratio = position.get("x_ratio", 0.0)
            y_ratio = position.get("y_ratio", 0.0)
            px, py = ratio_to_pixel(0, 0, rect.width, rect.height, x_ratio, y_ratio)
            r = 12
            draw.ellipse([px - r, py - r, px + r, py + r], outline="red", width=2)
            draw.text((px + r + 2, py - 6), slot_id, fill="red")
        return image

    def _display_image(self, image: Image.Image) -> None:
        canvas_width = self._canvas.winfo_width()
        canvas_height = self._canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 800
            canvas_height = 600
        img_width, img_height = image.size
        scale = min(canvas_width / img_width, canvas_height / img_height)
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        resized = image.resize((new_width, new_height), Image.LANCZOS)
        self._photo_image = ImageTk.PhotoImage(resized)
        self._canvas.delete("all")
        self._canvas.create_image(
            canvas_width // 2,
            canvas_height // 2,
            anchor=tk.CENTER,
            image=self._photo_image,
        )

    def on_execution_done(self, event: object) -> None:
        self._stop_auto_refresh()
