import json
import random
import re
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any

import duckdb
from faker import Faker

from lineageai.models import ColumnMetadata, MetadataContext
from lineageai.validation.type_mapping import to_duckdb_type

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class StubDatabaseBuilder:
    def __init__(self, *, row_count: int = 20, seed: int = 42) -> None:
        if not 10 <= row_count <= 100:
            raise ValueError("row_count must be between 10 and 100")
        self.row_count = row_count
        self.fake = Faker()
        self.fake.seed_instance(seed)
        self.random = random.Random(seed)

    def build(self, context: MetadataContext, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with duckdb.connect(str(database_path)) as connection:
            for dataset in context.datasets:
                schema = _identifier(dataset.schema_name)
                table = _identifier(dataset.name)
                connection.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
                columns = ", ".join(
                    f'"{_identifier(column.name)}" {to_duckdb_type(column.native_type)}'
                    f"{' NOT NULL' if not column.nullable else ''}"
                    for column in dataset.columns
                )
                connection.execute(f'CREATE OR REPLACE TABLE "{schema}"."{table}" ({columns})')
                rows = [
                    tuple(self._value(column, index) for column in dataset.columns)
                    for index in range(self.row_count)
                ]
                placeholders = ", ".join("?" for _ in dataset.columns)
                connection.executemany(
                    f'INSERT INTO "{schema}"."{table}" VALUES ({placeholders})',
                    rows,
                )

    def _value(self, column: ColumnMetadata, index: int) -> Any:
        if column.sample_values:
            value = column.sample_values[index % len(column.sample_values)]
            if value is not None or column.nullable:
                return value
        normalized = to_duckdb_type(column.native_type)
        is_identifier = (
            column.is_primary_key
            or column.name.lower() == "id"
            or column.name.lower().endswith("_id")
        )
        if is_identifier:
            return index + 1
        if normalized.startswith(("TINYINT", "SMALLINT", "INTEGER", "BIGINT")):
            return self.random.randint(int(column.min_value or 1), int(column.max_value or 10_000))
        if normalized.startswith(("DOUBLE", "REAL", "DECIMAL")):
            return round(self.random.uniform(column.min_value or 0, column.max_value or 10_000), 2)
        if normalized == "BOOLEAN":
            return bool(index % 2)
        if normalized == "DATE":
            return date(2025, 1, 1 + (index % 28))
        if normalized.startswith("TIMESTAMP"):
            return datetime(2025, 1, 1 + (index % 28), 12, tzinfo=UTC)
        if normalized == "TIME":
            return time(12, index % 60)
        if normalized == "JSON":
            return json.dumps({"sample": index + 1})
        if "email" in column.name.lower():
            return self.fake.unique.email()
        if "name" in column.name.lower():
            return self.fake.name()
        return f"{column.name}_{index + 1}"


def _identifier(value: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"Unsafe SQL identifier: {value!r}")
    return value
