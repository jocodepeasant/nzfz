import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { EditorSelection, ProjectFileV1, ProjectFloor, RatioRect, TowerDefenseScript, TrapLibraryEntry } from './script/types'
import {
  createDefaultScript,
  createSlotAt,
  parseScriptJson,
  scriptToJson
} from './script/defaultScript'
import {
  applySlotPosition,
  DEFAULT_SLOT_DEFAULTS,
  getFloorContentRect,
  resolveImageSize
} from './script/mapCoords'
import {
  DEFAULT_MAP_VIEWPORT,
  idleTool,
  type MapToolMode,
  type MapViewport,
  type PlaceSlotPending
} from './script/mapTools'
import { isTypingTarget } from './script/mapViewport'
import { addRoi, nextRoiId, removeRoi, validateRoiId } from './script/roiUtils'
import {
  buildScriptForExport,
  defaultProjectFile,
  getActiveFloor,
  normalizeProjectFile,
  nextFloorId
} from './script/projectUtils'
import {
  parseTrapDefinitionsFromDisk,
  projectJsonWithoutTraps,
  syncScriptTraps
} from './script/trapUtils'

type WorkspaceView = 'map' | 'trapLibrary'
import { MapCanvas } from './MapCanvas'
import { InspectorPanel } from './InspectorPanel'
import { TrapLibraryPanel } from './TrapLibraryPanel'

const viewportStorageKey = (floorId: string) => `mapConfigurator.viewport.${floorId}`

function loadViewport(floorId: string): MapViewport {
  try {
    const raw = sessionStorage.getItem(viewportStorageKey(floorId))
    if (raw) {
      const v = JSON.parse(raw) as MapViewport
      if (typeof v.scale === 'number') return v
    }
  } catch {
    /* ignore */
  }
  return { ...DEFAULT_MAP_VIEWPORT }
}

export function EditorWorkspace(): JSX.Element {
  const [projectRoot, setProjectRoot] = useState<string | null>(null)
  const [projectFile, setProjectFile] = useState<ProjectFileV1>(defaultProjectFile)
  const [script, setScript] = useState<TowerDefenseScript>(() => createDefaultScript())
  const [floorDataUrl, setFloorDataUrl] = useState<string | null>(null)
  const [rawJson, setRawJson] = useState(() => scriptToJson(createDefaultScript()))
  const [jsonError, setJsonError] = useState<string | null>(null)
  const [status, setStatus] = useState<'idle' | 'ok' | 'error'>('idle')
  const [errors, setErrors] = useState<{ path: string; message: string }[]>([])
  const [selection, setSelection] = useState<EditorSelection>({ kind: 'none' })
  const [mapTool, setMapTool] = useState<MapToolMode>(idleTool)
  const [mapViewport, setMapViewport] = useState<MapViewport>(DEFAULT_MAP_VIEWPORT)
  const [pendingRoiId, setPendingRoiId] = useState('roi_1')
  const [workspaceView, setWorkspaceView] = useState<WorkspaceView>('map')
  const imgNaturalRef = useRef({ width: 1920, height: 1080 })
  const prevTrapIdsRef = useRef<string[]>([])

  const activeFloorId = projectFile.activeFloorId ?? projectFile.floors[0]?.floor_id ?? '1'
  const defaultFloorId = activeFloorId
  const activeFloor = getActiveFloor(projectFile, activeFloorId)
  const slotDefaults = projectFile.slotDefaults ?? DEFAULT_SLOT_DEFAULTS
  const contentRect = getFloorContentRect(activeFloor)

  const highlightRegionId = useMemo(() => {
    if (selection.kind === 'region') return selection.regionId
    return null
  }, [selection])

  useEffect(() => {
    setMapViewport(loadViewport(activeFloorId))
    setMapTool(idleTool())
  }, [activeFloorId])

  useEffect(() => {
    sessionStorage.setItem(viewportStorageKey(activeFloorId), JSON.stringify(mapViewport))
  }, [mapViewport, activeFloorId])

  useEffect(() => {
    setPendingRoiId((id) => {
      const t = id.trim()
      if (!t || validateRoiId(t)) return nextRoiId(script)
      return id
    })
  }, [script.recognition.rois])

  const syncRawFromScript = useCallback((s: TowerDefenseScript) => {
    setRawJson(scriptToJson(s))
    setJsonError(null)
  }, [])

  const setScriptAndSync = useCallback(
    (updater: (prev: TowerDefenseScript) => TowerDefenseScript) => {
      setScript((prev) => {
        const next = updater(prev)
        queueMicrotask(() => syncRawFromScript(next))
        return next
      })
    },
    [syncRawFromScript]
  )

  const patchActiveFloor = useCallback(
    (patch: Partial<ProjectFloor>) => {
      setProjectFile((pf) => ({
        ...pf,
        floors: pf.floors.map((f) =>
          f.floor_id === activeFloorId ? { ...f, ...patch } : f
        )
      }))
    },
    [activeFloorId]
  )

  const loadFloorPreview = useCallback(async (root: string, rel: string | undefined) => {
    if (!rel) {
      setFloorDataUrl(null)
      return
    }
    const ex = await window.projectApi.fileExists(root, rel)
    if (!ex.exists) {
      setFloorDataUrl(null)
      return
    }
    const r = await window.projectApi.readFileBase64(root, rel)
    setFloorDataUrl(`data:${r.mime};base64,${r.base64}`)
  }, [])

  const persistProjectFile = useCallback(async (root: string, pf: ProjectFileV1) => {
    await window.projectApi.writeProjectJson(root, projectJsonWithoutTraps(pf))
  }, [])

  const handleTrapsChange = useCallback(
    (traps: TrapLibraryEntry[]) => {
      const prevIds = prevTrapIdsRef.current
      void window.trapApi.syncTrapDefinitions(traps, prevIds)
      prevTrapIdsRef.current = traps.map((t) => t.trap_id)
      setProjectFile((pf) => ({ ...pf, traps }))
      setScriptAndSync((s) => syncScriptTraps(s, traps))
    },
    [setScriptAndSync]
  )

  useEffect(() => {
    void (async () => {
      const diskResult = await window.trapApi.listTrapDefinitions()
      const traps = parseTrapDefinitionsFromDisk(diskResult.traps)
      prevTrapIdsRef.current = traps.map((t) => t.trap_id)
      setProjectFile((pf) => ({ ...pf, traps }))
      setScriptAndSync((s) => syncScriptTraps(s, traps))
    })()
  }, [setScriptAndSync])

  const openOrInitProject = useCallback(
    async (root: string) => {
      await window.projectApi.ensureDirs(root)
      const raw = (await window.projectApi.readProjectJson(root)).data
      let pf = normalizeProjectFile(raw)

      const exp = await window.projectApi.readExportScript(root)
      let nextScript: TowerDefenseScript
      if (exp.text && exp.text.trim()) {
        try {
          nextScript = parseScriptJson(exp.text)
        } catch {
          nextScript = createDefaultScript()
        }
      } else {
        nextScript = createDefaultScript()
      }

      const diskResult = await window.trapApi.listTrapDefinitions()
      const traps = parseTrapDefinitionsFromDisk(diskResult.traps)

      pf = { ...pf, traps }
      nextScript = syncScriptTraps(nextScript, traps)
      prevTrapIdsRef.current = traps.map((t) => t.trap_id)

      await persistProjectFile(root, pf)

      setScript(nextScript)
      syncRawFromScript(nextScript)
      setPendingRoiId(nextRoiId(nextScript))
      setProjectFile(pf)
      setProjectRoot(root)
      setWorkspaceView('map')
      setSelection({ kind: 'none' })
      setMapTool(idleTool())
      setStatus('idle')
      setErrors([])

      const floorId = pf.activeFloorId ?? pf.floors[0]?.floor_id ?? '1'
      const floor = pf.floors.find((f) => f.floor_id === floorId)
      await loadFloorPreview(root, floor?.imageRelative)
    },
    [loadFloorPreview, persistProjectFile, syncRawFromScript]
  )

  useEffect(() => {
    if (!projectRoot) return
    const floor = projectFile.floors.find((f) => f.floor_id === activeFloorId)
    void loadFloorPreview(projectRoot, floor?.imageRelative)
  }, [projectRoot, activeFloorId, projectFile.floors, loadFloorPreview])

  const getImgSize = () => {
    const mapMeta = script.map as Record<string, unknown>
    return resolveImageSize(imgNaturalRef.current.width, imgNaturalRef.current.height, mapMeta)
  }

  const handlePlaceSlot = (contentX: number, contentY: number, pending: PlaceSlotPending) => {
    const idx = script.slots.length + 1
    const slotId = `S${String(idx).padStart(2, '0')}`
    const regionId =
      script.regions.find((r) => r.region_id !== 'origin')?.region_id ??
      script.regions[0]?.region_id ??
      'main'
    const trapId = script.traps[0]?.trap_id ?? 'trap_a'
    const size = getImgSize()
    const slot = createSlotAt(
      slotId,
      `槽位 ${slotId}`,
      contentX,
      contentY,
      regionId,
      trapId,
      activeFloorId,
      {
        defaults: pending,
        contentRect,
        imgWidth: size.width,
        imgHeight: size.height,
        markerRadiusPx: pending.markerRadiusPx
      }
    )
    setScriptAndSync((prev) => ({ ...prev, slots: [...prev.slots, slot] }))
    setSelection({ kind: 'slot', slotId })
  }

  const handleDrawRoi = (roiId: string, rect: RatioRect) => {
    setScriptAndSync((p) => {
      let next = p.recognition.rois[roiId] ? p : addRoi(p, roiId)
      next = {
        ...next,
        recognition: {
          ...next.recognition,
          rois: { ...next.recognition.rois, [roiId]: rect }
        }
      }
      setPendingRoiId(nextRoiId(next))
      return next
    })
  }

  const handleCalibrateContentRect = (rect: RatioRect) => {
    patchActiveFloor({ contentRect: rect })
  }

  const handleMoveSlot = (slotId: string, contentX: number, contentY: number) => {
    const size = getImgSize()
    setScriptAndSync((prev) => ({
      ...prev,
      slots: prev.slots.map((s) =>
        s.slot_id === slotId
          ? applySlotPosition(s, contentX, contentY, contentRect, size.width, size.height, slotDefaults)
          : s
      )
    }))
  }

  const handleNudgeSlot = useCallback(
    (slotId: string, dxPx: number, dyPx: number) => {
      const slot = script.slots.find((s) => s.slot_id === slotId)
      if (!slot) return
      const size = getImgSize()
      const contentW = Math.max(1, contentRect.w_ratio * size.width)
      const contentH = Math.max(1, contentRect.h_ratio * size.height)
      const newX = Math.min(1, Math.max(0, slot.position.x_ratio + dxPx / contentW))
      const newY = Math.min(1, Math.max(0, slot.position.y_ratio + dyPx / contentH))
      handleMoveSlot(slotId, newX, newY)
    },
    [script.slots, contentRect, slotDefaults]
  )

  const handleDeleteMapSelection = useCallback(() => {
    if (selection.kind === 'slot') {
      if (!confirm(`删除槽位「${selection.slotId}」？`)) return
      setScriptAndSync((p) => ({
        ...p,
        slots: p.slots.filter((s) => s.slot_id !== selection.slotId)
      }))
      setSelection({ kind: 'none' })
    } else if (selection.kind === 'roi') {
      if (!confirm(`删除 ROI「${selection.key}」？`)) return
      setScriptAndSync((p) => removeRoi(p, selection.key))
      setSelection({ kind: 'none' })
    }
  }, [selection, setScriptAndSync])

  const handleDeleteInspectorSelection = useCallback(() => {
    if (selection.kind === 'region') {
      if (selection.regionId === 'origin') return
      if (!confirm(`删除区域「${selection.regionId}」？`)) return
      setScriptAndSync((p) => ({
        ...p,
        regions: p.regions.filter((r) => r.region_id !== selection.regionId)
      }))
      setSelection({ kind: 'none' })
    } else if (selection.kind === 'trap') {
      if (!confirm(`删除陷阱「${selection.trapId}」？`)) return
      const nextTraps = (projectFile.traps ?? []).filter((t) => t.trap_id !== selection.trapId)
      handleTrapsChange(nextTraps)
      setSelection({ kind: 'none' })
    }
  }, [selection, setScriptAndSync, projectFile.traps, handleTrapsChange])

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (isTypingTarget(e.target)) return
      if (e.key !== 'Delete' && e.key !== 'Backspace') return
      if (selection.kind === 'region' || selection.kind === 'trap') {
        e.preventDefault()
        handleDeleteInspectorSelection()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [selection, handleDeleteInspectorSelection])

  const handleSelectProject = async () => {
    try {
      if (!window.projectApi) {
        setStatus('error')
        setErrors([{ path: '/', message: 'projectApi 未就绪（请确认使用 npm run dev 启动 Electron）' }])
        return
      }
      const r = await window.projectApi.selectProjectDir()
      if (r.cancelled) return
      await openOrInitProject(r.path)
    } catch (e) {
      setStatus('error')
      setErrors([{ path: '/', message: e instanceof Error ? e.message : String(e) }])
    }
  }

  const handleImportFloor = async () => {
    if (!projectRoot) return
    const r = await window.projectApi.importFloorImage(projectRoot, activeFloorId)
    if (r.cancelled) return
    const nextPf: ProjectFileV1 = {
      ...projectFile,
      activeFloorId,
      floors: projectFile.floors.map((f) =>
        f.floor_id === activeFloorId ? { ...f, imageRelative: r.relativePath } : f
      )
    }
    setProjectFile(nextPf)
    await persistProjectFile(projectRoot, nextPf)
    await loadFloorPreview(projectRoot, r.relativePath)
  }

  const handleSaveProjectMeta = async () => {
    if (!projectRoot) return
    const pf = { ...projectFile, activeFloorId }
    await persistProjectFile(projectRoot, pf)
    setProjectFile(pf)
    setStatus('ok')
    setErrors([{ path: '/', message: '已保存 project.json' }])
  }

  const handleActiveFloorChange = async (floorId: string) => {
    const nextPf = { ...projectFile, activeFloorId: floorId }
    setProjectFile(nextPf)
    setSelection({ kind: 'none' })
    setMapTool(idleTool())
    if (projectRoot) {
      await persistProjectFile(projectRoot, nextPf)
      const floor = nextPf.floors.find((f) => f.floor_id === floorId)
      await loadFloorPreview(projectRoot, floor?.imageRelative)
    }
  }

  const handleAddFloor = async () => {
    const id = nextFloorId(projectFile.floors)
    const nextPf: ProjectFileV1 = {
      ...projectFile,
      floors: [...projectFile.floors, { floor_id: id, name: `${id} 层` }],
      activeFloorId: id
    }
    setProjectFile(nextPf)
    setFloorDataUrl(null)
    setSelection({ kind: 'none' })
    setMapTool(idleTool())
    if (projectRoot) {
      await persistProjectFile(projectRoot, nextPf)
    }
  }

  const runValidate = useCallback(async (text: string) => {
    const res = await window.scriptApi.validateScript(text)
    if (res.ok) {
      setStatus('ok')
      setErrors([])
    } else {
      setStatus('error')
      setErrors(res.errors)
    }
  }, [])

  const handleExportToProject = async () => {
    if (!projectRoot) return
    const exportScript = buildScriptForExport(script, { ...projectFile, activeFloorId })
    const text = scriptToJson(exportScript)
    const res = await window.scriptApi.validateScript(text)
    if (!res.ok) {
      setStatus('error')
      setErrors(res.errors)
      return
    }
    await window.projectApi.writeExportScript(projectRoot, text)
    setStatus('ok')
    setErrors([{ path: '/', message: '已写入 export/script.json' }])
  }

  const handleSaveScriptAs = async () => {
    const exportScript = buildScriptForExport(script, { ...projectFile, activeFloorId })
    const text = scriptToJson(exportScript)
    const res = await window.scriptApi.saveScriptFile(text, 'tower_defense_script.json')
    if (!res.cancelled) {
      setStatus('ok')
      setErrors([{ path: '/', message: `已保存: ${res.path}` }])
    }
  }

  const handleOpenScriptFile = async () => {
    const res = await window.scriptApi.openScriptFile()
    if (res.cancelled) return
    try {
      const next = parseScriptJson(res.content)
      setScript(next)
      syncRawFromScript(next)
      setStatus('idle')
      setErrors([])
    } catch (e) {
      setStatus('error')
      setErrors([{ path: '/', message: e instanceof Error ? e.message : String(e) }])
    }
  }

  const handleRawJsonChange = (text: string) => {
    setRawJson(text)
    try {
      const next = parseScriptJson(text)
      setJsonError(null)
      setScript(next)
    } catch (err) {
      setJsonError(err instanceof Error ? err.message : String(err))
    }
  }

  const handleStartDrawRoi = (roiId: string) => {
    const id = roiId.trim() && !validateRoiId(roiId) ? roiId.trim() : nextRoiId(script)
    setPendingRoiId(id)
    setMapTool({ kind: 'drawRoi', pendingRoiId: id })
  }

  return (
    <div className={`workspace ${workspaceView === 'trapLibrary' ? 'trap-library-mode' : ''}`}>
      <header className="workspace-topbar">
        <div className="topbar-title">
          <h1>塔防地图配置器</h1>
          <p className="muted">
            {workspaceView === 'map' ? '单页工作台 · 地图工具模式' : '工程陷阱库'}
          </p>
        </div>
        <div className="topbar-actions">
          <button type="button" onClick={() => void handleSelectProject()}>
            {projectRoot ? '切换工程' : '选择工程目录'}
          </button>
          {workspaceView === 'map' ? (
            <button type="button" onClick={() => setWorkspaceView('trapLibrary')}>
              陷阱库
            </button>
          ) : (
            <button type="button" className="active" onClick={() => setWorkspaceView('map')}>
              返回地图
            </button>
          )}
          <span className="topbar-path" title={projectRoot ?? ''}>
            {projectRoot ?? '（未选择工程）'}
          </span>
        </div>
        <div className={`badge ${status}`}>
          {status === 'idle' && '就绪'}
          {status === 'ok' && '成功'}
          {status === 'error' && '错误'}
        </div>
      </header>

      {workspaceView === 'map' && errors.length > 0 && (
        <ul className="errors workspace-errors">
          {errors.map((e, i) => (
            <li key={`${e.path}-${i}`}>
              <code>{e.path || '/'}</code> — {e.message}
            </li>
          ))}
        </ul>
      )}

      <div className="workspace-main">
        {workspaceView === 'trapLibrary' ? (
          <TrapLibraryPanel
            traps={projectFile.traps ?? []}
            selection={selection}
            onTrapsChange={handleTrapsChange}
            onSelect={setSelection}
          />
        ) : (
          <>
            <MapCanvas
          floorDataUrl={floorDataUrl}
          activeFloor={activeFloor}
          script={script}
          activeFloorId={activeFloorId}
          defaultFloorId={defaultFloorId}
          slotDefaults={slotDefaults}
          mapTool={mapTool}
          onMapToolChange={setMapTool}
          mapViewport={mapViewport}
          onViewportChange={setMapViewport}
          pendingRoiId={pendingRoiId}
          onPendingRoiIdChange={setPendingRoiId}
          selection={selection}
          highlightRegionId={highlightRegionId}
          onSelect={setSelection}
          onPlaceSlot={handlePlaceSlot}
          onDrawRoi={handleDrawRoi}
          onCalibrateContentRect={handleCalibrateContentRect}
          onMoveSlot={handleMoveSlot}
          onNudgeSlot={handleNudgeSlot}
          onDeleteMapSelection={handleDeleteMapSelection}
          onImageLoad={(w, h) => {
            imgNaturalRef.current = { width: w, height: h }
          }}
        />
        <InspectorPanel
          script={script}
          projectFile={projectFile}
          projectRoot={projectRoot}
          activeFloorId={activeFloorId}
          defaultFloorId={defaultFloorId}
          activeFloor={activeFloor}
          slotDefaults={slotDefaults}
          selection={selection}
          rawJson={rawJson}
          jsonError={jsonError}
          setScriptAndSync={setScriptAndSync}
          onSelect={setSelection}
          onProjectFileChange={setProjectFile}
          onActiveFloorChange={(id) => void handleActiveFloorChange(id)}
          onAddFloor={() => void handleAddFloor()}
          onImportFloorImage={() => void handleImportFloor()}
          onSaveProjectMeta={() => void handleSaveProjectMeta()}
          onPatchActiveFloor={patchActiveFloor}
          onRawJsonChange={handleRawJsonChange}
          onValidate={() => void runValidate(scriptToJson(buildScriptForExport(script, projectFile)))}
          onExport={() => void handleExportToProject()}
          onSaveAs={() => void handleSaveScriptAs()}
          onOpenScript={() => void handleOpenScriptFile()}
          onStartDrawRoi={handleStartDrawRoi}
          pendingRoiId={pendingRoiId}
          onPendingRoiIdChange={setPendingRoiId}
        />
          </>
        )}
      </div>
    </div>
  )
}