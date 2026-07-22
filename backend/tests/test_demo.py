from pathlib import Path

from lineageai.integrations.demo import DemoMetadataProvider
from lineageai.validation.stubs import StubDatabaseBuilder


def test_demo_provider_exposes_five_tables() -> None:
    context = DemoMetadataProvider().retrieve("any prompt")

    names = {dataset.name for dataset in context.datasets}
    assert names == {"customers", "products", "orders", "order_items", "payments"}


def test_foreign_keys_reference_real_datasets_and_columns() -> None:
    context = DemoMetadataProvider().retrieve("any prompt")

    for dataset in context.datasets:
        for fk in dataset.foreign_keys:
            local_columns = {column.name for column in dataset.columns}
            assert fk.column in local_columns
            referenced = context.dataset(fk.referenced_dataset)
            referenced_columns = {column.name for column in referenced.columns}
            assert fk.referenced_column in referenced_columns


def test_upstream_lineage_matches_foreign_keys() -> None:
    context = DemoMetadataProvider().retrieve("any prompt")

    for dataset in context.datasets:
        expected_upstreams = {fk.referenced_dataset for fk in dataset.foreign_keys}
        actual_upstreams = set(context.upstream_lineage.get(dataset.name, []))
        assert actual_upstreams == expected_upstreams


def test_demo_context_builds_stub_database(tmp_path: Path) -> None:
    context = DemoMetadataProvider().retrieve("any prompt")

    StubDatabaseBuilder().build(context, tmp_path / "demo.duckdb")
