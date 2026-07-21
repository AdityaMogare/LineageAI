from lineageai.models import GeneratedModel, MetadataContext, ValidationErrorKind
from lineageai.validation import DbtValidator


def test_executes_valid_model_against_duckdb(commerce_context: MetadataContext) -> None:
    model = GeneratedModel(
        name="customer_revenue",
        sql="""
            select
                c.customer_id,
                c.region,
                sum(o.amount) as total_revenue
            from main.customers c
            join main.orders o on c.customer_id = o.customer_id
            group by c.customer_id, c.region
        """,
        schema_yml="""
version: 2
models:
  - name: customer_revenue
    columns:
      - name: customer_id
        data_tests:
          - not_null
""",
        input_datasets=["customers", "orders"],
    )

    result = DbtValidator().validate(model, commerce_context)

    assert result.success, result.stderr or result.stdout
    assert result.command == "dbt build"


def test_returns_structured_error_for_invalid_model(
    commerce_context: MetadataContext,
) -> None:
    model = GeneratedModel(
        name="broken_revenue",
        sql="select missing_amount from main.orders",
        schema_yml="version: 2\nmodels:\n  - name: broken_revenue\n",
        input_datasets=["orders"],
    )

    result = DbtValidator().validate(model, commerce_context)

    assert not result.success
    assert result.diagnostics
    assert result.diagnostics[0].kind in {
        ValidationErrorKind.MISSING_COLUMN,
        ValidationErrorKind.BINDER,
    }
