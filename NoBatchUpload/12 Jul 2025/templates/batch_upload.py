<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <title>Batch Upload PDFs</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body class="container mt-4">

  <h2>📦 Batch Upload PDFs</h2>

  <p>
    Anda bisa unggah:
    <ul>
      <li>✅ Beberapa file PDF (tahan <strong>Ctrl</strong> untuk memilih lebih dari satu)</li>
      <li>✅ Seluruh isi sebuah folder (browser Chrome/Edge)</li>
      <li>✅ Kombinasi keduanya</li>
    </ul>
  </p>

  <form action="{{ url_for('batch_upload_bp.upload') }}"
        method="post"
        enctype="multipart/form-data"
        class="border rounded p-4 bg-light">

    <!-- Input 1 – multiple individual files -->
    <div class="mb-3">
      <label class="form-label">📄 Pilih file PDF (multi‑select):</label>
      <input type="file" name="documents" multiple class="form-control" />
    </div>

    <!-- Input 2 – whole folder -->
    <div class="mb-3">
      <label class="form-label">📁 Atau pilih folder:</label>
      <input type="file" name="documents" webkitdirectory class="form-control" />
      <small class="text-muted">*Fitur folder hanya tersedia di Chrome / Edge*</small>
    </div>

    <button type="submit" class="btn btn-success">Unggah Sekarang</button>
    <a href="{{ url_for('list_documents') }}" class="btn btn-secondary">Batal</a>
  </form>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
