import { useCallback, useState } from 'react'

function formatJson(text: string): string {
  return JSON.stringify(JSON.parse(text), null, 2)
}

export default function App(): JSX.Element {
  const [raw, setRaw] = useState('')
  const [preview, setPreview] = useState('')
  const [status, setStatus] = useState<'idle' | 'ok' | 'error'>('idle')
  const [errors, setErrors] = useState<{ path: string; message: string }[]>([])

  const runValidate = useCallback(async (text: string) => {
    if (!window.scriptApi) {
      setStatus('error')
      setErrors([{ path: '/', message: 'preload 未就绪' }])
      return
    }
    const res = await window.scriptApi.validateScript(text)
    if (res.ok) {
      setStatus('ok')
      setErrors([])
    } else {
      setStatus('error')
      setErrors(res.errors)
    }
  }, [])

  const handleOpen = async () => {
    const res = await window.scriptApi.openScriptFile()
    if (res.cancelled) return
    setRaw(res.content)
    try {
      setPreview(formatJson(res.content))
    } catch {
      setPreview(res.content)
    }
    setStatus('idle')
    setErrors([])
  }

  const handleValidate = () => {
    void runValidate(raw)
  }

  const handleExport = async () => {
    const res = await window.scriptApi.saveScriptFile(raw, 'tower_defense_script.json')
    if (!res.cancelled) {
      setStatus('ok')
      setErrors([{ path: '/', message: `已保存: ${res.path}` }])
    }
  }

  return (
    <div className="layout">
      <header className="header">
        <h1>塔防自动化 · 地图配置器（骨架）</h1>
        <p className="muted">
          读取 / 校验 / 预览 / 导出脚本 JSON（协议见仓库 <code>schemas/</code>）
        </p>
      </header>
      <div className="toolbar">
        <button type="button" onClick={() => void handleOpen()}>
          打开 JSON
        </button>
        <button type="button" onClick={() => void handleValidate()} disabled={!raw}>
          校验
        </button>
        <button type="button" onClick={() => void handleExport()} disabled={!raw}>
          导出
        </button>
        <button
          type="button"
          onClick={() => {
            try {
              setPreview(formatJson(raw))
            } catch {
              setPreview(raw)
            }
          }}
          disabled={!raw}
        >
          格式化预览
        </button>
      </div>
      <div className={`badge ${status}`}>
        {status === 'idle' && '未校验'}
        {status === 'ok' && '校验通过'}
        {status === 'error' && '校验失败或错误'}
      </div>
      {errors.length > 0 && (
        <ul className="errors">
          {errors.map((e, i) => (
            <li key={`${e.path}-${i}`}>
              <code>{e.path || '/'}</code> — {e.message}
            </li>
          ))}
        </ul>
      )}
      <div className="panes">
        <section className="pane">
          <h2>编辑区</h2>
          <textarea
            value={raw}
            onChange={(ev) => setRaw(ev.target.value)}
            spellCheck={false}
            placeholder="打开 JSON 或粘贴脚本…"
          />
        </section>
        <section className="pane">
          <h2>预览</h2>
          <pre className="preview">{preview || '（格式化后显示）'}</pre>
        </section>
      </div>
    </div>
  )
}
