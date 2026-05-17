import { useEffect, useState } from 'react'
import type { EditorSelection, TrapDefinition } from './script/types'
import { createDefaultTrapDefinition } from './script/trapUtils'

type TrapLibraryPanelProps = {
  open: boolean
  projectRoot: string | null
  traps: TrapDefinition[]
  selection: EditorSelection
  onTrapsChange: (traps: TrapDefinition[]) => void
  onSelect: (sel: EditorSelection) => void
  onPersist?: () => void
}

function TrapThumb({
  projectRoot,
  relativePath
}: {
  projectRoot: string | null
  relativePath?: string
}): JSX.Element {
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    if (!projectRoot || !relativePath) {
      setUrl(null)
      return
    }
    void (async () => {
      const ex = await window.projectApi.fileExists(projectRoot, relativePath)
      if (!ex.exists) {
        if (!cancelled) setUrl(null)
        return
      }
      const r = await window.projectApi.readFileBase64(projectRoot, relativePath)
      if (!cancelled) setUrl(`data:${r.mime};base64,${r.base64}`)
    })()
    return () => {
      cancelled = true
    }
  }, [projectRoot, relativePath])

  if (!url) {
    return <span className="trap-thumb trap-thumb-empty">无图</span>
  }
  return <img className="trap-thumb" src={url} alt="" />
}

export function TrapLibraryPanel({
  open,
  projectRoot,
  traps,
  selection,
  onTrapsChange,
  onSelect,
  onPersist
}: TrapLibraryPanelProps): JSX.Element | null {
  if (!open) return null

  const updateTrap = (index: number, patch: Partial<TrapDefinition>) => {
    onTrapsChange(traps.map((t, i) => (i === index ? { ...t, ...patch } : t)))
  }

  const handleImportImage = async (index: number, trapId: string) => {
    if (!projectRoot) return
    const r = await window.projectApi.importTrapRecognitionImage(projectRoot, trapId)
    if (r.cancelled) return
    updateTrap(index, { recognitionImageRelative: r.relativePath })
    onPersist?.()
  }

  return (
    <section className="trap-library-drawer">
      <div className="trap-library-header">
        <h2>工程陷阱库</h2>
        <p className="hint">
          陷阱为工程级共享，所有楼层与导出脚本共用；请为每个陷阱配置识别图（模板匹配用）。
        </p>
        <button
          type="button"
          onClick={() => onTrapsChange([...traps, createDefaultTrapDefinition(traps.length)])}
        >
          添加陷阱
        </button>
      </div>
      <table className="data-table compact trap-library-table">
        <thead>
          <tr>
            <th>识别图</th>
            <th>trap_id</th>
            <th>名称</th>
            <th>选择键</th>
            <th>升级键</th>
            <th>花费</th>
            <th>升级花费</th>
            <th>最大等级</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {traps.map((t, i) => {
            const selected = selection.kind === 'trap' && selection.trapId === t.trap_id
            return (
              <tr
                key={`${t.trap_id}-${i}`}
                className={selected ? 'row-selected' : ''}
                onClick={() => onSelect({ kind: 'trap', trapId: t.trap_id })}
              >
                <td className="trap-thumb-cell" onClick={(e) => e.stopPropagation()}>
                  <TrapThumb projectRoot={projectRoot} relativePath={t.recognitionImageRelative} />
                  <div className="trap-thumb-actions">
                    <button
                      type="button"
                      disabled={!projectRoot}
                      onClick={() => void handleImportImage(i, t.trap_id)}
                    >
                      导入
                    </button>
                    {t.recognitionImageRelative && (
                      <button
                        type="button"
                        onClick={() => updateTrap(i, { recognitionImageRelative: undefined })}
                      >
                        清除
                      </button>
                    )}
                  </div>
                </td>
                {(
                  [
                    ['trap_id', 'text'],
                    ['trap_name', 'text'],
                    ['select_key', 'text'],
                    ['upgrade_key', 'text'],
                    ['cost', 'number'],
                    ['upgrade_cost', 'number'],
                    ['max_level', 'number']
                  ] as const
                ).map(([field, kind]) => (
                  <td key={field}>
                    <input
                      value={String((t as Record<string, unknown>)[field] ?? '')}
                      type={kind}
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) => {
                        const v =
                          kind === 'number' ? Number(e.target.value) || 0 : e.target.value
                        updateTrap(i, { [field]: v } as Partial<TrapDefinition>)
                      }}
                    />
                  </td>
                ))}
                <td>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      if (!confirm(`删除陷阱「${t.trap_id}」？`)) return
                      onTrapsChange(traps.filter((_, j) => j !== i))
                      if (selection.kind === 'trap' && selection.trapId === t.trap_id) {
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
      {traps.length === 0 && (
        <p className="hint trap-library-empty">暂无陷阱，点击「添加陷阱」创建工程共享陷阱。</p>
      )}
    </section>
  )
}
