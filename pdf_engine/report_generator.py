"""Generate a PDF report of accessibility issues found in a document."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import fitz  # PyMuPDF


# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

_SEVERITY_COLORS: Dict[str, tuple] = {
    "critical": (0.80, 0.13, 0.13),   # red
    "serious": (0.90, 0.49, 0.13),    # orange
    "moderate": (0.85, 0.65, 0.13),   # amber
    "minor": (0.40, 0.40, 0.40),      # gray
}
_HEADER_BG = (0.16, 0.30, 0.46)       # dark-blue
_HEADER_FG = (1.0, 1.0, 1.0)
_RULE_COLOR = (0.80, 0.80, 0.80)
_BODY_COLOR = (0.20, 0.20, 0.20)
_MUTED_COLOR = (0.45, 0.45, 0.45)
_PASS_COLOR = (0.13, 0.55, 0.13)

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

_PAGE_W, _PAGE_H = 612, 792           # US Letter (pts)
_MARGIN = 54
_CONTENT_W = _PAGE_W - 2 * _MARGIN
_FOOTER_Y = _PAGE_H - 36


def generate_accessibility_report(
    filename: str,
    issues: List[Dict[str, Any]],
    score: int,
    metadata: Dict[str, Any],
    page_count: int,
) -> bytes:
    """Return a self-contained PDF (as bytes) summarising the accessibility audit.

    Parameters
    ----------
    filename:
        Original PDF file name.
    issues:
        List of issue dicts (as returned by ``AccessibilityIssue.to_dict()``).
    score:
        Accessibility score 0–100.
    metadata:
        Document metadata dict.
    page_count:
        Number of pages in the analysed PDF.
    """
    doc = fitz.open()

    # ── helpers ──────────────────────────────────────────────────────────
    page: fitz.Page | None = None
    y = _PAGE_H  # force new page on first use

    def _ensure_space(needed: float) -> None:
        nonlocal page, y
        if page is None or y + needed > _FOOTER_Y:
            _new_page()

    def _new_page() -> None:
        nonlocal page, y
        page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
        y = _MARGIN
        # footer
        page.insert_text(
            (_MARGIN, _FOOTER_Y),
            f"PDF Accessibility Report — generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}",
            fontsize=7,
            color=_MUTED_COLOR,
        )
        page_num = doc.page_count
        page.insert_text(
            (_PAGE_W - _MARGIN - 30, _FOOTER_Y),
            f"Page {page_num}",
            fontsize=7,
            color=_MUTED_COLOR,
        )

    def _draw_rule() -> None:
        nonlocal y
        if page is None:
            return
        page.draw_line(
            fitz.Point(_MARGIN, y),
            fitz.Point(_PAGE_W - _MARGIN, y),
            color=_RULE_COLOR,
            width=0.5,
        )
        y += 6

    def _write(
        text: str,
        fontsize: float = 10,
        color: tuple = _BODY_COLOR,
        bold: bool = False,
        indent: float = 0,
        spacing: float = 2,
    ) -> None:
        """Insert *text* with automatic wrapping and page breaks."""
        nonlocal y
        fontname = "helv" if not bold else "hebo"
        max_w = _CONTENT_W - indent
        lines = _wrap_text(text, fontname, fontsize, max_w)
        line_h = fontsize * 1.35
        for line in lines:
            _ensure_space(line_h + spacing)
            page.insert_text(  # type: ignore[union-attr]
                (_MARGIN + indent, y + fontsize),
                line,
                fontsize=fontsize,
                fontname=fontname,
                color=color,
            )
            y += line_h
        y += spacing

    # ── title page / header ─────────────────────────────────────────────
    _new_page()

    # Header band
    rect = fitz.Rect(_MARGIN, y, _PAGE_W - _MARGIN, y + 48)
    page.draw_rect(rect, color=_HEADER_BG, fill=_HEADER_BG)  # type: ignore[union-attr]
    page.insert_text(  # type: ignore[union-attr]
        (_MARGIN + 12, y + 30),
        "PDF Accessibility Report",
        fontsize=20,
        fontname="hebo",
        color=_HEADER_FG,
    )
    y += 60

    # File info
    _write(f"File: {filename}", fontsize=11, bold=True)
    _write(f"Pages: {page_count}", fontsize=10)
    title = metadata.get("title") or "(none)"
    _write(f"Document Title: {title}", fontsize=10)
    y += 4

    # ── score section ───────────────────────────────────────────────────
    _draw_rule()
    if score >= 80:
        score_color = _PASS_COLOR
    elif score >= 50:
        score_color = _SEVERITY_COLORS["moderate"]
    else:
        score_color = _SEVERITY_COLORS["critical"]
    _write(f"Accessibility Score: {score} / 100", fontsize=14, bold=True, color=score_color)
    y += 4

    # ── summary counts ──────────────────────────────────────────────────
    _draw_rule()
    _write("Issue Summary", fontsize=12, bold=True)
    y += 2
    for sev in ("critical", "serious", "moderate", "minor"):
        count = sum(1 for i in issues if i.get("severity") == sev)
        color = _SEVERITY_COLORS.get(sev, _BODY_COLOR)
        _write(f"  {sev.capitalize()}: {count}", fontsize=10, color=color, indent=8)
    total = len(issues)
    _write(f"  Total: {total}", fontsize=10, bold=True, indent=8)
    y += 6

    # ── detailed issues ─────────────────────────────────────────────────
    _draw_rule()
    _write("Detailed Issues", fontsize=13, bold=True)
    y += 4

    if not issues:
        _write(
            "No accessibility issues were detected. "
            "This PDF appears to meet WCAG 2.1 AA requirements for the checks performed.",
            fontsize=10,
            color=_PASS_COLOR,
        )
    else:
        for idx, issue in enumerate(issues, 1):
            sev = issue.get("severity", "minor")
            sev_color = _SEVERITY_COLORS.get(sev, _BODY_COLOR)

            # Issue heading — need space for at least the heading + one line
            _ensure_space(50)

            # Severity + title line
            _write(
                f"{idx}. [{sev.capitalize()}] {issue.get('title', '')}",
                fontsize=10,
                bold=True,
                color=sev_color,
            )

            # WCAG + page
            page_label = (
                "Document-level" if issue.get("page", 0) == 0 else f"Page {issue['page']}"
            )
            _write(
                f"   WCAG {issue.get('wcag_criterion', '')} — {issue.get('wcag_title', '')}  |  {page_label}",
                fontsize=8,
                color=_MUTED_COLOR,
                indent=12,
            )

            # Description
            desc = issue.get("description", "")
            if desc:
                _write(desc, fontsize=9, indent=12)

            # Remediation
            remediation = issue.get("remediation", "")
            if remediation:
                _write(f"How to fix: {remediation}", fontsize=9, indent=12, color=_MUTED_COLOR)

            y += 4

    # ── finalise ────────────────────────────────────────────────────────
    doc.set_metadata({"title": f"Accessibility Report — {filename}"})
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ---------------------------------------------------------------------------
# Text-wrapping helper
# ---------------------------------------------------------------------------


def _wrap_text(text: str, fontname: str, fontsize: float, max_width: float) -> List[str]:
    """Wrap *text* into lines that fit within *max_width* points."""
    font = fitz.Font(fontname)
    words = text.split()
    lines: List[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        w = font.text_length(candidate, fontsize=fontsize)
        if w > max_width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]
