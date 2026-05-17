/// <reference types="vite/client" />

type ValidateResult =
  | { ok: true; errors: [] }
  | { ok: false; errors: { path: string; message: string }[] }

type ProjectApi = {
  selectProjectDir: () => Promise<{ cancelled: true } | { cancelled: false; path: string }>
  ensureDirs: (projectRoot: string) => Promise<{ ok: true }>
  readProjectJson: (projectRoot: string) => Promise<{ data: unknown | null }>
  writeProjectJson: (projectRoot: string, data: unknown) => Promise<{ ok: true }>
  readExportScript: (projectRoot: string) => Promise<{ text: string | null }>
  writeExportScript: (projectRoot: string, jsonText: string) => Promise<{ ok: true }>
  importFloorImage: (
    projectRoot: string,
    floorId: string
  ) => Promise<{ cancelled: true } | { cancelled: false; relativePath: string }>
  importTrapRecognitionImage: (
    projectRoot: string,
    trapId: string
  ) => Promise<{ cancelled: true } | { cancelled: false; relativePath: string }>
  readFileBase64: (
    projectRoot: string,
    relativePath: string
  ) => Promise<{ base64: string; mime: string }>
  fileExists: (projectRoot: string, relativePath: string) => Promise<{ exists: boolean }>
}

declare global {
  interface Window {
    scriptApi: {
      validateScript: (jsonText: string) => Promise<ValidateResult>
      openScriptFile: () => Promise<
        { cancelled: true } | { cancelled: false; path: string; content: string }
      >
      saveScriptFile: (
        content: string,
        suggestedName?: string
      ) => Promise<{ cancelled: true } | { cancelled: false; path: string }>
    }
    projectApi: ProjectApi
  }
}

export {}
