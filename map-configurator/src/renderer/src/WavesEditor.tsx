import { useState } from 'react'
import type { TowerDefenseScript, WaveRow } from './script/types'

export function WavesEditor({
  script,
  setScriptAndSync
}: {
  script: TowerDefenseScript
  setScriptAndSync: (fn: (p: TowerDefenseScript) => TowerDefenseScript) => void
}): JSX.Element {
  const [waveIndex, setWaveIndex] = useState(0)
  const wave: WaveRow | undefined = script.waves[waveIndex]

  const updateWave = (patch: Partial<WaveRow>) => {
    setScriptAndSync((p) => {
      const waves = [...p.waves]
      waves[waveIndex] = { ...waves[waveIndex], ...patch }
      return { ...p, waves }
    })
  }

  const updateActions = (actions: WaveRow['actions']) => {
    setScriptAndSync((p) => {
      const waves = [...p.waves]
      waves[waveIndex] = { ...waves[waveIndex], actions }
      return { ...p, waves }
    })
  }

  if (!wave) {
    return (
      <section className="panel">
        <h2>波次</h2>
        <button
          type="button"
          onClick={() =>
            setScriptAndSync((p) => ({
              ...p,
              waves: [
                ...p.waves,
                {
                  wave: p.waves.length + 1,
                  name: `第${p.waves.length + 1}波`,
                  execute_once: true,
                  trigger: { type: 'wave_eq', value: p.waves.length + 1 },
                  actions: [{ type: 'log', message: '新波次' }]
                }
              ]
            }))
          }
        >
          添加波次
        </button>
      </section>
    )
  }

  return (
    <section className="panel">
      <h2>波次</h2>
      <div className="row">
        <label>
          选择波次
          <select value={waveIndex} onChange={(e) => setWaveIndex(Number(e.target.value))}>
            {script.waves.map((w, i) => (
              <option key={`${w.wave}-${i}`} value={i}>
                {w.wave} — {w.name}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={() =>
            setScriptAndSync((p) => ({
              ...p,
              waves: [
                ...p.waves,
                {
                  wave: p.waves.length + 1,
                  name: `第${p.waves.length + 1}波`,
                  execute_once: true,
                  trigger: { type: 'wave_eq', value: p.waves.length + 1 },
                  actions: [{ type: 'log', message: '新波次' }]
                }
              ]
            }))
          }
        >
          添加波次
        </button>
        <button
          type="button"
          disabled={script.waves.length <= 1}
          onClick={() => {
            setScriptAndSync((p) => ({
              ...p,
              waves: p.waves.filter((_, i) => i !== waveIndex)
            }))
            setWaveIndex((i) => Math.max(0, i - 1))
          }}
        >
          删除当前波次
        </button>
      </div>

      <div className="grid-form">
        <label>
          wave 序号
          <input
            type="number"
            value={wave.wave}
            onChange={(e) => updateWave({ wave: Number(e.target.value) || 0 })}
          />
        </label>
        <label>
          名称
          <input value={wave.name} onChange={(e) => updateWave({ name: e.target.value })} />
        </label>
        <label>
          trigger.value (wave_eq)
          <input
            type="number"
            value={Number(wave.trigger.value ?? 0)}
            onChange={(e) =>
              updateWave({
                trigger: { type: 'wave_eq', value: Number(e.target.value) || 0 }
              })
            }
          />
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={wave.execute_once}
            onChange={(e) => updateWave({ execute_once: e.target.checked })}
          />
          execute_once
        </label>
      </div>

      <h3>动作链</h3>
      {wave.actions.map((act, ai) => (
        <div key={ai} className="action-card">
          <div className="row">
            <label>
              类型
              <select
                value={(act as { type?: string }).type ?? 'log'}
                onChange={(e) => {
                  const t = e.target.value
                  const next = [...wave.actions]
                  if (t === 'log') {
                    next[ai] = { type: 'log', message: '日志' }
                  } else if (t === 'pan_to_region') {
                    next[ai] = {
                      type: 'pan_to_region',
                      region_id: script.regions[0]?.region_id ?? 'origin'
                    }
                  } else {
                    const sid = script.slots[0]?.slot_id ?? 'S01'
                    const tid = script.traps[0]?.trap_id ?? 'trap_a'
                    next[ai] = {
                      type: 'place_trap',
                      name: '放置',
                      trap_id: tid,
                      slot_id: sid,
                      conditions: { resource_gte: 0, slot_empty: sid },
                      on_condition_failed: {
                        policy: 'wait',
                        timeout_ms: 30000,
                        then: 'retry_condition'
                      },
                      verify: {
                        type: 'slot_has_trap',
                        slot_id: sid,
                        trap_id: tid,
                        required: true
                      },
                      retry: {
                        max_count: 2,
                        interval_ms: 800,
                        reset_view_before_retry: true,
                        micro_adjust_on_retry: true
                      },
                      on_fail: { policy: 'skip' }
                    }
                  }
                  updateActions(next)
                }}
              >
                <option value="log">log</option>
                <option value="pan_to_region">pan_to_region</option>
                <option value="place_trap">place_trap</option>
              </select>
            </label>
            <button
              type="button"
              onClick={() => {
                const next = wave.actions.filter((_, j) => j !== ai)
                updateActions(next)
              }}
            >
              删除动作
            </button>
          </div>
          {(act as { type?: string }).type === 'log' && (
            <label>
              message
              <input
                value={(act as { message?: string }).message ?? ''}
                onChange={(e) => {
                  const next = [...wave.actions]
                  next[ai] = { type: 'log', message: e.target.value }
                  updateActions(next)
                }}
              />
            </label>
          )}
          {(act as { type?: string }).type === 'pan_to_region' && (
            <label>
              region_id
              <select
                value={(act as { region_id?: string }).region_id ?? ''}
                onChange={(e) => {
                  const next = [...wave.actions]
                  next[ai] = { type: 'pan_to_region', region_id: e.target.value }
                  updateActions(next)
                }}
              >
                {script.regions.map((r) => (
                  <option key={r.region_id} value={r.region_id}>
                    {r.region_id}
                  </option>
                ))}
              </select>
            </label>
          )}
          {(act as { type?: string }).type === 'place_trap' && (
            <div className="grid-form">
              <label>
                name
                <input
                  value={(act as { name?: string }).name ?? ''}
                  onChange={(e) => {
                    const next = [...wave.actions]
                    next[ai] = { ...(act as object), name: e.target.value } as WaveRow['actions'][number]
                    updateActions(next)
                  }}
                />
              </label>
              <label>
                trap_id
                <select
                  value={(act as { trap_id?: string }).trap_id ?? ''}
                  onChange={(e) => {
                    const next = [...wave.actions]
                    next[ai] = { ...(act as object), trap_id: e.target.value } as WaveRow['actions'][number]
                    updateActions(next)
                  }}
                >
                  {script.traps.map((t) => (
                    <option key={t.trap_id} value={t.trap_id}>
                      {t.trap_id}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                slot_id
                <select
                  value={(act as { slot_id?: string }).slot_id ?? ''}
                  onChange={(e) => {
                    const next = [...wave.actions]
                    next[ai] = { ...(act as object), slot_id: e.target.value } as WaveRow['actions'][number]
                    updateActions(next)
                  }}
                >
                  {script.slots.map((s) => (
                    <option key={s.slot_id} value={s.slot_id}>
                      {s.slot_id}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                resource_gte
                <input
                  type="number"
                  value={Number(
                    ((act as { conditions?: { resource_gte?: number } }).conditions ?? {})
                      .resource_gte ?? 0
                  )}
                  onChange={(e) => {
                    const next = [...wave.actions]
                    const a = { ...(act as object) } as {
                      conditions?: Record<string, unknown>
                      slot_id?: string
                    }
                    const slotId = a.slot_id ?? script.slots[0]?.slot_id ?? 'S01'
                    a.conditions = {
                      ...(a.conditions ?? {}),
                      resource_gte: Number(e.target.value) || 0,
                      slot_empty: slotId
                    }
                    next[ai] = a as WaveRow['actions'][number]
                    updateActions(next)
                  }}
                />
              </label>
            </div>
          )}
        </div>
      ))}
      <button
        type="button"
        onClick={() => updateActions([...wave.actions, { type: 'log', message: '新动作' }])}
      >
        添加动作
      </button>
    </section>
  )
}
