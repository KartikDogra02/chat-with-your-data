from dataclasses import dataclass
from typing import Any, cast

import psycopg

from backend.db import get_connection
from backend.sql_validator import validate_sql


class QueryExecutionError(RuntimeError):
    """Raised when validated SQL fails to execute against the database."""

    def __init__(self, sql: str, original_error: Exception) -> None:
        self.sql = sql
        self.original_error = original_error
        super().__init__(str(original_error))


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list[Any]]


def execute_query(sql: str) -> QueryResult:
    # Validation errors are not execution errors: unsafe SQL should fail
    # immediately rather than be treated as something to retry.
    validated_sql = validate_sql(sql)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            cursor.execute("SET LOCAL statement_timeout = '5s'")

            try:
                cursor.execute(cast(Any, validated_sql))
            except psycopg.Error as error:
                raise QueryExecutionError(validated_sql, error) from error

            if cursor.description is None:
                raise QueryExecutionError(
                    validated_sql,
                    RuntimeError("The query did not return a result set."),
                )

            columns = [column.name for column in cursor.description]
            rows = [list(row) for row in cursor.fetchall()]

    return QueryResult(columns=columns, rows=rows)
