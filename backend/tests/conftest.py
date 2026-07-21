import pytest
from lineageai.models import ColumnMetadata, DatasetMetadata, MetadataContext


@pytest.fixture
def commerce_context() -> MetadataContext:
    return MetadataContext(
        datasets=[
            DatasetMetadata(
                name="orders",
                columns=[
                    ColumnMetadata(
                        name="id", native_type="BIGINT", nullable=False, is_primary_key=True
                    ),
                    ColumnMetadata(name="customer_id", native_type="BIGINT", nullable=False),
                    ColumnMetadata(name="amount", native_type="DECIMAL(12,2)", nullable=False),
                    ColumnMetadata(name="created_at", native_type="TIMESTAMP", nullable=False),
                ],
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
                    ColumnMetadata(name="email", native_type="STRING", nullable=False),
                    ColumnMetadata(name="region", native_type="STRING"),
                ],
            ),
        ]
    )
