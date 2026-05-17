from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from td_executor.runtime.capture import CaptureBackend, CaptureConfig, ScreenCapture


class TestCaptureBackend:
    def test_mss_value(self) -> None:
        assert CaptureBackend.MSS.value == "mss"

    def test_dxcam_value(self) -> None:
        assert CaptureBackend.DXCAM.value == "dxcam"

    def test_from_string(self) -> None:
        assert CaptureBackend("mss") == CaptureBackend.MSS
        assert CaptureBackend("dxcam") == CaptureBackend.DXCAM


class TestCaptureConfig:
    def test_defaults(self) -> None:
        cfg = CaptureConfig()
        assert cfg.backend == CaptureBackend.MSS
        assert cfg.region is None
        assert cfg.output_format == "bgr"

    def test_custom(self) -> None:
        region = {"left": 100, "top": 100, "width": 1920, "height": 1080}
        cfg = CaptureConfig(backend=CaptureBackend.DXCAM, region=region, output_format="rgb")
        assert cfg.backend == CaptureBackend.DXCAM
        assert cfg.region == region
        assert cfg.output_format == "rgb"


class TestScreenCaptureInit:
    def test_init_with_config(self) -> None:
        cfg = CaptureConfig(backend=CaptureBackend.DXCAM)
        sc = ScreenCapture(config=cfg)
        assert sc.config is cfg
        assert sc.closed is False

    def test_init_with_kwargs(self) -> None:
        sc = ScreenCapture(backend="dxcam", output_format="rgb")
        assert sc.config.backend == CaptureBackend.DXCAM
        assert sc.config.output_format == "rgb"

    def test_init_default(self) -> None:
        sc = ScreenCapture()
        assert sc.config.backend == CaptureBackend.MSS
        assert sc.config.region is None
        assert sc.config.output_format == "bgr"


class TestScreenCaptureLifecycle:
    def test_context_manager(self) -> None:
        fake_mss = MagicMock()
        fake_mss.monitors = [{"left": 0, "top": 0, "width": 1920, "height": 1080}]
        fake_shot = MagicMock()
        fake_shot.mode = "RGBA"
        fake_mss.grab.return_value = fake_shot

        with patch("td_executor.runtime.capture.mss", create=True) as mss_mod:
            mss_mod.mss.return_value = fake_mss
            with patch.dict(sys.modules, {"mss": mss_mod}):
                with ScreenCapture() as sc:
                    assert sc._backend_impl is not None
                assert sc.closed is True

    def test_close_idempotent(self) -> None:
        sc = ScreenCapture()
        sc._closed = True
        sc.close()
        assert sc.closed is True

    def test_start_after_close_raises(self) -> None:
        sc = ScreenCapture()
        sc._closed = True
        with pytest.raises(RuntimeError, match="已关闭"):
            sc.start()


class TestScreenCaptureMss:
    def _make_fake_mss(self) -> MagicMock:
        fake_mss = MagicMock()
        fake_mss.monitors = [{"left": 0, "top": 0, "width": 1920, "height": 1080}]
        rgba = np.zeros((1080, 1920, 4), dtype=np.uint8)
        rgba[:, :, 3] = 255
        fake_shot = MagicMock()
        fake_shot.mode = "RGBA"
        fake_mss.grab.return_value = fake_shot
        return fake_mss, rgba

    def test_capture_full_screen_bgr(self) -> None:
        fake_mss, rgba = self._make_fake_mss()
        with patch.dict(sys.modules, {"mss": MagicMock(mss=MagicMock(return_value=fake_mss))}):
            sc = ScreenCapture()
            with patch.object(sc, "_init_mss"):
                sc._backend_impl = fake_mss
                with patch("numpy.array", return_value=rgba):
                    result = sc.capture_frame()
                    assert isinstance(result, np.ndarray)

    def test_capture_with_region(self) -> None:
        fake_mss, rgba = self._make_fake_mss()
        region = {"left": 100, "top": 100, "width": 800, "height": 600}
        with patch.dict(sys.modules, {"mss": MagicMock(mss=MagicMock(return_value=fake_mss))}):
            sc = ScreenCapture(region=region)
            with patch.object(sc, "_init_mss"):
                sc._backend_impl = fake_mss
                with patch("numpy.array", return_value=rgba):
                    result = sc.capture_frame()
                    fake_mss.grab.assert_called_with(region)

    def test_capture_rgb_output(self) -> None:
        fake_mss, rgba = self._make_fake_mss()
        with patch.dict(sys.modules, {"mss": MagicMock(mss=MagicMock(return_value=fake_mss))}):
            sc = ScreenCapture(output_format="rgb")
            with patch.object(sc, "_init_mss"):
                sc._backend_impl = fake_mss
                with patch("numpy.array", return_value=rgba):
                    result = sc.capture_frame()
                    assert isinstance(result, np.ndarray)


class TestScreenCaptureDxcam:
    def test_dxcam_import_error(self) -> None:
        sc = ScreenCapture(backend="dxcam")
        with patch.dict(sys.modules, {"dxcam": None}):
            with pytest.raises(ImportError, match="dxcam"):
                sc.start()


class TestScreenCaptureClosedProtection:
    def test_capture_after_close_raises(self) -> None:
        sc = ScreenCapture()
        sc._closed = True
        with pytest.raises(RuntimeError, match="已关闭"):
            sc.capture_frame()


class TestScreenCaptureLazyInit:
    def test_lazy_init_on_capture(self) -> None:
        fake_mss = MagicMock()
        fake_mss.monitors = [{"left": 0, "top": 0, "width": 1920, "height": 1080}]
        rgba = np.zeros((1080, 1920, 4), dtype=np.uint8)
        rgba[:, :, 3] = 255
        fake_shot = MagicMock()
        fake_shot.mode = "RGBA"
        fake_mss.grab.return_value = fake_shot

        mss_mod = MagicMock()
        mss_mod.mss.return_value = fake_mss

        with patch.dict(sys.modules, {"mss": mss_mod}):
            sc = ScreenCapture()
            assert sc._backend_impl is None
            with patch("numpy.array", return_value=rgba):
                sc.capture_frame()
            assert sc._backend_impl is not None
