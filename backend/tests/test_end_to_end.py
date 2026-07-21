from lineageai.api.run_service import ReviewDecision, RunService
from lineageai.integrations.demo import DemoMetadataProvider
from lineageai.models import (
    GeneratedModel,
    MetadataContext,
    ValidationDiagnostic,
)
from lineageai.validation import DbtValidator


class CorrectingGenerator:
    def __init__(self) -> None:
        self.calls = 0

    def generate(
        self,
        prompt: str,
        context: MetadataContext,
        previous: GeneratedModel | None = None,
        diagnostics: list[ValidationDiagnostic] | None = None,
    ) -> GeneratedModel:
        self.calls += 1
        sql = (
            "select missing_amount from main.orders"
            if self.calls == 1
            else """
                select
                    c.customer_id,
                    c.region,
                    sum(o.amount) as total_revenue
                from main.customers c
                join main.orders o on c.customer_id = o.customer_id
                group by c.customer_id, c.region
            """
        )
        return GeneratedModel(
            name="customer_revenue",
            sql=sql,
            schema_yml="""
version: 2
models:
  - name: customer_revenue
    columns:
      - name: customer_id
        data_tests:
          - not_null
""",
            input_datasets=["customers", "orders"],
        )


class RecordingPublisher:
    def publish(self, run_id: str, model: GeneratedModel) -> dict[str, object]:
        return {
            "status": "published",
            "pull_request_url": f"https://github.test/pull/{run_id}",
            "dataset_urn": f"urn:li:dataset:(duckdb,main.{model.name},DEV)",
        }


def test_prompt_retry_review_and_publication() -> None:
    generator = CorrectingGenerator()
    service = RunService(
        DemoMetadataProvider(),
        generator,
        DbtValidator(),
        RecordingPublisher(),
    )

    run = service.start("Build customer revenue by region")

    assert run.status == "awaiting_review"
    assert run.retry_count == 1
    assert generator.calls == 2
    assert run.validation and run.validation.success

    approved = service.review(run.id, ReviewDecision(approved=True))

    assert approved.status == "approved"
    assert approved.publication
    assert approved.publication["status"] == "published"
