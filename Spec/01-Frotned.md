# Frontend Build — Spec, Decisions, and Implementation Log

This phase builds the review-UI components (`ValidationReport`,
`LineagePreview`) **before** any external API keys (Moonshot, GitHub,
DataHub) are configured. The frontend only ever talks to our own backend
through `frontend/src/api.ts`, so the JSON contract defined by the Pydantic
models in `backend/src/lineageai/models.py` is the build target — live
credentials are never required for frontend work.

## Why frontend-first works (decision record)

1. **The API contract is already stable.** `RunView` in
   `backend/src/lineageai/api/run_service.py` serializes `GeneratedModel`
   and `ValidationResult` verbatim. Both new components render data that
   already flows through `POST /api/runs` and `GET /api/runs/{id}`; no new
   endpoints were needed.
2. **Diagnostics were already returned but never rendered** (a known
   limitation in `01-Implementation-Context.md`). `ValidationReport` closes
   that gap purely client-side.
3. **Input datasets were already returned as badges.** `LineagePreview`
   upgrades them to a graphical DAG using the same `draft.input_datasets`
   field.
4. **Keys drop in later without code changes.** Demo metadata mode and the
   publisher-optional wiring in `routes.py` mean `MOONSHOT_API_KEY`,
   `GITHUB_TOKEN`, and `DATAHUB_TOKEN` only change runtime behavior, not
   frontend code.

## Implementation log and per-decision rationale

### Step 1 — Type contract first (`frontend/src/api.ts`)

Commit: `feat: render dbt validation diagnostics in review UI`

- **Decision:** Before writing components, the frontend `Validation` type
  was extended from `{ success, diagnostics }` to the full backend
  `ValidationResult` shape: `command`, `stdout`, `stderr`,
  `elapsed_seconds`, and a typed `DiagnosticKind` union mirroring
  `ValidationErrorKind`. *Rationale:* the backend already sends these
  fields; typing them prevents guess-and-reconcile churn later.
- **Decision:** `DiagnosticKind` is a string union, and the label lookup in
  `ValidationReport` falls back to "Unknown" for unrecognized kinds.
  *Rationale:* a new backend error kind must never break rendering.

### Step 2 — `ValidationReport` (`frontend/src/components/ValidationReport.tsx`)

Commit: `feat: render dbt validation diagnostics in review UI`

- Renders a pass/fail pill, the dbt command with elapsed seconds, the
  self-correction count, and one card per diagnostic (kind badge, line
  number when present, message, and the parser's correction suggestion).
- **Decision:** the component returns `null` when `validation` is null.
  *Rationale:* runs that error before validation simply omit the section;
  the parent needs no conditional wrapper.
- **Decision:** retry count is displayed here rather than only in the
  status card. *Rationale:* "passed after 2 corrections" is review-relevant
  context that belongs next to the diagnostics.
- **Decision:** `stdout`/`stderr` are typed but not rendered.
  *Rationale:* raw dbt logs are noisy; structured diagnostics are the
  reviewer-facing artifact. The fields stay in the type for future use.
- Tests (4): null state, success summary, full diagnostic rendering,
  singular/plural wording.

### Step 3 — `LineagePreview` (`frontend/src/components/LineagePreview.tsx`)

Commit: `feat: add SVG lineage preview of inputs to model`

- Hand-rolled SVG: input tables stacked left (sky blue), generated model
  right (emerald), one curved arrow per input with an arrowhead marker.
- **Decision:** no graph library (no reactflow/d3). *Rationale:* the
  topology is always a fixed two-column fan-in of 1–5 nodes; a layout
  engine adds a dependency and bundle weight for zero benefit.
- **Decision:** the SVG uses a computed `viewBox` whose height grows with
  the input count (`PADDING*2 + n*NODE_HEIGHT + (n-1)*NODE_GAP`).
  *Rationale:* responsive height for 1–5 inputs without clipping, per the
  acceptance criteria.
- **Decision:** empty model name falls back to `generated_model`, and the
  whole section returns `null` with zero inputs (backend enforces
  `input_datasets` min length 1, so this is a render guard, not
  validation).
- **Decision:** the DataHub write-back note is an opt-in prop
  (`showDatahubNote`), passed as `status === 'awaiting_review'` by the app.
  *Rationale:* the note describes what approval *will* do, so it is
  meaningless after approval/rejection.
- Accessibility: the SVG has `role="img"` and an `aria-label` naming the
  full edge list, which also gives tests a semantic query target.
- Tests (6): empty state, node rendering, edge count for 5 inputs,
  height growth, name fallback, note visibility.

### Step 4 — App integration (`frontend/src/App.tsx`)

Commit: `feat: surface lineage and validation in the review panel`

- Both components render in the right-hand review panel, above the SQL and
  `schema.yml` code panels, whenever a draft exists.
- **Decision:** they render for `failed` runs too, not just
  `awaiting_review`. *Rationale:* a run that exhausted its 3 corrections is
  exactly when a human most needs to see the diagnostics.
- **Decision:** the existing input-dataset badges were kept alongside the
  DAG. *Rationale:* badges are compact header context; removing them was
  churn with no benefit.
- App tests updated: mocks now send the complete `ValidationResult`
  payload, the happy-path test asserts the lineage graph and pass pill,
  and a new failed-run test asserts diagnostics rendering. The model-name
  query switched to `getByRole('heading')` because the name now also
  appears inside the SVG.

## Verification (all green as of this phase)

```text
npm run lint      # oxlint, no warnings
npm test -- --run # 13 tests, 3 files
npm run build     # tsc -b && vite build, succeeds
```

## Acceptance criteria

### Frontend
- ✅ ValidationReport component renders errors + retry count
- ✅ LineagePreview component displays input → output DAG
- ✅ All components styled with Tailwind, match existing theme
- ✅ No console errors when running demo mode
- ✅ Frontend tests pass (`npm test -- --run`)
- ✅ Build succeeds (`npm run build`)

### LineagePreview acceptance detail
- ✅ SVG renders correctly with input tables on left, generated model on right
- ✅ Arrows connect inputs to output
- ✅ Styling matches Tailwind theme (blue for inputs, green for output)
- ✅ Works with 1–5 input tables (responsive height)
- ✅ Shows model name (dynamic or "generated_model")
- ✅ Optional note about DataHub write-back

### Backend (unchanged this phase)
- ✅ DemoMetadataProvider has 5 tables with realistic schemas
- ✅ FK relationships defined correctly
- ✅ All 46 tests pass: `pytest backend/tests/ -v`
- ✅ Type mapping handles INT, VARCHAR, DECIMAL, TIMESTAMP
- ✅ Scenarios runner executes all 3 scenarios without errors

### Examples
- ✅ `examples/happy_path/` contains: prompt, SQL, YAML, validation_log
- ✅ `examples/self_healing/` contains: prompt, error_and_fix.md, validation traces
- ✅ `examples/complex_lineage/` contains: prompt, SQL, lineage notes
- ✅ All examples use realistic, interesting data

### Documentation
- ✅ README.md has: problem, solution, architecture, setup, usage, examples
- ✅ `.env.example` is complete and up-to-date
- ✅ No broken links or typos
- ✅ Setup instructions are tested and work

### Ready for APIs
- ✅ `MOONSHOT_API_KEY` can be added without code changes
- ✅ `GITHUB_TOKEN` and `DATAHUB_TOKEN` env vars recognized
- ✅ No blocking issues or TODOs
