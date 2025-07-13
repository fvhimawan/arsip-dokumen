import os
import shutil
import sqlite3

def safe_delete_folder(folder):
    if os.path.exists(folder):
        shutil.rmtree(folder)
        print(f"✅ Deleted folder: {folder}")
    else:
        print(f"⚠️ Folder not found: {folder}")

def reset_database(db_file):
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"✅ Deleted database: {db_file}")
    else:
        print(f"⚠️ Database not found: {db_file}")

safe_delete_folder('uploads')
safe_delete_folder('extracted_text')
reset_database('database.db')
