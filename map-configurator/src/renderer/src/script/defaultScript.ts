import type { RatioRect, SlotDefaults, SlotRow, TowerDefenseScript } from './types'
import {
  checkAreaFromContentCenter,
  DEFAULT_SLOT_DEFAULTS,
  normalizeContentRect
} from './mapCoords'

const defaultRuntime = {
  max_run_minutes: 30,
  default_action_timeout_ms: 8000,
  default_retry_count: 2,
  default_resource_policy: 'wait',
  default_wait_resource_timeout_ms: 30000,
  wait_after_pan_ms: 800,
  wait_after_place_ms: 600,
  wait_after_remove_ms: 600,
  wait_after_upgrade_ms: 1000,
  reset_view_on_retry: true
}

export function createDefaultScript(): TowerDefenseScript {
  return {
    schema_version: '1.0.0',
    script_id: 'new_map_script_v1',
    script_name: '新地图脚本',
    game_mode: 'tower_defense',
    map: {
      map_id: 'new_map',
      map_name: '新地图',
      difficulty: 'normal',
      strategy_id: 'baseline',
      base_resolution: { width: 1920, height: 1080 },
      coordinate_mode: 'region_screen_ratio',
      initial_view: {
        type: 'fixed_after_open_map',
        origin_region_id: 'origin'
      }
    },
    runtime: { ...defaultRuntime },
    recognition: {
      rois: {},
      multi_frame: {}
    },
    traps: [
      {
        trap_id: 'trap_a',
        trap_name: '陷阱A',
        select_key: '1',
        upgrade_key: '1',
        upgrade_hold_ms: 4000,
        cost: 500,
        upgrade_cost: 1000,
        max_level: 3,
        upgrade_mode: 'all_same_type'
      }
    ],
    regions: [
      {
        region_id: 'origin',
        name: '初始视野',
        description: '按 O 打开地图后的默认视野',
        enter_actions: []
      },
      {
        region_id: 'main',
        name: '主战区域',
        description: '主要布防区',
        enter_actions: []
      }
    ],
    slots: [],
    waves: [
      {
        wave: 1,
        name: '第1波',
        execute_once: true,
        trigger: { type: 'wave_eq', value: 1 },
        actions: [{ type: 'log', message: '第1波开始' }]
      }
    ],
    boss_reserved: {
      enabled: false,
      description: 'BOSS 专项逻辑预留'
    },
    metadata: {
      author: '',
      description: '',
      game_version: ''
    }
  }
}

export function createSlotAt(
  slotId: string,
  name: string,
  contentX: number,
  contentY: number,
  regionId: string,
  trapId: string,
  floorId: string,
  options?: {
    defaults?: SlotDefaults
    contentRect?: RatioRect
    imgWidth?: number
    imgHeight?: number
    markerRadiusPx?: number
  }
): SlotRow {
  const defs = options?.defaults ?? DEFAULT_SLOT_DEFAULTS
  const content = normalizeContentRect(options?.contentRect)
  const imgW = options?.imgWidth ?? 1920
  const imgH = options?.imgHeight ?? 1080
  return {
    slot_id: slotId,
    name,
    region_id: regionId,
    floor_id: floorId,
    editor_marker_radius_px: options?.markerRadiusPx ?? defs.markerRadiusPx,
    position: { x_ratio: contentX, y_ratio: contentY },
    precision: {
      click_tolerance_px: defs.clickTolerancePx,
      allow_micro_adjust: true,
      micro_adjust_pattern: 'cross_5_points',
      micro_adjust_step_px: 4
    },
    slot_type: 'ground',
    default_trap: trapId,
    verify: {
      empty_method: 'template_or_color',
      occupied_method: 'image_change',
      level_method: 'level_badge',
      check_area: checkAreaFromContentCenter(
        contentX,
        contentY,
        defs.checkHalfSizePx,
        content,
        imgW,
        imgH
      )
    }
  }
}

export function scriptToJson(script: TowerDefenseScript): string {
  return JSON.stringify(script, null, 2)
}

export function parseScriptJson(text: string): TowerDefenseScript {
  const data = JSON.parse(text) as TowerDefenseScript
  if (data.game_mode !== 'tower_defense') {
    throw new Error('game_mode 必须为 tower_defense')
  }
  return data
}
