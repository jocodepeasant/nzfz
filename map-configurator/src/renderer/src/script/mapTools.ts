import type { SlotDefaults } from './types'

export type MapViewport = {
  panX: number
  panY: number
  scale: number
}

export const DEFAULT_MAP_VIEWPORT: MapViewport = { panX: 0, panY: 0, scale: 1 }

export type PlaceSlotPending = SlotDefaults

export type MapToolMode =
  | { kind: 'idle' }
  | { kind: 'placeSlot'; pending: PlaceSlotPending }
  | { kind: 'drawRoi'; pendingRoiId: string }
  | { kind: 'calibrateContentRect' }

export function idleTool(): MapToolMode {
  return { kind: 'idle' }
}

export function placeSlotTool(defaults: SlotDefaults): MapToolMode {
  return { kind: 'placeSlot', pending: { ...defaults } }
}

export function toolLabel(mode: MapToolMode): string {
  switch (mode.kind) {
    case 'idle':
      return '浏览'
    case 'placeSlot':
      return '放置槽位'
    case 'drawRoi':
      return `框选 ROI: ${mode.pendingRoiId}`
    case 'calibrateContentRect':
      return '标定有效区域'
  }
}

export function rectFromDrag(
  x0: number,
  y0: number,
  x1: number,
  y1: number
): { x_ratio: number; y_ratio: number; w_ratio: number; h_ratio: number } {
  const x = Math.min(x0, x1)
  const y = Math.min(y0, y1)
  const w = Math.abs(x1 - x0)
  const h = Math.abs(y1 - y0)
  return {
    x_ratio: x,
    y_ratio: y,
    w_ratio: Math.max(0.01, w),
    h_ratio: Math.max(0.01, h)
  }
}
