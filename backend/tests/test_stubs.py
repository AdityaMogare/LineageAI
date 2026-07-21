from pathlib import Path

import duckdb
from lineageai.models import MetadataContext
from lineageai.validation.stubs import StubDatabaseBuilder


def test_builds_seeded_duckdb_tables(commerce_context: MetadataContext, tmp_path: Path) -> None:
    database = tmp_path / "stubs.duckdb"
    StubDatabaseBuilder(row_count=10).build(commerce_context, database)

    with duckdb.connect(str(database)) as connection:
        assert connection.sql("select count(*) from main.orders").fetchone() == (10,)
        assert connection.sql("select count(*) from main.customers").fetchone() == (10,)
        assert connection.sql("select count(distinct id) from main.orders").fetchone() == (10,)
