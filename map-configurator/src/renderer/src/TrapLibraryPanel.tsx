import { useEffect, useState } from 'react'
import type { EditorSelection, TrapLibraryEntry } from './script/types'
import { createDefaultTrapDefinition } from './script/trapUtils'

type TrapLibraryPanelProps = {
  traps: TrapLibraryEntry[]
  selection: EditorSelection
  onTrapsChange: (traps: TrapLibraryEntry[]) => void
  onSelect: (sel: EditorSelection) => void
}

type ThumbState = 'idle' | 'loading' | 'ready' | 'error'

function TrapThumb({
  relativePath,
  refreshKey
}: {
  relativePath?: string
  refreshKey?: number
}): JSX.Element {
  const [url, setUrl] = useState<string | null>(null)
  const [state, setState] = useState<ThumbState>('idle')

  useEffect(() => {
    let cancelled = false
    if (!relativePath) {
      setUrl(null)
      setState('idle')
      return
    }
    const normalized = relativePath.trim().replace(/\\/g, '/')
    setState('loading')
    setUrl(null)
    void (async () => {
      try {
        const r = await window.trapApi.readFileBase64(normalized)
        if (!cancelled) {
          setUrl(`data:${r.mime};base64,${r.base64}`)
          setState('ready')
        }
      } catch {
        if (!cancelled) {
          setUrl(null)
          setState('error')
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [relativePath, refreshKey])

  if (state === 'error') {
    return <span className="trap-thumb trap-thumb-empty">加载失败</span>
  }
  if (!url) {
    return <span className="trap-thumb trap-thumb-empty">{state === 'loading' ? '…' : '无图'}</span>
  }
  return <img className="trap-thumb" src={url} alt="" />
}

export function TrapLibraryPanel({
  traps,
  selection,
  onTrapsChange,
  onSelect
}: TrapLibraryPanelProps): JSX.Element {
  const [thumbRevisions, setThumbRevisions] = useState<Record<string, number>>({})

  const updateTrap = (index: number, patch: Partial<TrapLibraryEntry>) => {
    onTrapsChange(traps.map((t, i) => (i === index ? { ...t, ...patch } : t)))
  }

  const handleImportImage = async (index: number, trapId: string) => {
    const r = await window.trapApi.importTrapRecognitionImage(trapId)
    if (r.cancelled) return
    updateTrap(index, { recognitionImageRelative: r.relativePath })
    setThumbRevisions((prev) => ({ ...prev, [trapId]: Date.now() }))
  }

  const handleAddTrap = () => {
    onTrapsChange([...traps, createDefaultTrapDefinition(traps.length)])
  }

  return (
    <section className="trap-library-page">
      <div className="trap-library-header">
        <h2>应用陷阱库</h2>
        <p className="hint">
          陷阱库位于 <code>map-configurator/traps/</code>，识别图在{' '}
          <code>map-configurator/assets/verify_templates/</code>。应用级共享，与工程无关；每个陷阱自动保存为{' '}
          <code>traps/&#123;trap_id&#125;.json</code>。
        </p>
        <button type="button" onClick={handleAddTrap}>
          添加陷阱
        </button>
      </div>
      <table className="data-table trap-library-table">
        <thead>
          <tr>
            <th>识别图</th>
            <th>trap_id</th>
            <th>名称</th>
            <th>花费</th>
            <th>升级花费</th>
            <th>最大等级</th>
            <th>升级模式</th>
            <th>按住升级 ms</th>
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
                  <TrapThumb
                    relativePath={t.recognitionImageRelative}
                    refreshKey={thumbRevisions[t.trap_id]}
                  />
                  <div className="trap-thumb-actions">
                    <button type="button" onClick={() => void handleImportImage(i, t.trap_id)}>
                      导入识别图
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
                    ['cost', 'number'],
                    ['upgrade_cost', 'number'],
                    ['max_level', 'number'],
                    ['upgrade_mode', 'text'],
                    ['upgrade_hold_ms', 'number']
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
                        updateTrap(i, { [field]: v } as Partial<TrapLibraryEntry>)
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
        <p className="hint trap-library-empty">暂无陷阱，点击「添加陷阱」创建并自动保存到应用目录。</p>
      )}
    </section>
  )
}
