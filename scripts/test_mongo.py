#!/usr/bin/env python3
"""
Smoke test for the local database path used by the app.
This verifies that the Flask app can initialize and use the SQLite fallback
when MongoDB is unavailable.
"""
import logging
import sys

from flask import Flask

from database import get_db, init_db

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = "test-db-key"

with app.app_context():
    try:
        init_db()
        db = get_db()
        db.execute("DELETE FROM users WHERE username = ?", ("db_smoke_test",))
        db.execute(
            "INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)",
            ("db_smoke_test", "db_smoke_test@example.com", "hashed", 0),
        )
        db.commit()
        row = db.execute(
            "SELECT username, email FROM users WHERE username = ?",
            ("db_smoke_test",),
        ).fetchone()

        if row and row["username"] == "db_smoke_test":
            print("✅ Database is working")
            print(f"   user={row['username']} email={row['email']}")
        else:
            print("❌ Database smoke test failed")
            sys.exit(1)
    except Exception as exc:
        print(f"❌ Database smoke test failed: {exc}")
        sys.exit(1)
