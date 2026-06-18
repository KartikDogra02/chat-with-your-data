from dataclasses import dataclass, field

from backend.db import get_connection


@dataclass
class ForeignKey:
    column: str
    references_table: str
    references_column: str


@dataclass
class Column:
    name: str
    data_type: str
    nullable: bool


@dataclass
class Table:
    name: str
    columns: list[Column] = field(default_factory=list)
    primary_keys: list[str] = field(default_factory=list)
    foreign_keys: list[ForeignKey] = field(default_factory=list)


def get_schema(schema_name: str = "public") -> list[Table]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = %s
                ORDER BY table_name, ordinal_position;
                """,
                (schema_name,),
            )
            column_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT tc.table_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
                    AND tc.table_schema = %s
                ORDER BY tc.table_name, kcu.ordinal_position;
                """,
                (schema_name,),
            )
            primary_key_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS references_table,
                    ccu.column_name AS references_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                    AND tc.table_schema = ccu.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = %s
                ORDER BY tc.table_name, kcu.ordinal_position;
                """,
                (schema_name,),
            )
            foreign_key_rows = cursor.fetchall()

    tables: dict[str, Table] = {}

    def get_table(table_name: str) -> Table:
        if table_name not in tables:
            tables[table_name] = Table(name=table_name)
        return tables[table_name]

    for table_name, column_name, data_type, is_nullable in column_rows:
        get_table(table_name).columns.append(
            Column(name=column_name, data_type=data_type, nullable=is_nullable == "YES")
        )

    for table_name, column_name in primary_key_rows:
        get_table(table_name).primary_keys.append(column_name)

    for table_name, column_name, references_table, references_column in foreign_key_rows:
        get_table(table_name).foreign_keys.append(
            ForeignKey(
                column=column_name,
                references_table=references_table,
                references_column=references_column,
            )
        )

    return list(tables.values())


def format_schema(tables: list[Table]) -> str:
    lines: list[str] = []
    for table in tables:
        lines.append(f"{table.name}")
        for column in table.columns:
            nullable = "NULL" if column.nullable else "NOT NULL"
            lines.append(f"  {column.name}: {column.data_type} {nullable}")
        if table.primary_keys:
            lines.append(f"  primary key: {', '.join(table.primary_keys)}")
        for foreign_key in table.foreign_keys:
            lines.append(
                f"  foreign key: {foreign_key.column} -> "
                f"{foreign_key.references_table}.{foreign_key.references_column}"
            )
    return "\n".join(lines)


def main() -> None:
    print(format_schema(get_schema()))


if __name__ == "__main__":
    main()
