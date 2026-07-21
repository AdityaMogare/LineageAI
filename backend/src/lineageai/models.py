from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class ColumnMetadata(BaseModel):
    name: str
    native_type: str
    nullable: bool = True
    description: str | None = None
    is_primary_key: bool = False
    min_value: float | None = None
    max_value: float | None = None
    sample_values: list[str | int | float | bool | None] = Field(default_factory=list)


class ForeignKeyMetadata(BaseModel):
    column: str
    referenced_dataset: str
    referenced_column: str


class DatasetMetadata(BaseModel):
    name: str
    platform: str = "duckdb"
    schema_name: str = "main"
    columns: list[ColumnMetadata]
    foreign_keys: list[ForeignKeyMetadata] = Field(default_factory=list)
    row_count: int | None = None
    owner: str | None = None
    freshness: str | None = None


class MetadataContext(BaseModel):
    datasets: list[DatasetMetadata]
    upstream_lineage: dict[str, list[str]] = Field(default_factory=dict)

    def dataset(self, name: str) -> DatasetMetadata:
        for dataset in self.datasets:
            if dataset.name == name:
                return dataset
        raise KeyError(f"Dataset not found: {name}")


class GeneratedModel(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    sql: str = Field(min_length=1)
    schema_yml: str = Field(min_length=1)
    input_datasets: list[str] = Field(min_length=1)
    explanation: str = ""

    @field_validator("sql")
    @classmethod
    def reject_unsafe_sql(cls, value: str) -> str:
        normalized = value.upper()
        forbidden = ("DROP ", "TRUNCATE ", "DELETE ", "UPDATE ", "INSERT ", "ATTACH ")
        if any(token in normalized for token in forbidden):
            raise ValueError("Generated SQL must be read-only")
        return value.strip().rstrip(";")


class ValidationErrorKind(StrEnum):
    COMPILATION = "compilation"
    BINDER = "binder"
    TYPE = "type"
    MISSING_RELATION = "missing_relation"
    MISSING_COLUMN = "missing_column"
    AMBIGUOUS_COLUMN = "ambiguous_column"
    SYNTAX = "syntax"
    TEST_FAILURE = "test_failure"
    RUNTIME = "runtime"
    UNKNOWN = "unknown"


class ValidationDiagnostic(BaseModel):
    kind: ValidationErrorKind
    message: str
    line: int | None = None
    suggestion: str | None = None


class ValidationResult(BaseModel):
    success: bool
    command: str
    stdout: str = ""
    stderr: str = ""
    diagnostics: list[ValidationDiagnostic] = Field(default_factory=list)
    elapsed_seconds: float = 0
