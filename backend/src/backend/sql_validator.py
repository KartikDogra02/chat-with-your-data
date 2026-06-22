"""Validation for SQL produced by the language model.

The model's output is untrusted input. Prompting it to write read-only SQL is
useful, but this module enforces that rule in deterministic application code.
Database permissions will provide a second layer of protection later.
"""

from sqlglot import Expr, exp, parse
from sqlglot.errors import ParseError

MAX_ROWS = 100

# These expression types can change database state when they appear at the
# statement root or inside a writable common table expression (CTE).
WRITE_EXPRESSIONS = (
    exp.Alter,
    exp.Command,
    exp.Create,
    exp.Delete,
    exp.Drop,
    exp.Insert,
    exp.Merge,
    exp.TruncateTable,
    exp.Update,
)

# Some PostgreSQL functions are callable from SELECT but still have side
# effects, expose server files, or can intentionally consume resources.
BLOCKED_FUNCTIONS = {
    "dblink_connect",
    "lo_export",
    "lo_import",
    "pg_advisory_lock",
    "pg_advisory_xact_lock",
    "pg_read_binary_file",
    "pg_read_file",
    "pg_sleep",
    "pg_terminate_backend",
}


class UnsafeSQLError(ValueError):
    """Raised when SQL is invalid or violates the read-only policy."""


def _parse_one_statement(sql: str) -> Expr:
    """Parse PostgreSQL SQL and require exactly one non-empty statement."""

    if not sql.strip():
        raise UnsafeSQLError("SQL cannot be empty.")

    try:
        statements = parse(sql, read="postgres")
    except ParseError as error:
        raise UnsafeSQLError("SQL is not valid PostgreSQL.") from error

    if len(statements) != 1:
        raise UnsafeSQLError("Exactly one SQL statement is allowed.")

    statement = statements[0]
    if statement is None:
        raise UnsafeSQLError("SQL cannot be empty.")

    return statement


def _validate_read_only(query: Expr) -> None:
    """Reject syntax that can mutate data or acquire database locks."""

    # A SELECT containing a WITH clause still has Select as its root. Requiring
    # that root prevents commands such as INSERT, DELETE, COPY, and SET.
    if not isinstance(query, exp.Select):
        raise UnsafeSQLError("Only SELECT queries are allowed.")

    # Checking the complete syntax tree catches writes hidden inside a CTE,
    # such as: WITH deleted AS (DELETE ... RETURNING *) SELECT * FROM deleted.
    for expression_type in WRITE_EXPRESSIONS:
        if query.find(expression_type) is not None:
            raise UnsafeSQLError("SQL must be read-only.")

    # SELECT ... INTO creates a table even though the statement starts with
    # SELECT, so it needs an explicit check.
    if query.args.get("into") is not None:
        raise UnsafeSQLError("SELECT INTO is not allowed.")

    # Row-locking clauses can block other transactions and are unnecessary for
    # analytics queries.
    if query.find(exp.Lock) is not None:
        raise UnsafeSQLError("Row-locking clauses are not allowed.")

    for function in query.find_all(exp.Anonymous):
        if function.name.lower() in BLOCKED_FUNCTIONS:
            raise UnsafeSQLError(
                f"Function {function.name} is not allowed in generated SQL."
            )


def _apply_row_limit(query: exp.Select) -> None:
    """Ensure the outer query cannot request more than MAX_ROWS rows."""

    limit = query.args.get("limit")
    if limit is None:
        query.limit(MAX_ROWS, copy=False)
        return

    limit_expression = limit.expression
    if not isinstance(limit_expression, exp.Literal) or not limit_expression.is_int:
        raise UnsafeSQLError("LIMIT must be a fixed integer.")

    if int(limit_expression.this) > MAX_ROWS:
        query.limit(MAX_ROWS, copy=False)


def validate_sql(sql: str) -> str:
    """Return normalized, row-limited SQL or raise UnsafeSQLError.

    SQLGlot serializes the validated syntax tree back into PostgreSQL SQL. This
    avoids executing the model's original text after validation.
    """

    query = _parse_one_statement(sql)
    _validate_read_only(query)

    # _validate_read_only established this type, but the assertion also helps
    # static type checkers understand that _apply_row_limit expects a Select.
    assert isinstance(query, exp.Select)
    _apply_row_limit(query)

    return query.sql(dialect="postgres")
