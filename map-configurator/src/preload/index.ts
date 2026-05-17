import { contextBridge, ipcRenderer } from 'electron'

export type ValidateResult =
  | { ok: true; errors: [] }
  | { ok: false; errors: { path: string; message: string }[] }

contextBridge.exposeInMainWorld('scriptApi', {
  validateScript: (jsonText: string): Promise<ValidateResult> =>
    ipcRenderer.invoke('validate-script', jsonText),
  openScriptFile: (): Promise<
    { cancelled: true } | { cancelled: false; path: string; content: string }
  > => ipcRenderer.invoke('open-script-file'),
  saveScriptFile: (
    content: string,
    suggestedName?: string
  ): Promise<{ cancelled: true } | { cancelled: false; path: string }> =>
    ipcRenderer.invoke('save-script-file', content, suggestedName)
})

contextBridge.exposeInMainWorld('projectApi', {
  selectProjectDir: (): Promise<{ cancelled: true } | { cancelled: false; path: string }> =>
    ipcRenderer.invoke('project-select-dir'),
  ensureDirs: (projectRoot: string): Promise<{ ok: true }> =>
    ipcRenderer.invoke('project-ensure-dirs', projectRoot),
  readProjectJson: (projectRoot: string): Promise<{ data: unknown | null }> =>
    ipcRenderer.invoke('project-read-json', projectRoot),
  writeProjectJson: (projectRoot: string, data: unknown): Promise<{ ok: true }> =>
    ipcRenderer.invoke('project-write-json', projectRoot, data),
  readExportScript: (projectRoot: string): Promise<{ text: string | null }> =>
    ipcRenderer.invoke('project-read-export-script', projectRoot),
  writeExportScript: (projectRoot: string, jsonText: string): Promise<{ ok: true }> =>
    ipcRenderer.invoke('project-write-export-script', projectRoot, jsonText),
  importFloorImage: (
    projectRoot: string,
    floorId: string
  ): Promise<{ cancelled: true } | { cancelled: false; relativePath: string }> =>
    ipcRenderer.invoke('project-import-floor-image', projectRoot, floorId),
  importTrapRecognitionImage: (
    projectRoot: string,
    trapId: string
  ): Promise<{ cancelled: true } | { cancelled: false; relativePath: string }> =>
    ipcRenderer.invoke('project-import-trap-recognition-image', projectRoot, trapId),
  readFileBase64: (
    projectRoot: string,
    relativePath: string
  ): Promise<{ base64: string; mime: string }> =>
    ipcRenderer.invoke('project-read-file-base64', projectRoot, relativePath),
  fileExists: (projectRoot: string, relativePath: string): Promise<{ exists: boolean }> =>
    ipcRenderer.invoke('project-file-exists', projectRoot, relativePath)
})
