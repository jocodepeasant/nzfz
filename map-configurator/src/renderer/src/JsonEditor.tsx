import CodeMirror from '@uiw/react-codemirror'
import { json } from '@codemirror/lang-json'
import { search, searchKeymap } from '@codemirror/search'
import { keymap } from '@codemirror/view'

type JsonEditorProps = {
  value: string
  onChange: (value: string) => void
  className?: string
}

const extensions = [json(), search({ top: true }), keymap.of(searchKeymap)]

export function JsonEditor({ value, onChange, className }: JsonEditorProps): JSX.Element {
  return (
    <CodeMirror
      className={className}
      value={value}
      height="100%"
      minHeight="280px"
      theme="dark"
      extensions={extensions}
      basicSetup={{
        lineNumbers: false,
        foldGutter: false,
        highlightActiveLine: false
      }}
      onChange={onChange}
    />
  )
}
