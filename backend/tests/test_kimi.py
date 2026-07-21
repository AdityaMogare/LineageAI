import json
from types import SimpleNamespace
from typing import Any, cast

import pytest
from lineageai.agent.kimi import KimiGenerationError, KimiModelGenerator
from lineageai.config import Settings
from lineageai.models import MetadataContext
from openai import OpenAI


class FakeCompletions:
    def __init__(self, content: str) -> None:
        self.content = content
        self.request: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.request = kwargs
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def fake_client(content: str) -> tuple[OpenAI, FakeCompletions]:
    completions = FakeCompletions(content)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return cast(OpenAI, client), completions


def test_generates_structured_model(commerce_context: MetadataContext) -> None:
    client, completions = fake_client(
        json.dumps(
            {
                "name": "revenue",
                "sql": "select id from main.orders",
                "schema_yml": "version: 2\nmodels:\n  - name: revenue\n",
                "input_datasets": ["orders"],
                "explanation": "Revenue model",
            }
        )
    )
    generator = KimiModelGenerator(Settings(), client=client)

    model = generator.generate("Build revenue", commerce_context)

    assert model.name == "revenue"
    assert completions.request["model"] == "kimi-k3"
    assert completions.request["response_format"] == {"type": "json_object"}


def test_accepts_json_inside_markdown_fence(commerce_context: MetadataContext) -> None:
    client, _ = fake_client(
        """```json
{"name":"revenue","sql":"select 1","schema_yml":"version: 2","input_datasets":["orders"]}
```"""
    )

    model = KimiModelGenerator(Settings(), client=client).generate(
        "Build revenue", commerce_context
    )

    assert model.name == "revenue"


def test_rejects_malformed_generation(commerce_context: MetadataContext) -> None:
    client, _ = fake_client('{"sql": "select 1"}')

    with pytest.raises(KimiGenerationError):
        KimiModelGenerator(Settings(), client=client).generate("Build revenue", commerce_context)
