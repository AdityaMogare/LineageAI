"""Seed the local DataHub quickstart with LineageAI demo datasets."""

import os
import time
from dataclasses import dataclass

from datahub.emitter.mce_builder import make_data_platform_urn, make_dataset_urn
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import (
    AuditStampClass,
    DatasetLineageTypeClass,
    DatasetProfileClass,
    DatasetPropertiesClass,
    NumberTypeClass,
    OtherSchemaClass,
    SchemaFieldClass,
    SchemaFieldDataTypeClass,
    SchemaMetadataClass,
    StringTypeClass,
    UpstreamClass,
    UpstreamLineageClass,
)

PLATFORM = "duckdb"
ENVIRONMENT = "DEV"


@dataclass(frozen=True)
class Table:
    name: str
    columns: tuple[tuple[str, str, bool, bool], ...]
    row_count: int
    upstreams: tuple[str, ...] = ()


TABLES = (
    Table(
        "customers",
        (
            ("customer_id", "BIGINT", False, True),
            ("email", "VARCHAR", False, False),
            ("region", "VARCHAR", True, False),
            ("created_at", "TIMESTAMP", False, False),
        ),
        2_000,
    ),
    Table(
        "products",
        (
            ("product_id", "BIGINT", False, True),
            ("name", "VARCHAR", False, False),
            ("category", "VARCHAR", True, False),
            ("price", "DECIMAL(12,2)", False, False),
        ),
        500,
    ),
    Table(
        "orders",
        (
            ("id", "BIGINT", False, True),
            ("customer_id", "BIGINT", False, False),
            ("amount", "DECIMAL(12,2)", False, False),
            ("created_at", "TIMESTAMP", False, False),
        ),
        10_000,
        ("customers",),
    ),
    Table(
        "order_items",
        (
            ("order_id", "BIGINT", False, False),
            ("product_id", "BIGINT", False, False),
            ("quantity", "INTEGER", False, False),
        ),
        25_000,
        ("orders", "products"),
    ),
)


def main() -> None:
    emitter = DatahubRestEmitter(
        gms_server=os.getenv("DATAHUB_GMS_URL", "http://localhost:8080"),
        token=os.getenv("DATAHUB_TOKEN") or None,
    )
    emitter.test_connection()
    for table in TABLES:
        urn = make_dataset_urn(PLATFORM, f"main.{table.name}", ENVIRONMENT)
        emit(
            emitter,
            urn,
            DatasetPropertiesClass(
                name=table.name,
                description="LineageAI local demo dataset.",
                customProperties={"seeded_by": "infra/seed_datahub.py"},
            ),
        )
        emit(
            emitter,
            urn,
            SchemaMetadataClass(
                schemaName=f"main.{table.name}",
                platform=make_data_platform_urn(PLATFORM),
                version=0,
                hash="lineageai-demo-v1",
                platformSchema=OtherSchemaClass(rawSchema=""),
                fields=[
                    SchemaFieldClass(
                        fieldPath=name,
                        type=SchemaFieldDataTypeClass(
                            type=(
                                StringTypeClass()
                                if native_type in {"VARCHAR", "TIMESTAMP"}
                                else NumberTypeClass()
                            )
                        ),
                        nativeDataType=native_type,
                        nullable=nullable,
                        isPartOfKey=primary_key,
                    )
                    for name, native_type, nullable, primary_key in table.columns
                ],
                primaryKeys=[name for name, _, _, primary_key in table.columns if primary_key],
            ),
        )
        emit(
            emitter,
            urn,
            DatasetProfileClass(
                timestampMillis=int(time.time() * 1000),
                rowCount=table.row_count,
                columnCount=len(table.columns),
            ),
        )
        if table.upstreams:
            emit(
                emitter,
                urn,
                UpstreamLineageClass(
                    upstreams=[
                        UpstreamClass(
                            dataset=make_dataset_urn(PLATFORM, f"main.{name}", ENVIRONMENT),
                            type=DatasetLineageTypeClass.TRANSFORMED,
                            auditStamp=AuditStampClass(
                                time=int(time.time() * 1000),
                                actor="urn:li:corpuser:lineageai",
                            ),
                        )
                        for name in table.upstreams
                    ]
                ),
            )
        print(f"Seeded {urn}")


def emit(emitter: DatahubRestEmitter, urn: str, aspect: object) -> None:
    emitter.emit(
        MetadataChangeProposalWrapper(
            entityUrn=urn,
            aspect=aspect,  # type: ignore[arg-type]
        )
    )


if __name__ == "__main__":
    main()
