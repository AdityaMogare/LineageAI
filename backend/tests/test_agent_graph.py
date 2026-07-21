from dataclasses import dataclass, field

from lineageai.agent import build_generation_graph
from lineageai.models import (
    GeneratedModel,
    MetadataContext,
    ValidationDiagnostic,
    ValidationErrorKind,
    ValidationResult,
)


@dataclass
class FakeMetadataProvider:
    context: MetadataContext
    calls: int = 0

    def retrieve(self, prompt: str) -> MetadataContext:
        self.calls += 1
        return self.context


@dataclass
class FakeGenerator:
    calls: list[list[ValidationDiagnostic]] = field(default_factory=list)

    def generate(
        self,
        prompt: str,
        context: MetadataContext,
        previous: GeneratedModel | None = None,
        diagnostics: list[ValidationDiagnostic] | None = None,
    ) -> GeneratedModel:
        self.calls.append(diagnostics or [])
        return GeneratedModel(
            name="revenue",
            sql="select id from main.orders",
            schema_yml="version: 2\nmodels:\n  - name: revenue\n",
            input_datasets=["orders"],
        )


class SequenceValidator:
    def __init__(self, outcomes: list[bool]) -> None:
        self.outcomes = iter(outcomes)
        self.calls = 0

    def validate(self, model: GeneratedModel, context: MetadataContext) -> ValidationResult:
        self.calls += 1
        success = next(self.outcomes)
        return ValidationResult(
            success=success,
            command="dbt build",
            diagnostics=[]
            if success
            else [
                ValidationDiagnostic(
                    kind=ValidationErrorKind.MISSING_COLUMN,
                    message="missing column",
                    suggestion="use amount",
                )
            ],
        )


def test_successful_generation_reaches_review(commerce_context: MetadataContext) -> None:
    provider = FakeMetadataProvider(commerce_context)
    generator = FakeGenerator()
    validator = SequenceValidator([True])

    result = build_generation_graph(provider, generator, validator).invoke(
        {"prompt": "Build revenue"}
    )

    assert result["status"] == "awaiting_review"
    assert result["retry_count"] == 0
    assert provider.calls == 1
    assert validator.calls == 1


def test_retries_with_diagnostics_and_cached_context(
    commerce_context: MetadataContext,
) -> None:
    provider = FakeMetadataProvider(commerce_context)
    generator = FakeGenerator()
    validator = SequenceValidator([False, True])

    result = build_generation_graph(provider, generator, validator).invoke(
        {"prompt": "Build revenue"}
    )

    assert result["status"] == "awaiting_review"
    assert result["retry_count"] == 1
    assert len(generator.calls) == 2
    assert generator.calls[1][0].kind == ValidationErrorKind.MISSING_COLUMN
    assert provider.calls == 1


def test_stops_after_three_corrections(commerce_context: MetadataContext) -> None:
    provider = FakeMetadataProvider(commerce_context)
    generator = FakeGenerator()
    validator = SequenceValidator([False, False, False, False])

    result = build_generation_graph(provider, generator, validator, max_retries=3).invoke(
        {"prompt": "Build revenue"}
    )

    assert result["status"] == "failed"
    assert result["retry_count"] == 4
    assert validator.calls == 4
    assert provider.calls == 1
