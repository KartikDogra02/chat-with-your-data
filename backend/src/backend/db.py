import psycopg
from psycopg import Connection

from backend.config import get_settings


def get_connection() -> Connection:
    settings = get_settings()
    return psycopg.connect(settings.database_url)


def get_track_count() -> int:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM track;")
            result = cursor.fetchone()

    if result is None:
        raise RuntimeError("The track count query returned no result.")

    return result[0]


def main() -> None:
    print(f"Track count: {get_track_count()}")


if __name__ == "__main__":
    main()
