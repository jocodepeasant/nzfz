import { app, BrowserWindow, dialog, ipcMain } from 'electron'
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import Ajv from 'ajv/dist/2020.js'
import addFormats from 'ajv-formats'
import type { ErrorObject, ValidateFunction } from 'ajv'

const __dirname = dirname(fileURLToPath(import.meta.url))

function schemaPath(): string {
  return resolve(process.cwd(), '..', 'schemas', 'tower_defense_script_v1.schema.json')
}

let validateFn: ValidateFunction | null = null

function getValidator(): ValidateFunction {
  if (validateFn) return validateFn
  const ajv = new Ajv({ allErrors: true, strict: false })
  addFormats(ajv)
  const raw = readFileSync(schemaPath(), 'utf-8')
  validateFn = ajv.compile(JSON.parse(raw) as object)
  return validateFn
}

function createWindow(): void {
  const win = new BrowserWindow({
    width: 1080,
    height: 800,
    webPreferences: {
      preload: join(__dirname, '../preload/index.mjs'),
      contextIsolation: true,
      sandbox: false
    }
  })

  if (process.env.ELECTRON_RENDERER_URL) {
    void win.loadURL(process.env.ELECTRON_RENDERER_URL)
    win.webContents.openDevTools()
  } else {
    void win.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

app.whenReady().then(() => {
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

ipcMain.handle('validate-script', async (_evt, jsonText: string) => {
  let data: unknown
  try {
    data = JSON.parse(jsonText) as unknown
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    return { ok: false as const, errors: [{ path: '/', message: `JSON 解析失败: ${msg}` }] }
  }
  const validate = getValidator()
  if (validate(data)) {
    return { ok: true as const, errors: [] as { path: string; message: string }[] }
  }
  const errs = (validate.errors ?? []) as ErrorObject[]
  return {
    ok: false as const,
    errors: errs.map((er) => ({
      path: er.instancePath || '/',
      message: er.message ?? '校验错误'
    }))
  }
})

ipcMain.handle('open-script-file', async () => {
  const r = await dialog.showOpenDialog({
    properties: ['openFile'],
    filters: [{ name: 'JSON', extensions: ['json'] }]
  })
  if (r.canceled || !r.filePaths[0]) {
    return { cancelled: true as const }
  }
  const path = r.filePaths[0]
  const content = readFileSync(path, 'utf-8')
  return { cancelled: false as const, path, content }
})

ipcMain.handle('save-script-file', async (_evt, content: string, suggestedName?: string) => {
  const r = await dialog.showSaveDialog({
    defaultPath: suggestedName ?? 'script.json',
    filters: [{ name: 'JSON', extensions: ['json'] }]
  })
  if (r.canceled || !r.filePath) {
    return { cancelled: true as const }
  }
  writeFileSync(r.filePath, content, 'utf-8')
  return { cancelled: false as const, path: r.filePath }
})
