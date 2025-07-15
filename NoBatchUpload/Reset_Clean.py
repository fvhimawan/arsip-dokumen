import os
import sqlite3

DB_PATH = "archive.db"

# Delete the existing database
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

# Recreate the database with new structure
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute('''
    CREATE TABLE documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        category TEXT,
        doc_type TEXT,
        company_type TEXT,
        company_name TEXT,
        issued_date TEXT,
        notes TEXT,
        extracted_text TEXT
    )
''')
conn.commit()
conn.close()
print("✅ Database has been reset with new structure.")
