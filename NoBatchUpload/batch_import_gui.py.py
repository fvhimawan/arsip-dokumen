import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import subprocess, sys, shutil, sqlite3, os

# ---------- constants ----------
COMPANY_TYPES = ['PT', 'CV', 'UD', 'Koperasi', 'Yayasan']

# ---------- helper: call batch import inline ----------
def run_batch_import(src, uploads, db, ctype, cname):
    uploads = Path(uploads)
    uploads.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.execute('''CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT, category TEXT, doc_type TEXT,
        company_type TEXT, company_name TEXT, issued_date TEXT, notes TEXT
    )''')

    insert = '''INSERT INTO documents
                (filename, category, doc_type, company_type,
                 company_name, issued_date, notes)
                VALUES (?, '', '', ?, ?, '', '')'''

    pdfs = list(Path(src).glob('*.pdf'))
    if not pdfs:
        raise RuntimeError("Tidak ada PDF di folder sumber.")

    for p in pdfs:
        dest = uploads / p.name
        i = 1
        while dest.exists():
            dest = uploads / f"{p.stem}_{i}{p.suffix}"
            i += 1
        shutil.copy2(p, dest)
        conn.execute(insert, (dest.name, ctype, cname))

    conn.commit()
    conn.close()
    return len(pdfs)

# ---------- GUI ----------
root = tk.Tk()
root.title("Batch PDF Importer")

# Input fields
def browse_dir(entry):
    path = filedialog.askdirectory()
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)

tk.Label(root, text="📂 Folder sumber PDF:").grid(row=0, column=0, sticky='w')
src_entry = tk.Entry(root, width=55)
src_entry.grid(row=0, column=1)
tk.Button(root, text="Browse", command=lambda: browse_dir(src_entry)).grid(row=0, column=2)

tk.Label(root, text="📥 uploads/ Flask:").grid(row=1, column=0, sticky='w')
upl_entry = tk.Entry(root, width=55)
upl_entry.insert(0, str(Path('uploads').resolve()))
upl_entry.grid(row=1, column=1)
tk.Button(root, text="Browse", command=lambda: browse_dir(upl_entry)).grid(row=1, column=2)

tk.Label(root, text="📄 database.db:").grid(row=2, column=0, sticky='w')
db_entry = tk.Entry(root, width=55)
db_entry.insert(0, str(Path('database.db').resolve()))
db_entry.grid(row=2, column=1)
tk.Button(root, text="Browse", command=lambda: db_entry.insert(0, filedialog.askopenfilename(defaultextension=".db"))).grid(row=2, column=2)

tk.Label(root, text="Jenis Perusahaan:").grid(row=3, column=0, sticky='w')
ctype_var = tk.StringVar(value=COMPANY_TYPES[0])
tk.OptionMenu(root, ctype_var, *COMPANY_TYPES).grid(row=3, column=1, sticky='w')

tk.Label(root, text="Nama Perusahaan:").grid(row=4, column=0, sticky='w')
cname_entry = tk.Entry(root, width=55)
cname_entry.grid(row=4, column=1)

# Action
def on_import():
    try:
        count = run_batch_import(
            src_entry.get(), upl_entry.get(), db_entry.get(),
            ctype_var.get(), cname_entry.get().strip()
        )
        messagebox.showinfo("Sukses", f"{count} PDF berhasil di‑import.")
    except Exception as e:
        messagebox.showerror("Gagal", str(e))

tk.Button(root, text="🚀 Import sekarang", command=on_import,
          bg="#0d6efd", fg="white").grid(row=5, column=1, pady=10)

root.mainloop()
