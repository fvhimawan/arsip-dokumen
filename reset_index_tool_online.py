from flask import Flask
import sqlite3
import os

app = Flask(__name__)

DATABASE = 'database.db'  # Adjust if stored in a subfolder

def get_db_connection():
    if not os.path.exists(DATABASE):
        raise FileNotFoundError("❌ 'database.db' not found.")
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/reset_index', methods=['GET'])
def reset_index():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
        if not cursor.fetchone():
            return '❌ Table "documents" does not exist.', 404

        # Check if table is empty
        cursor.execute("SELECT COUNT(*) FROM documents")
        count = cursor.fetchone()[0]

        if count > 0:
            conn.close()
            return f'❌ Cannot reset: {count} documents still exist.', 400

        # Reset the auto-increment counter
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='documents'")
        conn.commit()
        conn.close()
        return '✅ Success: Document ID has been reset to 1.', 200

    except Exception as e:
        return f'⚠️ Error: {str(e)}', 500

if __name__ == '__main__':
    app.run(debug=True)
