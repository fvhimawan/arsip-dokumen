import sqlite3, shutil, os, sys

OLD_DB = 'database.db'
NEW_DB = 'database_new.db'
BACKUP_DB = 'database_backup.db'

def column_exists(conn, table, col):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == col for row in cur.fetchall())

# ---------- 0. Prep ----------
if not os.path.exists(OLD_DB):
    sys.exit(f"❌  {OLD_DB} not found. Abort.")

# remove any old scratch DB from earlier failed runs
if os.path.exists(NEW_DB):
    os.remove(NEW_DB)

# ---------- 1. Backup ----------
shutil.copy(OLD_DB, BACKUP_DB)
print("✅ Backup created as", BACKUP_DB)

# ---------- 2. Open connections ----------
old_conn = sqlite3.connect(OLD_DB)
new_conn = sqlite3.connect(NEW_DB)

# ---------- 3. Create new table with correct column order ----------
with new_conn:
    new_conn.execute('''
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            category TEXT,
            doc_type TEXT,
            company_type TEXT,
            company_name TEXT,
            issued_date TEXT,
            notes TEXT
        )
    ''')
print("✅ New table structure created.")

# ---------- 4. Copy data with proper mapping ----------
has_company_type = column_exists(old_conn, 'documents', 'company_type')

if has_company_type:
    select_stmt = '''
        SELECT
            id, filename, category, doc_type,
            company_type,
            company_name,
            issued_date,
            notes
        FROM documents
    '''
else:
    select_stmt = '''
        SELECT
            id, filename, category, doc_type,
            NULL    AS company_type,
            company_name,
            issued_date,
            notes
        FROM documents
    '''

rows = old_conn.execute(select_stmt).fetchall()
print(f"✅ {len(rows)} rows fetched from old table.")

with new_conn:
    new_conn.executemany('''
        INSERT INTO documents
        (id, filename, category, doc_type,
         company_type, company_name, issued_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', rows)
print("✅ Data inserted into new table.")

old_conn.close()
new_conn.close()

# ---------- 5. Replace old DB ----------
os.remove(OLD_DB)
shutil.move(NEW_DB, OLD_DB)
print("🎉 Migration complete. `database.db` now has the correct column order.")
