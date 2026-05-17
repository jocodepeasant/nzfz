import type { MapViewport } from './mapTools'

const MIN_SCALE = 0.2
const MAX_SCALE = 5

export function isTypingTarget(target: EventTarget | null): boolean {
  if (!target || !(target instanceof HTMLElement)) return false
  const tag = target.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true
  if (target.isContentEditable) return true
  if (target.closest('.cm-editor')) return true
  return false
}

export function panViewport(vp: MapViewport, dx: number, dy: number): MapViewport {
  return { ...vp, panX: vp.panX + dx, panY: vp.panY + dy }
}

export function zoomViewportAt(
  vp: MapViewport,
  localX: number,
  localY: number,
  factor: number
): MapViewport {
  const nextScale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, vp.scale * factor))
  const contentX = (localX - vp.panX) / vp.scale
  const contentY = (localY - vp.panY) / vp.scale
  return {
    scale: nextScale,
    panX: localX - contentX * nextScale,
    panY: localY - contentY * nextScale
  }
}

export function pointerLocalInScroll(
  scrollEl: HTMLElement,
  clientX: number,
  clientY: number
): { localX: number; localY: number } {
  const bounds = scrollEl.getBoundingClientRect()
  return {
    localX: clientX - bounds.left + scrollEl.scrollLeft,
    localY: clientY - bounds.top + scrollEl.scrollTop
  }
}
