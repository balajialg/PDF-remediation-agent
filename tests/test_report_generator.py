"""Tests for the PDF accessibility report generator."""

from __future__ import annotations

import os
import sys

import pytest
import fitz  # PyMuPDF

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pdf_engine.report_generator import generate_accessibility_report


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SAMPLE_ISSUES = [
    {
        "issue_id": "issue-0001",
        "wcag_criterion": "2.4.2",
        "wcag_title": "Page Titled",
        "level": "A",
        "severity": "serious",
        "page": 0,
        "title": "Missing Document Title",
        "description": "The PDF does not have a title in its metadata.",
        "remediation": "Add a descriptive title via File > Properties.",
        "auto_fixable": True,
        "rect": None,
        "element_info": {"type": "metadata", "field": "title"},
    },
    {
        "issue_id": "issue-0002",
        "wcag_criterion": "1.3.1",
        "wcag_title": "Info and Relationships",
        "level": "A",
        "severity": "critical",
        "page": 0,
        "title": "PDF is Not Tagged",
        "description": "The document lacks accessibility tags.",
        "remediation": "Re-export with tagging enabled.",
        "auto_fixable": False,
        "rect": None,
        "element_info": {"type": "document_structure", "has_tags": False},
    },
    {
        "issue_id": "issue-0003",
        "wcag_criterion": "1.4.3",
        "wcag_title": "Contrast (Minimum)",
        "level": "AA",
        "severity": "moderate",
        "page": 1,
        "title": "Insufficient Colour Contrast",
        "description": "Text on page 1 has a contrast ratio of 2.5:1.",
        "remediation": "Change text or background colour.",
        "auto_fixable": False,
        "rect": [72, 100, 300, 120],
        "element_info": {"type": "text"},
    },
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestReportGenerator:
    def test_returns_valid_pdf_bytes(self):
        result = generate_accessibility_report(
            filename="test.pdf",
            issues=_SAMPLE_ISSUES,
            score=62,
            metadata={"title": "", "author": "Tester"},
            page_count=3,
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_report_can_be_opened_by_pymupdf(self):
        result = generate_accessibility_report(
            filename="test.pdf",
            issues=_SAMPLE_ISSUES,
            score=62,
            metadata={"title": ""},
            page_count=3,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        assert doc.page_count >= 1
        doc.close()

    def test_report_contains_filename(self):
        result = generate_accessibility_report(
            filename="my_document.pdf",
            issues=_SAMPLE_ISSUES,
            score=50,
            metadata={},
            page_count=1,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        text = "".join(doc[i].get_text() for i in range(doc.page_count))
        doc.close()
        assert "my_document.pdf" in text

    def test_report_contains_score(self):
        result = generate_accessibility_report(
            filename="test.pdf",
            issues=_SAMPLE_ISSUES,
            score=75,
            metadata={},
            page_count=1,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        text = "".join(doc[i].get_text() for i in range(doc.page_count))
        doc.close()
        assert "75" in text

    def test_report_contains_issue_titles(self):
        result = generate_accessibility_report(
            filename="test.pdf",
            issues=_SAMPLE_ISSUES,
            score=62,
            metadata={},
            page_count=1,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        text = "".join(doc[i].get_text() for i in range(doc.page_count))
        doc.close()
        assert "Missing Document Title" in text
        assert "PDF is Not Tagged" in text

    def test_report_contains_severity_counts(self):
        result = generate_accessibility_report(
            filename="test.pdf",
            issues=_SAMPLE_ISSUES,
            score=62,
            metadata={},
            page_count=1,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        text = "".join(doc[i].get_text() for i in range(doc.page_count))
        doc.close()
        assert "Critical: 1" in text
        assert "Serious: 1" in text
        assert "Moderate: 1" in text

    def test_report_with_no_issues(self):
        result = generate_accessibility_report(
            filename="perfect.pdf",
            issues=[],
            score=100,
            metadata={"title": "Perfect Doc"},
            page_count=1,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        text = "".join(doc[i].get_text() for i in range(doc.page_count))
        doc.close()
        assert "No accessibility issues" in text
        assert "100" in text

    def test_report_metadata_title_is_set(self):
        result = generate_accessibility_report(
            filename="sample.pdf",
            issues=[],
            score=100,
            metadata={},
            page_count=1,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        assert "sample.pdf" in (doc.metadata.get("title") or "")
        doc.close()

    def test_report_with_many_issues_spans_multiple_pages(self):
        """A large number of issues should produce a multi-page report."""
        many_issues = []
        for i in range(40):
            many_issues.append({
                "issue_id": f"issue-{i:04d}",
                "wcag_criterion": "1.1.1",
                "wcag_title": "Non-text Content",
                "level": "A",
                "severity": "serious",
                "page": (i % 5) + 1,
                "title": f"Image Missing Alternative Text #{i + 1}",
                "description": f"An image on page {(i % 5) + 1} does not have alternative text.",
                "remediation": "Add a descriptive /Alt attribute.",
                "auto_fixable": False,
                "rect": None,
                "element_info": {"type": "image"},
            })
        result = generate_accessibility_report(
            filename="big.pdf",
            issues=many_issues,
            score=10,
            metadata={},
            page_count=5,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        assert doc.page_count > 1
        doc.close()
