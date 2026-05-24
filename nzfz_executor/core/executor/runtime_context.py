"""执行器运行时上下文（P2-07）。"""

from __future__ import annotations

from dataclasses import dataclass

from nzfz_executor.core.actions.mouse_controller import MouseController
from nzfz_executor.core.executor.coordinate_mapper import CoordinateMapper
from nzfz_executor.core.models import ConnectedWindow
from nzfz_executor.core.screenshot_manager import ScreenshotManager
from nzfz_executor.core.vision.recognizers import ImageRecognizer


@dataclass
class ExecutorRuntimeContext:
    """执行器运行时依赖注入容器。"""

    connected_context: ConnectedWindow
    screenshot_manager: ScreenshotManager
    recognizer: ImageRecognizer
    coordinate_mapper: CoordinateMapper
    mouse_controller: MouseController
    max_iterations: int
    loop_interval_ms: int
