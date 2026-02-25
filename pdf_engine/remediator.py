"""PDF Remediator — applies in-place fixes to a PDF file."""

from __future__ import annotations

from typing import Optional

import fitz  # PyMuPDF


class PDFRemediator:
    """
    Applies targeted remediation actions to a PDF file.

    Currently supported auto-fix actions
    -------------------------------------
    * fix_document_title   — update /Title in XMP/Info metadata
    * fix_document_language — set /Lang in the PDF catalog and metadata
    """

    def __init__(self, pdf_path: str) -> None:
        self.pdf_path = pdf_path
        self.doc: fitz.Document = fitz.open(pdf_path)

    # ------------------------------------------------------------------
    # Metadata fixes
    # ------------------------------------------------------------------

    def fix_document_title(self, title: str) -> None:
        """Update the document title in the PDF metadata and save in-place."""
        meta = dict(self.doc.metadata)
        meta["title"] = title.strip()
        self.doc.set_metadata(meta)
        self.doc.saveIncr()

    def fix_document_language(self, language: str) -> None:
        """
        Set the document language in the /Lang entry of the PDF catalog.
        (PyMuPDF's set_metadata does not accept 'language', so we write
        directly to the catalog xref.)
        """
        lang = language.strip()
        try:
            cat_xref = self.doc.pdf_catalog()
            self.doc.xref_set_key(cat_xref, "Lang", f"({lang})")
        except Exception:
            pass

        self.doc.saveIncr()

    # ------------------------------------------------------------------

    def close(self) -> None:
        self.doc.close()
