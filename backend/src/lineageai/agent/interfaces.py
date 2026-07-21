from typing import Protocol

from lineageai.models import (
    GeneratedModel,
    MetadataContext,
    ValidationDiagnostic,
    ValidationResult,
)


class MetadataProvider(Protocol):
    def retrieve(self, prompt: str) -> MetadataContext: ...


class ModelGenerator(Protocol):
    def generate(
        self,
        prompt: str,
        context: MetadataContext,
        previous: GeneratedModel | None = None,
        diagnostics: list[ValidationDiagnostic] | None = None,
    ) -> GeneratedModel: ...


class ModelValidator(Protocol):
    def validate(self, model: GeneratedModel, context: MetadataContext) -> ValidationResult: ...
