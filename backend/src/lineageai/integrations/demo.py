from lineageai.models import (
    ColumnMetadata,
    DatasetMetadata,
    ForeignKeyMetadata,
    MetadataContext,
)


def _customers() -> DatasetMetadata:
    return DatasetMetadata(
        name="customers",
        columns=[
            ColumnMetadata(
                name="customer_id",
                native_type="BIGINT",
                nullable=False,
                is_primary_key=True,
            ),
            ColumnMetadata(name="email", native_type="VARCHAR", nullable=False),
            ColumnMetadata(
                name="region",
                native_type="VARCHAR",
                sample_values=["north", "south", "east", "west"],
            ),
            ColumnMetadata(name="created_at", native_type="TIMESTAMP", nullable=False),
        ],
        row_count=2_000,
        owner="analytics",
    )


def _products() -> DatasetMetadata:
    return DatasetMetadata(
        name="products",
        columns=[
            ColumnMetadata(
                name="product_id",
                native_type="BIGINT",
                nullable=False,
                is_primary_key=True,
            ),
            ColumnMetadata(name="name", native_type="VARCHAR", nullable=False),
            ColumnMetadata(
                name="category",
                native_type="VARCHAR",
                sample_values=["electronics", "grocery", "apparel", "home"],
            ),
            ColumnMetadata(
                name="price",
                native_type="DECIMAL(12,2)",
                nullable=False,
                min_value=1,
                max_value=500,
            ),
        ],
        row_count=500,
        owner="catalog",
    )


def _orders() -> DatasetMetadata:
    return DatasetMetadata(
        name="orders",
        columns=[
            ColumnMetadata(
                name="id",
                native_type="BIGINT",
                nullable=False,
                is_primary_key=True,
            ),
            ColumnMetadata(name="customer_id", native_type="BIGINT", nullable=False),
            ColumnMetadata(
                name="amount",
                native_type="DECIMAL(12,2)",
                nullable=False,
                min_value=5,
                max_value=2_500,
            ),
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
    )


def _order_items() -> DatasetMetadata:
    return DatasetMetadata(
        name="order_items",
        columns=[
            ColumnMetadata(name="order_id", native_type="BIGINT", nullable=False),
            ColumnMetadata(name="product_id", native_type="BIGINT", nullable=False),
            ColumnMetadata(
                name="quantity",
                native_type="INTEGER",
                nullable=False,
                min_value=1,
                max_value=12,
            ),
        ],
        foreign_keys=[
            ForeignKeyMetadata(
                column="order_id",
                referenced_dataset="orders",
                referenced_column="id",
            ),
            ForeignKeyMetadata(
                column="product_id",
                referenced_dataset="products",
                referenced_column="product_id",
            ),
        ],
        row_count=25_000,
        owner="analytics",
    )


def _payments() -> DatasetMetadata:
    return DatasetMetadata(
        name="payments",
        columns=[
            ColumnMetadata(
                name="payment_id",
                native_type="BIGINT",
                nullable=False,
                is_primary_key=True,
            ),
            ColumnMetadata(name="order_id", native_type="BIGINT", nullable=False),
            ColumnMetadata(
                name="amount",
                native_type="DECIMAL(12,2)",
                nullable=False,
                min_value=5,
                max_value=2_500,
            ),
            ColumnMetadata(
                name="method",
                native_type="VARCHAR",
                nullable=False,
                sample_values=["card", "ach", "wallet"],
            ),
            ColumnMetadata(name="paid_at", native_type="TIMESTAMP", nullable=False),
        ],
        foreign_keys=[
            ForeignKeyMetadata(
                column="order_id",
                referenced_dataset="orders",
                referenced_column="id",
            )
        ],
        row_count=9_500,
        owner="finance",
    )


class DemoMetadataProvider:
    """Deterministic local context used when developing without DataHub.

    Mirrors the datasets seeded into the DataHub quickstart by
    ``infra/seed_datahub.py`` so demo mode and live mode describe the same
    world: ``customers``, ``products``, ``orders``, ``order_items``, and
    ``payments``, joined through explicit foreign keys.
    """

    def retrieve(self, prompt: str) -> MetadataContext:
        return MetadataContext(
            datasets=[
                _customers(),
                _products(),
                _orders(),
                _order_items(),
                _payments(),
            ],
            upstream_lineage={
                "orders": ["customers"],
                "order_items": ["orders", "products"],
                "payments": ["orders"],
            },
        )
