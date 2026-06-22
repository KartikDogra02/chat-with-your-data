import pytest
from sqlglot import parse_one

from backend.sql_validator import MAX_ROWS, UnsafeSQLError, validate_sql


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM track;",
        "SELECT genre_id, COUNT(*) FROM track GROUP BY genre_id;",
        "WITH totals AS (SELECT * FROM invoice) SELECT * FROM totals;",
    ],
)
def test_accepts_read_only_select_queries(sql: str) -> None:
    """Ordinary SELECT queries and read-only CTEs should pass validation."""

    validated = validate_sql(sql)

    # Parsing the output confirms that the validator returned valid PostgreSQL
    # rather than relying on formatting-specific string assertions.
    assert parse_one(validated, read="postgres") is not None


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM track;",
        "DROP TABLE track;",
        "SELECT * FROM track; DELETE FROM track;",
        (
            "WITH deleted AS "
            "(DELETE FROM track RETURNING *) "
            "SELECT * FROM deleted;"
        ),
        "SELECT pg_sleep(10);",
        "SELECT * FROM track FOR UPDATE;",
        "SELECT * INTO track_copy FROM track;",
        "This is not SQL.",
        "",
    ],
)
def test_rejects_unsafe_or_invalid_sql(sql: str) -> None:
    """Unsafe, ambiguous, and invalid model output must fail closed."""

    with pytest.raises(UnsafeSQLError):
        validate_sql(sql)


def test_adds_limit_when_query_has_no_limit() -> None:
    validated = validate_sql("SELECT * FROM track;")

    query = parse_one(validated, read="postgres")
    assert query.args["limit"].expression.this == str(MAX_ROWS)


def test_replaces_unbounded_limit_all() -> None:
    # PostgreSQL treats LIMIT ALL as no limit. SQLGlot normalizes it away, so
    # the validator applies the standard maximum just as it does when LIMIT is
    # omitted.
    validated = validate_sql("SELECT * FROM track LIMIT ALL;")

    query = parse_one(validated, read="postgres")
    assert query.args["limit"].expression.this == str(MAX_ROWS)


def test_reduces_limit_above_maximum() -> None:
    validated = validate_sql("SELECT * FROM track LIMIT 500;")

    query = parse_one(validated, read="postgres")
    assert query.args["limit"].expression.this == str(MAX_ROWS)


def test_preserves_limit_below_maximum() -> None:
    validated = validate_sql("SELECT * FROM track LIMIT 20;")

    query = parse_one(validated, read="postgres")
    assert query.args["limit"].expression.this == "20"
