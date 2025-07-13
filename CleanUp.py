import sqlite3

DB_FILE = 'database.db'

try:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Count how many rows need to be updated
    c.execute("SELECT COUNT(*) FROM documents WHERE category IS NULL OR TRIM(category) = ''")
    count = c.fetchone()[0]

    # Perform the update
    c.execute("UPDATE documents SET category = 'Uncategorized' WHERE category IS NULL OR TRIM(category) = ''")
    conn.commit()
    conn.close()

    print(f"✅ Cleanup completed. {count} record(s) updated to 'Uncategorized'.")
except Exception as e:
    print(f"❌ Error during cleanup: {e}")
