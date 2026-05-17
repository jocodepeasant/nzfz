import { useEffect, useRef, useState } from 'react'
import type {
  EditorSelection,
  PanMapAction,
  ProjectFileV1,
  ProjectFloor,
  RatioRect,
  SlotDefaults,
  TowerDefenseScript
} from './script/types'
import {
  applySlotPosition,
  DEFAULT_SLOT_DEFAULTS,
  getFloorContentRect,
  halfSizePxFromCheckArea,
  resolveImageSize
} from './script/mapCoords'
import {
  filterSlotsForFloor,
  regionFloorId
} from './script/projectUtils'
import {
  addRoi,
  listRoiKeys,
  removeRoi,
  resolvePendingRoiId,
  validateRoiId
} from './script/roiUtils'
import { WavesEditor } from './WavesEditor'
import { JsonEditor } from './JsonEditor'

type InspectorPanelProps = {
  script: TowerDefenseScript
  projectFile: ProjectFileV1
  projectRoot: string | null
  activeFloorId: string
  defaultFloorId: string
  activeFloor?: ProjectFloor
  slotDefaults: SlotDefaults
  selection: EditorSelection
  rawJson: string
  jsonError: string | null
  setScriptAndSync: (fn: (p: TowerDefenseScript) => TowerDefenseScript) => void
  onSelect: (sel: EditorSelection) => void
  onProjectFileChange: (pf: ProjectFileV1) => void
  onActiveFloorChange: (floorId: string) => void
  onAddFloor: () => void
  onImportFloorImage: () => void
  onSaveProjectMeta: () => void
  onPatchActiveFloor: (patch: Partial<ProjectFloor>) => void
  onRawJsonChange: (text: string) => void
  onValidate: () => void
  onExport: () => void
  onSaveAs: () => void
  onOpenScript: () => void
  pendingRoiId: string
  onPendingRoiIdChange: (id: string) => void
  onStartDrawRoi: (roiId: string) => void
}

export function InspectorPanel({
  script,
  projectFile,
  projectRoot,
  activeFloorId,
  defaultFloorId,
  activeFloor,
  slotDefaults,
  selection,
  rawJson,
  jsonError,
  setScriptAndSync,
  onSelect,
  onProjectFileChange,
  onActiveFloorChange,
  onAddFloor,
  onImportFloorImage,
  onSaveProjectMeta,
  onPatchActiveFloor,
  onRawJsonChange,
  onValidate,
  onExport,
  onSaveAs,
  onOpenScript,
  pendingRoiId,
  onPendingRoiIdChange,
  onStartDrawRoi
}: InspectorPanelProps): JSX.Element {
  const slotRowRef = useRef<HTMLTableRowElement | null>(null)
  const mapMeta = script.map as Record<string, unknown>
  const contentRect = getFloorContentRect(activeFloor)
  const roiKeys = listRoiKeys(script)
  const imgSize = resolveImageSize(0, 0, mapMeta)

  const floorSlots = filterSlotsForFloor(script.slots, activeFloorId, defaultFloorId)
  const floorRegions = script.regions.filter(
    (r) => regionFloorId(r, defaultFloorId) === activeFloorId || r.region_id === 'origin'
  )

  useEffect(() => {
    if (selection.kind === 'slot' && slotRowRef.current) {
      slotRowRef.current.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    }
  }, [selection])

  const updateFloor = (floorId: string, patch: Partial<ProjectFileV1['floors'][0]>) => {
    onProjectFileChange({
      ...projectFile,
      floors: projectFile.floors.map((f) => (f.floor_id === floorId ? { ...f, ...patch } : f))
    })
  }

  return (
    <aside className="inspector-panel">
      <details open>
        <summary>楼层</summary>
        <div className="inspector-block">
          <div className="floor-chips">
            {projectFile.floors.map((f) => (
              <button
                key={f.floor_id}
                type="button"
                className={activeFloorId === f.floor_id ? 'floor-chip active' : 'floor-chip'}
                onClick={() => onActiveFloorChange(f.floor_id)}
              >
                {f.name || f.floor_id}
              </button>
            ))}
            <button type="button" className="floor-chip add" onClick={onAddFloor}>
              + 楼层
            </button>
          </div>
          {projectFile.floors
            .filter((f) => f.floor_id === activeFloorId)
            .map((f) => (
              <div key={f.floor_id} className="grid-form">
                <label>
                  名称
                  <input
                    value={f.name}
                    onChange={(e) => updateFloor(f.floor_id, { name: e.target.value })}
                  />
                </label>
                <p className="hint">底图：{f.imageRelative ?? '（未导入）'}</p>
                <p className="hint">
                  地图滚轮缩放、空格/中键平移仅影响查看，不写入 JSON。有效区域请用地图工具「标定有效区域」或下方数值。
                </p>
                {(['x_ratio', 'y_ratio', 'w_ratio', 'h_ratio'] as const).map((field) => (
                  <label key={field}>
                    content {field}
                    <input
                      type="number"
                      step={0.01}
                      value={contentRect[field]}
                      onChange={(e) =>
                        onPatchActiveFloor({
                          contentRect: { ...contentRect, [field]: Number(e.target.value) }
                        })
                      }
                    />
                  </label>
                ))}
              </div>
            ))}
          <div className="grid-form">
            <label>
              默认显示半径
              <input
                type="number"
                step="any"
                value={slotDefaults.markerRadiusPx}
                onChange={(e) =>
                  onProjectFileChange({
                    ...projectFile,
                    slotDefaults: {
                      ...slotDefaults,
                      markerRadiusPx: Number(e.target.value) || DEFAULT_SLOT_DEFAULTS.markerRadiusPx
                    }
                  })
                }
              />
            </label>
            <label>
              默认识别半边长
              <input
                type="number"
                step="any"
                value={slotDefaults.checkHalfSizePx}
                onChange={(e) =>
                  onProjectFileChange({
                    ...projectFile,
                    slotDefaults: {
                      ...slotDefaults,
                      checkHalfSizePx: Number(e.target.value) || DEFAULT_SLOT_DEFAULTS.checkHalfSizePx
                    }
                  })
                }
              />
            </label>
            <label>
              默认点击容差
              <input
                type="number"
                step="any"
                value={slotDefaults.clickTolerancePx}
                onChange={(e) =>
                  onProjectFileChange({
                    ...projectFile,
                    slotDefaults: {
                      ...slotDefaults,
                      clickTolerancePx: Number(e.target.value) || DEFAULT_SLOT_DEFAULTS.clickTolerancePx
                    }
                  })
                }
              />
            </label>
          </div>
          <div className="row">
            <button type="button" disabled={!projectRoot} onClick={onImportFloorImage}>
              导入当前楼层底图
            </button>
            <button type="button" disabled={!projectRoot} onClick={onSaveProjectMeta}>
              保存 project.json
            </button>
          </div>
        </div>
      </details>

      <details open>
        <summary>元数据</summary>
        <div className="inspector-block grid-form">
          <label>
            script_id
            <input
              value={script.script_id}
              onChange={(e) => setScriptAndSync((p) => ({ ...p, script_id: e.target.value }))}
            />
          </label>
          <label>
            script_name
            <input
              value={script.script_name}
              onChange={(e) => setScriptAndSync((p) => ({ ...p, script_name: e.target.value }))}
            />
          </label>
          <label>
            map_id
            <input
              value={String(mapMeta.map_id ?? '')}
              onChange={(e) =>
                setScriptAndSync((p) => ({
                  ...p,
                  map: { ...((p.map as object) ?? {}), map_id: e.target.value }
                }))
              }
            />
          </label>
          <label>
            map_name
            <input
              value={String(mapMeta.map_name ?? '')}
              onChange={(e) =>
                setScriptAndSync((p) => ({
                  ...p,
                  map: { ...((p.map as object) ?? {}), map_name: e.target.value }
                }))
              }
            />
          </label>
          <label>
            difficulty
            <input
              value={String(mapMeta.difficulty ?? '')}
              onChange={(e) =>
                setScriptAndSync((p) => ({
                  ...p,
                  map: { ...((p.map as object) ?? {}), difficulty: e.target.value }
                }))
              }
            />
          </label>
          <label>
            strategy_id
            <input
              value={String(mapMeta.strategy_id ?? '')}
              onChange={(e) =>
                setScriptAndSync((p) => ({
                  ...p,
                  map: { ...((p.map as object) ?? {}), strategy_id: e.target.value }
                }))
              }
            />
          </label>
        </div>
      </details>

      <details>
        <summary>区域（当前楼层）</summary>
        <div className="inspector-block">
          <p className="hint region-help">
            区域是局内可拖拽的视野分区（不是地图上的框）。slot.region_id 绑定区域；波次 pan_to_region
            会执行下方 enter_actions 拖地图对齐视野后再放陷阱。origin 为打开地图后的初始视野。
          </p>
          <button
            type="button"
            onClick={() =>
              setScriptAndSync((p) => ({
                ...p,
                regions: [
                  ...p.regions,
                  {
                    region_id: `region_${p.regions.length + 1}`,
                    name: '新区域',
                    description: '',
                    enter_actions: [],
                    floor_id: activeFloorId
                  }
                ]
              }))
            }
          >
            添加区域
          </button>
          <table className="data-table">
            <thead>
              <tr>
                <th>region_id</th>
                <th>name</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {floorRegions.map((r, i) => {
                const globalIdx = script.regions.indexOf(r)
                const selected =
                  selection.kind === 'region' && selection.regionId === r.region_id
                return (
                  <tr
                    key={`${r.region_id}-${i}`}
                    className={selected ? 'row-selected' : ''}
                    onClick={() => onSelect({ kind: 'region', regionId: r.region_id })}
                  >
                    <td>
                      <input
                        value={r.region_id}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) =>
                          setScriptAndSync((p) => {
                            const regions = [...p.regions]
                            regions[globalIdx] = { ...regions[globalIdx], region_id: e.target.value }
                            return { ...p, regions }
                          })
                        }
                      />
                    </td>
                    <td>
                      <input
                        value={r.name}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) =>
                          setScriptAndSync((p) => {
                            const regions = [...p.regions]
                            regions[globalIdx] = { ...regions[globalIdx], name: e.target.value }
                            return { ...p, regions }
                          })
                        }
                      />
                    </td>
                    <td>
                      <button
                        type="button"
                        disabled={r.region_id === 'origin'}
                        onClick={(e) => {
                          e.stopPropagation()
                          setScriptAndSync((p) => ({
                            ...p,
                            regions: p.regions.filter((_, j) => j !== globalIdx)
                          }))
                        }}
                      >
                        删
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {selection.kind === 'region' &&
            (() => {
              const r = script.regions.find((x) => x.region_id === selection.regionId)
              if (!r || r.region_id === 'origin') return null
              const globalIdx = script.regions.indexOf(r)
              const panActions = r.enter_actions.filter(
                (a): a is PanMapAction => (a as PanMapAction).type === 'pan_map'
              )
              const setPanActions = (actions: PanMapAction[]) => {
                setScriptAndSync((p) => {
                  const regions = [...p.regions]
                  regions[globalIdx] = { ...regions[globalIdx], enter_actions: actions }
                  return { ...p, regions }
                })
              }
              return (
                <div className="pan-actions-editor">
                  <button
                    type="button"
                    className="danger-btn"
                    onClick={() => {
                      if (!confirm(`删除区域「${r.region_id}」？`)) return
                      setScriptAndSync((p) => ({
                        ...p,
                        regions: p.regions.filter((_, j) => j !== globalIdx)
                      }))
                      onSelect({ kind: 'none' })
                    }}
                  >
                    删除该区域
                  </button>
                  <p className="hint">进入区域 enter_actions（pan_map）</p>
                  {panActions.map((a, ai) => (
                    <div key={ai} className="pan-action-row grid-form">
                      <label>
                        direction
                        <input
                          value={a.direction}
                          onChange={(e) => {
                            const next = [...panActions]
                            next[ai] = { ...a, direction: e.target.value }
                            setPanActions(next)
                          }}
                        />
                      </label>
                      <label>
                        distance_ratio
                        <input
                          type="number"
                          step={0.05}
                          value={a.distance_ratio}
                          onChange={(e) => {
                            const next = [...panActions]
                            next[ai] = { ...a, distance_ratio: Number(e.target.value) }
                            setPanActions(next)
                          }}
                        />
                      </label>
                      <label>
                        duration_ms
                        <input
                          type="number"
                          value={a.duration_ms}
                          onChange={(e) => {
                            const next = [...panActions]
                            next[ai] = { ...a, duration_ms: Number(e.target.value) || 0 }
                            setPanActions(next)
                          }}
                        />
                      </label>
                      <label>
                        repeat
                        <input
                          type="number"
                          min={1}
                          value={a.repeat}
                          onChange={(e) => {
                            const next = [...panActions]
                            next[ai] = { ...a, repeat: Number(e.target.value) || 1 }
                            setPanActions(next)
                          }}
                        />
                      </label>
                      <button
                        type="button"
                        onClick={() => setPanActions(panActions.filter((_, j) => j !== ai))}
                      >
                        删步骤
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={() =>
                      setPanActions([
                        ...panActions,
                        {
                          type: 'pan_map',
                          direction: 'left',
                          distance_ratio: 0.3,
                          duration_ms: 600,
                          repeat: 1
                        }
                      ])
                    }
                  >
                    添加 pan_map
                  </button>
                </div>
              )
            })()}
        </div>
      </details>

      <details open>
        <summary>槽位（当前楼层）</summary>
        <div className="inspector-block">
          <p className="hint">须先点地图工具「放置槽位」，再在地图上点击；坐标相对有效地图区域。</p>
          {selection.kind === 'slot' &&
            (() => {
              const s = script.slots.find((x) => x.slot_id === selection.slotId)
              if (!s) return null
              const globalIdx = script.slots.indexOf(s)
              const half = halfSizePxFromCheckArea(
                s.verify.check_area,
                contentRect,
                imgSize.width,
                imgSize.height
              )
              return (
                <div className="grid-form slot-size-editor">
                  <label>
                    显示半径 px
                    <input
                      type="number"
                      min={2}
                      value={s.editor_marker_radius_px ?? slotDefaults.markerRadiusPx}
                      onChange={(e) => {
                        const v = Number(e.target.value) || slotDefaults.markerRadiusPx
                        setScriptAndSync((p) => {
                          const slots = [...p.slots]
                          slots[globalIdx] = { ...slots[globalIdx], editor_marker_radius_px: v }
                          return { ...p, slots }
                        })
                      }}
                    />
                  </label>
                  <label>
                    识别半边长 px
                    <input
                      type="number"
                      min={2}
                      value={half}
                      onChange={(e) => {
                        const h = Number(e.target.value) || slotDefaults.checkHalfSizePx
                        setScriptAndSync((p) => {
                          const slots = [...p.slots]
                          const slot = slots[globalIdx]
                          slots[globalIdx] = applySlotPosition(
                            slot,
                            slot.position.x_ratio,
                            slot.position.y_ratio,
                            contentRect,
                            imgSize.width,
                            imgSize.height,
                            slotDefaults,
                            h
                          )
                          return { ...p, slots }
                        })
                      }}
                    />
                  </label>
                  <label>
                    点击容差 px
                    <input
                      type="number"
                      min={0}
                      value={s.precision.click_tolerance_px}
                      onChange={(e) => {
                        setScriptAndSync((p) => {
                          const slots = [...p.slots]
                          slots[globalIdx] = {
                            ...slots[globalIdx],
                            precision: {
                              ...slots[globalIdx].precision,
                              click_tolerance_px: Number(e.target.value) || 0
                            }
                          }
                          return { ...p, slots }
                        })
                      }}
                    />
                  </label>
                </div>
              )
            })()}
          <table className="data-table">
            <thead>
              <tr>
                <th>slot_id</th>
                <th>region</th>
                <th>trap</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {floorSlots.map((s) => {
                const globalIdx = script.slots.findIndex((x) => x.slot_id === s.slot_id)
                const selected = selection.kind === 'slot' && selection.slotId === s.slot_id
                return (
                  <tr
                    key={s.slot_id}
                    ref={selected ? slotRowRef : undefined}
                    className={selected ? 'row-selected' : ''}
                    onClick={() => onSelect({ kind: 'slot', slotId: s.slot_id })}
                  >
                    <td>
                      <input
                        value={s.slot_id}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) =>
                          setScriptAndSync((p) => {
                            const slots = [...p.slots]
                            slots[globalIdx] = { ...slots[globalIdx], slot_id: e.target.value }
                            return { ...p, slots }
                          })
                        }
                      />
                    </td>
                    <td>
                      <select
                        value={s.region_id}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) =>
                          setScriptAndSync((p) => {
                            const slots = [...p.slots]
                            slots[globalIdx] = { ...slots[globalIdx], region_id: e.target.value }
                            return { ...p, slots }
                          })
                        }
                      >
                        {script.regions.map((r) => (
                          <option key={r.region_id} value={r.region_id}>
                            {r.region_id}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <select
                        value={s.default_trap}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) =>
                          setScriptAndSync((p) => {
                            const slots = [...p.slots]
                            slots[globalIdx] = { ...slots[globalIdx], default_trap: e.target.value }
                            return { ...p, slots }
                          })
                        }
                      >
                        {script.traps.map((t) => (
                          <option key={t.trap_id} value={t.trap_id}>
                            {t.trap_id}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          setScriptAndSync((p) => ({
                            ...p,
                            slots: p.slots.filter((_, j) => j !== globalIdx)
                          }))
                          if (selection.kind === 'slot' && selection.slotId === s.slot_id) {
                            onSelect({ kind: 'none' })
                          }
                        }}
                      >
                        删
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </details>

      <details open={selection.kind === 'roi'}>
        <summary>识别 ROI</summary>
        <div className="inspector-block">
          <p className="hint">
            ROI 为局内 HUD 屏幕比例（示意叠在底图上）。执行器按 id 裁剪 OCR。与底图 content_rect 独立。
          </p>
          <div className="row">
            <input
              placeholder="ROI id（如 wave）"
              value={pendingRoiId}
              onChange={(e) => onPendingRoiIdChange(e.target.value)}
            />
            <button
              type="button"
              onClick={() => {
                const id = resolvePendingRoiId(script, pendingRoiId)
                if (id !== pendingRoiId.trim()) onPendingRoiIdChange(id)
                if (!script.recognition.rois[id]) {
                  setScriptAndSync((p) => addRoi(p, id))
                }
                onStartDrawRoi(id)
              }}
            >
              在地图上框选
            </button>
          </div>
        </div>
        <div className="inspector-block roi-grid">
          {roiKeys.map((key) => {
            const rect = script.recognition.rois[key] ?? {
              x_ratio: 0,
              y_ratio: 0,
              w_ratio: 0.1,
              h_ratio: 0.05
            }
            const selected = selection.kind === 'roi' && selection.key === key
            const setRect = (patch: Partial<typeof rect>) => {
              setScriptAndSync((p) => ({
                ...p,
                recognition: {
                  ...p.recognition,
                  rois: {
                    ...p.recognition.rois,
                    [key]: { ...rect, ...patch }
                  }
                }
              }))
            }
            return (
              <fieldset
                key={key}
                className={`roi-fieldset ${selected ? 'roi-selected' : ''}`}
                onClick={() => onSelect({ kind: 'roi', key })}
              >
                <legend>
                  {script.recognition.roi_labels?.[key] ?? key}
                  <button
                    type="button"
                    className="roi-del"
                    onClick={(e) => {
                      e.stopPropagation()
                      if (confirm(`删除 ROI「${key}」？`)) {
                        setScriptAndSync((p) => removeRoi(p, key))
                        if (selection.kind === 'roi' && selection.key === key) {
                          onSelect({ kind: 'none' })
                        }
                      }
                    }}
                  >
                    ×
                  </button>
                </legend>
                <label>
                  显示名
                  <input
                    value={script.recognition.roi_labels?.[key] ?? ''}
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) =>
                      setScriptAndSync((p) => ({
                        ...p,
                        recognition: {
                          ...p.recognition,
                          roi_labels: {
                            ...(p.recognition.roi_labels ?? {}),
                            [key]: e.target.value
                          }
                        }
                      }))
                    }
                  />
                </label>
                <label>
                  x
                  <input
                    type="number"
                    step={0.01}
                    value={rect.x_ratio}
                    onChange={(e) => setRect({ x_ratio: Number(e.target.value) })}
                  />
                </label>
                <label>
                  y
                  <input
                    type="number"
                    step={0.01}
                    value={rect.y_ratio}
                    onChange={(e) => setRect({ y_ratio: Number(e.target.value) })}
                  />
                </label>
                <label>
                  w
                  <input
                    type="number"
                    step={0.01}
                    value={rect.w_ratio}
                    onChange={(e) => setRect({ w_ratio: Number(e.target.value) })}
                  />
                </label>
                <label>
                  h
                  <input
                    type="number"
                    step={0.01}
                    value={rect.h_ratio}
                    onChange={(e) => setRect({ h_ratio: Number(e.target.value) })}
                  />
                </label>
              </fieldset>
            )
          })}
        </div>
      </details>

      <details>
        <summary>波次</summary>
        <WavesEditor script={script} setScriptAndSync={setScriptAndSync} />
      </details>

      <details>
        <summary>导出</summary>
        <div className="inspector-block row">
          <button type="button" onClick={onValidate}>
            校验
          </button>
          <button type="button" disabled={!projectRoot} onClick={onExport}>
            写入 export/script.json
          </button>
          <button type="button" onClick={onSaveAs}>
            另存为…
          </button>
          <button type="button" onClick={onOpenScript}>
            打开外部 JSON
          </button>
        </div>
      </details>

      <details>
        <summary>高级 JSON</summary>
        <div className="inspector-block json-panel">
          {jsonError && <p className="errors-inline">{jsonError}</p>}
          <JsonEditor className="json-editor" value={rawJson} onChange={onRawJsonChange} />
        </div>
      </details>
    </aside>
  )
}
