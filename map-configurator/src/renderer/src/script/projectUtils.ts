import type { ProjectFileV1, ProjectFloor, RatioRect, SlotRow, TowerDefenseScript, TrapLibraryEntry } from './types'
import { DEFAULT_SLOT_DEFAULTS, getFloorContentRect, normalizeContentRect } from './mapCoords'
import { definitionFromUnknown, trapsForExport } from './trapUtils'

export function defaultProjectFile(): ProjectFileV1 {
  return {
    version: 1,
    floors: [{ floor_id: '1', name: '一层' }],
    activeFloorId: '1',
    slotDefaults: { ...DEFAULT_SLOT_DEFAULTS }
  }
}

function normalizeFloor(f: ProjectFloor): ProjectFloor {
  const { editorView: _ev, ...rest } = f
  return {
    ...rest,
    contentRect: f.contentRect ? normalizeContentRect(f.contentRect) : undefined
  }
}

export function normalizeProjectFile(raw: unknown): ProjectFileV1 {
  if (!raw || typeof raw !== 'object') {
    return defaultProjectFile()
  }
  const o = raw as Record<string, unknown>
  if (o.version !== 1) {
    return defaultProjectFile()
  }
  const legacyImage = typeof o.floorImageRelative === 'string' ? o.floorImageRelative : undefined
  let floors = Array.isArray(o.floors) ? (o.floors as ProjectFloor[]).map(normalizeFloor) : []
  if (floors.length === 0) {
    floors = [{ floor_id: '1', name: '一层', imageRelative: legacyImage }]
  } else if (legacyImage && !floors.some((f) => f.imageRelative)) {
    floors = floors.map((f, i) =>
      i === 0 && !f.imageRelative ? { ...f, imageRelative: legacyImage } : f
    )
  }
  const activeFloorId =
    typeof o.activeFloorId === 'string' && floors.some((f) => f.floor_id === o.activeFloorId)
      ? o.activeFloorId
      : floors[0]?.floor_id ?? '1'
  const slotDefaults =
    o.slotDefaults && typeof o.slotDefaults === 'object'
      ? {
          markerRadiusPx:
            Number((o.slotDefaults as SlotDefaultsLike).markerRadiusPx) ||
            DEFAULT_SLOT_DEFAULTS.markerRadiusPx,
          checkHalfSizePx:
            Number((o.slotDefaults as SlotDefaultsLike).checkHalfSizePx) ||
            DEFAULT_SLOT_DEFAULTS.checkHalfSizePx,
          clickTolerancePx:
            Number((o.slotDefaults as SlotDefaultsLike).clickTolerancePx) ||
            DEFAULT_SLOT_DEFAULTS.clickTolerancePx
        }
      : { ...DEFAULT_SLOT_DEFAULTS }
  const traps = Array.isArray(o.traps)
    ? (o.traps.map(definitionFromUnknown).filter(Boolean) as TrapLibraryEntry[])
    : undefined
  return { version: 1, floors, activeFloorId, slotDefaults, traps }
}

type SlotDefaultsLike = {
  markerRadiusPx?: number
  checkHalfSizePx?: number
  clickTolerancePx?: number
}

export function slotFloorId(slot: SlotRow, defaultId: string): string {
  return slot.floor_id ?? defaultId
}

export function regionFloorId(region: { floor_id?: string }, defaultId: string): string {
  return region.floor_id ?? defaultId
}

export function filterSlotsForFloor(slots: SlotRow[], floorId: string, defaultFloorId: string): SlotRow[] {
  return slots.filter((s) => slotFloorId(s, defaultFloorId) === floorId)
}

export function getActiveFloor(project: ProjectFileV1, floorId?: string): ProjectFloor | undefined {
  const id = floorId ?? project.activeFloorId ?? project.floors[0]?.floor_id
  return project.floors.find((f) => f.floor_id === id)
}

export function buildScriptForExport(
  script: TowerDefenseScript,
  project: ProjectFileV1
): TowerDefenseScript {
  const defaultFloorId = project.activeFloorId ?? project.floors[0]?.floor_id ?? '1'
  const map = { ...(script.map as Record<string, unknown>) }
  const defaultFloor = getActiveFloor(project, defaultFloorId)
  const defaultContent = getFloorContentRect(defaultFloor)

  if (project.floors.length > 0) {
    map.floors = project.floors.map((f) => {
      const content = getFloorContentRect(f)
      const entry: Record<string, unknown> = {
        floor_id: f.floor_id,
        name: f.name,
        ...(f.imageRelative ? { editor_reference_image: f.imageRelative } : {})
      }
      if (
        content.x_ratio !== 0 ||
        content.y_ratio !== 0 ||
        content.w_ratio !== 1 ||
        content.h_ratio !== 1 ||
        f.contentRect
      ) {
        entry.calibration = {
          content_rect: content,
          ...(f.imageRelative ? { reference_image: f.imageRelative } : {})
        }
      }
      return entry
    })
    map.default_floor_id = defaultFloorId
  }

  map.calibration = {
    content_rect: defaultContent,
    ...(defaultFloor?.imageRelative ? { reference_image: defaultFloor.imageRelative } : {})
  }

  const exportTraps =
    project.traps && project.traps.length > 0
      ? (trapsForExport(project.traps) as TowerDefenseScript['traps'])
      : script.traps

  return { ...script, map, traps: exportTraps }
}

export function nextFloorId(floors: ProjectFloor[]): string {
  const nums = floors
    .map((f) => parseInt(f.floor_id, 10))
    .filter((n) => !Number.isNaN(n))
  const max = nums.length ? Math.max(...nums) : 0
  return String(max + 1)
}
