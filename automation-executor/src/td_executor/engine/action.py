"""放置 / 升级 / 拆除等动作执行。"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

try:
    from pynput.keyboard import Controller as KeyboardController, Key

    _PYNPUT_AVAILABLE = True
except ImportError:
    KeyboardController = None  # type: ignore[assignment, misc]
    Key = None  # type: ignore[assignment, misc]
    _PYNPUT_AVAILABLE = False

try:
    import pyautogui

    _PYAUTOGUI_AVAILABLE = True
except Exception:
    pyautogui = None  # type: ignore[assignment]
    _PYAUTOGUI_AVAILABLE = False

_SPECIAL_KEY_MAP: dict[str, Any] = {}

_KNOWN_ACTION_TYPES = {"place_trap", "upgrade_trap", "remove_trap", "pan_to_region", "log"}

MAP_OPEN_WAIT_MS = 800
MAP_OPEN_MAX_RETRIES = 3

def _build_special_key_map() -> dict[str, Any]:
    if not _PYNPUT_AVAILABLE or Key is None:
        return {}
    mapping: dict[str, Any] = {}
    for attr_name in dir(Key):
        if attr_name.startswith("_"):
            continue
        mapping[attr_name.lower()] = getattr(Key, attr_name)
    return mapping

_SPECIAL_KEY_MAP = _build_special_key_map()

def _resolve_key(key: str) -> Any:
    if key.lower() in _SPECIAL_KEY_MAP:
        return _SPECIAL_KEY_MAP[key.lower()]
    if len(key) == 1:
        return key
    return key


def press_key(key: str, hold_ms: int = 0) -> None:
    if not _PYNPUT_AVAILABLE or KeyboardController is None:
        logger.warning("pynput is not available; cannot press key '%s'", key)
        raise RuntimeError(f"pynput is not available; cannot press key '{key}'")
    kb = KeyboardController()
    resolved = _resolve_key(key)
    kb.press(resolved)
    if hold_ms > 0:
        time.sleep(hold_ms / 1000.0)
    kb.release(resolved)


def click_at(x: int, y: int, button: str = "left") -> None:
    if not _PYAUTOGUI_AVAILABLE or pyautogui is None:
        logger.warning("pyautogui is not available; cannot click at (%d, %d)", x, y)
        raise RuntimeError(f"pyautogui is not available; cannot click at ({x}, {y})")
    pyautogui.click(x=x, y=y, button=button)


def drag(from_x: int, from_y: int, to_x: int, to_y: int, duration_ms: int = 600) -> None:
    if not _PYAUTOGUI_AVAILABLE or pyautogui is None:
        logger.warning("pyautogui is not available; cannot drag from (%d, %d) to (%d, %d)", from_x, from_y, to_x, to_y)
        raise RuntimeError(
            f"pyautogui is not available; cannot drag from ({from_x}, {from_y}) to ({to_x}, {to_y})"
        )
    duration_s = duration_ms / 1000.0
    pyautogui.moveTo(from_x, from_y, duration=0.0)
    pyautogui.mouseDown(button="left")
    pyautogui.moveTo(to_x, to_y, duration=duration_s)
    pyautogui.mouseUp(button="left")


def ensure_map_open(capture: Any, rect: Any, rois: dict) -> bool:
    from td_executor.vision.detector import VisionDetector

    detector = VisionDetector()
    if detector.is_map_ui_open(capture, rect, rois):
        return True
    for _ in range(MAP_OPEN_MAX_RETRIES):
        press_key("o")
        time.sleep(MAP_OPEN_WAIT_MS / 1000.0)
        if detector.is_map_ui_open(capture, rect, rois):
            return True
    logger.warning("Failed to open map UI after %d retries", MAP_OPEN_MAX_RETRIES)
    return False


def execute_action(action: dict, context: dict) -> dict:
    action_type = action.get("type", "")
    if action_type == "log":
        message = action.get("message", "")
        logger.info("[log] %s", message)
        return {"success": True, "skipped": False}
    if action_type in _KNOWN_ACTION_TYPES:
        return {"success": False, "skipped": False, "error": f"not implemented: {action_type}"}
    logger.warning("Unknown action type: %s", action_type)
    return {"success": False, "skipped": False, "error": f"unknown action type: {action_type}"}
