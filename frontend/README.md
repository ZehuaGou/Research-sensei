# ResearchSensei Frontend

Vue 3 + TypeScript + Vite frontend for the Chinese ResearchSensei workflow:
Home, Upload, DirectionSearchView, SeedExpansionPanel, Settings,
PaperWorkspace, and the M4 tutor panel.

## Commands

```powershell
npm install
npm test
npm run build
npm run dev
```

The Vite dev server runs on port `13000` and proxies `/api` and `/ws` to
`127.0.0.1:8765`.

Start the backend from the repository root:

```powershell
.venv\Scripts\python.exe -m uvicorn "researchsensei.web.app:create_app" --factory --host 127.0.0.1 --port 8765
```

## UI Contract

- User-facing copy is Chinese by default.
- PaperWorkspace uses a left reading nav, central card pane, and right M4 tutor.
- `StatusBanner` is compact; detailed technical fields live under a collapsed
  status section.
- `TextSelectionToolbar` positions from the selected text rectangle and clamps
  to the viewport to avoid browser-native selection menus.
- M4 UI mounts only when `/cards` is allowed.
- `BASELINE_ONLY`, `BLOCKED_UNDERSTANDING`, and `FAILED` must not show
  explanatory cards.
