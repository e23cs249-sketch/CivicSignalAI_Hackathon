from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from app import database
from app.config import PROJECT_ROOT, get_database_url

TABLES = (
    "citizen_users",
    "reports",
    "report_events",
    "report_media",
    "citizen_sessions",
)


def migrate_sqlite_to_postgres(source_path: str | Path) -> dict[str, tuple[int, int]]:
    source_file = Path(source_path).expanduser().resolve()
    if not source_file.is_file():
        raise FileNotFoundError(f"SQLite source database does not exist: {source_file}")
    if not get_database_url():
        raise RuntimeError("Set DATABASE_URL to the PostgreSQL destination before migrating.")

    database.initialize_database()
    source = sqlite3.connect(source_file)
    source.row_factory = sqlite3.Row
    source.execute("PRAGMA query_only = ON")
    target = None
    results: dict[str, tuple[int, int]] = {}

    try:
        target = database.connect_database()
        source_tables = {
            row["name"]
            for row in source.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        target.execute("BEGIN")

        for table in TABLES:
            if table not in source_tables:
                continue

            source_info = source.execute(f'PRAGMA table_info("{table}")').fetchall()
            source_columns = [row["name"] for row in source_info]
            primary_key = [
                row["name"]
                for row in sorted(source_info, key=lambda item: item["pk"])
                if row["pk"]
            ]
            if not primary_key:
                raise RuntimeError(f"Cannot safely migrate table without a primary key: {table}")

            destination_columns = {
                row["column_name"]
                for row in target.execute(
                    """SELECT column_name FROM information_schema.columns
                       WHERE table_schema = current_schema() AND table_name = ?""",
                    (table,),
                ).fetchall()
            }
            unknown_columns = set(source_columns) - destination_columns
            if unknown_columns:
                raise RuntimeError(
                    f"Destination schema is missing columns for table {table}; migration stopped."
                )

            quoted_columns = ", ".join(f'"{column}"' for column in source_columns)
            placeholders = ", ".join("?" for _ in source_columns)
            insert_sql = (
                f'INSERT INTO "{table}" ({quoted_columns}) VALUES ({placeholders}) '
                "ON CONFLICT DO NOTHING RETURNING 1"
            )
            primary_key_filter = " AND ".join(f'"{column}" = ?' for column in primary_key)
            select_sql = f'SELECT * FROM "{table}" WHERE {primary_key_filter}'
            inserted = 0
            unchanged = 0
            source_order = " ORDER BY rowid" if table == "report_events" else ""

            for source_row in source.execute(f'SELECT * FROM "{table}"{source_order}'):
                values = tuple(source_row[column] for column in source_columns)
                result = target.execute(insert_sql, values).fetchone()
                if result is not None:
                    inserted += 1
                    continue

                key_values = tuple(source_row[column] for column in primary_key)
                existing = target.execute(select_sql, key_values).fetchone()
                if existing is None or any(
                    existing[column] != source_row[column] for column in source_columns
                ):
                    raise RuntimeError(
                        f"Conflicting destination data found in table {table}; "
                        "the transaction was rolled back."
                    )
                unchanged += 1

            results[table] = (inserted, unchanged)

        target.commit()
        return results
    except Exception:
        if target is not None:
            target.rollback()
        raise
    finally:
        source.close()
        if target is not None:
            target.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy SQLite app data into the PostgreSQL database in DATABASE_URL."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=PROJECT_ROOT / "data" / "civicsignal.db",
        help="SQLite source file (default: data/civicsignal.db)",
    )
    arguments = parser.parse_args()
    for table, (inserted, unchanged) in migrate_sqlite_to_postgres(arguments.source).items():
        print(f"{table}: copied {inserted}; already present unchanged {unchanged}")


if __name__ == "__main__":
    main()
