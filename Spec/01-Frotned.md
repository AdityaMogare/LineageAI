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

### Step 5 — Demo metadata expansion (`backend/src/lineageai/integrations/demo.py`)

Commit: `feat: expand demo metadata to five related tables`

- `DemoMetadataProvider` now serves `customers`, `products`, `orders`,
  `order_items`, and `payments`.
- **Decision:** the fifth table is `payments` (not `regions`).
  *Rationale:* `region` already exists as a column on `customers`, so a
  `regions` dimension would duplicate information; payments adds a new join
  path (`payments.order_id -> orders.id`), a new owner (`finance`), and an
  interesting left-join case for generated models.
- **Decision:** schemas mirror `infra/seed_datahub.py` exactly, and
  `payments` was added to the seed script and `DATAHUB_DATASETS` defaults in
  the same commit. *Rationale:* demo mode and DataHub mode must describe the
  same world, or prompts that work in the demo break against the live
  catalog.
- **Decision:** columns carry `min_value`/`max_value` ranges and
  `sample_values` (regions, categories, payment methods). *Rationale:*
  `StubDatabaseBuilder` uses these to seed realistic DuckDB rows, so demo
  validation exercises the same value-aware paths as profiled DataHub
  metadata.
- Tests (`backend/tests/test_demo.py`): table set, FK referential integrity
  (every FK points at a real dataset and column), lineage map consistent
  with FKs, and a stub-database build from the demo context.

### Step 6 — Scenarios runner (`backend/src/lineageai/scenarios.py`)

Commit: `feat: add scenarios runner for the three demo flows`

- `python -m lineageai.scenarios` executes `happy_path`, `self_healing`,
  and `complex_lineage`; `--write-examples` regenerates
  `examples/<scenario>/` with prompt, SQL, YAML, and a validation trace.
- **Decision:** scenarios drive the real `RunService` -> LangGraph ->
  `DbtValidator` pipeline; only the LLM is a `ScriptedGenerator` returning
  pre-written drafts in order. *Rationale:* every failure, correction, and
  dbt build in the traces is real, and no `MOONSHOT_API_KEY` is needed —
  consistent with the frontend-first, keys-last plan.
- **Decision:** `self_healing` submits a draft with a misspelled column
  (`regoin`) first, then the corrected SQL, asserting exactly one retry.
  *Rationale:* proves the diagnostic-driven correction loop with a real
  `missing_column` diagnostic from the error parser.
- **Decision:** `complex_lineage` joins all five demo tables (including a
  left join to `payments`). *Rationale:* exercises the widest lineage fan-in
  the `LineagePreview` supports (5 inputs).
- **Decision:** every scenario directory gets the same uniform artifact set
  (`prompt.md`, `<model>.sql`, `<model>.yml`, `validation.log`) instead of
  bespoke files per scenario. *Rationale:* one writer function, and the
  self-healing `validation.log` already contains the error-and-fix
  narrative (attempt 1 failure with diagnostics, attempt 2 success).
- Tests (`backend/tests/test_scenarios.py`): flow list, exit code 0, all
  artifacts written, and the self-healing trace shows failure-then-success.

## Verification (all green as of this phase)

```text
npm run lint      # oxlint, no warnings
npm test -- --run # 13 tests, 3 files
npm run build     # tsc -b && vite build, succeeds
ruff check / ruff format --check / mypy backend/src   # clean
pytest            # 52 backend tests
python -m lineageai.scenarios   # 3/3 scenarios ok, exit 0
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

### Backend
- ✅ DemoMetadataProvider has 5 tables with realistic schemas
- ✅ FK relationships defined correctly
- ✅ All 52 tests pass: `pytest backend/tests/ -v`
- ✅ Type mapping handles INT, VARCHAR, DECIMAL, TIMESTAMP
- ✅ Scenarios runner executes all 3 scenarios without errors
  (`python -m lineageai.scenarios`)

### Examples
- ✅ `examples/happy_path/` contains: prompt, SQL, YAML, validation log
- ✅ `examples/self_healing/` contains: prompt, SQL, YAML, and a validation
  trace showing the failed attempt, its diagnostics, and the fix
- ✅ `examples/complex_lineage/` contains: prompt, five-table SQL, YAML,
  validation log (lineage is captured in `input_datasets` and the trace)
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
