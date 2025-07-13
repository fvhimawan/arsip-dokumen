from flask import Flask, render_template, request, redirect
import os
import pdfplumber
import docx
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import sqlite3

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
EXTRACTED_FOLDER = 'extracted_text'
DB_FILE = 'database.db'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXTRACTED_FOLDER, exist_ok=True)

# ----------- DB Setup -----------

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            doc_type TEXT,
            company_name TEXT,
            issued_date TEXT,
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()

# ----------- Text Extraction -----------

def extract_text_from_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    text = ""

    if ext == '.pdf':
        # Try extracting text with pdfplumber
        try:
            with pdfplumber.open(filepath) as pdf:
                if pdf.pages:
                    first_page_text = pdf.pages[0].extract_text()
                    if first_page_text and first_page_text.strip():
                        return first_page_text.strip()
        except Exception as e:
            print(f"Error using pdfplumber: {e}")

        # If no text found, fallback to OCR
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

# ----------- Routes -----------

@app.route('/')
def index():
    return list_documents()

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
    doc_type = request.form['doc_type']
    company_name = request.form['company_name']
    issued_date = request.form['issued_date']
    notes = request.form['notes']

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO documents (filename, doc_type, company_name, issued_date, notes)
        VALUES (?, ?, ?, ?, ?)
    ''', (filename, doc_type, company_name, issued_date, notes))
    conn.commit()
    conn.close()

    return render_template('saved.html', filename=filename)

@app.route('/documents')
def list_documents():
    search = request.args.get('search', '')

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if search:
        c.execute('''
            SELECT * FROM documents
            WHERE company_name LIKE ? OR doc_type LIKE ? OR filename LIKE ?
        ''', (f'%{search}%', f'%{search}%', f'%{search}%'))
    else:
        c.execute('SELECT * FROM documents')
    rows = c.fetchall()
    conn.close()

    filtered_rows = [row for row in rows if os.path.exists(os.path.join(UPLOAD_FOLDER, row[1]))]

    return render_template('list_documents.html', documents=filtered_rows, search=search)

@app.route('/edit/<int:doc_id>')
def edit_document(doc_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT * FROM documents WHERE id=?', (doc_id,))
    row = c.fetchone()
    conn.close()

    if row:
        return render_template('edit.html', doc=row)
    else:
        return f"<h3>Document with ID {doc_id} not found.</h3><a href='/documents'>← Back</a>"

@app.route('/update/<int:doc_id>', methods=['POST'])
def update_document(doc_id):
    filename = request.form['filename']
    doc_type = request.form['doc_type']
    company_name = request.form['company_name']
    issued_date = request.form['issued_date']
    notes = request.form['notes']

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        UPDATE documents
        SET filename=?, doc_type=?, company_name=?, issued_date=?, notes=?
        WHERE id=?
    ''', (filename, doc_type, company_name, issued_date, notes, doc_id))
    conn.commit()
    conn.close()

    return f"<h3>✅ Document Updated</h3><a href='/documents'>← Back to Archive</a>"

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
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            extracted_path = os.path.join(EXTRACTED_FOLDER, filename + ".txt")
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                if os.path.exists(extracted_path):
                    os.remove(extracted_path)
            except PermissionError:
                conn.close()
                return f"<h3>❌ Cannot delete '{filename}' — it is currently open in another application. Please close it and try again.</h3><a href='/documents'>← Back</a>"

        c.execute('DELETE FROM documents WHERE id=?', (doc_id,))
        conn.commit()

    conn.close()
    return redirect('/documents')

# ----------- Launch App -----------

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
