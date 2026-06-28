from dataclasses import dataclass
from typing import Any

from backend.db import get_connection
from backend.sql_validator import validate_sql


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list[Any]]


def execute_query(sql: str) -> QueryResult:
    validated_sql = validate_sql(sql)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            cursor.execute("SET LOCAL statement_timeout = '5s'")
            cursor.execute(validated_sql)

            columns = [column.name for column in cursor.description]
            rows = [list(row) for row in cursor.fetchall()]

    return QueryResult(columns=columns, rows=rows)