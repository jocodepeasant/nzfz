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
