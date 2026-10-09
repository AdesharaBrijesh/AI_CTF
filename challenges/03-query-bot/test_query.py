"""Basic tests for query-bot (no Ollama needed).

    python -m unittest test_query
"""
import os
import tempfile
import unittest

import config

# Use a throwaway DB so tests never touch the real seed file.
config.DB_PATH = os.path.join(tempfile.mkdtemp(), "test_directory.db")

import app  # noqa: E402  (imported after DB_PATH override)
import db   # noqa: E402


class SelectGuard(unittest.TestCase):
    def test_allows_plain_select(self):
        self.assertTrue(db.is_select_only("SELECT name FROM employees"))
        self.assertTrue(db.is_select_only("select secret from employees where name='David Okafor'"))

    def test_rejects_writes_and_stacking(self):
        for bad in [
            "DELETE FROM employees",
            "DROP TABLE employees",
            "SELECT 1; DELETE FROM employees",
            "UPDATE employees SET secret='x'",
            "PRAGMA table_info(employees)",
            "",
        ]:
            self.assertFalse(db.is_select_only(bad), bad)


class Extraction(unittest.TestCase):
    def test_strips_fences_and_prose(self):
        raw = "Here you go:\n```sql\nSELECT name FROM employees;\n```"
        self.assertEqual(app.extract_sql(raw), "SELECT name FROM employees")


class SeedAndLeak(unittest.TestCase):
    def test_seed_and_readonly_leak(self):
        db.init_db()
        cols, rows = db.run_select("SELECT name, secret FROM employees WHERE department='Finance'")
        self.assertIn("secret", cols)
        flat = [str(c) for r in rows for c in r]
        self.assertIn(config.FLAG, flat)  # David's secret is the flag

    def test_readonly_blocks_writes_at_db_layer(self):
        db.init_db()
        with self.assertRaises(Exception):
            db.run_select("DELETE FROM employees")  # read-only connection refuses


if __name__ == "__main__":
    unittest.main()
