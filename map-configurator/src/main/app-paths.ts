import { existsSync, readFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { app } from 'electron'

const __dirname = dirname(fileURLToPath(import.meta.url))

function isConfiguratorRoot(dir: string): boolean {
  const pkgPath = join(dir, 'package.json')
  if (!existsSync(pkgPath)) return false
  try {
    const pkg = JSON.parse(readFileSync(pkgPath, 'utf-8')) as { name?: string }
    return pkg.name === 'map-configurator'
  } catch {
    return false
  }
}

function findConfiguratorRootFrom(start: string): string | null {
  let dir = resolve(start)
  for (let i = 0; i < 8; i++) {
    if (isConfiguratorRoot(dir)) return dir
    const parent = dirname(dir)
    if (parent === dir) break
    dir = parent
  }
  return null
}

/** map-configurator package root (traps/, assets/verify_templates/). */
export function getConfiguratorRoot(): string {
  const candidates: string[] = []

  if (app.isPackaged) {
    candidates.push(join(process.resourcesPath, '..'))
    candidates.push(app.getAppPath())
  } else {
    candidates.push(app.getAppPath())
  }

  candidates.push(resolve(__dirname, '../..'))
  candidates.push(process.cwd())

  for (const c of candidates) {
    const found = findConfiguratorRootFrom(c)
    if (found) return found
  }

  return resolve(__dirname, '../..')
}
