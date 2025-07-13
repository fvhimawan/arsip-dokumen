#!/usr/bin/env python3
"""
reset_dev_environment.py
-------------------------------------------------
Utility to wipe and recreate the local development
environment for the Arsip document‑archive project.

• Deletes the existing SQLite database (if any)
• Recreates an empty database with the approved schema
• Removes and recreates all upload/preview folders
  so no leftover files remain from previous sessions

Run: python reset_dev_environment.py
"""

from pathlib import Path
import sqlite3
import shutil
import sys

# ───────────────────────── CONFIGURE HERE ──────────────────────────
# Adjust these paths only if your project uses different names.
PROJECT_ROOT = Path(__file__).resolve().parent          # project root
DB_FILE       = PROJECT_ROOT / "database.db"            # SQLite file
UPLOAD_DIRS   = [
    PROJECT_ROOT / "uploads",                           # raw uploads
    PROJECT_ROOT / "static" / "previews",               # PDF/IMG previews
    PROJECT_ROOT / "static" / "thumbnails",             # tiny thumbs
]
# ───────────────────────────────────────────────────────────────────

def wipe_and_recreate_dirs(dirs):
    """Remove each directory (if exists) and create it empty."""
    for d in dirs:
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
        # keep Git/VCS happy with an empty placeholder file
        (d / ".gitkeep").touch()

def reset_database(db_path):
    """Delete old DB and create a fresh one with the stable schema."""
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE documents (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            filename      TEXT    NOT NULL,
            category      TEXT    NOT NULL,
            doc_type      TEXT    NOT NULL,
            company_type  TEXT    NOT NULL,
            company_name  TEXT    NOT NULL,
            issued_date   TEXT    NOT NULL,
            notes         TEXT
        );
        """
    )
    conn.commit()
    conn.close()

def main() -> None:
    print("⚙️  Resetting development environment…")
    wipe_and_recreate_dirs(UPLOAD_DIRS)
    reset_database(DB_FILE)

    print("✅ Done. Fresh workspace is ready:")
    print(f"   • New empty database  : {DB_FILE}")
    for d in UPLOAD_DIRS:
        print(f"   • Clean directory     : {d}")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("❌ Something went wrong:", exc, file=sys.stderr)
        sys.exit(1)
