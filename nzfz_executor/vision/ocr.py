"""OCR 识别器：基于光学字符识别读取游戏画面中的数字信息。"""

from __future__ import annotations

from typing import Any


class OCRReader:
    """OCR 识别器：从游戏截图中提取波次、资源、血量等数字信息。"""

    def __init__(self) -> None:
        """初始化 OCR 识别器。"""
        pass

    def read_wave(
        self,
        capture: Any,
        rect: Any,
        rois: Any,
        multi_frame: bool = False,
    ) -> int | None:
        """读取当前波次编号。

        Args:
            capture: 截图对象。
            rect: 窗口矩形区域。
            rois: 感兴趣区域集合。
            multi_frame: 是否启用多帧确认。

        Returns:
            波次编号，识别失败时返回 None。
        """
        raise NotImplementedError

    def read_resource(
        self,
        capture: Any,
        rect: Any,
        rois: Any,
        multi_frame: bool = False,
    ) -> int | None:
        """读取当前资源数量。

        Args:
            capture: 截图对象。
            rect: 窗口矩形区域。
            rois: 感兴趣区域集合。
            multi_frame: 是否启用多帧确认。

        Returns:
            资源数量，识别失败时返回 None。
        """
        raise NotImplementedError

    def read_core_hp(
        self,
        capture: Any,
        rect: Any,
        rois: Any,
        multi_frame: bool = False,
    ) -> int | None:
        """读取核心血量值。

        Args:
            capture: 截图对象。
            rect: 窗口矩形区域。
            rois: 感兴趣区域集合。
            multi_frame: 是否启用多帧确认。

        Returns:
            核心血量值，识别失败时返回 None。
        """
        raise NotImplementedError

    def read_digits_roi(
        self,
        capture: Any,
        rect: Any,
        roi: Any,
        keyword: str,
    ) -> str:
        """在指定感兴趣区域内识别数字文本。

        Args:
            capture: 截图对象。
            rect: 窗口矩形区域。
            roi: 感兴趣区域。
            keyword: 识别关键字，用于选择对应的预处理策略。

        Returns:
            识别到的数字字符串。
        """
        raise NotImplementedError