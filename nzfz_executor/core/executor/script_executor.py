"""塔防脚本动作执行器（P2-10）。"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from nzfz_executor.core.actions.models import (
    ClickAction,
    KeyPressAction,
    MouseButton,
    MouseDragAction,
)
from nzfz_executor.core.executor.options import ExecutorLaunchOptions
from nzfz_executor.core.executor.runtime_context import ExecutorRuntimeContext
from nzfz_executor.core.executor.script_execution_state import ScriptExecutionState
from nzfz_executor.core.scripts.constants import (
    DEFAULT_MAP_RESET_SEQUENCE,
    DEFAULT_RETRY_INTERVAL_MS,
    REGION_ENTER_ACTION_TYPES,
    SCRIPT_EXECUTION_MODE_SEQUENTIAL,
    SCRIPT_EXECUTION_MODE_SINGLE_WAVE,
    UNSUPPORTED_ENABLED_ACTION_TYPES_BASIC,
    DEFAULT_WAIT_AFTER_SELECT_TRAP_MS,
)
from nzfz_executor.core.scripts.models import (
    RatioPoint,
    ScriptAction,
    ScriptDefinition,
    ScriptIndexes,
    SlotDefinition,
    TrapDefinition,
    WaveDefinition,
)


@dataclass(frozen=True)
class ScriptExecutorCallbacks:
    log: Callable[[str], None]
    progress: Callable[[int, str], None]
    is_stop_requested: Callable[[], bool]


@dataclass(frozen=True)
class ActionExecutionResult:
    success: bool
    stopped: bool = False
    message: str = ""


@dataclass(frozen=True)
class ScriptExecutionResult:
    success: bool
    stopped: bool = False
    message: str = ""


class ScriptExecutor:
    """Basic Profile 脚本执行器。"""

    _WAIT_SLICE_MS = 100

    def __init__(self) -> None:
        self._state = ScriptExecutionState()

    def execute(
        self,
        script: ScriptDefinition,
        indexes: ScriptIndexes,
        context: ExecutorRuntimeContext,
        options: ExecutorLaunchOptions,
        callbacks: ScriptExecutorCallbacks,
    ) -> ScriptExecutionResult:
        self._state = ScriptExecutionState()
        self._script = script
        self._indexes = indexes
        self._context = context
        self._options = options
        self._callbacks = callbacks

        self._log(
            f"[Script] schema_version={script.schema_version}, "
            f"profile={script.compatibility.profile}",
        )
        self._log("[Script] Basic Profile: manual_wave_driver enabled")
        self._log(
            "[Script] 注意：Basic Profile 不执行 OCR、conditions、verify",
        )
        self._log(f"[Script] execution_mode={options.script_execution_mode}")

        waves, wave_error = self._select_waves(script, options)
        if wave_error:
            self._log(f"[Script] {wave_error}")
            return ScriptExecutionResult(success=False, message=wave_error)

        total_actions = sum(
            1
            for wave in waves
            for action in wave.actions
            if action.enabled
        )
        if total_actions == 0:
            self._log("[Script] 没有 enabled=true 的 action 需要执行")

        completed_actions = 0
        for wave in waves:
            if self._check_stop():
                return ScriptExecutionResult(success=False, stopped=True, message="已停止")

            self._log(f"[Wave] 开始执行 wave={wave.wave} {wave.name}")
            for action in wave.actions:
                if self._check_stop():
                    return ScriptExecutionResult(
                        success=False,
                        stopped=True,
                        message="已停止",
                    )

                if not action.enabled:
                    if action.type in UNSUPPORTED_ENABLED_ACTION_TYPES_BASIC:
                        reason = f"basic profile 暂不支持 {action.type}"
                    else:
                        reason = "enabled=false"
                    self._log(
                        f"[Action] {action.action_id} {action.type} disabled, skip. "
                        f"reason={reason}",
                    )
                    continue

                result = self._execute_action_with_retry(action)
                if result.stopped:
                    return ScriptExecutionResult(
                        success=False,
                        stopped=True,
                        message=result.message or "已停止",
                    )
                if not result.success:
                    policy = self._on_fail_policy(action)
                    if policy == "fail":
                        return ScriptExecutionResult(
                            success=False,
                            message=result.message or "动作执行失败",
                        )
                    self._log(
                        f"[Action] {action.action_id} 失败，on_fail=skip，继续执行",
                    )

                completed_actions += 1
                if total_actions > 0:
                    percent = int(completed_actions / total_actions * 100)
                    self._progress(percent, f"已完成 action {action.action_id}")

            self._state.executed_waves.add(wave.wave)

        self._log("[Script] 执行完成")
        self._progress(100, "脚本执行完成")
        return ScriptExecutionResult(success=True, message="脚本执行完成")

    def _select_waves(
        self,
        script: ScriptDefinition,
        options: ExecutorLaunchOptions,
    ) -> tuple[list[WaveDefinition], str | None]:
        if options.script_execution_mode == SCRIPT_EXECUTION_MODE_SEQUENTIAL:
            self._log(
                "manual_wave_driver: sequential，按脚本顺序模拟触发 wave。",
            )
            return list(script.waves), None

        if options.script_execution_mode == SCRIPT_EXECUTION_MODE_SINGLE_WAVE:
            wave_num = options.script_single_wave
            selected = [
                wave for wave in script.waves if wave.wave == wave_num
            ]
            if not selected:
                return [], f"执行失败：未找到 wave={wave_num}"
            self._log(
                f"manual_wave_driver: single_wave，"
                f"手动模拟 wave={wave_num} trigger 满足。",
            )
            return selected, None

        return [], f"不支持的 execution_mode：{options.script_execution_mode}"

    def _execute_action_with_retry(
        self,
        action: ScriptAction,
    ) -> ActionExecutionResult:
        retry = action.raw.get("retry") or {}
        max_attempts = int(
            retry.get(
                "max_attempts",
                self._script.runtime.default_retry_count,
            )
            or 1,
        )
        max_attempts = max(1, max_attempts)
        interval_ms = int(retry.get("interval_ms", DEFAULT_RETRY_INTERVAL_MS))

        if retry.get("reset_view_before_retry"):
            self._log(
                f"[Retry] reset_view_before_retry=true 已忽略："
                f"action_id={action.action_id}",
            )
        if retry.get("micro_adjust_on_retry"):
            self._log(
                f"[Retry] micro_adjust_on_retry=true 已忽略："
                f"action_id={action.action_id}",
            )

        last_result = ActionExecutionResult(success=False, message="未执行")
        for attempt in range(1, max_attempts + 1):
            self._log(
                f"[Action] {action.action_id} {action.type} "
                f"{action.name} attempt={attempt}/{max_attempts}",
            )
            last_result = self._dispatch_action(action)
            if last_result.success or last_result.stopped:
                return last_result
            if attempt < max_attempts:
                self._log(
                    f"[Retry] action_id={action.action_id} 将在 "
                    f"{interval_ms}ms 后重试",
                )
                wait_result = self._wait_ms(interval_ms)
                if wait_result.stopped:
                    return wait_result

        return last_result

    def _dispatch_action(self, action: ScriptAction) -> ActionExecutionResult:
        action_type = action.type
        if action_type == "log":
            return self._execute_log_action(action)
        if action_type == "wait":
            return self._execute_wait_action(action)
        if action_type == "pan_to_region":
            return self._execute_pan_to_region_action(action)
        if action_type == "place_trap":
            return self._execute_place_trap_action(action)
        return ActionExecutionResult(
            success=False,
            message=f"不支持的 action 类型：{action_type}",
        )

    def _execute_log_action(self, action: ScriptAction) -> ActionExecutionResult:
        level = str(action.raw.get("level", "info"))
        message = str(action.raw.get("message", action.name))
        self._log(f"[Log:{level}] {message}")
        return ActionExecutionResult(success=True)

    def _execute_wait_action(self, action: ScriptAction) -> ActionExecutionResult:
        duration_ms = int(action.raw.get("duration_ms", 0))
        self._log(f"[Action] {action.action_id} wait duration={duration_ms}ms")
        return self._wait_ms(duration_ms)

    def _execute_pan_to_region_action(
        self,
        action: ScriptAction,
    ) -> ActionExecutionResult:
        region_id = str(action.raw.get("region_id", ""))
        return self._enter_region(region_id)

    def _execute_place_trap_action(
        self,
        action: ScriptAction,
    ) -> ActionExecutionResult:
        trap_id = str(action.raw.get("trap_id", ""))
        slot_id = str(action.raw.get("slot_id", ""))

        trap = self._indexes.traps_by_id.get(trap_id)
        slot = self._indexes.slots_by_id.get(slot_id)
        if trap is None or slot is None:
            return ActionExecutionResult(
                success=False,
                message=f"place_trap 引用无效：trap_id={trap_id}, slot_id={slot_id}",
            )

        self._warn_conditions(action)
        self._warn_verify(action)

        ensure_result = self._ensure_region(slot.region_id)
        if not ensure_result.success:
            return ensure_result

        key_result = self._press_select_key(trap, action)
        if not key_result.success:
            return key_result

        wait_result = self._wait_ms(DEFAULT_WAIT_AFTER_SELECT_TRAP_MS)
        if wait_result.stopped:
            return wait_result

        click_result = self._click_slot(slot, action)
        if not click_result.success:
            return click_result

        wait_ms = self._script.runtime.wait_after_place_ms
        self._log(f"[PlaceTrap] wait_after_place_ms={wait_ms}")
        wait_result = self._wait_ms(wait_ms)
        if wait_result.stopped:
            return wait_result

        self._state.current_region_id = slot.region_id
        return ActionExecutionResult(success=True)

    def _ensure_region(self, region_id: str) -> ActionExecutionResult:
        current = self._state.current_region_id
        self._log(
            f"[Region] ensure_region: target={region_id}, current={current}",
        )
        if current == region_id:
            self._log("[Region] 当前已在目标 region，跳过导航")
            return ActionExecutionResult(success=True)
        return self._enter_region(region_id)

    def _enter_region(self, region_id: str) -> ActionExecutionResult:
        region = self._indexes.regions_by_id.get(region_id)
        if region is None:
            return ActionExecutionResult(
                success=False,
                message=f"region_id 不存在：{region_id}",
            )

        self._log(f"[Region] 进入 region={region_id} ({region.name})")
        for enter_action in region.enter_actions:
            if self._check_stop():
                return ActionExecutionResult(success=False, stopped=True)

            action_type = str(enter_action.get("type", ""))
            if action_type not in REGION_ENTER_ACTION_TYPES:
                self._log(
                    f"[Region] 跳过不支持的 enter_action 类型：{action_type}",
                )
                continue

            if action_type == "reset_view_to_origin":
                result = self._run_reset_sequence()
                if not result.success:
                    return result
            elif action_type == "drag_ratio":
                result = self._execute_drag_ratio(enter_action)
                if not result.success:
                    return result
            elif action_type == "wait":
                duration_ms = int(enter_action.get("duration_ms", 0))
                wait_result = self._wait_ms(duration_ms)
                if not wait_result.success:
                    return wait_result

        wait_ms = self._script.runtime.wait_after_pan_ms
        wait_result = self._wait_ms(wait_ms)
        if wait_result.stopped:
            return wait_result

        self._state.current_region_id = region_id
        self._log(f"[Region] current_region_id={region_id}")
        return ActionExecutionResult(success=True)

    def _execute_drag_ratio(
        self,
        enter_action: dict[str, Any],
    ) -> ActionExecutionResult:
        viewport = self._context.connected_context.window_rect
        mapper = self._context.coordinate_mapper
        from_point = self._parse_ratio_dict(enter_action.get("from"))
        to_point = self._parse_ratio_dict(enter_action.get("to"))
        from_screen = mapper.ratio_to_screen_point(viewport, from_point)
        to_screen = mapper.ratio_to_screen_point(viewport, to_point)
        duration_ms = int(enter_action.get("duration_ms", 300))
        repeat = max(1, int(enter_action.get("repeat", 1)))

        drag_action = MouseDragAction(
            start=from_screen,
            end=to_screen,
            duration_ms=duration_ms,
            button=MouseButton.LEFT,
        )
        for index in range(repeat):
            if self._check_stop():
                return ActionExecutionResult(success=False, stopped=True)

            result = self._context.mouse_controller.drag(
                drag_action,
                context=self._context.connected_context,
                log=self._log,
            )
            if not result.success:
                return ActionExecutionResult(
                    success=False,
                    message=result.message,
                )
            if result.message:
                self._log(result.message)
            if repeat > 1:
                self._log(
                    f"[Region] drag_ratio repeat {index + 1}/{repeat}",
                )

        return ActionExecutionResult(success=True)

    def _run_reset_sequence(self) -> ActionExecutionResult:
        self._log("[Region] reset_view_to_origin sequence start")
        for step in DEFAULT_MAP_RESET_SEQUENCE:
            if self._check_stop():
                return ActionExecutionResult(success=False, stopped=True)

            step_type = str(step.get("type", ""))
            if step_type == "press_key":
                key = str(step.get("key", ""))
                press_result = self._context.keyboard_controller.press(
                    KeyPressAction(key=key),
                    context=self._context.connected_context,
                    log=self._log,
                )
                if not press_result.success:
                    return ActionExecutionResult(
                        success=False,
                        message=press_result.message,
                    )
                if press_result.message:
                    self._log(press_result.message)

                wait_ms = int(step.get("wait_ms", 0))
                if wait_ms > 0:
                    self._log(f"[Wait] {wait_ms}ms")
                    wait_result = self._wait_ms(wait_ms)
                    if not wait_result.success:
                        return wait_result
            elif step_type == "wait":
                duration_ms = int(step.get("duration_ms", 0))
                self._log(f"[Wait] {duration_ms}ms")
                wait_result = self._wait_ms(duration_ms)
                if not wait_result.success:
                    return wait_result
            else:
                self._log(
                    f"[Region] reset sequence 跳过未知步骤类型：{step_type}",
                )

        origin = self._script.map.initial_view.origin_region_id
        self._state.current_region_id = origin
        self._log(
            f"[Region] reset_view_to_origin completed -> "
            f"current_region_id={origin}",
        )
        self._log(
            "[Region][Warning] P2-11 暂无 map_ui_detection，"
            "无法确认地图视野是否真的回到 origin",
        )
        return ActionExecutionResult(success=True)

    def _press_select_key(
        self,
        trap: TrapDefinition,
        action: ScriptAction,
    ) -> ActionExecutionResult:
        self._log(
            f"[PlaceTrap] trap={trap.trap_id} select_key={trap.select_key}",
        )
        press_result = self._context.keyboard_controller.press(
            KeyPressAction(key=trap.select_key),
            context=self._context.connected_context,
            log=self._log,
        )
        if not press_result.success:
            return ActionExecutionResult(
                success=False,
                message=press_result.message,
            )
        if press_result.message:
            self._log(press_result.message)
        return ActionExecutionResult(success=True)

    def _click_slot(
        self,
        slot: SlotDefinition,
        action: ScriptAction,
    ) -> ActionExecutionResult:
        viewport = self._context.connected_context.window_rect
        screen_point = self._context.coordinate_mapper.ratio_to_screen_point(
            viewport,
            slot.position,
        )
        self._log(
            f"[PlaceTrap] slot={slot.slot_id} "
            f"ratio=({slot.position.x_ratio:.3f},{slot.position.y_ratio:.3f}) "
            f"screen=({screen_point.x},{screen_point.y})",
        )

        click_action = ClickAction(point=screen_point, button=MouseButton.LEFT)
        result = self._context.mouse_controller.click(
            click_action,
            context=self._context.connected_context,
            log=self._log,
        )
        if not result.success:
            return ActionExecutionResult(success=False, message=result.message)

        self._log(result.message or f"[Mouse] click at ({screen_point.x},{screen_point.y})")
        return ActionExecutionResult(success=True)

    def _wait_ms(self, duration_ms: int) -> ActionExecutionResult:
        remaining_ms = max(0, duration_ms)
        while remaining_ms > 0:
            if self._check_stop():
                return ActionExecutionResult(success=False, stopped=True)
            slice_ms = min(self._WAIT_SLICE_MS, remaining_ms)
            time.sleep(slice_ms / 1000)
            remaining_ms -= slice_ms
        return ActionExecutionResult(success=True)

    def _warn_conditions(self, action: ScriptAction) -> None:
        conditions = action.raw.get("conditions")
        if conditions:
            self._log(
                "Basic Profile 当前不执行 conditions，已视为通过："
                f"action_id={action.action_id}",
            )

    def _warn_verify(self, action: ScriptAction) -> None:
        verify = action.raw.get("verify")
        if verify:
            self._log(
                f"action.verify 存在，Basic Profile 将跳过："
                f"action_id={action.action_id}",
            )

    def _on_fail_policy(self, action: ScriptAction) -> str:
        on_fail = action.raw.get("on_fail") or {}
        policy = str(on_fail.get("policy", "skip"))
        return policy if policy in {"skip", "fail"} else "skip"

    @staticmethod
    def _parse_ratio_dict(raw: Any) -> RatioPoint:
        data = raw if isinstance(raw, dict) else {}
        return RatioPoint(
            x_ratio=float(data.get("x_ratio", 0)),
            y_ratio=float(data.get("y_ratio", 0)),
        )

    def _log(self, message: str) -> None:
        self._callbacks.log(message)

    def _progress(self, percent: int, message: str) -> None:
        self._callbacks.progress(percent, message)

    def _check_stop(self) -> bool:
        return self._callbacks.is_stop_requested()
