"""OCR 引擎：轻量数字识别与多帧投票。"""

from abc import ABC, abstractmethod
from collections import Counter
from pathlib import Path

import numpy

__all__ = [
    "OCREngine",
    "TemplateDigitRecognizer",
    "MultiFrameVoter",
    "PaddleOCRAdapter",
    "create_ocr_engine",
]


class OCREngine(ABC):
    @abstractmethod
    def read_wave(self, frame: numpy.ndarray) -> int | None: ...

    @abstractmethod
    def read_resource(self, frame: numpy.ndarray) -> int | None: ...

    @abstractmethod
    def read_core_hp(self, frame: numpy.ndarray) -> int | None: ...


class TemplateDigitRecognizer(OCREngine):
    def __init__(self, template_dir: str | Path | None = None) -> None:
        import cv2

        self._cv2 = cv2
        self._templates: dict[int, numpy.ndarray] = {}
        if template_dir is not None:
            self._load_templates(Path(template_dir))
        else:
            self._generate_templates()

    def _load_templates(self, template_dir: Path) -> None:
        for digit in range(10):
            path = template_dir / f"{digit}.png"
            if path.exists():
                img = self._cv2.imread(str(path), self._cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    _, binary = self._cv2.threshold(
                        img, 0, 255, self._cv2.THRESH_BINARY_INV + self._cv2.THRESH_OTSU
                    )
                    self._templates[digit] = binary

    def _generate_templates(self) -> None:
        for digit in range(10):
            canvas = numpy.zeros((40, 28), dtype=numpy.uint8)
            self._cv2.putText(
                canvas,
                str(digit),
                (2, 32),
                self._cv2.FONT_HERSHEY_SIMPLEX,
                1.1,
                255,
                2,
                self._cv2.LINE_AA,
            )
            self._templates[digit] = canvas

    def _preprocess(
        self, frame: numpy.ndarray
    ) -> tuple[numpy.ndarray, list[numpy.ndarray]]:
        cv2 = self._cv2
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame.copy()
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        digit_imgs: list[numpy.ndarray] = []
        bboxes: list[tuple[int, int, int, int]] = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w < 3 or h < 5:
                continue
            bboxes.append((x, y, w, h))
        bboxes.sort(key=lambda b: b[0])
        for x, y, w, h in bboxes:
            roi = binary[y : y + h, x : x + w]
            digit_imgs.append(roi)
        return binary, digit_imgs

    def _match_digit(self, digit_img: numpy.ndarray) -> int | None:
        cv2 = self._cv2
        best_digit: int | None = None
        best_score: float = -1.0
        for digit_val, tmpl in self._templates.items():
            resized = cv2.resize(digit_img, (tmpl.shape[1], tmpl.shape[0]))
            result = cv2.matchTemplate(resized, tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            if max_val > best_score:
                best_score = max_val
                best_digit = digit_val
        if best_score < 0.5:
            return None
        return best_digit

    def _read_number(self, frame: numpy.ndarray) -> int | None:
        _, digit_imgs = self._preprocess(frame)
        if not digit_imgs:
            return None
        digits: list[int] = []
        for dimg in digit_imgs:
            d = self._match_digit(dimg)
            if d is None:
                return None
            digits.append(d)
        if not digits:
            return None
        number = 0
        for d in digits:
            number = number * 10 + d
        return number

    def read_wave(self, frame: numpy.ndarray) -> int | None:
        return self._read_number(frame)

    def read_resource(self, frame: numpy.ndarray) -> int | None:
        return self._read_number(frame)

    def read_core_hp(self, frame: numpy.ndarray) -> int | None:
        return self._read_number(frame)


class MultiFrameVoter(OCREngine):
    def __init__(self, engine: OCREngine, vote_frames: int = 3) -> None:
        self._engine = engine
        self._vote_frames = vote_frames
        self._wave_buffer: list[int] = []
        self._resource_buffer: list[int] = []
        self._hp_buffer: list[int] = []

    @staticmethod
    def _vote(buffer: list[int]) -> int | None:
        if not buffer:
            return None
        counter = Counter(buffer)
        most_common = counter.most_common(1)[0]
        if most_common[1] < 2 and len(buffer) >= 3:
            return None
        return most_common[0]

    def _collect_and_vote(self, buffer: list[int], read_fn: object) -> int | None:
        result = read_fn()
        if result is not None:
            buffer.append(result)
        if len(buffer) > self._vote_frames:
            buffer.pop(0)
        if len(buffer) < self._vote_frames:
            if buffer:
                return buffer[-1]
            return None
        return self._vote(buffer)

    def read_wave(self, frame: numpy.ndarray) -> int | None:
        return self._collect_and_vote(
            self._wave_buffer, lambda: self._engine.read_wave(frame)
        )

    def read_resource(self, frame: numpy.ndarray) -> int | None:
        return self._collect_and_vote(
            self._resource_buffer, lambda: self._engine.read_resource(frame)
        )

    def read_core_hp(self, frame: numpy.ndarray) -> int | None:
        return self._collect_and_vote(
            self._hp_buffer, lambda: self._engine.read_core_hp(frame)
        )


class PaddleOCRAdapter(OCREngine):
    def __init__(self) -> None:
        self._ocr: object | None = None

    def _get_ocr(self) -> object:
        if self._ocr is None:
            from paddleocr import PaddleOCR

            self._ocr = PaddleOCR(use_angle_cls=False, show_log=False, lang="en")
        return self._ocr

    def _ocr_read(self, frame: numpy.ndarray) -> int | None:
        import cv2

        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        result = self._get_ocr().ocr(gray, cls=False)
        if not result or not result[0]:
            return None
        texts: list[str] = []
        for line in result[0]:
            texts.append(line[1][0])
        combined = "".join(texts).strip()
        digits_only = "".join(c for c in combined if c.isdigit())
        if not digits_only:
            return None
        try:
            return int(digits_only)
        except ValueError:
            return None

    def read_wave(self, frame: numpy.ndarray) -> int | None:
        return self._ocr_read(frame)

    def read_resource(self, frame: numpy.ndarray) -> int | None:
        return self._ocr_read(frame)

    def read_core_hp(self, frame: numpy.ndarray) -> int | None:
        return self._ocr_read(frame)


def create_ocr_engine(backend: str = "template", vote_frames: int = 3) -> OCREngine:
    if backend == "paddleocr":
        try:
            import paddleocr

            _ = paddleocr
            inner: OCREngine = PaddleOCRAdapter()
        except ImportError:
            inner = TemplateDigitRecognizer()
    elif backend == "template":
        inner = TemplateDigitRecognizer()
    else:
        raise ValueError(f"不支持的 OCR 后端: {backend}")
    if vote_frames > 1:
        return MultiFrameVoter(inner, vote_frames=vote_frames)
    return inner
