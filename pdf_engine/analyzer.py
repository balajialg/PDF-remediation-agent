"""PDF Accessibility Analyzer — WCAG 2.1 AA checks."""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF

from .wcag_rules import WCAG_RULES, SCORED_CRITERIA


@dataclass
class AccessibilityIssue:
    """Represents a single WCAG accessibility issue found in the PDF."""

    issue_id: str
    wcag_criterion: str
    wcag_title: str
    level: str          # "A" or "AA"
    severity: str       # "critical" | "serious" | "moderate" | "minor"
    page: int           # 0 = document-level, 1+ = page number
    title: str
    description: str
    remediation: str
    auto_fixable: bool
    rect: Optional[List[float]] = None          # [x0, y0, x1, y1] in PDF pts
    element_info: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "wcag_criterion": self.wcag_criterion,
            "wcag_title": self.wcag_title,
            "level": self.level,
            "severity": self.severity,
            "page": self.page,
            "title": self.title,
            "description": self.description,
            "remediation": self.remediation,
            "auto_fixable": self.auto_fixable,
            "rect": self.rect,
            "element_info": self.element_info or {},
        }


class PDFAccessibilityAnalyzer:
    """
    Analyses a PDF file against WCAG 2.1 AA criteria relevant to PDF documents.

    Checks implemented
    ------------------
    1.1.1  Non-text Content         — images missing alt text
    1.3.1  Info and Relationships   — untagged PDF / missing headings
    1.3.2  Meaningful Sequence      — tab order
    1.4.3  Contrast (Minimum)       — text/background contrast ratio
    2.4.2  Page Titled              — document title metadata
    2.4.4  Link Purpose             — non-descriptive link text
    2.4.5  Multiple Ways            — bookmarks for multi-page docs
    2.4.6  Headings and Labels      — heading structure
    3.1.1  Language of Page         — document language metadata
    4.1.2  Name, Role, Value        — unlabelled form fields
    """

    def __init__(self, pdf_path: str) -> None:
        self.pdf_path = pdf_path
        self.doc: fitz.Document = fitz.open(pdf_path)
        self.issues: List[AccessibilityIssue] = []
        self._counter = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self) -> List[AccessibilityIssue]:
        """Run all checks and return the list of issues found."""
        self.issues = []
        self._counter = 0

        self._check_document_title()
        self._check_document_language()
        self._check_tagged_pdf()
        self._check_bookmarks()
        self._check_images_alt_text()
        self._check_color_contrast()
        self._check_form_fields()
        self._check_links()
        self._check_heading_structure()
        self._check_tab_order()

        return self.issues

    def render_page(self, page_num: int, scale: float = 1.5) -> bytes:
        """Render *page_num* (0-based) and return PNG bytes."""
        page = self.doc[page_num]
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat)
        return pix.tobytes("png")

    def get_page_dimensions(self, page_num: int) -> Dict[str, float]:
        """Return the width and height of *page_num* in PDF user-space points."""
        r = self.doc[page_num].rect
        return {"width": r.width, "height": r.height}

    def get_score(self) -> int:
        """
        Calculate an accessibility score 0–100.

        Each unique failing WCAG criterion deducts points proportional to the
        highest severity of its issues.  Score = 100 minus total deductions,
        clamped to [0, 100].
        """
        severity_deductions = {"critical": 20, "serious": 12, "moderate": 6, "minor": 2}
        # Worst severity per criterion
        worst: Dict[str, str] = {}
        for issue in self.issues:
            c = issue.wcag_criterion
            cur = worst.get(c)
            if cur is None or self._sev_rank(issue.severity) > self._sev_rank(cur):
                worst[c] = issue.severity
        total = sum(severity_deductions.get(sev, 5) for sev in worst.values())
        return max(0, 100 - total)

    def close(self) -> None:
        self.doc.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sev_rank(s: str) -> int:
        return {"minor": 1, "moderate": 2, "serious": 3, "critical": 4}.get(s, 0)

    def _new_id(self) -> str:
        self._counter += 1
        return f"issue-{self._counter:04d}"

    def _add(self, **kwargs: Any) -> None:
        """Add an issue, auto-filling WCAG title from the rules table."""
        criterion = kwargs["wcag_criterion"]
        rule = WCAG_RULES.get(criterion, {})
        kwargs.setdefault("wcag_title", rule.get("title", ""))
        kwargs.setdefault("level", rule.get("level", "A"))
        kwargs.setdefault("issue_id", self._new_id())
        self.issues.append(AccessibilityIssue(**kwargs))

    @staticmethod
    def _xref_val(result) -> str:
        """
        Normalise the return value of doc.xref_get_key().

        PyMuPDF ≥ 1.24 returns a (type, value) tuple; older builds returned
        a plain string.  We always want the *value* part.
        """
        if isinstance(result, tuple):
            return result[1] if len(result) > 1 else ""
        return result or ""

    def _is_tagged(self) -> bool:
        """Return True if the PDF has an accessibility structure tree."""
        try:
            cat = self.doc.pdf_catalog()
            if self._xref_val(self.doc.xref_get_key(cat, "StructTreeRoot")) not in ("", "null"):
                return True
            mark_info = self._xref_val(self.doc.xref_get_key(cat, "MarkInfo"))
            if mark_info not in ("", "null"):
                return True
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    # Check: document title (WCAG 2.4.2)
    # ------------------------------------------------------------------

    def _check_document_title(self) -> None:
        title = (self.doc.metadata.get("title") or "").strip()
        if not title:
            self._add(
                wcag_criterion="2.4.2",
                severity="serious",
                page=0,
                title="Missing Document Title",
                description=(
                    "The PDF does not have a title in its metadata. "
                    "Screen readers and browser tabs display the document title, "
                    "so its absence makes the document harder to identify."
                ),
                remediation=(
                    "Add a descriptive title via File ▸ Properties ▸ Description, "
                    "or use the remediation form below."
                ),
                auto_fixable=True,
                element_info={"type": "metadata", "field": "title"},
            )

    # ------------------------------------------------------------------
    # Check: document language (WCAG 3.1.1)
    # ------------------------------------------------------------------

    def _check_document_language(self) -> None:
        lang = ""
        try:
            cat = self.doc.pdf_catalog()
            raw = self._xref_val(self.doc.xref_get_key(cat, "Lang"))
            if raw and raw not in ("", "null"):
                lang = raw.strip("()")
        except Exception:
            pass
        if not lang:
            self._add(
                wcag_criterion="3.1.1",
                severity="serious",
                page=0,
                title="Missing Document Language",
                description=(
                    "The natural language of the document is not specified. "
                    "Screen readers need this to select the correct voice and "
                    "pronounce words accurately."
                ),
                remediation=(
                    "Set the language in File ▸ Properties ▸ Advanced ▸ Language "
                    "(e.g. 'en-US'), or use the remediation form below."
                ),
                auto_fixable=True,
                element_info={"type": "metadata", "field": "language"},
            )

    # ------------------------------------------------------------------
    # Check: tagged PDF (WCAG 1.3.1)
    # ------------------------------------------------------------------

    def _check_tagged_pdf(self) -> None:
        if not self._is_tagged():
            self._add(
                wcag_criterion="1.3.1",
                severity="critical",
                page=0,
                title="PDF is Not Tagged",
                description=(
                    "The document lacks accessibility tags (structure tree). "
                    "Tags define headings, paragraphs, lists, and reading order "
                    "so that assistive technologies can interpret the content correctly."
                ),
                remediation=(
                    "Re-export the source document (Word, InDesign, etc.) with "
                    "accessibility/tagging enabled, or use Adobe Acrobat Pro's "
                    "Accessibility Checker to add tags automatically."
                ),
                auto_fixable=False,
                element_info={"type": "document_structure", "has_tags": False},
            )

    # ------------------------------------------------------------------
    # Check: bookmarks / table of contents (WCAG 2.4.5)
    # ------------------------------------------------------------------

    def _check_bookmarks(self) -> None:
        if self.doc.page_count > 1 and not self.doc.get_toc():
            self._add(
                wcag_criterion="2.4.5",
                severity="moderate",
                page=0,
                title="No Bookmarks / Navigation",
                description=(
                    f"The document has {self.doc.page_count} pages but no bookmarks "
                    "(outline / table of contents). Bookmarks allow users to jump "
                    "directly to sections without reading all content."
                ),
                remediation=(
                    "Add a bookmarks panel via Acrobat ▸ Tools ▸ Edit PDF ▸ "
                    "More ▸ Add Bookmarks, or export from the source with "
                    "headings mapped to bookmarks."
                ),
                auto_fixable=False,
                element_info={"type": "navigation", "page_count": self.doc.page_count},
            )

    # ------------------------------------------------------------------
    # Check: images without alternative text (WCAG 1.1.1)
    # ------------------------------------------------------------------

    def _check_images_alt_text(self) -> None:
        tagged = self._is_tagged()
        # Build a set of xrefs that DO have alt text in the structure tree
        alt_xrefs: set = self._collect_figure_alt_xrefs() if tagged else set()

        for page_num in range(self.doc.page_count):
            page = self.doc[page_num]
            for img_info in page.get_images(full=True):
                xref, _, width, height = img_info[0], img_info[1], img_info[2], img_info[3]
                # Skip tiny images (bullets, icons, decorative dots)
                if width < 16 and height < 16:
                    continue

                rects = page.get_image_rects(xref)
                rect = list(rects[0]) if rects else None

                if not tagged:
                    severity = "critical"
                    desc = (
                        f"An image on page {page_num + 1} does not have alternative text. "
                        "Because the document is untagged, screen reader users will skip "
                        "this image entirely."
                    )
                elif xref not in alt_xrefs:
                    severity = "serious"
                    desc = (
                        f"An image on page {page_num + 1} could not be verified to have "
                        "alternative text in the structure tree. "
                        "Please confirm the Figure element has an /Alt attribute."
                    )
                else:
                    continue  # Has verified alt text — no issue

                self._add(
                    wcag_criterion="1.1.1",
                    severity=severity,
                    page=page_num + 1,
                    title="Image Missing Alternative Text",
                    description=desc,
                    remediation=(
                        "Add a descriptive /Alt attribute to the corresponding "
                        "Figure element in the structure tree, or mark the image "
                        "as an artifact if it is purely decorative."
                    ),
                    auto_fixable=False,
                    rect=rect,
                    element_info={
                        "type": "image",
                        "page": page_num + 1,
                        "xref": xref,
                        "width": width,
                        "height": height,
                    },
                )

    def _collect_figure_alt_xrefs(self) -> set:
        """
        Walk the PDF's xref table and return xrefs of images that are
        referenced by a tagged Figure element *with* an /Alt attribute.
        """
        xrefs_with_alt: set = set()
        try:
            limit = self.doc.xref_length()
            for xref in range(1, limit):
                try:
                    s_type = self.doc.xref_get_key(xref, "S")
                    if "/Figure" not in s_type:
                        continue
                    alt = self.doc.xref_get_key(xref, "Alt")
                    if alt and alt not in ("", "null"):
                        # Try to find the OBJR or child reference to an image
                        k_val = self.doc.xref_get_key(xref, "K")
                        if k_val and k_val not in ("", "null"):
                            xrefs_with_alt.add(xref)
                except Exception:
                    continue
        except Exception:
            pass
        return xrefs_with_alt

    # ------------------------------------------------------------------
    # Check: colour contrast (WCAG 1.4.3)
    # ------------------------------------------------------------------

    def _check_color_contrast(self) -> None:
        seen: set = set()  # Deduplicate (color, bg_color) pairs per page

        for page_num in range(self.doc.page_count):
            page = self.doc[page_num]
            # Pre-compute background fills for this page
            bg_fills = self._get_background_fills(page)

            text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:   # 0 = text
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                        size: float = span.get("size", 12)
                        flags: int = span.get("flags", 0)
                        if size < 8:
                            continue  # Skip tiny decorative text

                        color_int: int = span.get("color", 0)
                        tr, tg, tb = self._int_to_rgb(color_int)

                        bbox = span["bbox"]
                        br, bg, bb = self._background_at(bbox, bg_fills)

                        key = (page_num, color_int, br, bg, bb)
                        if key in seen:
                            continue
                        seen.add(key)

                        lum_text = self._luminance(tr, tg, tb)
                        lum_bg = self._luminance(br, bg, bb)
                        ratio = self._contrast(lum_text, lum_bg)

                        is_large = size >= 18 or (size >= 14 and bool(flags & (1 << 4)))
                        required = 3.0 if is_large else 4.5

                        if ratio < required:
                            self._add(
                                wcag_criterion="1.4.3",
                                severity="serious" if ratio < 3.0 else "moderate",
                                page=page_num + 1,
                                title="Insufficient Colour Contrast",
                                description=(
                                    f"Text on page {page_num + 1} has a contrast ratio "
                                    f"of {ratio:.1f}:1 (required ≥ {required}:1). "
                                    f"Sample text: \"{text[:60]}\""
                                ),
                                remediation=(
                                    f"Change the text colour (#{tr:02X}{tg:02X}{tb:02X}) "
                                    f"or background (#{br:02X}{bg:02X}{bb:02X}) so that "
                                    f"the contrast ratio meets {required}:1."
                                ),
                                auto_fixable=False,
                                rect=list(bbox),
                                element_info={
                                    "type": "text",
                                    "text": text[:100],
                                    "text_color": f"#{tr:02X}{tg:02X}{tb:02X}",
                                    "bg_color": f"#{br:02X}{bg:02X}{bb:02X}",
                                    "contrast_ratio": round(ratio, 2),
                                    "required_ratio": required,
                                    "font_size": round(size, 1),
                                },
                            )

    def _get_background_fills(self, page: fitz.Page) -> List[Dict]:
        """Return list of filled rectangles with their RGB colours."""
        fills: List[Dict] = []
        try:
            for path in page.get_drawings():
                fill = path.get("fill")
                if fill is None:
                    continue
                rect = path.get("rect")
                if rect is None:
                    continue
                r = int(fill[0] * 255)
                g = int(fill[1] * 255)
                b = int(fill[2] * 255)
                fills.append({"rect": fitz.Rect(rect), "rgb": (r, g, b)})
        except Exception:
            pass
        return fills

    def _background_at(
        self,
        bbox: Tuple[float, float, float, float],
        fills: List[Dict],
    ) -> Tuple[int, int, int]:
        """Return the RGB background colour at a text bbox."""
        text_rect = fitz.Rect(bbox)
        # Find the topmost (last drawn) fill that contains or overlaps the text
        bg = (255, 255, 255)  # default white
        for fill in fills:
            if fill["rect"].contains(text_rect) or fill["rect"].intersects(text_rect):
                bg = fill["rgb"]
        return bg

    @staticmethod
    def _int_to_rgb(color: int) -> Tuple[int, int, int]:
        return ((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)

    @staticmethod
    def _luminance(r: int, g: int, b: int) -> float:
        def _lin(c: int) -> float:
            v = c / 255.0
            return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)

    @staticmethod
    def _contrast(l1: float, l2: float) -> float:
        lighter, darker = (l1, l2) if l1 >= l2 else (l2, l1)
        return (lighter + 0.05) / (darker + 0.05)

    # ------------------------------------------------------------------
    # Check: form fields without labels (WCAG 4.1.2)
    # ------------------------------------------------------------------

    def _check_form_fields(self) -> None:
        for page_num in range(self.doc.page_count):
            page = self.doc[page_num]
            try:
                for widget in page.widgets():
                    name = (widget.field_name or "").strip()
                    label = (getattr(widget, "field_label", None) or "").strip()
                    tooltip = (getattr(widget, "field_tooltip", None) or "").strip()
                    if not name and not label and not tooltip:
                        self._add(
                            wcag_criterion="4.1.2",
                            severity="critical",
                            page=page_num + 1,
                            title="Form Field Missing Accessible Name",
                            description=(
                                f"A form field on page {page_num + 1} has no name, "
                                "label, or tooltip. Screen reader users cannot "
                                "determine the field's purpose."
                            ),
                            remediation=(
                                "In Acrobat Pro, right-click the field ▸ Properties "
                                "▸ General ▸ Tooltip and add a descriptive label."
                            ),
                            auto_fixable=False,
                            rect=list(widget.rect),
                            element_info={
                                "type": "form_field",
                                "field_type": str(widget.field_type),
                                "page": page_num + 1,
                            },
                        )
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Check: links with non-descriptive text (WCAG 2.4.4)
    # ------------------------------------------------------------------

    _GENERIC_LINK_TEXTS = frozenset(
        {
            "click here", "here", "read more", "more", "link", "click",
            "this", "see here", "go", "see more", "find out more", "learn more",
            "details", "info", "information", "view", "open", "download",
        }
    )

    def _check_links(self) -> None:
        for page_num in range(self.doc.page_count):
            page = self.doc[page_num]
            for link in page.get_links():
                uri = link.get("uri") or link.get("page")
                if uri is None:
                    continue
                link_rect = fitz.Rect(link["from"])
                link_text = self._text_in_rect(page, link_rect).strip()
                normalised = link_text.lower()
                if normalised in self._GENERIC_LINK_TEXTS or not normalised:
                    self._add(
                        wcag_criterion="2.4.4",
                        severity="moderate",
                        page=page_num + 1,
                        title="Non-descriptive Link Text",
                        description=(
                            f"A link on page {page_num + 1} uses the text "
                            f'"{link_text or "(no text)"}", which does not '
                            "describe its destination or purpose."
                        ),
                        remediation=(
                            "Replace the link text with a description of the "
                            "link destination (e.g., 'Download the 2024 Annual Report')."
                        ),
                        auto_fixable=False,
                        rect=list(link["from"]),
                        element_info={
                            "type": "link",
                            "text": link_text,
                            "uri": str(uri),
                            "page": page_num + 1,
                        },
                    )

    def _text_in_rect(self, page: fitz.Page, rect: fitz.Rect) -> str:
        expanded = rect + (-3, -3, 3, 3)
        words = page.get_text("words")
        return " ".join(w[4] for w in words if fitz.Rect(w[:4]).intersects(expanded))

    # ------------------------------------------------------------------
    # Check: heading structure (WCAG 1.3.1 / 2.4.6)
    # ------------------------------------------------------------------

    def _check_heading_structure(self) -> None:
        if not self._is_tagged():
            return  # Already reported as untagged

        if self.doc.page_count < 2:
            return  # Single-page docs may legitimately have no headings

        has_headings = False
        try:
            for xref in range(1, min(self.doc.xref_length(), 2000)):
                try:
                    s = self.doc.xref_get_key(xref, "S")
                    if s and any(
                        tag in s for tag in ["/H1", "/H2", "/H3", "/H4", "/H5", "/H6", "/H"]
                    ):
                        has_headings = True
                        break
                except Exception:
                    continue
        except Exception:
            pass

        if not has_headings:
            self._add(
                wcag_criterion="2.4.6",
                severity="moderate",
                page=0,
                title="No Heading Structure Detected",
                description=(
                    "The document does not appear to use heading tags (H1–H6). "
                    "Headings give structure that helps screen reader users "
                    "navigate and understand document organisation."
                ),
                remediation=(
                    "Apply heading styles in the source document (Word, InDesign) "
                    "before exporting to PDF, or use Acrobat Pro's Reading Order "
                    "tool to assign heading tags."
                ),
                auto_fixable=False,
                element_info={"type": "document_structure", "has_headings": False},
            )

    # ------------------------------------------------------------------
    # Check: tab order (WCAG 1.3.2)
    # ------------------------------------------------------------------

    def _check_tab_order(self) -> None:
        """Flag pages where the tab order does not follow the structure order."""
        if not self._is_tagged():
            return
        try:
            for page_num in range(self.doc.page_count):
                page = self.doc[page_num]
                page_xref = page.xref
                tab_order = self._xref_val(self.doc.xref_get_key(page_xref, "Tabs"))
                # "S" means structure order — correct for tagged PDFs
                if tab_order and tab_order not in ("", "null", "/S"):
                    self._add(
                        wcag_criterion="1.3.2",
                        severity="moderate",
                        page=page_num + 1,
                        title="Tab Order Does Not Follow Structure",
                        description=(
                            f"Page {page_num + 1} has a tab order setting of "
                            f'"{tab_order}" instead of "/S" (structure order). '
                            "This may cause form fields or links to receive focus "
                            "in the wrong order for keyboard users."
                        ),
                        remediation=(
                            "In Acrobat Pro, open Page Properties and set the "
                            "Tab Order to 'Use Document Structure'."
                        ),
                        auto_fixable=False,
                        element_info={
                            "type": "tab_order",
                            "tab_order": tab_order,
                            "page": page_num + 1,
                        },
                    )
        except Exception:
            pass
