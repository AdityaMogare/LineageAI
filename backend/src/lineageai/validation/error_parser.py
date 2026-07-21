import re

from lineageai.models import ValidationDiagnostic, ValidationErrorKind

_LINE_PATTERN = re.compile(r"(?:line|at)\s+(\d+)", re.IGNORECASE)

_ERROR_RULES: tuple[tuple[ValidationErrorKind, tuple[str, ...], str], ...] = (
    (
        ValidationErrorKind.AMBIGUOUS_COLUMN,
        ("ambiguous",),
        "Qualify the column with its table alias.",
    ),
    (
        ValidationErrorKind.MISSING_COLUMN,
        ("column", "not found"),
        "Use a column present in the supplied DataHub schema.",
    ),
    (
        ValidationErrorKind.MISSING_COLUMN,
        ("does not have a column",),
        "Use a column present in the supplied DataHub schema.",
    ),
    (
        ValidationErrorKind.MISSING_RELATION,
        ("table", "does not exist"),
        "Use an available source relation and verify its dbt source reference.",
    ),
    (
        ValidationErrorKind.MISSING_RELATION,
        ("catalog error",),
        "Use an available source relation and verify its dbt source reference.",
    ),
    (
        ValidationErrorKind.TYPE,
        ("type mismatch",),
        "Cast operands to compatible types.",
    ),
    (
        ValidationErrorKind.TYPE,
        ("conversion error",),
        "Cast values using the DataHub column types.",
    ),
    (
        ValidationErrorKind.BINDER,
        ("binder error",),
        "Check aliases, grouping, and join expressions.",
    ),
    (
        ValidationErrorKind.SYNTAX,
        ("parser error",),
        "Correct the SQL syntax near the reported line.",
    ),
    (
        ValidationErrorKind.SYNTAX,
        ("syntax error",),
        "Correct the SQL syntax near the reported line.",
    ),
    (
        ValidationErrorKind.COMPILATION,
        ("compilation error",),
        "Correct the dbt/Jinja compilation issue.",
    ),
    (
        ValidationErrorKind.TEST_FAILURE,
        ("failure in test",),
        "Adjust the model or test configuration to satisfy the declared invariant.",
    ),
)


def parse_dbt_errors(output: str) -> list[ValidationDiagnostic]:
    clean = _strip_ansi(output)
    lowered = clean.lower()
    line_match = _LINE_PATTERN.search(clean)
    line = int(line_match.group(1)) if line_match else None

    for kind, markers, suggestion in _ERROR_RULES:
        if all(marker in lowered for marker in markers):
            return [
                ValidationDiagnostic(
                    kind=kind,
                    message=_meaningful_excerpt(clean),
                    line=line,
                    suggestion=suggestion,
                )
            ]

    if clean.strip():
        return [
            ValidationDiagnostic(
                kind=ValidationErrorKind.RUNTIME,
                message=_meaningful_excerpt(clean),
                line=line,
                suggestion="Review the dbt output and metadata context before retrying.",
            )
        ]
    return []


def _strip_ansi(value: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", value)


def _meaningful_excerpt(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    error_lines = [
        line for line in lines if any(token in line.lower() for token in ("error", "failure"))
    ]
    selected = error_lines[-1] if error_lines else (lines[-1] if lines else "Unknown dbt error")
    return selected[:1000]
