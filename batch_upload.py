from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, current_app
)
from werkzeug.utils import secure_filename
from pathlib import Path
from pdf2image import convert_from_path
import pytesseract
import sqlite3, os

# ───────────────────────── CONSTANTS ─────────────────────────
DB_FILE      = "database.db"
ALLOWED_EXT  = {".pdf"}

# ──────────────────────── BLUEPRINT SETUP ─────────────────────
batch_upload_bp = Blueprint(
    "batch_upload_bp", __name__, template_folder="templates"
)

# ────────────────────────── HELPERS ──────────────────────────
def allowed_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXT

def extract_text_from_pdf(path: Path) -> str:
    """
    Returns OCR text from the first page of a PDF.
    Falls back to an error string if something goes wrong.
    """
    try:
        img = convert_from_path(path, first_page=1, last_page=1)[0]
        return pytesseract.image_to_string(img)
    except Exception as e:
        return f"[Gagal ekstraksi: {e}]"

def insert_document(filename: str, notes: str) -> None:
    """
    Inserts a *minimal* record into the 'documents' table.
    Blank strings are stored for category, company, etc.
    """
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            INSERT INTO documents
            (filename, category, doc_type, company_type,
             company_name, issued_date, notes)
            VALUES (?, '', '', '', '', '', ?)
            """,
            (filename, notes)
        )

# ─────────────────────────── ROUTES ──────────────────────────
@batch_upload_bp.route("/batch-upload", methods=["GET"])
def show():
    """Render the batch‑upload form."""
    return render_template("batch_upload.html")

@batch_upload_bp.route("/batch-upload", methods=["POST"])
def upload():
    """Handle multi‑file or folder upload of PDFs."""
    files = request.files.getlist("documents")
    if not files:
        flash("⚠️ Tidak ada file yang dipilih.", "warning")
        return redirect(url_for("batch_upload_bp.show"))

    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    success, failed = 0, 0

    for file in files:
        if not file or file.filename == "":
            continue
        if not allowed_file(file.filename):
            failed += 1
            continue

        filename  = secure_filename(file.filename)
        save_path = upload_dir / filename
        file.save(save_path)

        try:
            notes = extract_text_from_pdf(save_path).strip()
            insert_document(filename, notes)
            success += 1
        except Exception as e:
            print("❌ Batch error:", filename, "→", e)
            failed += 1

    flash(f"✅ {success} dokumen berhasil diunggah. ❌ {failed} gagal.", "info")
    return redirect(url_for("list_documents"))
