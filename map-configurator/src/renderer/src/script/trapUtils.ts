import type { TrapDefinition, TrapRow, TowerDefenseScript } from './types'

export function trapRowFromDefinition(def: TrapDefinition): TrapRow {
  const {
    trap_id,
    trap_name,
    select_key,
    upgrade_key,
    upgrade_hold_ms,
    cost,
    upgrade_cost,
    max_level,
    upgrade_mode
  } = def
  return {
    trap_id,
    trap_name,
    select_key,
    upgrade_key,
    upgrade_hold_ms,
    cost,
    upgrade_cost,
    max_level,
    upgrade_mode
  }
}

export function definitionFromTrapRow(row: TrapRow): TrapDefinition {
  return { ...row }
}

export function definitionFromUnknown(raw: unknown): TrapDefinition | null {
  if (!raw || typeof raw !== 'object') return null
  const o = raw as Record<string, unknown>
  if (typeof o.trap_id !== 'string' || !o.trap_id.trim()) return null
  return {
    trap_id: o.trap_id,
    trap_name: typeof o.trap_name === 'string' ? o.trap_name : o.trap_id,
    select_key: typeof o.select_key === 'string' ? o.select_key : '1',
    upgrade_key: typeof o.upgrade_key === 'string' ? o.upgrade_key : '1',
    upgrade_hold_ms: Number(o.upgrade_hold_ms) || 4000,
    cost: Number(o.cost) || 0,
    upgrade_cost: Number(o.upgrade_cost) || 0,
    max_level: Number(o.max_level) || 1,
    upgrade_mode: typeof o.upgrade_mode === 'string' ? o.upgrade_mode : 'all_same_type',
    recognitionImageRelative:
      typeof o.recognitionImageRelative === 'string'
        ? o.recognitionImageRelative
        : typeof o.recognition_template === 'string'
          ? o.recognition_template
          : undefined
  }
}

export function syncScriptTraps(script: TowerDefenseScript, traps: TrapDefinition[]): TowerDefenseScript {
  return { ...script, traps: traps.map(trapRowFromDefinition) }
}

export function trapsForExport(traps: TrapDefinition[]): Record<string, unknown>[] {
  return traps.map((d) => {
    const row = trapRowFromDefinition(d)
    return d.recognitionImageRelative
      ? { ...row, recognition_template: d.recognitionImageRelative }
      : row
  })
}

export function createDefaultTrapDefinition(index: number): TrapDefinition {
  const id = `trap_${index + 1}`
  return {
    trap_id: id,
    trap_name: '新陷阱',
    select_key: '1',
    upgrade_key: '1',
    upgrade_hold_ms: 4000,
    cost: 100,
    upgrade_cost: 200,
    max_level: 3,
    upgrade_mode: 'all_same_type'
  }
}
