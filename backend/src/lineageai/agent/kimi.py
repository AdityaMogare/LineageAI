import json
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from lineageai.agent.interfaces import ModelGenerator
from lineageai.config import Settings
from lineageai.models import (
    GeneratedModel,
    MetadataContext,
    ValidationDiagnostic,
)

_SYSTEM_PROMPT = """You are LineageAI, a senior analytics engineer.
Generate one production-ready dbt SQL model using only datasets and columns in
the metadata context. Return a JSON object with exactly these fields:
name, sql, schema_yml, input_datasets, explanation.

Requirements:
- SQL must be a read-only SELECT and valid DuckDB SQL.
- Reference available relations as schema.table (for example main.orders).
- Qualify joined columns and use explicit grouping.
- schema_yml must be dbt schema version 2 and include useful not_null/unique tests.
- input_datasets must contain each source dataset name.
- Do not use markdown fences or add text outside the JSON object.
"""


class KimiGenerationError(RuntimeError):
    pass


class KimiModelGenerator(ModelGenerator):
    def __init__(
        self,
        settings: Settings,
        client: OpenAI | None = None,
    ) -> None:
        if client is None and not settings.moonshot_api_key:
            raise ValueError("MOONSHOT_API_KEY is required for live generation")
        self.settings = settings
        self.client = client or OpenAI(
            api_key=settings.moonshot_api_key,
            base_url=settings.moonshot_base_url,
        )

    def generate(
        self,
        prompt: str,
        context: MetadataContext,
        previous: GeneratedModel | None = None,
        diagnostics: list[ValidationDiagnostic] | None = None,
    ) -> GeneratedModel:
        user_payload: dict[str, Any] = {
            "request": prompt,
            "metadata_context": context.model_dump(mode="json"),
        }
        if previous is not None:
            user_payload["previous_draft"] = previous.model_dump(mode="json")
        if diagnostics:
            user_payload["validation_errors"] = [
                diagnostic.model_dump(mode="json") for diagnostic in diagnostics
            ]
            user_payload["instruction"] = (
                "Correct every validation error while preserving the requested intent."
            )

        response = self.client.chat.completions.create(
            model=self.settings.moonshot_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_payload)},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            extra_body={"reasoning_effort": "high"},
        )
        content = response.choices[0].message.content
        if not content:
            raise KimiGenerationError("Kimi returned an empty response")
        try:
            return GeneratedModel.model_validate_json(_remove_markdown_fence(content))
        except ValidationError as error:
            raise KimiGenerationError(f"Kimi returned an invalid model payload: {error}") from error


def _remove_markdown_fence(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1])
    return stripped
