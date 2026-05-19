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


def press_key(key: str, hold_ms: int = 0, overlay=None, hwnd: int = 0) -> None:
    if hwnd:
        from td_executor.runtime.input import send_key
        send_key(hwnd, key, hold_ms)
    elif _PYNPUT_AVAILABLE and KeyboardController is not None:
        kb = KeyboardController()
        resolved = _resolve_key(key)
        kb.press(resolved)
        if hold_ms > 0:
            time.sleep(hold_ms / 1000.0)
        kb.release(resolved)
    else:
        raise RuntimeError(f"pynput is not available; cannot press key '{key}'")
    if overlay is not None:
        overlay.draw_key_info(key, hold_ms)


def click_at(x: int, y: int, button: str = "left", overlay=None, hwnd: int = 0, rect_left: int = 0, rect_top: int = 0) -> None:
    if hwnd:
        from td_executor.runtime.input import send_click
        send_click(hwnd, x - rect_left, y - rect_top, button)
    elif _PYAUTOGUI_AVAILABLE and pyautogui is not None:
        pyautogui.click(x=x, y=y, button=button)
    else:
        raise RuntimeError(f"pyautogui is not available; cannot click at ({x}, {y})")
    if overlay is not None:
        overlay.draw_click_marker(x, y)


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


def ensure_map_open(capture: Any, rect: Any, rois: dict, context=None) -> bool:
    if capture is None or rect is None:
        return False
    from td_executor.vision.detector import VisionDetector
    detector = VisionDetector()
    if detector.is_map_ui_open(capture, rect, rois):
        return True
    overlay = (context or {}).get("overlay")
    hwnd = rect.hwnd if hasattr(rect, 'hwnd') else 0
    for _ in range(MAP_OPEN_MAX_RETRIES):
        try:
            press_key("o", overlay=overlay, hwnd=hwnd)
        except RuntimeError:
            logger.warning("press_key unavailable in ensure_map_open")
            return False
        time.sleep(MAP_OPEN_WAIT_MS / 1000.0)
        if detector.is_map_ui_open(capture, rect, rois):
            return True
    logger.warning("Failed to open map UI after %d retries", MAP_OPEN_MAX_RETRIES)
    return False


class ActionExecutor:
    def __init__(self, runtime_defaults: dict | None = None, detector: Any | None = None) -> None:
        from td_executor.engine.retry import RetryManager
        from td_executor.engine.condition import ConditionEngine
        from td_executor.vision.detector import VisionDetector

        self._retry_manager = RetryManager(runtime_defaults=runtime_defaults)
        self._detector = detector or VisionDetector()
        self._condition_engine = ConditionEngine(detector=self._detector)

    def execute(self, action: dict, context: dict) -> dict:
        action_type = action.get("type", "")
        if action_type == "log":
            message = action.get("message", "")
            logger.info("[log] %s", message)
            return {"success": True, "skipped": False}
        if action_type == "place_trap":
            return self._execute_place_trap(action, context)
        if action_type == "upgrade_trap":
            return self._execute_upgrade_trap(action, context)
        if action_type == "remove_trap":
            return self._execute_remove_trap(action, context)
        if action_type == "pan_to_region":
            return self._execute_pan_to_region(action, context)
        logger.warning("Unknown action type: %s", action_type)
        return {"success": False, "skipped": False, "error": f"unknown action type: {action_type}"}

    def _build_verify_fn(self, action: dict, context: dict):
        verify = action.get("verify", {})
        if not verify:
            return lambda _result: True
        verify_type = verify.get("type", "")
        capture = context.get("capture")
        rect = context.get("rect")
        slots = context.get("slots", [])
        if verify_type == "slot_has_trap":
            slot_id = verify.get("slot_id", "")
            slot_info = None
            for s in slots:
                if s.get("slot_id") == slot_id:
                    slot_info = s
                    break
            slot_verify = (slot_info or {}).get("verify", {})
            def _verify_slot_occupied(_result) -> bool:
                return self._detector.is_slot_occupied(capture, rect, slot_verify)
            return _verify_slot_occupied
        if verify_type == "slot_empty":
            slot_id = verify.get("slot_id", "")
            slot_info = None
            for s in slots:
                if s.get("slot_id") == slot_id:
                    slot_info = s
                    break
            slot_verify = (slot_info or {}).get("verify", {})
            def _verify_slot_empty(_result) -> bool:
                return self._detector.is_slot_empty(capture, rect, slot_verify)
            return _verify_slot_empty
        if verify_type == "trap_level_gte":
            trap_id = verify.get("trap_id", "")
            level = verify.get("level", 0)
            required = verify.get("required", True)
            state = context.get("state") or {}
            trap_levels = state.get("trap_levels", {})
            def _verify_trap_level(_result) -> bool:
                current = trap_levels.get(trap_id)
                if current is not None:
                    return current >= level
                return not required
            return _verify_trap_level
        logger.warning("Unknown verify type: %s", verify_type)
        required = verify.get("required", True)
        return lambda _result: not required

    def _check_conditions(self, action: dict, context: dict) -> dict | None:
        from td_executor.engine.condition import ConditionContext

        conditions = action.get("conditions")
        if not conditions:
            return None
        capture = context.get("capture")
        rect = context.get("rect")
        rois = context.get("rois", {})
        slots = context.get("slots", [])
        traps = context.get("traps", [])
        state = context.get("state")
        multi_frame = context.get("multi_frame")
        ctx = ConditionContext(
            capture=capture, rect=rect, rois=rois,
            slots=slots, traps=traps, state=state, multi_frame=multi_frame,
        )
        if self._condition_engine.eval_conditions(conditions, ctx):
            return None
        on_cf_config = self._retry_manager.resolve_on_condition_failed(action)
        if on_cf_config.policy.value == "skip":
            return {"success": False, "skipped": True}
        condition_fn = lambda: self._condition_engine.eval_conditions(conditions, ctx)
        waited = self._retry_manager.wait_for_condition(condition_fn, on_cf_config)
        if not waited:
            then = on_cf_config.then
            if then == "retry_condition":
                return {"success": False, "skipped": True}
            return {"success": False, "skipped": True}
        return None

    def _find_trap(self, traps: list[dict], trap_id: str) -> dict | None:
        for t in traps:
            if t.get("trap_id") == trap_id:
                return t
        return None

    def _execute_place_trap(self, action: dict, context: dict) -> dict:
        from td_executor.engine.navigator import pan_to_region as nav_pan_to_region
        from td_executor.engine.navigator import go_to_origin
        from td_executor.engine.retry import RetryConfig
        from td_executor.engine.slot import click_slot, locate_slot

        capture = context.get("capture")
        rect = context.get("rect")
        rois = context.get("rois", {})
        slots = context.get("slots", [])
        traps = context.get("traps", [])
        regions = context.get("regions", [])
        runtime = context.get("runtime", {})

        slot_id = action.get("slot_id", "")
        trap_id = action.get("trap_id", "")

        if not ensure_map_open(capture, rect, rois, context=context):
            return {"success": False, "skipped": False, "error": "map not open"}

        info = locate_slot(slot_id, rect, slots)
        if not info:
            return {"success": False, "skipped": False, "error": f"slot not found: {slot_id}"}

        if not nav_pan_to_region(info["region_id"], rect, regions, capture, rois, runtime):
            return {"success": False, "skipped": False, "error": f"pan_to_region failed: {info['region_id']}"}

        cond_result = self._check_conditions(action, context)
        if cond_result is not None:
            return cond_result

        trap = self._find_trap(traps, trap_id)
        if trap is None:
            return {"success": False, "skipped": False, "error": f"trap not found: {trap_id}"}

        select_key = trap.get("select_key", "")
        wait_after = runtime.get("wait_after_place_ms", 600)

        retry_config = self._retry_manager.resolve_retry_config(action.get("retry"))
        on_fail_config = self._retry_manager.resolve_on_fail(action.get("on_fail"))
        verify_fn = self._build_verify_fn(action, context)

        reset_fn = None
        if retry_config.reset_view_before_retry:
            def reset_fn():
                go_to_origin(capture, rect, rois, runtime)
                nav_pan_to_region(info["region_id"], rect, regions, capture, rois, runtime)

        micro_fn = None
        if retry_config.micro_adjust_on_retry:
            def micro_fn():
                click_slot(slot_id, rect, slots, micro_adjust=True, overlay=context.get("overlay"), hwnd=rect.hwnd)

        def action_fn():
            press_key(select_key, overlay=context.get("overlay"), hwnd=rect.hwnd)
            click_slot(slot_id, rect, slots, overlay=context.get("overlay"), hwnd=rect.hwnd)
            time.sleep(wait_after / 1000.0)

        result = self._retry_manager.execute_with_retry(
            action_fn=action_fn,
            verify_fn=verify_fn,
            retry_config=retry_config,
            on_fail_config=on_fail_config,
            reset_view_fn=reset_fn,
            micro_adjust_fn=micro_fn,
        )

        if result.success:
            state = context.setdefault("state", {})
            trap_levels = state.setdefault("trap_levels", {})
            trap_levels[trap_id] = 1

        return {"success": result.success, "skipped": result.skipped, "attempts": result.attempts}

    def _execute_upgrade_trap(self, action: dict, context: dict) -> dict:
        from td_executor.engine.retry import RetryConfig

        capture = context.get("capture")
        rect = context.get("rect")
        rois = context.get("rois", {})
        traps = context.get("traps", [])
        runtime = context.get("runtime", {})

        trap_id = action.get("trap_id", "")
        target_level = action.get("target_level", 0)

        if not ensure_map_open(capture, rect, rois, context=context):
            return {"success": False, "skipped": False, "error": "map not open"}

        cond_result = self._check_conditions(action, context)
        if cond_result is not None:
            return cond_result

        trap = self._find_trap(traps, trap_id)
        if trap is None:
            return {"success": False, "skipped": False, "error": f"trap not found: {trap_id}"}

        execute_config = action.get("execute", {})
        method = execute_config.get("method", "")
        if method == "hold_key":
            key = execute_config.get("key", trap.get("upgrade_key", ""))
            hold_ms = execute_config.get("hold_ms", trap.get("upgrade_hold_ms", 4000))
        else:
            key = trap.get("upgrade_key", "")
            hold_ms = trap.get("upgrade_hold_ms", 4000)

        wait_after = runtime.get("wait_after_upgrade_ms", 1000)

        retry_config = self._retry_manager.resolve_retry_config(action.get("retry"))
        on_fail_config = self._retry_manager.resolve_on_fail(action.get("on_fail"))
        verify_fn = self._build_verify_fn(action, context)

        def action_fn():
            press_key(key, hold_ms=hold_ms, overlay=context.get("overlay"), hwnd=rect.hwnd)
            time.sleep(wait_after / 1000.0)

        result = self._retry_manager.execute_with_retry(
            action_fn=action_fn,
            verify_fn=verify_fn,
            retry_config=retry_config,
            on_fail_config=on_fail_config,
        )

        if result.success:
            state = context.setdefault("state", {})
            trap_levels = state.setdefault("trap_levels", {})
            trap_levels[trap_id] = target_level

        return {"success": result.success, "skipped": result.skipped, "attempts": result.attempts}

    def _execute_remove_trap(self, action: dict, context: dict) -> dict:
        from td_executor.engine.navigator import pan_to_region as nav_pan_to_region
        from td_executor.engine.navigator import go_to_origin
        from td_executor.engine.retry import RetryConfig
        from td_executor.engine.slot import click_slot, locate_slot

        capture = context.get("capture")
        rect = context.get("rect")
        rois = context.get("rois", {})
        slots = context.get("slots", [])
        regions = context.get("regions", [])
        runtime = context.get("runtime", {})
        traps = context.get("traps", [])

        slot_id = action.get("slot_id", "")

        if not ensure_map_open(capture, rect, rois, context=context):
            return {"success": False, "skipped": False, "error": "map not open"}

        info = locate_slot(slot_id, rect, slots)
        if not info:
            return {"success": False, "skipped": False, "error": f"slot not found: {slot_id}"}

        if not nav_pan_to_region(info["region_id"], rect, regions, capture, rois, runtime):
            return {"success": False, "skipped": False, "error": f"pan_to_region failed: {info['region_id']}"}

        cond_result = self._check_conditions(action, context)
        if cond_result is not None:
            return cond_result

        execute_config = action.get("execute", {})
        method = execute_config.get("method", "")
        steps = execute_config.get("steps", [])

        if method == "custom_steps" and steps:
            logger.warning("custom_steps not implemented for remove_trap")
            return {"success": False, "skipped": True, "error": "custom_steps not implemented"}

        wait_after = runtime.get("wait_after_remove_ms", 600)

        retry_config = self._retry_manager.resolve_retry_config(action.get("retry"))
        on_fail_config = self._retry_manager.resolve_on_fail(action.get("on_fail"))
        verify_fn = self._build_verify_fn(action, context)

        reset_fn = None
        if retry_config.reset_view_before_retry:
            def reset_fn():
                go_to_origin(capture, rect, rois, runtime)
                nav_pan_to_region(info["region_id"], rect, regions, capture, rois, runtime)

        def action_fn():
            click_slot(slot_id, rect, slots, overlay=context.get("overlay"), hwnd=rect.hwnd)
            time.sleep(wait_after / 1000.0)

        result = self._retry_manager.execute_with_retry(
            action_fn=action_fn,
            verify_fn=verify_fn,
            retry_config=retry_config,
            on_fail_config=on_fail_config,
            reset_view_fn=reset_fn,
        )

        if result.success:
            state = context.get("state") or {}
            trap_levels = state.get("trap_levels", {})
            trap_id_to_remove = None
            for tid, lvl in list(trap_levels.items()):
                slot_trap = None
                for s in slots:
                    if s.get("slot_id") == slot_id and s.get("default_trap") == tid:
                        slot_trap = tid
                        break
                if slot_trap:
                    trap_id_to_remove = slot_trap
                    break
            if trap_id_to_remove and trap_id_to_remove in trap_levels:
                del trap_levels[trap_id_to_remove]

        return {"success": result.success, "skipped": result.skipped, "attempts": result.attempts}

    def _execute_pan_to_region(self, action: dict, context: dict) -> dict:
        from td_executor.engine.navigator import pan_to_region as nav_pan_to_region

        capture = context.get("capture")
        rect = context.get("rect")
        rois = context.get("rois", {})
        regions = context.get("regions", [])
        runtime = context.get("runtime", {})

        region_id = action.get("region_id", "")

        retry_config = self._retry_manager.resolve_retry_config(action.get("retry"))
        on_fail_config = self._retry_manager.resolve_on_fail(action.get("on_fail"))

        def action_fn():
            return nav_pan_to_region(region_id, rect, regions, capture, rois, runtime)

        def verify_fn(result):
            return result is True

        result = self._retry_manager.execute_with_retry(
            action_fn=action_fn,
            verify_fn=verify_fn,
            retry_config=retry_config,
            on_fail_config=on_fail_config,
        )

        if not result.success:
            return {"success": False, "skipped": result.skipped, "attempts": result.attempts, "error": "pan_to_region failed"}

        return {"success": True, "skipped": False, "attempts": result.attempts}


def execute_action(action: dict, context: dict) -> dict:
    executor = ActionExecutor()
    return executor.execute(action, context)
