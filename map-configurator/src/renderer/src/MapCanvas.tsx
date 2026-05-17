import { useCallback, useEffect, useRef, useState } from 'react'
import type {
  EditorSelection,
  ProjectFloor,
  RatioRect,
  SlotDefaults,
  SlotRow,
  TowerDefenseScript
} from './script/types'
import {
  type MapToolMode,
  type MapViewport,
  type PlaceSlotPending,
  rectFromDrag,
  placeSlotTool,
  idleTool,
  toolLabel
} from './script/mapTools'
import { contentNormToImageNorm, DEFAULT_SLOT_DEFAULTS, getFloorContentRect, imageNormToContentNorm } from './script/mapCoords'
import { filterSlotsForFloor } from './script/projectUtils'
import { listRoiKeys, resolvePendingRoiId } from './script/roiUtils'
import {
  isTypingTarget,
  panViewport,
  pointerLocalInScroll,
  zoomViewportAt
} from './script/mapViewport'

const PAN_STEP = 40
const PAN_STEP_FAST = 120
const SLOT_NUDGE_PX = 4

const TRAP_COLORS = ['#58a6ff', '#3fb950', '#d29922', '#f85149', '#a371f7', '#79c0ff']

function trapColor(trapId: string, traps: TowerDefenseScript['traps']): string {
  const i = traps.findIndex((t) => t.trap_id === trapId)
  return TRAP_COLORS[(i >= 0 ? i : 0) % TRAP_COLORS.length]
}

type PointerCoords = {
  imageX: number
  imageY: number
  contentX: number
  contentY: number
}

export type { MapToolMode, MapViewport, PlaceSlotPending }

type MapCanvasProps = {
  floorDataUrl: string | null
  activeFloor?: ProjectFloor
  script: TowerDefenseScript
  activeFloorId: string
  defaultFloorId: string
  slotDefaults: SlotDefaults
  mapTool: MapToolMode
  onMapToolChange: (tool: MapToolMode) => void
  mapViewport: MapViewport
  onViewportChange: (v: MapViewport) => void
  pendingRoiId: string
  onPendingRoiIdChange: (id: string) => void
  selection: EditorSelection
  highlightRegionId: string | null
  onSelect: (sel: EditorSelection) => void
  onPlaceSlot: (contentX: number, contentY: number, pending: PlaceSlotPending) => void
  onDrawRoi: (roiId: string, rect: RatioRect) => void
  onCalibrateContentRect: (rect: RatioRect) => void
  onMoveSlot: (slotId: string, contentX: number, contentY: number) => void
  onNudgeSlot: (slotId: string, dxPx: number, dyPx: number) => void
  onDeleteMapSelection: () => void
  onImageLoad?: (width: number, height: number) => void
}

export function MapCanvas({
  floorDataUrl,
  activeFloor,
  script,
  activeFloorId,
  defaultFloorId,
  slotDefaults,
  mapTool,
  onMapToolChange,
  mapViewport,
  onViewportChange,
  pendingRoiId,
  onPendingRoiIdChange,
  selection,
  highlightRegionId,
  onSelect,
  onPlaceSlot,
  onDrawRoi,
  onCalibrateContentRect,
  onMoveSlot,
  onNudgeSlot,
  onDeleteMapSelection,
  onImageLoad
}: MapCanvasProps): JSX.Element {
  const imgRef = useRef<HTMLImageElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const slotDragRef = useRef<{ slotId: string } | null>(null)
  const drawStartRef = useRef<{ imageX: number; imageY: number } | null>(null)
  const panRef = useRef<{ startX: number; startY: number; panX: number; panY: number } | null>(null)
  const [drawPreview, setDrawPreview] = useState<RatioRect | null>(null)
  const [spaceHeld, setSpaceHeld] = useState(false)
  const [imgNatural, setImgNatural] = useState<{ w: number; h: number } | null>(null)

  useEffect(() => {
    setImgNatural(null)
  }, [floorDataUrl])

  const contentRect = getFloorContentRect(activeFloor)
  const floorSlots = filterSlotsForFloor(script.slots, activeFloorId, defaultFloorId)
  const roiKeys = listRoiKeys(script)
  const rois = script.recognition.rois
  const cr = contentRect

  const coordsFromEvent = useCallback(
    (clientX: number, clientY: number): PointerCoords | null => {
      const img = imgRef.current
      if (!img) return null
      const rect = img.getBoundingClientRect()
      if (rect.width <= 0 || rect.height <= 0) return null
      const imageX = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width))
      const imageY = Math.min(1, Math.max(0, (clientY - rect.top) / rect.height))
      const content = imageNormToContentNorm(imageX, imageY, contentRect)
      return { imageX, imageY, contentX: content.x, contentY: content.y }
    },
    [contentRect]
  )

  const panBy = useCallback(
    (dx: number, dy: number) => {
      onViewportChange(panViewport(mapViewport, dx, dy))
    },
    [mapViewport, onViewportChange]
  )

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space') {
        setSpaceHeld(true)
        e.preventDefault()
        return
      }
      if (e.key === 'Escape') {
        onMapToolChange(idleTool())
        return
      }
      if (isTypingTarget(e.target)) return

      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (
          selection.kind === 'slot' ||
          selection.kind === 'roi'
        ) {
          e.preventDefault()
          onDeleteMapSelection()
        }
        return
      }

      const arrowDx =
        e.key === 'ArrowLeft' ? -1 : e.key === 'ArrowRight' ? 1 : 0
      const arrowDy =
        e.key === 'ArrowUp' ? -1 : e.key === 'ArrowDown' ? 1 : 0
      if (arrowDx === 0 && arrowDy === 0) return

      e.preventDefault()
      const panView =
        e.shiftKey ||
        selection.kind !== 'slot' ||
        mapTool.kind !== 'idle'

      if (panView) {
        const step = e.shiftKey ? PAN_STEP_FAST : PAN_STEP
        panBy(arrowDx * step, arrowDy * step)
        return
      }

      onNudgeSlot(
        selection.slotId,
        arrowDx * SLOT_NUDGE_PX,
        arrowDy * SLOT_NUDGE_PX
      )
    }
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.code === 'Space') setSpaceHeld(false)
    }
    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('keyup', onKeyUp)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('keyup', onKeyUp)
    }
  }, [
    mapTool.kind,
    onDeleteMapSelection,
    onMapToolChange,
    onNudgeSlot,
    panBy,
    selection
  ])

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const scroll = scrollRef.current
    if (!scroll) return
    const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1
    const { localX, localY } = pointerLocalInScroll(scroll, e.clientX, e.clientY)
    onViewportChange(zoomViewportAt(mapViewport, localX, localY, factor))
  }

  const slotMarkerStyle = (slot: SlotRow) => {
    const img = contentNormToImageNorm(slot.position.x_ratio, slot.position.y_ratio, contentRect)
    const radius = slot.editor_marker_radius_px ?? slotDefaults.markerRadiusPx
    const selected = selection.kind === 'slot' && selection.slotId === slot.slot_id
    const r = selected ? radius + 2 : radius
    return {
      left: `${img.x * 100}%`,
      top: `${img.y * 100}%`,
      width: r * 2,
      height: r * 2,
      marginLeft: -r,
      marginTop: -r
    }
  }

  const isRegionHighlighted = (slot: SlotRow) =>
    highlightRegionId != null && slot.region_id === highlightRegionId

  const canDragSlot = mapTool.kind === 'idle'

  const startDraw = (imageX: number, imageY: number) => {
    drawStartRef.current = { imageX, imageY }
    setDrawPreview(rectFromDrag(imageX, imageY, imageX, imageY))
  }

  const handleOverlayPointerDown = (ev: React.PointerEvent) => {
    const isPan = ev.button === 1 || (ev.button === 0 && spaceHeld)
    if (isPan) {
      panRef.current = {
        startX: ev.clientX,
        startY: ev.clientY,
        panX: mapViewport.panX,
        panY: mapViewport.panY
      }
      return
    }
    if (ev.button !== 0) return
    if ((ev.target as HTMLElement).closest('.map-slot-marker')) return
    if ((ev.target as HTMLElement).closest('.map-roi')) return

    const p = coordsFromEvent(ev.clientX, ev.clientY)
    if (!p) return

    if (mapTool.kind === 'drawRoi') {
      startDraw(p.imageX, p.imageY)
      ;(ev.currentTarget as HTMLElement).setPointerCapture(ev.pointerId)
      return
    }
    if (mapTool.kind === 'calibrateContentRect') {
      startDraw(p.imageX, p.imageY)
      ;(ev.currentTarget as HTMLElement).setPointerCapture(ev.pointerId)
    }
  }

  const handleOverlayPointerMove = (ev: React.PointerEvent) => {
    if (panRef.current) {
      const dx = ev.clientX - panRef.current.startX
      const dy = ev.clientY - panRef.current.startY
      onViewportChange({
        ...mapViewport,
        panX: panRef.current.panX + dx,
        panY: panRef.current.panY + dy
      })
      return
    }
    if (slotDragRef.current && canDragSlot) {
      const p = coordsFromEvent(ev.clientX, ev.clientY)
      if (p) onMoveSlot(slotDragRef.current.slotId, p.contentX, p.contentY)
      return
    }
    if (drawStartRef.current) {
      const p = coordsFromEvent(ev.clientX, ev.clientY)
      if (p) {
        setDrawPreview(
          rectFromDrag(
            drawStartRef.current.imageX,
            drawStartRef.current.imageY,
            p.imageX,
            p.imageY
          )
        )
      }
    }
  }

  const handleOverlayPointerUp = (ev: React.PointerEvent) => {
    if (panRef.current) {
      panRef.current = null
      return
    }
    if (slotDragRef.current) {
      slotDragRef.current = null
      return
    }
    if (drawStartRef.current) {
      const start = drawStartRef.current
      drawStartRef.current = null
      const p = coordsFromEvent(ev.clientX, ev.clientY)
      setDrawPreview(null)
      if (!p) return
      const rect = rectFromDrag(start.imageX, start.imageY, p.imageX, p.imageY)
      if (rect.w_ratio < 0.005 && rect.h_ratio < 0.005) return
      if (mapTool.kind === 'drawRoi') {
        const roiId = mapTool.pendingRoiId.trim()
        onDrawRoi(roiId, rect)
        onSelect({ kind: 'roi', key: roiId })
        onMapToolChange(idleTool())
      } else if (mapTool.kind === 'calibrateContentRect') {
        onCalibrateContentRect(rect)
        onMapToolChange(idleTool())
      }
    }
  }

  const handleImgClick = (ev: React.MouseEvent) => {
    if (mapTool.kind !== 'placeSlot') return
    if ((ev.target as HTMLElement).closest('.map-slot-marker')) return
    const p = coordsFromEvent(ev.clientX, ev.clientY)
    if (!p) return
    onPlaceSlot(p.contentX, p.contentY, mapTool.pending)
  }

  const handleSlotPointerDown = (ev: React.PointerEvent, slotId: string) => {
    if (!canDragSlot) return
    ev.stopPropagation()
    ev.preventDefault()
    slotDragRef.current = { slotId }
    onSelect({ kind: 'slot', slotId })
    ;(ev.target as HTMLElement).setPointerCapture(ev.pointerId)
  }

  const viewportStyle = {
    transform: `translate(${mapViewport.panX}px, ${mapViewport.panY}px) scale(${mapViewport.scale})`,
    transformOrigin: '0 0'
  }

  const updatePlacePending = (patch: Partial<PlaceSlotPending>) => {
    if (mapTool.kind !== 'placeSlot') return
    onMapToolChange({ kind: 'placeSlot', pending: { ...mapTool.pending, ...patch } })
  }

  const isActive = (kind: MapToolMode['kind']) => mapTool.kind === kind

  return (
    <div
      className={`map-canvas ${mapTool.kind !== 'idle' ? 'tool-active' : ''} ${spaceHeld ? 'pan-cursor' : ''}`}
      onPointerMove={handleOverlayPointerMove}
      onPointerUp={handleOverlayPointerUp}
      onPointerLeave={handleOverlayPointerUp}
    >
      <div className="map-toolbar map-toolbar-tools">
        <button
          type="button"
          className={isActive('placeSlot') ? 'active' : ''}
          disabled={!floorDataUrl}
          onClick={() =>
            onMapToolChange(
              isActive('placeSlot') ? idleTool() : placeSlotTool(slotDefaults)
            )
          }
        >
          放置槽位
        </button>
        {mapTool.kind === 'placeSlot' && (
          <div className="map-tool-params">
            <label>
              显示半径
              <input
                type="number"
                min={0.1}
                step="any"
                value={mapTool.pending.markerRadiusPx}
                onChange={(e) =>
                  updatePlacePending({ markerRadiusPx: Number(e.target.value) || DEFAULT_SLOT_DEFAULTS.markerRadiusPx })
                }
              />
            </label>
            <label>
              识别半边长
              <input
                type="number"
                min={0.1}
                step="any"
                value={mapTool.pending.checkHalfSizePx}
                onChange={(e) =>
                  updatePlacePending({ checkHalfSizePx: Number(e.target.value) || DEFAULT_SLOT_DEFAULTS.checkHalfSizePx })
                }
              />
            </label>
            <label>
              点击容差
              <input
                type="number"
                min={0}
                step="any"
                value={mapTool.pending.clickTolerancePx}
                onChange={(e) =>
                  updatePlacePending({ clickTolerancePx: Number(e.target.value) || DEFAULT_SLOT_DEFAULTS.clickTolerancePx })
                }
              />
            </label>
          </div>
        )}
        <input
          className="roi-id-input"
          placeholder="ROI id"
          value={pendingRoiId}
          onChange={(e) => onPendingRoiIdChange(e.target.value)}
        />
        <button
          type="button"
          className={isActive('drawRoi') ? 'active' : ''}
          disabled={!floorDataUrl}
          onClick={() => {
            if (isActive('drawRoi')) {
              onMapToolChange(idleTool())
              return
            }
            const id = resolvePendingRoiId(script, pendingRoiId)
            if (id !== pendingRoiId.trim()) onPendingRoiIdChange(id)
            onMapToolChange({ kind: 'drawRoi', pendingRoiId: id })
          }}
        >
          框选 ROI
        </button>
        <button
          type="button"
          className={isActive('calibrateContentRect') ? 'active' : ''}
          disabled={!floorDataUrl}
          onClick={() =>
            onMapToolChange(
              isActive('calibrateContentRect') ? idleTool() : { kind: 'calibrateContentRect' }
            )
          }
        >
          标定有效区域
        </button>
        <button type="button" onClick={() => onMapToolChange(idleTool())}>
          取消
        </button>
        <span className="map-pan-group" title="平移视野（等同方向键）">
          <button type="button" className="map-pan-btn" disabled={!floorDataUrl} onClick={() => panBy(0, -PAN_STEP)} aria-label="上移">
            ↑
          </button>
          <span className="map-pan-row">
            <button type="button" className="map-pan-btn" disabled={!floorDataUrl} onClick={() => panBy(-PAN_STEP, 0)} aria-label="左移">
              ←
            </button>
            <button type="button" className="map-pan-btn" disabled={!floorDataUrl} onClick={() => panBy(PAN_STEP, 0)} aria-label="右移">
              →
            </button>
          </span>
          <button type="button" className="map-pan-btn" disabled={!floorDataUrl} onClick={() => panBy(0, PAN_STEP)} aria-label="下移">
            ↓
          </button>
        </span>
        <button
          type="button"
          className="map-delete-btn"
          disabled={
            !floorDataUrl ||
            mapTool.kind !== 'idle' ||
            (selection.kind !== 'slot' && selection.kind !== 'roi')
          }
          onClick={onDeleteMapSelection}
        >
          删除选中
        </button>
        <span className="hint map-tool-status">
          {toolLabel(mapTool)} · 方向键平移/移槽位 · Shift+方向键平移 · 滚轮以指针缩放 · Delete 删除
        </span>
      </div>

      {!floorDataUrl ? (
        <div className="map-placeholder">请选择工程并导入当前楼层底图</div>
      ) : (
        <div className="map-scroll" ref={scrollRef} onWheel={handleWheel}>
          <div className="map-viewport" style={viewportStyle}>
            <div
              className="map-inner"
              onPointerDown={handleOverlayPointerDown}
            >
              <img
                ref={imgRef}
                className="floor-img"
                src={floorDataUrl}
                alt="floor"
                width={imgNatural?.w}
                height={imgNatural?.h}
                draggable={false}
                onClick={handleImgClick}
                onLoad={(e) => {
                  const img = e.currentTarget
                  const w = img.naturalWidth
                  const h = img.naturalHeight
                  setImgNatural({ w, h })
                  onImageLoad?.(w, h)
                }}
              />
              <div
                className="map-content-rect"
                style={{
                  left: `${cr.x_ratio * 100}%`,
                  top: `${cr.y_ratio * 100}%`,
                  width: `${cr.w_ratio * 100}%`,
                  height: `${cr.h_ratio * 100}%`
                }}
                title="有效地图区域（槽位坐标相对此框，会写入导出 JSON）"
              />
              {drawPreview && (
                <div
                  className="map-draw-preview"
                  style={{
                    left: `${drawPreview.x_ratio * 100}%`,
                    top: `${drawPreview.y_ratio * 100}%`,
                    width: `${drawPreview.w_ratio * 100}%`,
                    height: `${drawPreview.h_ratio * 100}%`
                  }}
                />
              )}
              <div className="map-overlay" aria-hidden>
                {roiKeys.map((key) => {
                  const rect: RatioRect = rois[key]
                  const selected = selection.kind === 'roi' && selection.key === key
                  const label = script.recognition.roi_labels?.[key] ?? key
                  return (
                    <div
                      key={key}
                      className={`map-roi ${selected ? 'selected' : ''}`}
                      style={{
                        left: `${rect.x_ratio * 100}%`,
                        top: `${rect.y_ratio * 100}%`,
                        width: `${rect.w_ratio * 100}%`,
                        height: `${rect.h_ratio * 100}%`
                      }}
                      onClick={(e) => {
                        e.stopPropagation()
                        onSelect({ kind: 'roi', key })
                      }}
                      title={label}
                    >
                      <span className="map-roi-label">{label}</span>
                    </div>
                  )
                })}
                {floorSlots.map((slot) => {
                  const color = trapColor(slot.default_trap, script.traps)
                  const selected = isSlotSelected(slot.slot_id)
                  const regionHi = isRegionHighlighted(slot)
                  return (
                    <div
                      key={slot.slot_id}
                      className={`map-slot-marker ${selected ? 'selected' : ''} ${regionHi ? 'region-hi' : ''}`}
                      style={{
                        ...slotMarkerStyle(slot),
                        borderColor: color,
                        backgroundColor: selected ? color : `${color}88`
                      }}
                      onPointerDown={(e) => handleSlotPointerDown(e, slot.slot_id)}
                      title={`${slot.slot_id} · ${slot.default_trap}`}
                    >
                      <span className="map-slot-label">{slot.slot_id}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )

  function isSlotSelected(slotId: string) {
    return selection.kind === 'slot' && selection.slotId === slotId
  }
}
