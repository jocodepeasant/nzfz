/** V1 protocol-aligned editor types (loose where schema allows extension). */

export type RatioRect = {
  x_ratio: number
  y_ratio: number
  w_ratio: number
  h_ratio: number
}

export type RatioPoint = { x_ratio: number; y_ratio: number }

export type EditorView = {
  panX: number
  panY: number
  scale: number
}

export type ProjectFloor = {
  floor_id: string
  name: string
  imageRelative?: string
  /** Map-valid area on reference image (0–1 relative to full image). */
  contentRect?: RatioRect
  /** @deprecated session-only viewport; not read or written */
  editorView?: EditorView
}

export type SlotDefaults = {
  markerRadiusPx: number
  checkHalfSizePx: number
  clickTolerancePx: number
}

export type ProjectFileV1 = {
  version: 1
  floors: ProjectFloor[]
  activeFloorId?: string
  slotDefaults?: SlotDefaults
  /** Shared trap library for all floors / export scripts in this project. */
  traps?: TrapDefinition[]
  /** @deprecated migrated to floors[] */
  floorImageRelative?: string
}

export type EditorSelection =
  | { kind: 'none' }
  | { kind: 'slot'; slotId: string }
  | { kind: 'roi'; key: string }
  | { kind: 'region'; regionId: string }
  | { kind: 'trap'; trapId: string }

export type PanMapAction = {
  type: 'pan_map'
  direction: string
  distance_ratio: number
  duration_ms: number
  repeat: number
}

export type RegionRow = {
  region_id: string
  name: string
  description: string
  enter_actions: PanMapAction[]
  floor_id?: string
}

export type TrapRow = {
  trap_id: string
  trap_name: string
  select_key: string
  upgrade_key: string
  upgrade_hold_ms: number
  cost: number
  upgrade_cost: number
  max_level: number
  upgrade_mode: string
}

/** Project-level trap with optional recognition template image. */
export type TrapDefinition = TrapRow & {
  /** Relative to project root, e.g. assets/verify_templates/trap_slow_trap.png */
  recognitionImageRelative?: string
}

export type SlotRow = {
  slot_id: string
  name: string
  region_id: string
  floor_id?: string
  /** Editor-only display radius (px); falls back to project.slotDefaults. */
  editor_marker_radius_px?: number
  position: RatioPoint
  precision: {
    click_tolerance_px: number
    allow_micro_adjust: boolean
    micro_adjust_pattern: string
    micro_adjust_step_px: number
  }
  slot_type: string
  default_trap: string
  verify: {
    empty_method: string
    occupied_method: string
    level_method: string
    check_area: RatioRect
  }
}

export type WaveTrigger = { type: string; value?: number }

export type ActionPanToRegion = {
  type: 'pan_to_region'
  region_id: string
  retry?: Record<string, unknown>
}

export type ActionPlaceTrap = {
  type: 'place_trap'
  name?: string
  trap_id: string
  slot_id: string
  conditions: Record<string, unknown>
  on_condition_failed: Record<string, unknown>
  verify: Record<string, unknown>
  retry: Record<string, unknown>
  on_fail: { policy: string }
}

export type ActionLog = { type: 'log'; message: string }

export type WaveAction = ActionPanToRegion | ActionPlaceTrap | ActionLog | Record<string, unknown>

export type WaveRow = {
  wave: number
  name: string
  execute_once: boolean
  trigger: WaveTrigger
  actions: WaveAction[]
}

export type TowerDefenseScript = {
  schema_version: string
  script_id: string
  script_name: string
  game_mode: 'tower_defense'
  map: Record<string, unknown>
  runtime: Record<string, unknown>
  recognition: {
    rois: Record<string, RatioRect>
    multi_frame: Record<string, number>
    roi_labels?: Record<string, string>
  }
  traps: TrapRow[]
  regions: RegionRow[]
  slots: SlotRow[]
  waves: WaveRow[]
  boss_reserved?: Record<string, unknown>
  metadata?: Record<string, unknown>
}
