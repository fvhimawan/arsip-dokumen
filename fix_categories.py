import sqlite3

DB_FILE = 'database.db'

try:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Count documents to fix
    c.execute("""
        SELECT COUNT(*) FROM documents
        WHERE category IS NULL OR TRIM(category) = '' OR LOWER(category) = 'none'
    """)
    count = c.fetchone()[0]

    # Perform the fix
    c.execute("""
        UPDATE documents
        SET category = 'Uncategorized'
        WHERE category IS NULL OR TRIM(category) = '' OR LOWER(category) = 'none'
    """)
    conn.commit()
    conn.close()

    print(f"✅ Fixed {count} document(s) with empty or invalid category.")
except Exception as e:
    print(f"❌ Error: {e}")
