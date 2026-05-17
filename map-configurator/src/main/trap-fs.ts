import { copyFile, mkdir, readdir, readFile, stat, unlink, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { dialog, type BrowserWindow } from 'electron'
import { getConfiguratorRoot } from './app-paths'
import { guessMimeFromRelativePath, resolveSafe } from './project-fs'

function sanitizeTrapId(trapId: string): string {
  const s = trapId.replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 48)
  return s || 'trap'
}

function trapDefinitionRelativePath(trapId: string): string {
  return join('traps', `${sanitizeTrapId(trapId)}.json`).replace(/\\/g, '/')
}

function normalizeConfiguratorRelativePath(relativePath: string): string {
  return relativePath.trim().replace(/\\/g, '/').replace(/^\/+/, '')
}

export async function ensureTrapLibraryDirs(): Promise<void> {
  const root = getConfiguratorRoot()
  await mkdir(join(root, 'traps'), { recursive: true })
  await mkdir(join(root, 'assets', 'verify_templates'), { recursive: true })
}

export async function listTrapDefinitions(): Promise<unknown[]> {
  await ensureTrapLibraryDirs()
  const root = getConfiguratorRoot()
  const dir = join(root, 'traps')
  let files: string[]
  try {
    files = await readdir(dir)
  } catch {
    return []
  }
  const traps: unknown[] = []
  for (const name of files) {
    if (!name.endsWith('.json')) continue
    try {
      const raw = JSON.parse(await readFile(join(dir, name), 'utf-8')) as unknown
      traps.push(raw)
    } catch {
      /* skip invalid file */
    }
  }
  return traps.sort((a, b) => {
    const idA = (a as { trap_id?: string }).trap_id ?? ''
    const idB = (b as { trap_id?: string }).trap_id ?? ''
    return idA.localeCompare(idB)
  })
}

export async function writeTrapDefinition(trap: unknown): Promise<void> {
  const trapId = (trap as { trap_id?: string }).trap_id
  if (!trapId || !String(trapId).trim()) {
    throw new Error('trap_id is required')
  }
  await ensureTrapLibraryDirs()
  const root = getConfiguratorRoot()
  const rel = trapDefinitionRelativePath(trapId)
  const full = resolveSafe(root, rel)
  await writeFile(full, JSON.stringify(trap, null, 2), 'utf-8')
}

export async function deleteTrapDefinition(trapId: string): Promise<void> {
  const root = getConfiguratorRoot()
  const rel = trapDefinitionRelativePath(trapId)
  try {
    await unlink(resolveSafe(root, rel))
  } catch {
    /* file may not exist */
  }
}

export async function syncTrapDefinitions(
  traps: unknown[],
  previousTrapIds: string[]
): Promise<void> {
  const nextIds = new Set(
    traps
      .map((t) => (t as { trap_id?: string }).trap_id)
      .filter((id): id is string => typeof id === 'string' && !!id.trim())
  )
  for (const trap of traps) {
    await writeTrapDefinition(trap)
  }
  for (const oldId of previousTrapIds) {
    if (!nextIds.has(oldId)) {
      await deleteTrapDefinition(oldId)
    }
  }
}

export async function importTrapRecognitionImage(
  trapId: string,
  parent?: BrowserWindow | null
): Promise<{ cancelled: true } | { cancelled: false; relativePath: string }> {
  const r = await dialog.showOpenDialog(parent ?? undefined, {
    properties: ['openFile'],
    filters: [{ name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'webp'] }]
  })
  if (r.canceled || !r.filePaths[0]) {
    return { cancelled: true as const }
  }
  await ensureTrapLibraryDirs()
  const root = getConfiguratorRoot()
  const parts = r.filePaths[0].split('.')
  const ext = parts.length > 1 ? parts.pop()?.toLowerCase() : 'png'
  const safeExt = ext === 'jpg' || ext === 'jpeg' || ext === 'png' || ext === 'webp' ? ext : 'png'
  const relativePath = join('assets', 'verify_templates', `trap_${sanitizeTrapId(trapId)}.${safeExt}`).replace(
    /\\/g,
    '/'
  )
  const dest = resolveSafe(root, relativePath)
  await copyFile(r.filePaths[0], dest)
  return { cancelled: false as const, relativePath }
}

export async function readConfiguratorFileBase64(relativePath: string): Promise<string> {
  const rel = normalizeConfiguratorRelativePath(relativePath)
  if (!rel) {
    throw new Error('relativePath is required')
  }
  const root = getConfiguratorRoot()
  const full = resolveSafe(root, rel)
  try {
    const buf = await readFile(full)
    return buf.toString('base64')
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    throw new Error(`Cannot read configurator file "${rel}": ${msg}`)
  }
}

export async function configuratorFileExists(relativePath: string): Promise<boolean> {
  try {
    const rel = normalizeConfiguratorRelativePath(relativePath)
    if (!rel) return false
    const root = getConfiguratorRoot()
    const full = resolveSafe(root, rel)
    await stat(full)
    return true
  } catch {
    return false
  }
}

export { guessMimeFromRelativePath }
