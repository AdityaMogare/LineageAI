# LineageAI

LineageAI is a metadata-aware dbt developer agent. It retrieves schemas and
lineage from DataHub, asks Kimi K3 to draft a dbt model, validates the model
against DuckDB, self-corrects failures, pauses for review, then opens a GitHub
pull request and writes lineage back to DataHub.

## Development

Requirements: Python 3.11–3.13, Node.js 22+, Docker, and Git.

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd frontend && npm install
```

Start the API:

```bash
uvicorn lineageai.main:app --reload --app-dir backend/src
```

Start the UI in another terminal:

```bash
cd frontend
npm run dev
```

Run checks:

```bash
ruff check .
ruff format --check .
mypy backend/src
pytest
cd frontend && npm run lint && npm test -- --run && npm run build
```

Detailed DataHub setup, credentials, architecture, and the demo workflow are
documented as the implementation is completed.

## License

Apache License 2.0.
