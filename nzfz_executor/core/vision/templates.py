"""模板资源模型（P2-09）。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class TemplateResource:
    """已加载的模板图片资源。"""

    name: str
    path: Path
    image: np.ndarray
    width: int
    height: int
    threshold: float
