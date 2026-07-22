"""Run the three LineageAI demo scenarios end to end without external services.

Each scenario drives the real ``RunService`` -> LangGraph -> ``DbtValidator``
pipeline with the ``DemoMetadataProvider`` and a scripted generator, so the
full generate -> validate -> correct -> review loop executes without a
Moonshot key, DataHub, or GitHub. The only faked boundary is the LLM.

Usage:

    python -m lineageai.scenarios                    # run and print a summary
    python -m lineageai.scenarios --write-examples   # also write examples/<name>/
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from lineageai.api.run_service import ReviewDecision, RunService, RunView
from lineageai.integrations.demo import DemoMetadataProvider
from lineageai.models import (
    GeneratedModel,
    MetadataContext,
    ValidationDiagnostic,
    ValidationResult,
)
from lineageai.validation import DbtValidator


class ScriptedGenerator:
    """Returns pre-written drafts in order; repeats the last one if exhausted."""

    def __init__(self, drafts: list[GeneratedModel]) -> None:
        if not drafts:
            raise ValueError("ScriptedGenerator requires at least one draft")
        self.drafts = drafts
        self.calls = 0

    def generate(
        self,
        prompt: str,
        context: MetadataContext,
        previous: GeneratedModel | None = None,
        diagnostics: list[ValidationDiagnostic] | None = None,
    ) -> GeneratedModel:
        draft = self.drafts[min(self.calls, len(self.drafts) - 1)]
        self.calls += 1
        return draft


class RecordingValidator:
    """Delegates to DbtValidator while keeping every attempt for the trace."""

    def __init__(self) -> None:
        self.inner = DbtValidator()
        self.results: list[ValidationResult] = []

    def validate(self, model: GeneratedModel, context: MetadataContext) -> ValidationResult:
        result = self.inner.validate(model, context)
        self.results.append(result)
        return result


@dataclass(frozen=True)
class Scenario:
    name: str
    prompt: str
    drafts: list[GeneratedModel]
    expected_retries: int


@dataclass
class ScenarioOutcome:
    scenario: Scenario
    run: RunView
    attempts: list[ValidationResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return (
            self.run.status == "approved"
            and self.run.retry_count == self.scenario.expected_retries
            and self.run.validation is not None
            and self.run.validation.success
        )


def _model(name: str, sql: str, inputs: list[str], tested_column: str) -> GeneratedModel:
    schema_yml = f"""
version: 2
models:
  - name: {name}
    columns:
      - name: {tested_column}
        data_tests:
          - not_null
"""
    return GeneratedModel(name=name, sql=sql, schema_yml=schema_yml, input_datasets=inputs)


def build_scenarios() -> list[Scenario]:
    happy_sql = """
select
    c.customer_id,
    c.region,
    sum(o.amount) as total_revenue
from main.customers c
join main.orders o on o.customer_id = c.customer_id
group by c.customer_id, c.region
"""
    healing_broken_sql = """
select
    c.customer_id,
    c.regoin,
    sum(o.amount) as total_revenue
from main.customers c
join main.orders o on o.customer_id = c.customer_id
group by c.customer_id, c.regoin
"""
    complex_sql = """
select
    p.category,
    c.region,
    sum(oi.quantity * p.price) as gross_item_revenue,
    count(distinct pay.payment_id) as payment_count
from main.orders o
join main.customers c on c.customer_id = o.customer_id
join main.order_items oi on oi.order_id = o.id
join main.products p on p.product_id = oi.product_id
left join main.payments pay on pay.order_id = o.id
group by p.category, c.region
"""
    return [
        Scenario(
            name="happy_path",
            prompt="Build a customer revenue model by region from orders and customers.",
            drafts=[
                _model(
                    "customer_revenue",
                    happy_sql,
                    ["customers", "orders"],
                    "customer_id",
                )
            ],
            expected_retries=0,
        ),
        Scenario(
            name="self_healing",
            prompt="Build a regional revenue model; the first draft misspells a column.",
            drafts=[
                _model(
                    "regional_revenue",
                    healing_broken_sql,
                    ["customers", "orders"],
                    "customer_id",
                ),
                _model(
                    "regional_revenue",
                    happy_sql,
                    ["customers", "orders"],
                    "customer_id",
                ),
            ],
            expected_retries=1,
        ),
        Scenario(
            name="complex_lineage",
            prompt=(
                "Build category revenue by region joining orders, order items, "
                "products, and payments."
            ),
            drafts=[
                _model(
                    "category_revenue",
                    complex_sql,
                    ["orders", "customers", "order_items", "products", "payments"],
                    "category",
                )
            ],
            expected_retries=0,
        ),
    ]


def run_scenario(scenario: Scenario) -> ScenarioOutcome:
    validator = RecordingValidator()
    service = RunService(
        DemoMetadataProvider(),
        ScriptedGenerator(list(scenario.drafts)),
        validator,
    )
    run = service.start(scenario.prompt)
    if run.status == "awaiting_review":
        run = service.review(run.id, ReviewDecision(approved=True))
    return ScenarioOutcome(scenario=scenario, run=run, attempts=validator.results)


def write_example(outcome: ScenarioOutcome, examples_root: Path) -> Path:
    directory = examples_root / outcome.scenario.name
    directory.mkdir(parents=True, exist_ok=True)
    draft = outcome.run.draft
    assert draft is not None
    (directory / "prompt.md").write_text(f"# Prompt\n\n{outcome.scenario.prompt}\n")
    (directory / f"{draft.name}.sql").write_text(draft.sql.strip() + "\n")
    (directory / f"{draft.name}.yml").write_text(draft.schema_yml.strip() + "\n")
    lines = []
    for attempt_number, attempt in enumerate(outcome.attempts, start=1):
        verdict = "success" if attempt.success else "failure"
        lines.append(
            f"attempt {attempt_number}: {verdict}"
            f" ({attempt.command}, {attempt.elapsed_seconds:.1f}s)"
        )
        for diagnostic in attempt.diagnostics:
            location = f" line {diagnostic.line}" if diagnostic.line else ""
            lines.append(f"  [{diagnostic.kind}]{location} {diagnostic.message}")
            if diagnostic.suggestion:
                lines.append(f"  suggestion: {diagnostic.suggestion}")
    (directory / "validation.log").write_text("\n".join(lines) + "\n")
    return directory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-examples",
        action="store_true",
        help="write prompt, SQL, YAML, and validation trace to examples/<scenario>/",
    )
    parser.add_argument(
        "--examples-root",
        type=Path,
        default=Path("examples"),
        help="directory that receives scenario artifacts (default: examples/)",
    )
    args = parser.parse_args(argv)

    failures = 0
    for scenario in build_scenarios():
        outcome = run_scenario(scenario)
        verdict = "ok" if outcome.ok else "FAILED"
        print(
            f"{scenario.name}: {verdict}"
            f" (status={outcome.run.status},"
            f" retries={outcome.run.retry_count},"
            f" dbt_attempts={len(outcome.attempts)})"
        )
        if not outcome.ok:
            failures += 1
            continue
        if args.write_examples:
            directory = write_example(outcome, args.examples_root)
            print(f"  wrote {directory}/")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
