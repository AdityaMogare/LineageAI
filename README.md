# LineageAI

LineageAI is a metadata-aware dbt developer agent. It retrieves schemas,
profiles, and lineage from DataHub; asks Kimi K3 to draft SQL and tests; runs
the model with dbt against metadata-derived DuckDB tables; self-corrects up to
three times; pauses for review; then opens a GitHub pull request and writes the
new dataset, tag, PR URL, and upstream lineage to DataHub.

## Architecture

```text
React UI → FastAPI → LangGraph
                       ├─ DataHub context retrieval
                       ├─ Kimi K3 generation
                       ├─ DuckDB stub generation
                       ├─ dbt parse + dbt build
                       ├─ bounded self-correction loop
                       ├─ human interrupt / resume
                       └─ GitHub PR + DataHub write-back
```

The backend uses typed adapters, so deterministic fakes can verify the whole
workflow without external writes. Live credentials are only read from the
environment. Validation runs in a temporary dbt project that is removed after
every attempt.

## Quickstart

Requirements: Python 3.11–3.13, Node.js 22+, Docker, and Git.

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd frontend && npm install && cd ..
```

Set `MOONSHOT_API_KEY` in `.env`. The default metadata mode is `demo`, which
uses the same seeded schema without requiring DataHub. To use the live catalog,
set `LINEAGEAI_METADATA_MODE=datahub`.

Start the API:

```bash
.venv/bin/uvicorn lineageai.main:app --reload --app-dir backend/src
```

Start the UI in another terminal:

```bash
cd frontend
npm run dev
```

Open <http://localhost:5173>.

## Local DataHub

Start the official DataHub quickstart and seed the demo metadata:

```bash
source .venv/bin/activate
datahub docker quickstart
python infra/seed_datahub.py
```

DataHub is available at <http://localhost:9002>; the API defaults to
`http://localhost:8080`. The seed creates `customers`, `products`, `orders`,
`order_items`, and `payments`, including schemas, row counts, primary-key
annotations, and lineage relationships. Demo metadata mode serves the same
five tables locally without DataHub.

Then update `.env`:

```dotenv
LINEAGEAI_METADATA_MODE=datahub
DATAHUB_GMS_URL=http://localhost:8080
DATAHUB_DATASETS=["orders","customers","products","order_items","payments"]
```

For authenticated DataHub deployments, also set `DATAHUB_TOKEN`.

## Publishing credentials

Approval performs write-back immediately when both GitHub values are set:

```dotenv
GITHUB_TOKEN=github_pat_...
GITHUB_REPOSITORY=owner/dbt-repository
GITHUB_BASE_BRANCH=main
GITHUB_MODELS_PATH=models/generated
```

The token needs repository contents and pull-request write permission. The
publisher uses a deterministic `lineageai/<run-id>` branch, reuses an existing
PR, and resumes at DataHub if GitHub succeeded but metadata write-back failed.
Never commit `.env`.

## Tests

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

Coverage includes type mapping, profile-informed stubs, 10+ known dbt error
forms, real dbt success/failure, Kimi payload validation, retries, exhausted
retries, checkpointed approval/rejection, GitHub idempotency, DataHub aspects,
and a complete prompt → one correction → approval → publication scenario.

The [`examples`](examples/) directory contains one folder per demo scenario
(`happy_path/`, `self_healing/`, `complex_lineage/`), each with the prompt,
generated SQL, `schema.yml`, and a validation trace.

## Demo scenarios

Run the three end-to-end scenarios without any API keys — the real LangGraph
loop and dbt validation execute, and only the LLM is scripted:

```bash
.venv/bin/python -m lineageai.scenarios                  # run and summarize
.venv/bin/python -m lineageai.scenarios --write-examples # regenerate examples/
```

`happy_path` validates first try, `self_healing` recovers from a misspelled
column after one correction, and `complex_lineage` joins all five demo tables.

## Three-minute demo

1. Show the five seeded datasets and lineage in DataHub.
2. Enter “Build customer revenue by region from orders and customers.”
3. Use the deterministic demo fixture to show one missing-column failure and
   the automatic correction.
4. Review SQL, `schema.yml`, and input lineage; click Approve.
5. Open the generated GitHub PR.
6. Refresh DataHub and show `main.customer_revenue`, the `agent-generated` tag,
   PR URL, and upstream lineage.

If a live service is unavailable during recording, use the deterministic
integration test and sanitized artifacts as the fallback; do not represent a
mocked service as a live write.

## Troubleshooting

- `MOONSHOT_API_KEY is required`: set the key and restart the API.
- DataHub schema not found: run `infra/seed_datahub.py` and verify platform,
  environment, and dataset names match `.env`.
- dbt executable not found: activate `.venv` or reinstall `.[dev]`.
- GitHub 403: verify fine-grained token repository permissions.
- A rejected run is terminal and intentionally performs no external writes.

## Security

Generated SQL is restricted to read-only statements. Identifiers are validated
before stub DDL is created, dbt runs in an isolated temporary directory, API
secrets are never returned to the client, and publication requires explicit
human approval. This prototype does not replace repository branch protection
or DataHub authorization policies.

## License

Apache License 2.0.
