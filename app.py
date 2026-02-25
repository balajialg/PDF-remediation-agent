"""PDF Accessibility Engine — Flask web application."""

from __future__ import annotations

import io
import os
import tempfile
import uuid

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from werkzeug.utils import secure_filename

from pdf_engine.analyzer import PDFAccessibilityAnalyzer
from pdf_engine.remediator import PDFRemediator
from pdf_engine.wcag_rules import WCAG_RULES

# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), "pdf_a11y_engine")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf"}

# In-process session store (sufficient for a single-process dev/demo server).
_sessions: dict = {}


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    if not file.filename or not _allowed_file(file.filename):
        return jsonify({"error": "Please upload a valid PDF file"}), 400

    # Persist uploaded file
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_dir, exist_ok=True)

    filename = secure_filename(file.filename)
    pdf_path = os.path.join(session_dir, filename)
    file.save(pdf_path)

    # Run analysis
    analyzer = PDFAccessibilityAnalyzer(pdf_path)
    issues = analyzer.analyze()
    score = analyzer.get_score()
    page_count = analyzer.doc.page_count
    page_dims = [analyzer.get_page_dimensions(i) for i in range(page_count)]
    metadata = dict(analyzer.doc.metadata)
    analyzer.close()

    _sessions[session_id] = {
        "pdf_path": pdf_path,
        "filename": filename,
        "issues": [i.to_dict() for i in issues],
        "score": score,
        "page_count": page_count,
        "page_dims": page_dims,
        "metadata": metadata,
    }

    return redirect(url_for("report", session_id=session_id))


@app.route("/report/<session_id>")
def report(session_id: str):
    if session_id not in _sessions:
        return redirect(url_for("index"))
    data = _sessions[session_id]
    return render_template(
        "report.html",
        session_id=session_id,
        data=data,
        wcag_rules=WCAG_RULES,
    )


@app.route("/page/<session_id>/<int:page_num>")
def get_page(session_id: str, page_num: int):
    """Serve a rendered PNG of the requested page (0-based)."""
    if session_id not in _sessions:
        return "Session not found", 404

    pdf_path = _sessions[session_id]["pdf_path"]
    page_count = _sessions[session_id]["page_count"]
    if page_num < 0 or page_num >= page_count:
        return "Page out of range", 404

    analyzer = PDFAccessibilityAnalyzer(pdf_path)
    try:
        png_bytes = analyzer.render_page(page_num, scale=1.5)
    finally:
        analyzer.close()

    return send_file(io.BytesIO(png_bytes), mimetype="image/png")


@app.route("/remediate/<session_id>", methods=["POST"])
def remediate(session_id: str):
    if session_id not in _sessions:
        return jsonify({"error": "Session not found"}), 404

    payload = request.get_json(force=True)
    action = payload.get("action", "")
    pdf_path = _sessions[session_id]["pdf_path"]

    remediator = PDFRemediator(pdf_path)
    try:
        if action == "fix_title":
            new_title = payload.get("title", "").strip()
            if not new_title:
                return jsonify({"error": "Title cannot be empty"}), 400
            remediator.fix_document_title(new_title)
            _sessions[session_id]["metadata"]["title"] = new_title

        elif action == "fix_language":
            new_lang = payload.get("language", "").strip()
            if not new_lang:
                return jsonify({"error": "Language cannot be empty"}), 400
            remediator.fix_document_language(new_lang)
            _sessions[session_id]["metadata"]["language"] = new_lang

        else:
            return jsonify({"error": f"Unknown action: {action}"}), 400

    finally:
        remediator.close()

    # Re-run analysis so the updated issues list is returned
    analyzer = PDFAccessibilityAnalyzer(pdf_path)
    issues = analyzer.analyze()
    score = analyzer.get_score()
    analyzer.close()

    _sessions[session_id]["issues"] = [i.to_dict() for i in issues]
    _sessions[session_id]["score"] = score

    return jsonify(
        {
            "success": True,
            "message": f"Action '{action}' applied successfully.",
            "score": score,
            "issues": _sessions[session_id]["issues"],
        }
    )


@app.route("/download/<session_id>")
def download(session_id: str):
    if session_id not in _sessions:
        return "Session not found", 404
    pdf_path = _sessions[session_id]["pdf_path"]
    filename = _sessions[session_id]["filename"]
    return send_file(
        pdf_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"remediated_{filename}",
    )


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
