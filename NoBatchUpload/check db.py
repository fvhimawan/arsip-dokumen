import os

if os.access('database.db', os.W_OK):
    print("✅ database.db is writable.")
else:
    print("❌ database.db is not writable.")
