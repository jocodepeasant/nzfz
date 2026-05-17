import { copyFile, mkdir, readFile, stat, writeFile } from 'node:fs/promises'
import { join, normalize, relative, resolve } from 'node:path'
import { dialog, type BrowserWindow } from 'electron'

export function resolveSafe(projectRoot: string, relativePath: string): string {
  const rel = normalize(relativePath).replace(/^(\.\.(\/|\\|$))+/, '')
  if (rel.includes('..')) {
    throw new Error('Invalid path')
  }
  const base = resolve(projectRoot)
  const full = resolve(join(base, rel))
  const relToBase = relative(base, full)
  if (relToBase.startsWith('..') || relToBase === '..') {
    throw new Error('Path escapes project root')
  }
  return full
}

export async function ensureProjectDirs(projectRoot: string): Promise<void> {
  await mkdir(join(projectRoot, 'assets'), { recursive: true })
  await mkdir(join(projectRoot, 'export'), { recursive: true })
}

export async function readProjectJson(projectRoot: string): Promise<unknown | null> {
  const p = join(projectRoot, 'project.json')
  try {
    const raw = await readFile(p, 'utf-8')
    return JSON.parse(raw) as unknown
  } catch {
    return null
  }
}

export async function writeProjectJson(projectRoot: string, data: unknown): Promise<void> {
  await ensureProjectDirs(projectRoot)
  const p = join(projectRoot, 'project.json')
  await writeFile(p, JSON.stringify(data, null, 2), 'utf-8')
}

export async function readExportScript(projectRoot: string): Promise<string | null> {
  const p = join(projectRoot, 'export', 'script.json')
  try {
    return await readFile(p, 'utf-8')
  } catch {
    return null
  }
}

export async function writeExportScript(projectRoot: string, jsonText: string): Promise<void> {
  await ensureProjectDirs(projectRoot)
  const p = join(projectRoot, 'export', 'script.json')
  await writeFile(p, jsonText, 'utf-8')
}

function sanitizeFloorId(floorId: string): string {
  const s = floorId.replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 32)
  return s || '1'
}

export async function importFloorImage(
  projectRoot: string,
  floorId: string,
  parent?: BrowserWindow | null
): Promise<{ cancelled: true } | { cancelled: false; relativePath: string }> {
  const r = await dialog.showOpenDialog(parent ?? undefined, {
    properties: ['openFile'],
    filters: [{ name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'webp'] }]
  })
  if (r.canceled || !r.filePaths[0]) {
    return { cancelled: true as const }
  }
  await ensureProjectDirs(projectRoot)
  const parts = r.filePaths[0].split('.')
  const ext = parts.length > 1 ? parts.pop()?.toLowerCase() : 'png'
  const safeExt = ext === 'jpg' || ext === 'jpeg' || ext === 'png' || ext === 'webp' ? ext : 'png'
  const relativePath = join('assets', `floor_${sanitizeFloorId(floorId)}.${safeExt}`).replace(/\\/g, '/')
  const dest = resolveSafe(projectRoot, relativePath)
  await copyFile(r.filePaths[0], dest)
  return { cancelled: false as const, relativePath }
}

export async function readFileBase64(projectRoot: string, relativePath: string): Promise<string> {
  const full = resolveSafe(projectRoot, relativePath)
  const buf = await readFile(full)
  return buf.toString('base64')
}

export async function fileExists(projectRoot: string, relativePath: string): Promise<boolean> {
  try {
    const full = resolveSafe(projectRoot, relativePath)
    await stat(full)
    return true
  } catch {
    return false
  }
}

export function guessMimeFromRelativePath(rel: string): string {
  const lower = rel.toLowerCase()
  if (lower.endsWith('.png')) return 'image/png'
  if (lower.endsWith('.jpg') || lower.endsWith('.jpeg')) return 'image/jpeg'
  if (lower.endsWith('.webp')) return 'image/webp'
  return 'application/octet-stream'
}
