# AGENTS.md

## Cursor Cloud specific instructions

This is a monorepo with two independent sub-projects sharing a JSON Schema protocol (`schemas/`).

### Services

| Service | Path | Stack | Dev Command |
|---|---|---|---|
| Map Configurator | `map-configurator/` | Electron + Vite + React + TypeScript | `cd map-configurator && npm run dev` |
| Automation Executor | `automation-executor/` | Python 3.10+ CLI (typer, jsonschema, rich) | `cd automation-executor && pip install -e . && python -m td_executor --help` |

### Lint / Type-check

- **Map Configurator**: No ESLint config exists. Use `npx tsc --build --noEmit` in `map-configurator/` for TypeScript type-checking.
- **Automation Executor**: No ruff/mypy/flake8 config exists. No automated tests are configured.

### Running the Electron app (map-configurator)

- `npm run dev` from `map-configurator/` starts electron-vite dev server on `http://localhost:5173/` and launches the Electron window.
- In headless/container environments (Cloud Agent VMs), the dbus/GPU errors in the console are expected and non-fatal — the app still renders via Xvfb.
- The main process resolves the JSON Schema at `../schemas/tower_defense_script_v1.schema.json` relative to `process.cwd()`, so always launch from inside `map-configurator/`.

### Running the Python CLI (automation-executor)

- Install: `cd automation-executor && pip install -e .`
- Validate: `python -m td_executor validate ../schemas/examples/space_station_normal_baseline_v1.json`
- Dry-run: `python -m td_executor run ../schemas/examples/space_station_normal_baseline_v1.json --dry-run`
- The `td-executor` entry-point script installs to `~/.local/bin/` (user install); ensure this is on `PATH` if using the CLI directly.

### Key gotchas

- No lockfiles exist (`package-lock.json`, `yarn.lock`, etc.) — `npm install` will resolve latest compatible versions each time.
- Optional Python extras (`[runtime,win,input,ocr]`) are not needed for core validate/dry-run functionality; `[win]` extras will fail on Linux.
