from flask import Flask, render_template, request, redirect, send_from_directory
import os
import pdfplumber
import docx
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import sqlite3
from datetime import datetime

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
EXTRACTED_FOLDER = 'extracted_text'
DB_FILE = 'database.db'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXTRACTED_FOLDER, exist_ok=True)

# ---------- Jinja Filter ----------
@app.template_filter('datetimeformat')
def format_datetime(value):
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
        return dt.strftime("%d/%b/%Y")
    except:
        return value

# ---------- DB Setup ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            category TEXT,
            company_name TEXT,
            issued_date TEXT,
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()

# ---------- OCR/Text Extraction ----------
def extract_text_from_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    text = ""

    if ext == '.pdf':
        try:
            with pdfplumber.open(filepath) as pdf:
                if pdf.pages:
                    first_page_text = pdf.pages[0].extract_text()
                    if first_page_text and first_page_text.strip():
                        return first_page_text.strip()
        except Exception:
            pass
        try:
            images = convert_from_path(filepath, dpi=300, first_page=1, last_page=1)
            if images:
                text = pytesseract.image_to_string(images[0])
        except Exception as e:
            text = f"[OCR fallback failed: {e}]"

    elif ext == '.docx':
        try:
            doc = docx.Document(filepath)
            text = "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            text = f"[DOCX extraction error: {e}]"

    elif ext in ['.jpg', '.jpeg', '.png']:
        try:
            image = Image.open(filepath)
            text = pytesseract.image_to_string(image)
        except Exception as e:
            text = f"[OCR error: {e}]"

    else:
        text = "[Unsupported file type]"

    return text.strip()

# ---------- Routes ----------
@app.route('/')
def index():
    return redirect('/documents')

@app.route('/upload-form')
def upload_form():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    if file:
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(save_path)

        extracted_text = extract_text_from_file(save_path)

        with open(os.path.join(EXTRACTED_FOLDER, file.filename + ".txt"), "w", encoding="utf-8") as f:
            f.write(extracted_text)

        return render_template('confirm.html',
                               filename=file.filename,
                               extracted_text=extracted_text)
    return "No file uploaded"

@app.route('/save', methods=['POST'])
def save_metadata():
    filename = request.form['filename']
    category = request.form.get('custom_category') or request.form.get('category') or 'Uncategorized'
    company_name = request.form['company_name']
    issued_date = request.form['issued_date']
    notes = request.form['notes']

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO documents (filename, category, company_name, issued_date, notes)
        VALUES (?, ?, ?, ?, ?)
    ''', (filename, category, company_name, issued_date, notes))
    conn.commit()
    conn.close()

    return render_template('saved.html', filename=filename)

@app.route('/documents')
def list_documents():
    selected_category = request.args.get('category')

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT DISTINCT category FROM documents WHERE category IS NOT NULL AND TRIM(category) != ''")
    categories = [row[0] for row in c.fetchall()]

    if selected_category:
        c.execute("SELECT * FROM documents WHERE category=? ORDER BY id", (selected_category,))
    else:
        c.execute("SELECT * FROM documents ORDER BY id")

    documents = c.fetchall()
    conn.close()

    return render_template('list_documents.html',
                           documents=documents,
                           categories=categories,
                           selected_category=selected_category)

@app.route('/view/<filename>')
def view_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/edit/<int:doc_id>', methods=['GET', 'POST'])
def edit_document(doc_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if request.method == 'POST':
        category = request.form.get('custom_category') or request.form.get('category') or 'Uncategorized'
        company_name = request.form['company_name']
        issued_date = request.form['issued_date']
        notes = request.form['notes']

        c.execute('''
            UPDATE documents
            SET category=?, company_name=?, issued_date=?, notes=?
            WHERE id=?
        ''', (category, company_name, issued_date, notes, doc_id))
        conn.commit()
        conn.close()
        return redirect('/documents')

    c.execute('SELECT * FROM documents WHERE id=?', (doc_id,))
    doc = c.fetchone()
    conn.close()

    extracted_text = "[No extracted content found]"
    extracted_path = os.path.join(EXTRACTED_FOLDER, doc[1] + ".txt")
    if os.path.exists(extracted_path):
        with open(extracted_path, "r", encoding="utf-8") as f:
            extracted_text = f.read()

    return render_template('edit.html', doc=doc, extracted_text=extracted_text)

@app.route('/delete/<int:doc_id>')
def delete_document(doc_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT filename FROM documents WHERE id=?', (doc_id,))
    row = c.fetchone()

    if row:
        filename = row[0]
        c.execute('SELECT COUNT(*) FROM documents WHERE filename=?', (filename,))
        count = c.fetchone()[0]

        if count == 1:
            try:
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                extracted_path = os.path.join(EXTRACTED_FOLDER, filename + ".txt")
                if os.path.exists(extracted_path):
                    os.remove(extracted_path)
            except PermissionError:
                conn.close()
                return f"<h3>❌ File '{filename}' is open elsewhere. Close and retry.</h3><a href='/documents'>← Back</a>"

        c.execute('DELETE FROM documents WHERE id=?', (doc_id,))
        conn.commit()

    conn.close()
    return redirect('/documents')

# ---------- Launch ----------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
