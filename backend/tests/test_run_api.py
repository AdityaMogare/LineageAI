from dataclasses import dataclass

from fastapi.testclient import TestClient
from lineageai.api.routes import get_run_service
from lineageai.api.run_service import ReviewDecision, RunService
from lineageai.main import app
from lineageai.models import (
    GeneratedModel,
    MetadataContext,
    ValidationDiagnostic,
    ValidationResult,
)


@dataclass
class Provider:
    context: MetadataContext

    def retrieve(self, prompt: str) -> MetadataContext:
        return self.context


class Generator:
    def generate(
        self,
        prompt: str,
        context: MetadataContext,
        previous: GeneratedModel | None = None,
        diagnostics: list[ValidationDiagnostic] | None = None,
    ) -> GeneratedModel:
        return GeneratedModel(
            name="revenue",
            sql="select id from main.orders",
            schema_yml="version: 2\nmodels:\n  - name: revenue\n",
            input_datasets=["orders"],
        )


class Validator:
    def validate(self, model: GeneratedModel, context: MetadataContext) -> ValidationResult:
        return ValidationResult(success=True, command="dbt build")


class Publisher:
    def __init__(self) -> None:
        self.calls = 0

    def publish(self, run_id: str, model: GeneratedModel) -> dict[str, object]:
        self.calls += 1
        return {
            "status": "published",
            "pull_request_url": "https://github.test/pr/1",
            "dataset_urn": "urn:li:dataset:test",
        }


def service(context: MetadataContext, publisher: Publisher | None = None) -> RunService:
    return RunService(Provider(context), Generator(), Validator(), publisher)


def test_approval_resumes_interrupted_run(commerce_context: MetadataContext) -> None:
    publisher = Publisher()
    runs = service(commerce_context, publisher)
    created = runs.start("Build customer revenue")

    assert created.status == "awaiting_review"
    assert created.draft

    approved = runs.review(
        created.id,
        decision=ReviewDecision(approved=True),
    )

    assert approved.status == "approved"
    assert approved.publication
    assert approved.publication["status"] == "published"
    assert publisher.calls == 1


def test_rejection_is_terminal_without_publication(
    commerce_context: MetadataContext,
) -> None:
    runs = service(commerce_context)
    created = runs.start("Build customer revenue")

    rejected = runs.review(
        created.id,
        decision=ReviewDecision(approved=False, feedback="Wrong grain"),
    )

    assert rejected.status == "rejected"
    assert rejected.feedback == "Wrong grain"
    assert rejected.publication is None


def test_run_endpoints(commerce_context: MetadataContext) -> None:
    runs = service(commerce_context)
    app.dependency_overrides[get_run_service] = lambda: runs
    client = TestClient(app)
    try:
        response = client.post("/api/runs", json={"prompt": "Build customer revenue"})
        assert response.status_code == 201
        created = response.json()
        assert created["status"] == "awaiting_review"

        reviewed = client.post(
            f"/api/runs/{created['id']}/review",
            json={"approved": True},
        )
        assert reviewed.status_code == 200
        assert reviewed.json()["status"] == "approved"
    finally:
        app.dependency_overrides.clear()
