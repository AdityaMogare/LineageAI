import pytest
from lineageai.validation.type_mapping import UnsupportedDataTypeError, to_duckdb_type


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("STRING", "VARCHAR"),
        ("VARCHAR(255)", "VARCHAR(255)"),
        ("NUMBER(10, 2)", "DECIMAL(10,2)"),
        ("TIMESTAMP_NTZ", "TIMESTAMP"),
        ("TIMESTAMP_TZ", "TIMESTAMPTZ"),
        ("FLOAT64", "DOUBLE"),
        ("ARRAY<STRING>", "VARCHAR[]"),
        ("BIGINT[]", "BIGINT[]"),
        ("VARIANT", "JSON"),
        ("STRUCT<id INT>", "JSON"),
    ],
)
def test_maps_warehouse_types(source: str, expected: str) -> None:
    assert to_duckdb_type(source) == expected


def test_unknown_type_has_safe_json_fallback() -> None:
    assert to_duckdb_type("GEOMETRY") == "JSON"


def test_unknown_type_can_fail_strictly() -> None:
    with pytest.raises(UnsupportedDataTypeError):
        to_duckdb_type("GEOMETRY", fallback_to_json=False)
