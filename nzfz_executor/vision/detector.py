"""视觉检测器：基于模板匹配实现界面状态判断与元素识别。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DetectorConfig:
    """视觉检测器配置。"""

    match_threshold: float = 0.8
    """模板匹配阈值，越高要求越严格。"""

    multi_frame_count: int = 3
    """多帧确认时采集的帧数。"""

    multi_frame_interval_ms: int = 100
    """多帧确认时相邻帧的间隔（毫秒）。"""

    templates_dir: str = "assets/templates"
    """模板图片存放目录。"""


class VisionDetector:
    """视觉检测器：封装模板匹配与界面状态判断逻辑。"""

    def __init__(self, config: DetectorConfig | None = None) -> None:
        """初始化视觉检测器。

        Args:
            config: 检测器配置，为 None 时使用默认配置。
        """
        self.config: DetectorConfig = config or DetectorConfig()
        """当前检测器配置实例。"""

    def match_template(
        self,
        capture: Any,
        rect: Any,
        roi: Any,
        template_path: str,
        threshold: float,
    ) -> bool:
        """在截图的指定区域内进行模板匹配。

        Args:
            capture: 截图对象。
            rect: 窗口矩形区域。
            roi: 感兴趣区域。
            template_path: 模板图片路径。
            threshold: 匹配阈值。

        Returns:
            匹配是否成功。
        """
        raise NotImplementedError

    def is_map_ui_open(self, capture: Any, rect: Any, rois: Any) -> bool:
        """判断地图界面是否已打开。

        Args:
            capture: 截图对象。
            rect: 窗口矩形区域。
            rois: 感兴趣区域集合。

        Returns:
            地图界面是否已打开。
        """
        raise NotImplementedError

    def is_slot_empty(self, capture: Any, rect: Any, slot_verify: Any) -> bool:
        """判断指定槽位是否为空。

        Args:
            capture: 截图对象。
            rect: 窗口矩形区域。
            slot_verify: 槽位验证信息。

        Returns:
            槽位是否为空。
        """
        raise NotImplementedError

    def is_slot_occupied(self, capture: Any, rect: Any, slot_verify: Any) -> bool:
        """判断指定槽位是否已被占用。

        Args:
            capture: 截图对象。
            rect: 窗口矩形区域。
            slot_verify: 槽位验证信息。

        Returns:
            槽位是否已被占用。
        """
        raise NotImplementedError

    def detect_error_tip(self, capture: Any, rect: Any, rois: Any) -> bool:
        """检测画面中是否出现错误提示。

        Args:
            capture: 截图对象。
            rect: 窗口矩形区域。
            rois: 感兴趣区域集合。

        Returns:
            是否检测到错误提示。
        """
        raise NotImplementedError