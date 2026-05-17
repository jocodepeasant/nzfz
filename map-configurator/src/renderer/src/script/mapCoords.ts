import type { ProjectFloor, RatioRect, SlotRow, SlotDefaults } from './types'

export const DEFAULT_CONTENT_RECT: RatioRect = {
  x_ratio: 0,
  y_ratio: 0,
  w_ratio: 1,
  h_ratio: 1
}

export const DEFAULT_EDITOR_VIEW = { panX: 0, panY: 0, scale: 1 }

export const DEFAULT_SLOT_DEFAULTS: SlotDefaults = {
  markerRadiusPx: 0.5,
  checkHalfSizePx: 1,
  clickTolerancePx: 1
}

export function normalizeContentRect(rect?: RatioRect): RatioRect {
  if (!rect) return { ...DEFAULT_CONTENT_RECT }
  return {
    x_ratio: clamp01(rect.x_ratio),
    y_ratio: clamp01(rect.y_ratio),
    w_ratio: Math.max(0.01, Math.min(1, rect.w_ratio)),
    h_ratio: Math.max(0.01, Math.min(1, rect.h_ratio))
  }
}

export function getFloorContentRect(floor?: ProjectFloor): RatioRect {
  return normalizeContentRect(floor?.contentRect)
}

export function getFloorEditorView(floor?: ProjectFloor) {
  const v = floor?.editorView
  return {
    panX: v?.panX ?? 0,
    panY: v?.panY ?? 0,
    scale: v?.scale && v.scale > 0 ? v.scale : 1
  }
}

/** Click on full image (0–1) → position inside content rect (0–1), clamped. */
export function imageNormToContentNorm(
  imageX: number,
  imageY: number,
  content: RatioRect
): { x: number; y: number } {
  const x = (imageX - content.x_ratio) / content.w_ratio
  const y = (imageY - content.y_ratio) / content.h_ratio
  return { x: clamp01(x), y: clamp01(y) }
}

/** Content-relative (0–1) → position on full image (0–1). */
export function contentNormToImageNorm(
  contentX: number,
  contentY: number,
  content: RatioRect
): { x: number; y: number } {
  return {
    x: content.x_ratio + contentX * content.w_ratio,
    y: content.y_ratio + contentY * content.h_ratio
  }
}

export function contentCenter(content: RatioRect): { x: number; y: number } {
  return { x: 0.5, y: 0.5 }
}

export function checkAreaFromContentCenter(
  cx: number,
  cy: number,
  halfSizePx: number,
  content: RatioRect,
  imgWidth: number,
  imgHeight: number
): RatioRect {
  const contentW = Math.max(1, content.w_ratio * imgWidth)
  const contentH = Math.max(1, content.h_ratio * imgHeight)
  const wRatio = (halfSizePx * 2) / contentW
  const hRatio = (halfSizePx * 2) / contentH
  return {
    x_ratio: clamp01(cx - wRatio / 2),
    y_ratio: clamp01(cy - hRatio / 2),
    w_ratio: Math.min(1, wRatio),
    h_ratio: Math.min(1, hRatio)
  }
}

export function halfSizePxFromCheckArea(
  check: RatioRect,
  content: RatioRect,
  imgWidth: number,
  imgHeight: number
): number {
  const contentW = Math.max(1, content.w_ratio * imgWidth)
  const halfW = (check.w_ratio * contentW) / 2
  return Math.round(halfW) || DEFAULT_SLOT_DEFAULTS.checkHalfSizePx
}

export function applySlotPosition(
  slot: SlotRow,
  contentX: number,
  contentY: number,
  content: RatioRect,
  imgWidth: number,
  imgHeight: number,
  defaults: SlotDefaults,
  checkHalfSizePx?: number
): SlotRow {
  const half = checkHalfSizePx ?? defaults.checkHalfSizePx
  return {
    ...slot,
    position: { x_ratio: clamp01(contentX), y_ratio: clamp01(contentY) },
    precision: {
      ...slot.precision,
      click_tolerance_px: slot.precision?.click_tolerance_px ?? defaults.clickTolerancePx
    },
    verify: {
      ...slot.verify,
      check_area: checkAreaFromContentCenter(
        clamp01(contentX),
        clamp01(contentY),
        half,
        content,
        imgWidth,
        imgHeight
      )
    }
  }
}

export function resolveImageSize(
  naturalWidth: number,
  naturalHeight: number,
  mapMeta: Record<string, unknown>
): { width: number; height: number } {
  if (naturalWidth > 0 && naturalHeight > 0) {
    return { width: naturalWidth, height: naturalHeight }
  }
  const br = mapMeta.base_resolution as { width?: number; height?: number } | undefined
  return { width: br?.width ?? 1920, height: br?.height ?? 1080 }
}

function clamp01(n: number): number {
  return Math.min(1, Math.max(0, n))
}
