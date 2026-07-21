import re


class UnsupportedDataTypeError(ValueError):
    pass


_SIMPLE_TYPES = {
    "STRING": "VARCHAR",
    "TEXT": "VARCHAR",
    "VARCHAR": "VARCHAR",
    "CHAR": "VARCHAR",
    "BOOLEAN": "BOOLEAN",
    "BOOL": "BOOLEAN",
    "BYTEINT": "TINYINT",
    "TINYINT": "TINYINT",
    "SMALLINT": "SMALLINT",
    "INTEGER": "INTEGER",
    "INT": "INTEGER",
    "BIGINT": "BIGINT",
    "FLOAT": "DOUBLE",
    "FLOAT64": "DOUBLE",
    "DOUBLE": "DOUBLE",
    "REAL": "REAL",
    "DATE": "DATE",
    "DATETIME": "TIMESTAMP",
    "TIMESTAMP": "TIMESTAMP",
    "TIMESTAMP_NTZ": "TIMESTAMP",
    "TIMESTAMP_LTZ": "TIMESTAMPTZ",
    "TIMESTAMP_TZ": "TIMESTAMPTZ",
    "TIME": "TIME",
    "BINARY": "BLOB",
    "BYTES": "BLOB",
    "JSON": "JSON",
    "VARIANT": "JSON",
    "OBJECT": "JSON",
    "RECORD": "JSON",
    "STRUCT": "JSON",
    "GEOGRAPHY": "VARCHAR",
}

_PARAMETERIZED = re.compile(
    r"^(?P<base>VARCHAR|CHAR|CHARACTER VARYING|NUMBER|NUMERIC|DECIMAL)"
    r"\s*\((?P<args>\d+(?:\s*,\s*\d+)?)\)$"
)
_ARRAY = re.compile(r"^(?:ARRAY<(?P<angle>.+)>|(?P<suffix>.+)\[\])$")


def to_duckdb_type(native_type: str, *, fallback_to_json: bool = True) -> str:
    normalized = " ".join(native_type.strip().upper().split())
    if normalized in _SIMPLE_TYPES:
        return _SIMPLE_TYPES[normalized]

    parameterized = _PARAMETERIZED.match(normalized)
    if parameterized:
        base = parameterized.group("base")
        args = parameterized.group("args").replace(" ", "")
        if base in {"VARCHAR", "CHAR", "CHARACTER VARYING"}:
            return f"VARCHAR({args})"
        return f"DECIMAL({args})"

    array = _ARRAY.match(normalized)
    if array:
        item_type = array.group("angle") or array.group("suffix")
        return f"{to_duckdb_type(item_type, fallback_to_json=fallback_to_json)}[]"

    if normalized.startswith(("MAP", "STRUCT", "ROW")):
        return "JSON"
    if fallback_to_json:
        return "JSON"
    raise UnsupportedDataTypeError(f"Unsupported DataHub type: {native_type}")
