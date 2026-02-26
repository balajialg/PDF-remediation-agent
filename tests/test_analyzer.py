"""Tests for the PDF Accessibility Analyzer."""

from __future__ import annotations

import io
import os
import sys

import pytest
import fitz  # PyMuPDF

# Add the repo root to sys.path so the engine can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pdf_engine.analyzer import PDFAccessibilityAnalyzer
from pdf_engine.remediator import PDFRemediator
from pdf_engine.wcag_rules import WCAG_RULES


# ---------------------------------------------------------------------------
# PDF factory helpers
# ---------------------------------------------------------------------------

def _make_pdf(
    title: str = "",
    language: str = "",
    add_image: bool = False,
    add_link: bool = False,
    add_form_field: bool = False,
    page_count: int = 1,
    tagged: bool = False,
    light_text: bool = False,
    tmp_path: str = "/tmp",
    filename: str = "test.pdf",
) -> str:
    """Create a simple PDF for testing and return the file path."""
    doc = fitz.open()

    for i in range(page_count):
        page = doc.new_page(width=595, height=842)

        # Normal dark text
        page.insert_text((72, 100 + i * 10), f"Sample text on page {i + 1}.", fontsize=12)

        if light_text:
            # Very light gray text — will fail contrast check against white bg
            page.insert_text(
                (72, 200),
                "Low contrast text.",
                fontsize=12,
                color=(0.85, 0.85, 0.85),
            )

        if add_image and i == 0:
            # Insert a small red rectangle rendered as an image
            img_doc = fitz.open()
            img_page = img_doc.new_page(width=100, height=100)
            img_page.draw_rect(fitz.Rect(0, 0, 100, 100), color=(1, 0, 0), fill=(1, 0, 0))
            pix = img_page.get_pixmap()
            png_bytes = pix.tobytes("png")
            img_doc.close()
            page.insert_image(fitz.Rect(200, 300, 350, 450), stream=png_bytes)

        if add_link and i == 0:
            # Insert hyperlink with generic text
            page.insert_text((72, 400), "click here", fontsize=12, color=(0, 0, 1))
            link_rect = fitz.Rect(72, 388, 160, 408)
            page.insert_link({"kind": fitz.LINK_URI, "from": link_rect, "uri": "https://example.com"})

        if add_form_field and i == 0:
            widget = fitz.Widget()
            widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
            widget.field_name = ""  # No name — accessibility issue
            widget.rect = fitz.Rect(72, 500, 300, 525)
            page.add_widget(widget)

    # Metadata
    meta = {}
    if title:
        meta["title"] = title
    if meta:
        doc.set_metadata(meta)

    out_path = os.path.join(tmp_path, filename)

    if not language:
        doc.save(out_path)
        doc.close()
    else:
        # Save first so the file exists, then re-open and set /Lang incrementally
        doc.save(out_path)
        doc.close()
        doc = fitz.open(out_path)
        cat = doc.pdf_catalog()
        doc.xref_set_key(cat, "Lang", f"({language})")
        doc.saveIncr()
        doc.close()

    return out_path


def _make_scanned_pdf(
    tmp_path: str = "/tmp",
    filename: str = "scanned.pdf",
    add_text_layer: bool = False,
    ocr_detectable: bool = True,
) -> str:
    """Create a PDF simulating a scanned document.

    The page contains a full-page image.  When *ocr_detectable* is True the
    image is rendered from text (so that OCR will find readable characters).
    When False, the image is a plain colour rectangle that contains no text.

    If *add_text_layer* is True, normal extractable text is also added to the
    page (simulating a PDF that has already been OCR-processed).
    """
    # Step 1 — build a source page to render as an image
    src = fitz.open()
    src_page = src.new_page(width=595, height=842)
    if ocr_detectable:
        # Draw readable text so that OCR will detect it
        src_page.insert_text(
            (72, 100),
            "This is a sample scanned document page that contains "
            "readable text content for OCR testing purposes.",
            fontsize=14,
        )
        src_page.insert_text((72, 140), "Second line of sample text.", fontsize=12)
    else:
        # Plain colour fill — no readable text
        src_page.draw_rect(fitz.Rect(0, 0, 595, 842), fill=(0.95, 0.95, 0.95))
    pix = src_page.get_pixmap()
    png_bytes = pix.tobytes("png")
    src.close()

    # Step 2 — build the actual "scanned" PDF with the image
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(fitz.Rect(0, 0, 595, 842), stream=png_bytes)

    if add_text_layer:
        page.insert_text((72, 100), "Extracted text layer.", fontsize=12)

    out_path = os.path.join(tmp_path, filename)
    doc.save(out_path)
    doc.close()
    return out_path


# ---------------------------------------------------------------------------
# Tests — WCAG 2.4.2 Document Title
# ---------------------------------------------------------------------------

class TestDocumentTitle:
    def test_missing_title_raises_issue(self, tmp_path):
        path = _make_pdf(title="", tmp_path=str(tmp_path))
        analyzer = PDFAccessibilityAnalyzer(path)
        issues = analyzer.analyze()
        analyzer.close()
        crits = [i for i in issues if i.wcag_criterion == "2.4.2"]
        assert crits, "Expected a 2.4.2 issue for missing title"
        assert crits[0].auto_fixable is True

    def test_present_title_no_issue(self, tmp_path):
        path = _make_pdf(title="My Document Title", tmp_path=str(tmp_path))
        analyzer = PDFAccessibilityAnalyzer(path)
        issues = analyzer.analyze()
        analyzer.close()
        crits = [i for i in issues if i.wcag_criterion == "2.4.2"]
        assert not crits, "Expected no 2.4.2 issue when title is set"


# ---------------------------------------------------------------------------
# Tests — WCAG 3.1.1 Document Language
# ---------------------------------------------------------------------------

class TestDocumentLanguage:
    def test_missing_language_raises_issue(self, tmp_path):
        path = _make_pdf(language="", tmp_path=str(tmp_path))
        analyzer = PDFAccessibilityAnalyzer(path)
        issues = analyzer.analyze()
        analyzer.close()
        crits = [i for i in issues if i.wcag_criterion == "3.1.1"]
        assert crits, "Expected a 3.1.1 issue for missing language"

    def test_present_language_no_issue(self, tmp_path):
        path = _make_pdf(language="en-US", tmp_path=str(tmp_path))
        analyzer = PDFAccessibilityAnalyzer(path)
        issues = analyzer.analyze()
        analyzer.close()
        crits = [i for i in issues if i.wcag_criterion == "3.1.1"]
        assert not crits, "Expected no 3.1.1 issue when language is set"


# ---------------------------------------------------------------------------
# Tests — WCAG 1.3.1 Tagged PDF
# ---------------------------------------------------------------------------

class TestTaggedPDF:
    def test_untagged_pdf_raises_issue(self, tmp_path):
        path = _make_pdf(tmp_path=str(tmp_path), tagged=False)
        analyzer = PDFAccessibilityAnalyzer(path)
        issues = analyzer.analyze()
        analyzer.close()
        crits = [i for i in issues if i.wcag_criterion == "1.3.1"]
        assert crits, "Expected a 1.3.1 issue for untagged PDF"
        assert crits[0].severity == "critical"


# ---------------------------------------------------------------------------
# Tests — WCAG 2.4.5 Bookmarks
# ---------------------------------------------------------------------------

class TestBookmarks:
    def test_multipage_without_bookmarks_raises_issue(self, tmp_path):
        path = _make_pdf(page_count=3, tmp_path=str(tmp_path))
        analyzer = PDFAccessibilityAnalyzer(path)
        issues = analyzer.analyze()
        analyzer.close()
        crits = [i for i in issues if i.wcag_criterion == "2.4.5"]
        assert crits, "Expected a 2.4.5 issue for multi-page doc without bookmarks"

    def test_single_page_no_bookmark_issue(self, tmp_path):
        path = _make_pdf(page_count=1, tmp_path=str(tmp_path))
        analyzer = PDFAccessibilityAnalyzer(path)
        issues = analyzer.analyze()
        analyzer.close()
        crits = [i for i in issues if i.wcag_criterion == "2.4.5"]
        assert not crits, "Single-page docs should not require bookmarks"


# ---------------------------------------------------------------------------
# Tests — WCAG 1.1.1 Images Alt Text
# ---------------------------------------------------------------------------

class TestImageAltText:
    def test_image_without_alt_raises_issue(self, tmp_path):
        path = _make_pdf(add_image=True, tmp_path=str(tmp_path))
        analyzer = PDFAccessibilityAnalyzer(path)
        issues = analyzer.analyze()
        analyzer.close()
        crits = [i for i in issues if i.wcag_criterion == "1.1.1"]
        assert crits, "Expected a 1.1.1 issue for image without alt text"

    def test_no_image_no_alt_issue(self, tmp_path):
        path = _make_pdf(add_image=False, tmp_path=str(tmp_path))
        analyzer = PDFAccessibilityAnalyzer(path)
        issues = analyzer.analyze()
        analyzer.close()
        crits = [i for i in issues if i.wcag_criterion == "1.1.1"]
        assert not crits, "Expected no 1.1.1 issue when there are no images"

    def test_full_page_image_with_text_not_flagged_as_image(self, tmp_path):
        """A full-page image containing text (scanned page) should NOT
        be flagged as 'Image Missing Alternative Text'."""
        path = _make_scanned_pdf(tmp_path=str(tmp_path))
        analyzer = PDFAccessibilityAnalyzer(path)
        issues = analyzer.analyze()
        analyzer.close()
        img_issues = [i for i in issues if i.wcag_criterion == "1.1.1"]
        assert not img_issues, (
            "Full-page scanned text should not be flagged as an image missing alt text"
        )

    def test_full_page_image_with_existing_text_layer_not_flagged(self, tmp_path):
        """A page with both a full-page image and extractable text (already
        OCR'd) should NOT be flagged as an image issue."""
        path = _make_scanned_pdf(tmp_path=str(tmp_path), add_text_layer=True)
        analyzer = PDFAccessibilityAnalyzer(path)
        issues = analyzer.analyze()
        analyzer.close()
        img_issues = [i for i in issues if i.wcag_criterion == "1.1.1"]
        assert not img_issues, (
            "Full-page image with existing text layer should not be flagged"
        )


# ---------------------------------------------------------------------------
# Tests — Scanned Content Detection
# ---------------------------------------------------------------------------

class TestScannedContent:
    def test_scanned_page_flagged_for_ocr(self, tmp_path):
        """A scanned page (full-page image, no text) should be flagged as
        needing OCR and tagging."""
        path = _make_scanned_pdf(tmp_path=str(tmp_path), ocr_detectable=False)
        analyzer = PDFAccessibilityAnalyzer(path)
        issues = analyzer.analyze()
        analyzer.close()
        scanned = [
            i for i in issues
            if i.element_info and i.element_info.get("type") == "scanned_page"
        ]
        assert scanned, "Expected a scanned-content issue for image-only page"
        assert scanned[0].auto_fixable is True

    def test_page_with_text_not_flagged_as_scanned(self, tmp_path):
        """A page with normal text should not be flagged as scanned."""
        path = _make_pdf(tmp_path=str(tmp_path))
        analyzer = PDFAccessibilityAnalyzer(path)
        issues = analyzer.analyze()
        analyzer.close()
        scanned = [
            i for i in issues
            if i.element_info and i.element_info.get("type") == "scanned_page"
        ]
        assert not scanned, "Normal text page should not be flagged as scanned"


# ---------------------------------------------------------------------------
# Tests — WCAG 1.4.3 Colour Contrast
# ---------------------------------------------------------------------------

class TestColourContrast:
    def test_light_text_raises_contrast_issue(self, tmp_path):
        path = _make_pdf(light_text=True, tmp_path=str(tmp_path))
        analyzer = PDFAccessibilityAnalyzer(path)
        issues = analyzer.analyze()
        analyzer.close()
        crits = [i for i in issues if i.wcag_criterion == "1.4.3"]
        assert crits, "Expected a 1.4.3 issue for light-gray text on white background"

    def test_dark_text_no_contrast_issue(self, tmp_path):
        path = _make_pdf(light_text=False, tmp_path=str(tmp_path))
        analyzer = PDFAccessibilityAnalyzer(path)
        issues = analyzer.analyze()
        analyzer.close()
        crits = [i for i in issues if i.wcag_criterion == "1.4.3"]
        assert not crits, "Expected no 1.4.3 issue for dark text on white background"


# ---------------------------------------------------------------------------
# Tests — WCAG 2.4.4 Link Purpose
# ---------------------------------------------------------------------------

class TestLinkPurpose:
    def test_generic_link_text_raises_issue(self, tmp_path):
        path = _make_pdf(add_link=True, tmp_path=str(tmp_path))
        analyzer = PDFAccessibilityAnalyzer(path)
        issues = analyzer.analyze()
        analyzer.close()
        crits = [i for i in issues if i.wcag_criterion == "2.4.4"]
        assert crits, "Expected a 2.4.4 issue for 'click here' link text"


# ---------------------------------------------------------------------------
# Tests — Accessibility Score
# ---------------------------------------------------------------------------

class TestAccessibilityScore:
    def test_score_decreases_with_issues(self, tmp_path):
        # A bare-minimum PDF will have many issues → low score
        path = _make_pdf(tmp_path=str(tmp_path))
        analyzer = PDFAccessibilityAnalyzer(path)
        analyzer.analyze()
        score = analyzer.get_score()
        analyzer.close()
        assert score < 100, "A PDF with issues should score below 100"

    def test_score_improves_with_fixes(self, tmp_path):
        # PDF with everything set should score better than one missing metadata
        bare_path = _make_pdf(tmp_path=str(tmp_path), filename="bare.pdf")
        full_path = _make_pdf(
            title="Full Doc",
            language="en-US",
            tmp_path=str(tmp_path),
            filename="full.pdf",
        )
        analyzer_bare = PDFAccessibilityAnalyzer(bare_path)
        analyzer_bare.analyze()
        score_bare = analyzer_bare.get_score()
        analyzer_bare.close()

        analyzer_full = PDFAccessibilityAnalyzer(full_path)
        analyzer_full.analyze()
        score_full = analyzer_full.get_score()
        analyzer_full.close()

        assert score_full > score_bare, "Setting metadata should improve the score"


# ---------------------------------------------------------------------------
# Tests — Remediator
# ---------------------------------------------------------------------------

class TestRemediator:
    def test_fix_title(self, tmp_path):
        path = _make_pdf(tmp_path=str(tmp_path), filename="remediate_title.pdf")
        remediator = PDFRemediator(path)
        remediator.fix_document_title("Fixed Title")
        remediator.close()

        # Re-open and check
        doc = fitz.open(path)
        assert doc.metadata.get("title") == "Fixed Title"
        doc.close()

    def test_fix_language(self, tmp_path):
        path = _make_pdf(tmp_path=str(tmp_path), filename="remediate_lang.pdf")
        remediator = PDFRemediator(path)
        remediator.fix_document_language("en-US")
        remediator.close()

        doc = fitz.open(path)
        cat = doc.pdf_catalog()
        raw = doc.xref_get_key(cat, "Lang")
        # xref_get_key returns (type, value) tuple in PyMuPDF ≥ 1.24
        lang_val = raw[1] if isinstance(raw, tuple) else raw
        doc.close()
        assert "en-US" in lang_val

    def test_fix_title_removes_issue(self, tmp_path):
        path = _make_pdf(tmp_path=str(tmp_path), filename="fix_removes.pdf")

        # Initially has a title issue
        analyzer = PDFAccessibilityAnalyzer(path)
        issues_before = analyzer.analyze()
        analyzer.close()
        title_issues_before = [i for i in issues_before if i.wcag_criterion == "2.4.2"]
        assert title_issues_before, "Should have title issue before fix"

        # Fix it
        remediator = PDFRemediator(path)
        remediator.fix_document_title("My New Title")
        remediator.close()

        # Re-analyse
        analyzer2 = PDFAccessibilityAnalyzer(path)
        issues_after = analyzer2.analyze()
        analyzer2.close()
        title_issues_after = [i for i in issues_after if i.wcag_criterion == "2.4.2"]
        assert not title_issues_after, "Title issue should be gone after fix"

    def test_ocr_and_tag_adds_text_layer(self, tmp_path):
        """perform_ocr_and_tag should add extractable text to a scanned PDF."""
        path = _make_scanned_pdf(tmp_path=str(tmp_path), filename="ocr_test.pdf")

        # Before OCR — no extractable text
        doc = fitz.open(path)
        text_before = doc[0].get_text("text").strip()
        doc.close()
        assert not text_before, "Scanned PDF should have no text before OCR"

        # Run OCR & tag
        remediator = PDFRemediator(path)
        result = remediator.perform_ocr_and_tag()
        remediator.close()

        assert result["pages_ocrd"] >= 1, "At least one page should be OCR'd"

        # After OCR — should now have extractable text
        doc = fitz.open(path)
        text_after = doc[0].get_text("text").strip()
        doc.close()
        assert text_after, "Scanned PDF should have extractable text after OCR"

    def test_ocr_and_tag_returns_tag_count(self, tmp_path):
        """perform_ocr_and_tag should return the number of tags added."""
        path = _make_scanned_pdf(tmp_path=str(tmp_path), filename="tag_test.pdf")
        remediator = PDFRemediator(path)
        result = remediator.perform_ocr_and_tag()
        remediator.close()
        assert "tags_added" in result
        assert "pages_ocrd" in result


# ---------------------------------------------------------------------------
# Tests — WCAG rules table
# ---------------------------------------------------------------------------

class TestWCAGRules:
    def test_all_expected_criteria_present(self):
        expected = {"1.1.1", "1.3.1", "1.3.2", "1.4.3", "2.4.2",
                    "2.4.4", "2.4.5", "2.4.6", "3.1.1", "4.1.2"}
        assert expected == set(WCAG_RULES.keys())

    def test_each_rule_has_required_fields(self):
        for criterion, rule in WCAG_RULES.items():
            assert "title" in rule, f"{criterion} missing title"
            assert "level" in rule, f"{criterion} missing level"
            assert rule["level"] in ("A", "AA"), f"{criterion} invalid level"
            assert "help_url" in rule, f"{criterion} missing help_url"


# ---------------------------------------------------------------------------
# Tests — render_page and get_page_dimensions
# ---------------------------------------------------------------------------

class TestRendering:
    def test_render_page_returns_png(self, tmp_path):
        path = _make_pdf(tmp_path=str(tmp_path))
        analyzer = PDFAccessibilityAnalyzer(path)
        png = analyzer.render_page(0)
        analyzer.close()
        assert png[:4] == b"\x89PNG", "Expected PNG magic bytes"

    def test_get_page_dimensions(self, tmp_path):
        path = _make_pdf(tmp_path=str(tmp_path))
        analyzer = PDFAccessibilityAnalyzer(path)
        dims = analyzer.get_page_dimensions(0)
        analyzer.close()
        assert "width" in dims and "height" in dims
        assert dims["width"] == pytest.approx(595, abs=1)
        assert dims["height"] == pytest.approx(842, abs=1)
