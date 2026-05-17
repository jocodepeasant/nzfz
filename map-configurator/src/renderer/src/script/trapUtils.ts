import type { TrapLibraryEntry, TrapRow, TowerDefenseScript } from './types'

export const DEFAULT_TRAP_KEYS = { select_key: '1', upgrade_key: '1' } as const

export function trapRowFromDefinition(def: TrapLibraryEntry): TrapRow {
  return {
    trap_id: def.trap_id,
    trap_name: def.trap_name,
    select_key: DEFAULT_TRAP_KEYS.select_key,
    upgrade_key: DEFAULT_TRAP_KEYS.upgrade_key,
    upgrade_hold_ms: def.upgrade_hold_ms,
    cost: def.cost,
    upgrade_cost: def.upgrade_cost,
    max_level: def.max_level,
    upgrade_mode: def.upgrade_mode
  }
}

export function definitionFromTrapRow(row: TrapRow): TrapLibraryEntry {
  const {
    trap_id,
    trap_name,
    upgrade_hold_ms,
    cost,
    upgrade_cost,
    max_level,
    upgrade_mode
  } = row
  return {
    trap_id,
    trap_name,
    upgrade_hold_ms,
    cost,
    upgrade_cost,
    max_level,
    upgrade_mode
  }
}

export function definitionFromUnknown(raw: unknown): TrapLibraryEntry | null {
  if (!raw || typeof raw !== 'object') return null
  const o = raw as Record<string, unknown>
  if (typeof o.trap_id !== 'string' || !o.trap_id.trim()) return null
  return {
    trap_id: o.trap_id,
    trap_name: typeof o.trap_name === 'string' ? o.trap_name : o.trap_id,
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

export function parseTrapDefinitionsFromDisk(rawList: unknown[]): TrapLibraryEntry[] {
  return rawList.map(definitionFromUnknown).filter((t): t is TrapLibraryEntry => t != null)
}

export function syncScriptTraps(
  script: TowerDefenseScript,
  traps: TrapLibraryEntry[]
): TowerDefenseScript {
  return { ...script, traps: traps.map(trapRowFromDefinition) }
}

export function trapsForExport(traps: TrapLibraryEntry[]): Record<string, unknown>[] {
  return traps.map((d) => {
    const row = trapRowFromDefinition(d)
    return d.recognitionImageRelative
      ? { ...row, recognition_template: d.recognitionImageRelative }
      : row
  })
}

export function createDefaultTrapDefinition(index: number): TrapLibraryEntry {
  const id = `trap_${index + 1}`
  return {
    trap_id: id,
    trap_name: '新陷阱',
    upgrade_hold_ms: 4000,
    cost: 100,
    upgrade_cost: 200,
    max_level: 3,
    upgrade_mode: 'all_same_type'
  }
}

/** Strip traps from project.json payload (app traps/ dir is source of truth). */
export function projectJsonWithoutTraps<T extends { traps?: TrapLibraryEntry[] }>(
  pf: T
): Omit<T, 'traps'> {
  const { traps: _t, ...rest } = pf
  return rest
}
