# app_batch_upload_11Jul2025.py
from flask import (
    Flask, render_template, request, redirect,
    send_from_directory, url_for, flash
)
import os, re, sqlite3, uuid
from datetime import datetime
from pdf2image import convert_from_path
import pytesseract

app = Flask(__name__)
app.secret_key = "CHANGE‑ME"                # needed for flash() messages

# ── Paths & constants ────────────────────────────────────────────────────
UPLOAD_FOLDER  = 'uploads'
DB_FILE        = 'database.db'
COMPANY_TYPES  = ['PT', 'CV', 'UD', 'Koperasi', 'Yayasan']
ALLOWED_EXT    = {'.pdf'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ── Filters ──────────────────────────────────────────────────────────────
@app.template_filter('datetimeformat')
def datetimeformat(value, fmt='%d/%b/%Y'):
    try:
        return datetime.strptime(value, '%Y-%m-%d').strftime(fmt)
    except Exception:
        return value

# ── DB helper ────────────────────────────────────────────────────────────
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            category TEXT,
            doc_type TEXT,
            company_type TEXT,
            company_name TEXT,
            issued_date TEXT,
            notes TEXT
        )''')

# ── Validation helpers ───────────────────────────────────────────────────
def company_name_valid(name: str) -> bool:
    """
    Returns True when the *name* does **not** start with (PT.|CV.|…) ␣.
    Used to warn the user if they accidentally type “PT. ABC” instead of
    choosing “PT.” in the dropdown.
    """
    pattern = r'^(?:' + '|'.join(re.escape(t)+r'\.?' for t in COMPANY_TYPES) + r')\s'
    return not re.match(pattern, name.strip(), re.IGNORECASE)

def allowed_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXT

# ═════════════════════════ ROUTES ════════════════════════════════════════
@app.route('/')
def home():
    return redirect(url_for('list_documents'))

# ————— Single‑file upload ————————————————————————————————
@app.route('/upload-form')
def upload_form():
    return render_template('upload.html', company_types=COMPANY_TYPES)

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    if not file or not allowed_file(file.filename):
        return "Only PDF files are supported.", 400

    # Ensure unique on disk (keep DB filename exactly as user supplied)
    save_name = file.filename
    save_path = os.path.join(UPLOAD_FOLDER, save_name)
    file.save(save_path)

    try:
        img = convert_from_path(save_path, first_page=1, last_page=1)[0]
        extracted_text = pytesseract.image_to_string(img)
    except Exception as e:
        extracted_text = f"[Gagal ekstraksi: {e}]"

    return render_template(
        'confirm.html',
        filename=save_name,
        extracted_text=extracted_text,
        company_types=COMPANY_TYPES
    )

@app.route('/save', methods=['POST'])
def save_metadata():
    f = request.form
    if not company_name_valid(f.get('company_name', '')):
        return "Nama perusahaan tidak boleh diawali dengan jenis perusahaan.", 400

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''INSERT INTO documents
            (filename, category, doc_type, company_type,
             company_name, issued_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)''', (
                f.get('filename'),
                f.get('category') or f.get('custom_category'),
                f.get('doc_type'),
                f.get('company_type'),
                f.get('company_name'),
                f.get('issued_date'),
                f.get('notes')
        ))
    return redirect(url_for('list_documents'))

# ————— NEW: Batch upload ————————————————————————————————
@app.route('/batch-upload-form')
def batch_upload_form():
    """
    Shows a form that lets the user pick multiple PDFs and optional
    *default* metadata (category, doc_type, company_type) that will be
    applied to every file.  Everything else can be edited later.
    """
    return render_template('batch_upload.html', company_types=COMPANY_TYPES)

@app.route('/batch-upload', methods=['POST'])
def batch_upload():
    """
    Handles the actual multi‑file POST.  For each PDF:
     1. Saves it with its original name (renaming on collision).
     2. Extracts OCR text from page 1 (non‑fatal if failure).
     3. Inserts a DB row with the shared default metadata.
    """
    files = request.files.getlist('files')
    if not files:
        flash("No files were selected.", 'danger')
        return redirect(url_for('batch_upload_form'))

    # pull shared defaults
    f = request.form
    default_category     = f.get('category') or f.get('custom_category') or ''
    default_doc_type     = f.get('doc_type') or ''
    default_company_type = f.get('company_type') or ''
    inserted = []   # keep (filename, doc_id)

    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()

        for file in files:
            if not file or not allowed_file(file.filename):
                continue  # silently skip junk

            original_name = file.filename
            save_name     = original_name
            save_path     = os.path.join(UPLOAD_FOLDER, save_name)

            # avoid overwriting existing file names
            if os.path.exists(save_path):
                stem, ext = os.path.splitext(original_name)
                save_name = f"{stem}_{uuid.uuid4().hex[:8]}{ext}"
                save_path = os.path.join(UPLOAD_FOLDER, save_name)

            file.save(save_path)

            try:
                img = convert_from_path(save_path, first_page=1, last_page=1)[0]
                ocr_text = pytesseract.image_to_string(img)
            except Exception as e:
                ocr_text = f"[OCR gagal: {e}]"

            cur.execute('''INSERT INTO documents
                (filename, category, doc_type, company_type,
                 company_name, issued_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)''', (
                    save_name,
                    default_category,
                    default_doc_type,
                    default_company_type,
                    '',         # company_name left empty
                    '',         # issued_date left empty
                    ocr_text.strip()
            ))
            inserted.append((save_name, cur.lastrowid))

        conn.commit()

    flash(f"{len(inserted)} file(s) uploaded successfully.", "success")
    # Optional: redirect to list filtered by IDs, but simple list is ok
    return redirect(url_for('list_documents'))

# ————— List / edit / delete ——————————————————————————————
@app.route('/documents')
def list_documents():
    # Query params
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

        categories = [r[0] for r in cur.execute(
            "SELECT DISTINCT category FROM documents WHERE category!='' AND category IS NOT NULL")]
        company_types = [r[0] for r in cur.execute(
            "SELECT DISTINCT company_type FROM documents WHERE company_type!='' AND company_type IS NOT NULL")]
        companies = [r[0] for r in cur.execute(
            "SELECT DISTINCT company_name FROM documents WHERE company_name!='' AND company_name IS NOT NULL")]

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

            cur.execute('''UPDATE documents
                SET category=?, doc_type=?, company_type=?, company_name=?,
                    issued_date=?, notes=? WHERE id=?''', (
                        f.get('category') or f.get('custom_category'),
                        f.get('doc_type'),
                        f.get('company_type'),
                        f.get('company_name'),
                        f.get('issued_date'),
                        f.get('notes'),
                        doc_id
            ))
            conn.commit()
            return redirect(url_for('list_documents'))

        cur.execute("SELECT * FROM documents WHERE id=?", (doc_id,))
        doc = cur.fetchone()

    pdf_path = os.path.join(UPLOAD_FOLDER, doc[1])
    try:
        img = convert_from_path(pdf_path, first_page=1, last_page=1)[0]
        extracted_text = pytesseract.image_to_string(img)
    except Exception as e:
        extracted_text = f"[Gagal ekstraksi: {e}]"

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
    return redirect(url_for('list_documents'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ── bootstrap ────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
