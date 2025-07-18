from flask import (
    Flask, render_template, request, redirect,
    send_from_directory, url_for
)
import os, re, sqlite3
from datetime import datetime
from pdf2image import convert_from_path
import pytesseract

# === INIT ===
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24).hex())

# --- Paths & constants ---
UPLOAD_FOLDER  = 'uploads'
DB_FILE        = 'database.db'
COMPANY_TYPES  = ['PT', 'CV', 'UD', 'Koperasi', 'Yayasan']
ALLOWED_EXT    = {'.pdf'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# === Filters ===
@app.template_filter('datetimeformat')
def datetimeformat(value, fmt='%d/%b/%Y'):
    try:
        return datetime.strptime(value, '%Y-%m-%d').strftime(fmt)
    except Exception:
        return value

# === Helpers ===
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS documents (
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

def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXT

def company_name_valid(name: str) -> bool:
    pattern = r'^(?:' + '|'.join(re.escape(t) + r'\.?' for t in COMPANY_TYPES) + r')\s'
    return not re.match(pattern, name.strip(), re.IGNORECASE)

def extract_text_from_pdf(path):
    try:
        img = convert_from_path(path, first_page=1, last_page=1)[0]
        return pytesseract.image_to_string(img)
    except Exception as e:
        return f"[Gagal ekstraksi: {e}]"

def insert_document_db(meta):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''
            INSERT INTO documents
            (filename, category, doc_type, company_type,
             company_name, issued_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            meta['filename'],
            meta.get('category') or meta.get('custom_category'),
            meta['doc_type'],
            meta['company_type'],
            meta['company_name'],
            meta['issued_date'],
            meta['notes']
        ))

# === Routes ===
@app.route('/')
def home():
    return redirect('/documents')

@app.route('/upload-form')
def upload_form():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    if not file.filename.lower().endswith('.pdf'):
        return "Only PDF files are supported.", 400

    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)

    extracted_text = extract_text_from_pdf(path)

    return render_template(
        'confirm.html',
        filename=file.filename,
        extracted_text=extracted_text,
        company_types=COMPANY_TYPES
    )

@app.route('/save', methods=['POST'])
def save_metadata():
    f = request.form

    if not company_name_valid(f.get('company_name', '')):
        return "Nama perusahaan tidak boleh diawali dengan jenis perusahaan.", 400

    insert_document_db(f)
    return redirect('/documents')

@app.route('/documents')
def list_documents():
    category      = request.args.get('category', '')
    company_type  = request.args.get('company_type', '')
    company_name  = request.args.get('company_name', '')
    date_from     = request.args.get('date_from', '')
    date_to       = request.args.get('date_to', '')
    sort_by       = request.args.get('sort_by', 'id')
    sort_dir      = request.args.get('sort_dir', 'asc').lower()

    valid_sort = {'id','filename','category','company_type','company_name','issued_date'}
    if sort_by not in valid_sort: sort_by = 'id'
    if sort_dir not in {'asc','desc'}: sort_dir = 'asc'

    where, params = [], []
    if category:      where.append("category = ?");      params.append(category)
    if company_type:  where.append("company_type = ?");  params.append(company_type)
    if company_name:  where.append("company_name = ?");  params.append(company_name)
    if date_from:     where.append("issued_date >= ?");  params.append(date_from)
    if date_to:       where.append("issued_date <= ?");  params.append(date_to)

    sql = "SELECT * FROM documents"
    if where: sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY {sort_by} {sort_dir.upper()}"

    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        docs = cur.execute(sql, params).fetchall()
        categories = [r[0] for r in cur.execute("SELECT DISTINCT category FROM documents WHERE category IS NOT NULL AND category != ''")]
        company_types = [r[0] for r in cur.execute("SELECT DISTINCT company_type FROM documents WHERE company_type IS NOT NULL AND company_type != ''")]
        companies = [r[0] for r in cur.execute("SELECT DISTINCT company_name FROM documents WHERE company_name IS NOT NULL AND company_name != ''")]

    return render_template(
        'list_documents.html',
        documents=docs,
        categories=categories,
        company_types=company_types,
        companies=companies,
        selected_category=category,
        selected_company_type=company_type,
        selected_company=company_name,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_dir=sort_dir
    )

@app.route('/edit/<int:doc_id>', methods=['GET', 'POST'])
def edit_metadata(doc_id):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()

        if request.method == 'POST':
            f = request.form
            if not company_name_valid(f.get('company_name','')):
                return "Nama perusahaan tidak boleh diawali dengan jenis perusahaan.", 400

            cur.execute('''
                UPDATE documents
                SET category=?, doc_type=?, company_type=?, company_name=?,
                    issued_date=?, notes=?
                WHERE id=?
            ''', (
                f.get('category') or f.get('custom_category'),
                f.get('doc_type'),
                f.get('company_type'),
                f.get('company_name'),
                f.get('issued_date'),
                f.get('notes'),
                doc_id
            ))
            conn.commit()
            return redirect('/documents')

        cur.execute("SELECT * FROM documents WHERE id=?", (doc_id,))
        doc = cur.fetchone()

    pdf_path = os.path.join(UPLOAD_FOLDER, doc[1])
    extracted_text = extract_text_from_pdf(pdf_path)

    return render_template(
        'edit.html',
        doc=doc,
        filename=doc[1],
        extracted_text=extracted_text,
        company_types=COMPANY_TYPES
    )

@app.route('/delete/<int:doc_id>')
def delete_document(doc_id):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT filename FROM documents WHERE id=?", (doc_id,))
        r = cur.fetchone()
        if r:
            file_path = os.path.join(UPLOAD_FOLDER, r[0])
            if os.path.exists(file_path):
                os.remove(file_path)
        cur.execute("DELETE FROM documents WHERE id=?", (doc_id,))
        conn.commit()
    return redirect('/documents')

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/healthz')
def health_check():
    return "OK", 200

# === Register batch upload blueprint ===
from batch_upload import batch_upload_bp
app.register_blueprint(batch_upload_bp)

# === Always initialize DB on app start ===
init_db()

# === Only run Flask dev server in local ===
if __name__ == '__main__':
    app.run(debug=True)


@app.route('/reset_index')
def reset_index_route():
    import sqlite3
    try:
        conn = sqlite3.connect('arsip.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='documents'")
        conn.commit()
        conn.close()
        return '✅ Document index reset successfully.'
    except Exception as e:
        return f'❌ Error: {e}'

@app.route('/reset_index')
def reset_index_route():
    import sqlite3
    try:
        conn = sqlite3.connect('arsip.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='documents'")
        conn.commit()
        conn.close()
        return '✅ Document index reset successfully.'
    except Exception as e:
        return f'❌ Error: {e}'
