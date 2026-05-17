# 当 `npm run dev` 报 `Error: Electron uninstall` 或 `node_modules/electron` 为空时，
# 从 GitHub 下载与 package.json 中一致的 Windows x64 二进制到 `node_modules/electron/dist`，
# 并写入 `path.txt`。随后在本目录执行 `npm install`（恢复 .bin 等）。
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $here '..')
$electronDir = Join-Path $root 'node_modules\electron'
$ver = '33.3.1'
$url = "https://github.com/electron/electron/releases/download/v$ver/electron-v$ver-win32-x64.zip"
$zip = Join-Path $env:TEMP "electron-v$ver-win32-x64.zip"
$dist = Join-Path $electronDir 'dist'

New-Item -ItemType Directory -Force -Path $dist | Out-Null
Write-Host "Downloading $url ..."
Invoke-WebRequest -Uri $url -OutFile $zip
Write-Host "Extracting to $dist ..."
Expand-Archive -Path $zip -DestinationPath $dist -Force
Set-Content -Path (Join-Path $electronDir 'path.txt') -Value 'electron.exe' -NoNewline
$pkg = @'
{
  "name": "electron",
  "version": "33.3.1",
  "main": "index.js"
}
'@
Set-Content -Path (Join-Path $electronDir 'package.json') -Value $pkg -Encoding utf8
$index = @'
throw new Error(
  "The Electron module is not supported in Node.js. Use electron-vite or the electron CLI."
)
'@
Set-Content -Path (Join-Path $electronDir 'index.js') -Value $index -Encoding utf8
Write-Host "Done. electron.exe:" (Test-Path (Join-Path $dist 'electron.exe'))
Write-Host "Next: cd map-configurator && npm install && npm run dev"
