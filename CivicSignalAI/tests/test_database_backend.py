import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import database
from app.migrate_sqlite_to_postgres import migrate_sqlite_to_postgres


class FakePostgresConnection:
    def __init__(self):
        self.executed = []

    def execute(self, query, parameters=()):
        self.executed.append((query, parameters))
        return None

    def executemany(self, query, parameters):
        self.executed.append((query, parameters))
        return None

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class DatabaseBackendTests(unittest.TestCase):
    def test_postgres_adapter_translates_placeholders_and_write_transactions(self):
        raw_connection = FakePostgresConnection()
        connection = database.PostgresConnection(raw_connection)

        connection.execute("SELECT id FROM reports WHERE id = ?", ("report-1",))
        connection.execute("BEGIN IMMEDIATE")
        connection.executemany("INSERT INTO reports (id) VALUES (?)", [("report-1",)])

        self.assertEqual(raw_connection.executed, [
            ("SELECT id FROM reports WHERE id = %s", ("report-1",)),
            ("BEGIN", ()),
            ("INSERT INTO reports (id) VALUES (%s)", [("report-1",)]),
        ])

    def test_database_url_selects_postgres_with_tls(self):
        raw_connection = FakePostgresConnection()
        with (
            patch.dict(os.environ, {"DATABASE_URL": "postgresql://db.example/app"}),
            patch.object(database.psycopg, "connect", return_value=raw_connection) as connect,
        ):
            connection = database.connect_database()

        self.assertIsInstance(connection, database.PostgresConnection)
        self.assertEqual(connect.call_args.args, ("postgresql://db.example/app",))
        self.assertEqual(connect.call_args.kwargs["sslmode"], "require")
        self.assertEqual(connect.call_args.kwargs["connect_timeout"], 10)
        connection.close()

    def test_vercel_requires_postgres_instead_of_ephemeral_sqlite(self):
        with patch.dict(os.environ, {"VERCEL": "1", "DATABASE_URL": ""}):
            with self.assertRaisesRegex(RuntimeError, "DATABASE_URL must be configured"):
                database.connect_database()

    def test_explicit_sqlite_path_overrides_database_url_for_isolated_tests(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "test.db"
            with patch.dict(os.environ, {"DATABASE_URL": "postgresql://unused"}):
                connection = database.connect_database(path)
            try:
                self.assertEqual(connection.execute("SELECT 1").fetchone()[0], 1)
            finally:
                connection.close()

    def test_migration_requires_a_destination_without_modifying_source(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.db"
            connection = sqlite3.connect(source)
            try:
                connection.execute("CREATE TABLE preserved_data (value TEXT)")
                connection.execute("INSERT INTO preserved_data VALUES ('preserve me')")
                connection.commit()
            finally:
                connection.close()
            before = source.read_bytes()

            with patch.dict(os.environ, {"DATABASE_URL": ""}):
                with self.assertRaisesRegex(RuntimeError, "Set DATABASE_URL"):
                    migrate_sqlite_to_postgres(source)

            self.assertEqual(source.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
