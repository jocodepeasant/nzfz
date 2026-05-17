import { app, BrowserWindow, dialog, ipcMain, type IpcMainInvokeEvent } from 'electron'
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import Ajv from 'ajv/dist/2020.js'
import addFormats from 'ajv-formats'
import type { ErrorObject, ValidateFunction } from 'ajv'
import {
  ensureProjectDirs,
  fileExists,
  guessMimeFromRelativePath,
  importFloorImage,
  importTrapRecognitionImage,
  readExportScript,
  readFileBase64,
  readProjectJson,
  writeExportScript,
  writeProjectJson
} from './project-fs'

const __dirname = dirname(fileURLToPath(import.meta.url))

/** 将系统对话框挂到发起 IPC 的窗口，避免 Windows 上对话框在后台或无焦点。 */
function dialogParent(event: IpcMainInvokeEvent): BrowserWindow | undefined {
  return (
    BrowserWindow.fromWebContents(event.sender) ??
    BrowserWindow.getFocusedWindow() ??
    BrowserWindow.getAllWindows()[0]
  )
}

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
    width: 1280,
    height: 900,
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

ipcMain.handle('open-script-file', async (event) => {
  const r = await dialog.showOpenDialog(dialogParent(event), {
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

ipcMain.handle('save-script-file', async (event, content: string, suggestedName?: string) => {
  const r = await dialog.showSaveDialog(dialogParent(event), {
    defaultPath: suggestedName ?? 'script.json',
    filters: [{ name: 'JSON', extensions: ['json'] }]
  })
  if (r.canceled || !r.filePath) {
    return { cancelled: true as const }
  }
  writeFileSync(r.filePath, content, 'utf-8')
  return { cancelled: false as const, path: r.filePath }
})

ipcMain.handle('project-select-dir', async (event) => {
  const r = await dialog.showOpenDialog(dialogParent(event), {
    properties: ['openDirectory']
  })
  if (r.canceled || !r.filePaths[0]) {
    return { cancelled: true as const }
  }
  return { cancelled: false as const, path: r.filePaths[0] }
})

ipcMain.handle('project-ensure-dirs', async (_evt, projectRoot: string) => {
  await ensureProjectDirs(projectRoot)
  return { ok: true as const }
})

ipcMain.handle('project-read-json', async (_evt, projectRoot: string) => {
  const data = await readProjectJson(projectRoot)
  return { data }
})

ipcMain.handle('project-write-json', async (_evt, projectRoot: string, data: unknown) => {
  await writeProjectJson(projectRoot, data)
  return { ok: true as const }
})

ipcMain.handle('project-read-export-script', async (_evt, projectRoot: string) => {
  const text = await readExportScript(projectRoot)
  return { text }
})

ipcMain.handle('project-write-export-script', async (_evt, projectRoot: string, jsonText: string) => {
  await writeExportScript(projectRoot, jsonText)
  return { ok: true as const }
})

ipcMain.handle('project-import-floor-image', async (event, projectRoot: string, floorId: string) => {
  return importFloorImage(projectRoot, floorId, dialogParent(event))
})

ipcMain.handle(
  'project-import-trap-recognition-image',
  async (event, projectRoot: string, trapId: string) => {
    return importTrapRecognitionImage(projectRoot, trapId, dialogParent(event))
  }
)

ipcMain.handle(
  'project-read-file-base64',
  async (_evt, projectRoot: string, relativePath: string) => {
    const b64 = await readFileBase64(projectRoot, relativePath)
    const mime = guessMimeFromRelativePath(relativePath)
    return { base64: b64, mime }
  }
)

ipcMain.handle('project-file-exists', async (_evt, projectRoot: string, relativePath: string) => {
  const exists = await fileExists(projectRoot, relativePath)
  return { exists }
})
