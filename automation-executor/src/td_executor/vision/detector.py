"""视觉检测器：模板匹配与颜色区域检测。"""

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy
except ImportError:
    numpy = None


class VisionDetector:
    def __init__(self, templates_dir: str | None = None) -> None:
        self.templates_dir = templates_dir
        self._templates: dict[str, numpy.ndarray] = {}

    def load_template(self, name: str, image_path: str) -> None:
        if cv2 is None or numpy is None:
            raise RuntimeError("cv2 或 numpy 未安装")
        img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if img is None:
            raise FileNotFoundError(f"模板图片未找到: {image_path}")
        self._templates[name] = img

    def _get_template(self, name: str) -> numpy.ndarray | None:
        if name in self._templates:
            return self._templates[name]
        if self.templates_dir is not None:
            path = f"{self.templates_dir}/{name}.png"
            if cv2 is None or numpy is None:
                return None
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is not None:
                self._templates[name] = img
                return img
        return None

    def match_template(
        self,
        frame: numpy.ndarray,
        template_name: str,
        threshold: float = 0.8,
    ) -> bool:
        if cv2 is None or numpy is None:
            return False
        template = self._get_template(template_name)
        if template is None:
            return False
        if frame.shape[0] < template.shape[0] or frame.shape[1] < template.shape[1]:
            return False
        result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        return max_val >= threshold

    def color_region_check(
        self,
        frame: numpy.ndarray,
        target_color: tuple[int, int, int],
        tolerance: int = 30,
        min_ratio: float = 0.1,
    ) -> bool:
        if cv2 is None or numpy is None:
            return False
        r, g, b = target_color
        lower = numpy.array([b - tolerance, g - tolerance, r - tolerance], dtype=numpy.int32)
        upper = numpy.array([b + tolerance, g + tolerance, r + tolerance], dtype=numpy.int32)
        lower = numpy.clip(lower, 0, 255).astype(numpy.uint8)
        upper = numpy.clip(upper, 0, 255).astype(numpy.uint8)
        mask = cv2.inRange(frame, lower, upper)
        matching = numpy.count_nonzero(mask)
        total = frame.shape[0] * frame.shape[1]
        if total == 0:
            return False
        ratio = matching / total
        return ratio >= min_ratio

    def detect_map_ui(
        self,
        frame: numpy.ndarray,
        template_name: str = "map_ui_indicator",
        threshold: float = 0.7,
    ) -> bool:
        return self.match_template(frame, template_name, threshold)

    def detect_slot_state(
        self,
        frame: numpy.ndarray,
        check_area: dict | None = None,
        template_name: str | None = None,
        threshold: float = 0.7,
    ) -> str:
        if cv2 is None or numpy is None:
            return "unknown"
        region = frame
        if check_area is not None:
            x = check_area.get("x", 0)
            y = check_area.get("y", 0)
            w = check_area.get("w", frame.shape[1])
            h = check_area.get("h", frame.shape[0])
            x2 = min(x + w, frame.shape[1])
            y2 = min(y + h, frame.shape[0])
            region = frame[y:y2, x:x2]
        if template_name is not None:
            if self.match_template(frame, template_name, threshold):
                return "occupied"
            return "empty"
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        std_dev = numpy.std(gray)
        if std_dev > 15:
            return "occupied"
        return "empty"

    def detect_place_error(
        self,
        frame: numpy.ndarray,
        template_name: str = "place_error_tip",
        threshold: float = 0.7,
    ) -> bool:
        return self.match_template(frame, template_name, threshold)
