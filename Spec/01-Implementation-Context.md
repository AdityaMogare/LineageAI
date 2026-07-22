# LineageAI Implementation Context

This document is the implementation map for LineageAI. Use it to understand
what the product does, which dependencies it uses, and where each capability
is implemented. The product requirements remain in `00-Inital-app.md` and
`00-Architecture.md`.

## 1. Product Purpose

LineageAI is a metadata-aware dbt developer agent. It:

1. Accepts a natural-language request for a data model.
2. Retrieves table schemas, profiles, and lineage from DataHub or a
   deterministic demo provider.
3. Sends the request and metadata context to Kimi K3.
4. Receives a dbt SQL model and `schema.yml`.
5. Creates metadata-derived DuckDB tables with representative rows.
6. Runs real `dbt parse` and `dbt build` commands.
7. Returns structured validation errors to Kimi and retries up to three times.
8. Pauses for human approval or rejection.
9. On approval, creates a GitHub pull request and immediately writes the new
   dataset, tag, PR URL, and upstream lineage to DataHub.

## 2. Current Implementation Status

The initial product is implemented as a Python/TypeScript monorepo:

- Backend API and agent: `backend/src/lineageai/`
- Backend tests: `backend/tests/`
- React frontend: `frontend/`
- DataHub seed infrastructure: `infra/`
- Generated examples and validation logs: `examples/`
- CI: `.github/workflows/ci.yml`

The implementation is split across six feature commits:

- `cfc3089` — repository foundation
- `7327a15` — metadata-backed dbt validation
- `c8805e9` — self-healing LangGraph agent
- `1fe190e` — human review workflow
- `0968efa` — GitHub and DataHub publication
- `232148c` — demo assets and setup documentation

## 3. End-to-End Runtime Flow

```text
React prompt form
  -> POST /api/runs
  -> RunService creates a checkpointed LangGraph thread
  -> MetadataProvider retrieves context
  -> KimiModelGenerator creates SQL + schema.yml
  -> StubDatabaseBuilder creates and seeds DuckDB tables
  -> DbtValidator runs dbt parse + dbt build
      -> failure: parse diagnostics and regenerate (maximum 3 corrections)
      -> success: interrupt at awaiting_review
  -> POST /api/runs/{id}/review
      -> reject: terminal state, no external writes
      -> approve: GitHub PR, then DataHub write-back
  -> React displays the final state and PR link
```

The graph and its transitions are implemented in:

- `backend/src/lineageai/agent/graph.py`
- `backend/src/lineageai/api/run_service.py`

## 4. Architecture Layers

### Presentation

- `frontend/src/App.tsx`
  - Prompt form
  - Run status and retry count
  - Generated SQL and YAML review
  - Input-dataset badges
  - Approval and rejection controls
  - Published PR link
- `frontend/src/api.ts`
  - Typed requests for run creation and review
- `frontend/vite.config.ts`
  - Vite, Tailwind, Vitest, and `/api` development proxy

### HTTP API

- `backend/src/lineageai/main.py`
  - FastAPI application
  - CORS
  - `/api/health`
  - `/api/config`
- `backend/src/lineageai/api/routes.py`
  - `POST /api/runs`
  - `GET /api/runs/{run_id}`
  - `POST /api/runs/{run_id}/review`
  - Dependency wiring for metadata, Kimi, validation, and publication
- `backend/src/lineageai/api/run_service.py`
  - Run IDs and lifecycle
  - LangGraph checkpoint configuration
  - Review resume commands
  - Publication trigger and result storage

### Agent Orchestration

- `backend/src/lineageai/agent/graph.py`
  - LangGraph state schema
  - Context, generation, validation, retry, failure, and review nodes
  - Human `interrupt()`
  - Maximum-three-correction routing
- `backend/src/lineageai/agent/interfaces.py`
  - `MetadataProvider`
  - `ModelGenerator`
  - `ModelValidator`
  - Protocol-based boundaries for deterministic tests
- `backend/src/lineageai/agent/kimi.py`
  - Moonshot OpenAI-compatible client
  - Kimi K3 prompt and JSON-output contract
  - Pydantic validation of generated output

### Domain Models

All shared Pydantic models are in `backend/src/lineageai/models.py`:

- `ColumnMetadata`
- `ForeignKeyMetadata`
- `DatasetMetadata`
- `MetadataContext`
- `GeneratedModel`
- `ValidationDiagnostic`
- `ValidationResult`
- `ValidationErrorKind`

`GeneratedModel` keeps SQL and YAML together and rejects generated SQL that
contains mutating operations such as `DROP`, `DELETE`, `UPDATE`, or `INSERT`.

### Validation

- `backend/src/lineageai/validation/type_mapping.py`
  - Maps warehouse/DataHub types to DuckDB
  - Handles parameterized decimals and strings
  - Handles arrays
  - Maps `VARIANT`, `OBJECT`, `RECORD`, structures, and unknown types to JSON
  - Supports strict failure instead of fallback
- `backend/src/lineageai/validation/stubs.py`
  - Creates DuckDB schemas and tables from metadata
  - Validates identifiers before using them in DDL
  - Generates 10–100 deterministic rows
  - Uses profile ranges, sample values, Faker names/emails, and stable IDs
- `backend/src/lineageai/validation/error_parser.py`
  - Removes ANSI output
  - Extracts line numbers
  - Classifies compilation, binder, type, relation, column, ambiguity, syntax,
    test, and runtime failures
  - Adds correction suggestions for the generator
- `backend/src/lineageai/validation/validator.py`
  - Creates an isolated temporary dbt project
  - Writes `dbt_project.yml`, `profiles.yml`, SQL, and `schema.yml`
  - Runs `dbt parse`, followed by `dbt build`
  - Captures stdout and stderr
  - Returns a typed `ValidationResult`
  - Deletes the sandbox automatically

### Metadata and Publication Integrations

- `backend/src/lineageai/integrations/demo.py`
  - Deterministic local metadata for `orders` and `customers`
  - Default development mode
- `backend/src/lineageai/integrations/datahub.py`
  - `DataHubMetadataProvider` reads schema, profile, and upstream-lineage
    aspects with `DataHubGraph`
  - `DataHubPublisher` emits dataset properties, the `agent-generated` tag,
    PR URL, and upstream lineage with `MetadataChangeProposalWrapper`
- `backend/src/lineageai/integrations/github.py`
  - Creates a deterministic `lineageai/<run-id>` branch
  - Creates or updates generated SQL and YAML
  - Opens a pull request
  - Reuses an existing PR for the same run
- `backend/src/lineageai/integrations/publishing.py`
  - Coordinates GitHub before DataHub
  - Records partial success
  - Avoids repeating a successful GitHub operation when DataHub is retried

The runtime uses the DataHub Python SDK directly. In this codebase, DataHub
`MetadataChangeProposalWrapper` is abbreviated MCP by the SDK; there is not
currently a separate DataHub MCP Server client.

## 5. LangGraph State Schema

`AgentState` is a `TypedDict` in `backend/src/lineageai/agent/graph.py`:

- `prompt: str` — original user request
- `context: MetadataContext` — cached metadata for the whole run
- `draft: GeneratedModel` — latest SQL, YAML, inputs, and explanation
- `validation: ValidationResult` — latest dbt result and diagnostics
- `retry_count: int` — number of failed validation attempts
- `status: str` — current workflow state

SQL and YAML are nested in `draft`. Validation errors are nested in
`validation.diagnostics`; they are not duplicated as separate state fields.

Expected statuses are:

```text
running -> validating -> correcting -> awaiting_review
                                      -> failed
awaiting_review -> approved | rejected
```

Run checkpoints use LangGraph `InMemorySaver`. Prompt, feedback, and
publication side data also live in process memory, so runs do not survive an
API restart.

## 6. Dependency Context

### Python Runtime

Declared in `pyproject.toml`:

- `fastapi` and `uvicorn` — API server
- `langgraph` — graph execution, checkpoints, interrupts, cyclic retries
- `openai` — Kimi K3 through Moonshot's OpenAI-compatible API
- `dbt-core`, `dbt-duckdb`, and `duckdb` — local SQL execution
- `acryl-datahub` — metadata retrieval and write-back
- `pygithub` — branch, file, commit, and PR operations
- `faker` — representative stub rows
- `pydantic-settings` — environment-backed configuration
- `pyyaml` — generated dbt project files
- `httpx` — HTTP support and API tests

Supported Python versions are 3.11 through 3.13.

### Python Development

- `pytest`, `pytest-asyncio`, and `pytest-cov`
- `ruff`
- `mypy`
- `pre-commit`
- `types-pyyaml`

### Frontend Runtime and Build

Declared in `frontend/package.json`:

- `react` and `react-dom`
- `vite` and `@vitejs/plugin-react`
- `typescript`
- `tailwindcss` and `@tailwindcss/vite`
- `vitest`
- `@testing-library/react` and `@testing-library/jest-dom`
- `jsdom`
- `oxlint`

The recommended Node.js version is 22 or newer.

### External Services

- Moonshot API — required for live Kimi generation
- DataHub GMS — required for live metadata mode and write-back
- GitHub — required for PR publication
- Docker — only required for the local DataHub Quickstart

Demo metadata mode does not require DataHub, but live generation still requires
a Moonshot API key.

## 7. Configuration and Environment Variables

Configuration is defined in `backend/src/lineageai/config.py`. The safe
template is `.env.example`.

### Application

- `LINEAGEAI_ENVIRONMENT`
- `LINEAGEAI_API_HOST`
- `LINEAGEAI_API_PORT`
- `LINEAGEAI_CORS_ORIGINS`
- `LINEAGEAI_METADATA_MODE`
  - `demo` uses `DemoMetadataProvider`
  - `datahub` uses `DataHubMetadataProvider`

### Moonshot / Kimi

- `MOONSHOT_API_KEY`
- `MOONSHOT_BASE_URL`
  - Default: `https://api.moonshot.ai/v1`
- `MOONSHOT_MODEL`
  - Default: `kimi-k3`

### DataHub

- `DATAHUB_GMS_URL`
- `DATAHUB_TOKEN`
- `DATAHUB_PLATFORM`
- `DATAHUB_ENV`
- `DATAHUB_DATASETS`

### GitHub

- `GITHUB_TOKEN`
- `GITHUB_REPOSITORY`
- `GITHUB_BASE_BRANCH`
- `GITHUB_MODELS_PATH`

Publication is enabled only when both `GITHUB_TOKEN` and
`GITHUB_REPOSITORY` are configured. Secrets must remain in `.env`, which is
ignored by Git.

## 8. Test Context

Backend tests are under `backend/tests/`:

- `test_main.py` — health/config and secret non-disclosure
- `test_type_mapping.py` — warehouse type conversion and fallback
- `test_stubs.py` — DuckDB table creation and seeded rows
- `test_error_parser.py` — 10+ representative dbt error forms
- `test_validator.py` — real successful and failing dbt builds
- `test_kimi.py` — structured Kimi payload handling
- `test_agent_graph.py` — success, correction, exhaustion, and context caching
- `test_run_api.py` — API lifecycle, approval, and terminal rejection
- `test_datahub_retrieval.py` — DataHub read adapter
- `test_publishing.py` — GitHub idempotency, DataHub aspects, partial retry
- `test_end_to_end.py` — prompt, one real correction, approval, publication

Frontend behavior is tested in `frontend/src/App.test.tsx`.

The local suite currently covers 46 backend tests and 2 frontend tests.
External calls are replaced with typed fakes; live Moonshot, DataHub, and
GitHub smoke tests require credentials and running services.

CI runs:

```text
ruff check
ruff format --check
mypy
pytest
oxlint
vitest
vite build
```

## 9. Infrastructure and Examples

- `infra/seed_datahub.py`
  - Seeds `customers`, `products`, `orders`, and `order_items`
  - Adds schemas, row counts, key annotations, and lineage
- `examples/customer_revenue.sql`
  - Example generated dbt model
- `examples/customer_revenue.yml`
  - Example dbt tests
- `examples/validation.log`
  - Sanitized failure-and-correction trace

## 10. Local Setup

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd frontend && npm install && cd ..
```

Run the backend:

```bash
.venv/bin/uvicorn lineageai.main:app --reload --app-dir backend/src
```

Run the frontend in another terminal:

```bash
cd frontend
npm run dev
```

Optional local DataHub:

```bash
source .venv/bin/activate
datahub docker quickstart
python infra/seed_datahub.py
```

Full verification:

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy backend/src
.venv/bin/pytest
cd frontend
npm run lint
npm test -- --run
npm run build
```

## 11. Known Limitations and Follow-Up Context

- Run state is in memory and disappears when the API restarts.
- API run creation is synchronous; the frontend does not poll or stream.
- Demo metadata contains only `orders` and `customers`; the seed script creates
  four datasets.
- The frontend shows input datasets as badges, not a graphical lineage view.
- Validation diagnostics are returned by the API but are not rendered in the
  review UI.
- Rejection is terminal; there is no edit-and-resubmit path.
- Each run generates one model and one YAML file.
- The DataHub SDK is used directly rather than a separate DataHub MCP Server.
- Live Moonshot, DataHub, and GitHub behavior is not validated by CI.
- Unknown warehouse types fall back to DuckDB JSON unless strict mapping is
  requested.
- Publishing is coupled to GitHub configuration because DataHub write-back
  follows successful PR creation.

When changing any workflow component, update this document, the relevant
tests, `.env.example` if configuration changes, and `README.md` if setup or
operator behavior changes.
