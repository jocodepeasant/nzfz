"""截图放大查看对话框。"""

import logging

from PIL.Image import Image as PILImage
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QImage, QWheelEvent, QMouseEvent, QResizeEvent
from PySide6.QtWidgets import QDialog, QLabel, QScrollArea, QVBoxLayout

logger = logging.getLogger(__name__)

_MIN_SCALE = 0.1
_MAX_SCALE = 4.0
_SCALE_STEP = 0.1


class ScreenshotViewerDialog(QDialog):
    """截图放大查看对话框，支持滚轮缩放和拖拽平移。"""

    def __init__(
        self,
        parent=None,
        pil_image: PILImage | None = None,
        window_title: str = "",
    ) -> None:
        super().__init__(parent)
        self._pil_image = pil_image
        self._scale = 1.0
        self._drag_start_pos: QPoint | None = None

        self.setWindowTitle(f"截图查看 - {window_title}" if window_title else "截图查看")
        self.setMinimumSize(400, 300)
        self.resize(800, 600)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(False)
        self._scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setMouseTracking(True)
        self._scroll_area.setWidget(self._image_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._scroll_area)

        if self._pil_image is not None:
            self._update_pixmap()

    def _pil_to_original_pixmap(self) -> QPixmap:
        """将 PIL 图像转为原始分辨率 QPixmap。"""
        if self._pil_image.mode == "RGBA":
            rgba_image = self._pil_image
        else:
            rgba_image = self._pil_image.convert("RGBA")
        data = rgba_image.tobytes("raw", "RGBA")
        qimage = QImage(
            data,
            rgba_image.width,
            rgba_image.height,
            QImage.Format.Format_RGBA8888,
        )
        return QPixmap.fromImage(qimage)

    def _update_pixmap(self) -> None:
        """按当前缩放比例更新显示的 pixmap。"""
        if self._pil_image is None:
            return
        original = self._pil_to_original_pixmap()
        scaled_w = int(original.width() * self._scale)
        scaled_h = int(original.height() * self._scale)
        scaled = original.scaled(
            scaled_w,
            scaled_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self._image_label.setPixmap(scaled)
        self._image_label.resize(scaled.size())

    def wheelEvent(self, event: QWheelEvent) -> None:
        """鼠标滚轮缩放。"""
        if self._pil_image is None:
            return

        delta = event.angleDelta().y()
        if delta > 0:
            new_scale = min(self._scale + _SCALE_STEP, _MAX_SCALE)
        else:
            new_scale = max(self._scale - _SCALE_STEP, _MIN_SCALE)

        if new_scale != self._scale:
            self._scale = new_scale
            self._update_pixmap()
            logger.debug("Screenshot viewer scale changed to %.1f", self._scale)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """记录拖拽起点。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """拖拽平移滚动区域。"""
        if self._drag_start_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            self._drag_start_pos = event.globalPosition().toPoint()
            h_bar = self._scroll_area.horizontalScrollBar()
            v_bar = self._scroll_area.verticalScrollBar()
            h_bar.setValue(h_bar.value() - delta.x())
            v_bar.setValue(v_bar.value() - delta.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """结束拖拽。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        """ESC 关闭窗口。"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        super().keyPressEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """窗口大小变化时无需特殊处理。"""
        super().resizeEvent(event)