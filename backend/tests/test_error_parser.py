import pytest
from lineageai.models import ValidationErrorKind
from lineageai.validation.error_parser import parse_dbt_errors


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        (
            "Binder Error: Ambiguous reference to column id at line 9",
            ValidationErrorKind.AMBIGUOUS_COLUMN,
        ),
        (
            "Binder Error: Referenced column total not found at line 4",
            ValidationErrorKind.MISSING_COLUMN,
        ),
        ("Table orders does not exist", ValidationErrorKind.MISSING_RELATION),
        ("Catalog Error: Table customers not found", ValidationErrorKind.MISSING_RELATION),
        ("Type mismatch in join predicate", ValidationErrorKind.TYPE),
        ("Conversion Error: could not convert string", ValidationErrorKind.TYPE),
        ("Binder Error: column must appear in GROUP BY", ValidationErrorKind.BINDER),
        ("Parser Error: syntax error at or near FROM", ValidationErrorKind.SYNTAX),
        ("syntax error at line 3", ValidationErrorKind.SYNTAX),
        ("Compilation Error in model revenue", ValidationErrorKind.COMPILATION),
        ("Failure in test unique_revenue_id", ValidationErrorKind.TEST_FAILURE),
        ("IO Error: could not read file", ValidationErrorKind.RUNTIME),
    ],
)
def test_classifies_known_dbt_errors(output: str, expected: ValidationErrorKind) -> None:
    diagnostic = parse_dbt_errors(output)[0]

    assert diagnostic.kind == expected
    assert diagnostic.suggestion


def test_extracts_line_number() -> None:
    diagnostic = parse_dbt_errors("Parser Error at line 17: bad token")[0]

    assert diagnostic.line == 17


def test_empty_output_has_no_diagnostic() -> None:
    assert parse_dbt_errors("") == []
