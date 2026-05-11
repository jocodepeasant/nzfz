/// <reference types="vite/client" />

type ValidateResult =
  | { ok: true; errors: [] }
  | { ok: false; errors: { path: string; message: string }[] }

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
  }
}

export {}
