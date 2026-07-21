from typing import Any

from datahub.metadata.schema_classes import (
    DatasetProfileClass,
    OtherSchemaClass,
    SchemaFieldClass,
    SchemaFieldDataTypeClass,
    SchemaMetadataClass,
    StringTypeClass,
    UpstreamLineageClass,
)
from lineageai.config import Settings
from lineageai.integrations.datahub import DataHubMetadataProvider


class FakeGraph:
    def get_aspect(self, urn: str, aspect_type: type[Any]) -> Any:
        if aspect_type is SchemaMetadataClass:
            return SchemaMetadataClass(
                schemaName="main.orders",
                platform="urn:li:dataPlatform:duckdb",
                version=0,
                hash="test",
                platformSchema=OtherSchemaClass(rawSchema=""),
                fields=[
                    SchemaFieldClass(
                        fieldPath="id",
                        type=SchemaFieldDataTypeClass(type=StringTypeClass()),
                        nativeDataType="BIGINT",
                        nullable=False,
                        isPartOfKey=True,
                    )
                ],
            )
        if aspect_type is DatasetProfileClass:
            return DatasetProfileClass(timestampMillis=0, rowCount=42)
        if aspect_type is UpstreamLineageClass:
            return UpstreamLineageClass(upstreams=[])
        return None


def test_retrieves_schema_and_profile_from_datahub() -> None:
    provider = DataHubMetadataProvider(
        Settings(),
        ["orders", "customers"],
        graph=FakeGraph(),
    )

    context = provider.retrieve("Build an orders model")

    assert len(context.datasets) == 1
    assert context.datasets[0].name == "orders"
    assert context.datasets[0].columns[0].native_type == "BIGINT"
    assert context.datasets[0].columns[0].is_primary_key
    assert context.datasets[0].row_count == 42
