from lineageai.models import (
    ColumnMetadata,
    DatasetMetadata,
    ForeignKeyMetadata,
    MetadataContext,
)


class DemoMetadataProvider:
    """Deterministic local context used when developing without DataHub."""

    def retrieve(self, prompt: str) -> MetadataContext:
        return MetadataContext(
            datasets=[
                DatasetMetadata(
                    name="orders",
                    columns=[
                        ColumnMetadata(
                            name="id",
                            native_type="BIGINT",
                            nullable=False,
                            is_primary_key=True,
                        ),
                        ColumnMetadata(name="customer_id", native_type="BIGINT", nullable=False),
                        ColumnMetadata(name="amount", native_type="DECIMAL(12,2)", nullable=False),
                        ColumnMetadata(name="created_at", native_type="TIMESTAMP", nullable=False),
                    ],
                    foreign_keys=[
                        ForeignKeyMetadata(
                            column="customer_id",
                            referenced_dataset="customers",
                            referenced_column="customer_id",
                        )
                    ],
                    row_count=10_000,
                    owner="analytics",
                ),
                DatasetMetadata(
                    name="customers",
                    columns=[
                        ColumnMetadata(
                            name="customer_id",
                            native_type="BIGINT",
                            nullable=False,
                            is_primary_key=True,
                        ),
                        ColumnMetadata(name="email", native_type="VARCHAR", nullable=False),
                        ColumnMetadata(name="region", native_type="VARCHAR"),
                        ColumnMetadata(name="created_at", native_type="TIMESTAMP", nullable=False),
                    ],
                    row_count=2_000,
                    owner="analytics",
                ),
            ],
            upstream_lineage={"orders": ["customers"]},
        )
