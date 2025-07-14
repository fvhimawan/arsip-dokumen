# batch_upload.py
"""
Minimal Flask Blueprint so the app can start on Render.
You can extend this later with real batch‑upload functionality.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for

batch_upload_bp = Blueprint(
    "batch_upload_bp",
    __name__,
    template_folder="templates"
)

@batch_upload_bp.route("/batch-upload", methods=["GET", "POST"])
def show():
    if request.method == "POST":
        flash("Batch upload feature is not implemented yet.", "warning")
        return redirect(url_for("batch_upload_bp.show"))

    # Simple placeholder page so we can confirm the service works
    return (
        "<h3 style='font-family:sans-serif'>Batch upload placeholder</h3>"
        "<p>Your web service is running. "
        "Implement real batch-upload logic here later.</p>"
    )
