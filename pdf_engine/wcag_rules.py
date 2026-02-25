"""WCAG 2.1 AA rule definitions used by the PDF Accessibility Engine."""

WCAG_RULES: dict = {
    "1.1.1": {
        "title": "Non-text Content",
        "level": "A",
        "category": "Perceivable",
        "description": (
            "All non-text content presented to the user has a text alternative "
            "that serves the equivalent purpose."
        ),
        "pdf_guidance": (
            "Images must have Alt text set in the PDF structure tree. "
            "Purely decorative images should be marked as artifacts."
        ),
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/non-text-content",
    },
    "1.3.1": {
        "title": "Info and Relationships",
        "level": "A",
        "category": "Perceivable",
        "description": (
            "Information, structure, and relationships conveyed through presentation "
            "can be programmatically determined or are available in text."
        ),
        "pdf_guidance": (
            "The PDF must be tagged. Headings, lists, tables, and other structural "
            "elements must use the correct PDF tag types (H1–H6, L, Table, etc.)."
        ),
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/info-and-relationships",
    },
    "1.3.2": {
        "title": "Meaningful Sequence",
        "level": "A",
        "category": "Perceivable",
        "description": (
            "If the sequence in which content is presented affects its meaning, "
            "a correct reading sequence can be programmatically determined."
        ),
        "pdf_guidance": (
            "The tag reading order in the structure tree must match the logical "
            "reading order of the document."
        ),
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/meaningful-sequence",
    },
    "1.4.3": {
        "title": "Contrast (Minimum)",
        "level": "AA",
        "category": "Perceivable",
        "description": (
            "The visual presentation of text has a contrast ratio of at least 4.5:1. "
            "Large text (18 pt or 14 pt bold) requires at least 3:1."
        ),
        "pdf_guidance": (
            "Ensure text colours have sufficient contrast against their background. "
            "Use tools such as the Colour Contrast Analyser to verify."
        ),
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum",
    },
    "2.4.2": {
        "title": "Page Titled",
        "level": "A",
        "category": "Navigable",
        "description": "Web pages and documents have titles that describe topic or purpose.",
        "pdf_guidance": (
            "Set a descriptive title in File > Properties > Description > Title."
        ),
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/page-titled",
    },
    "2.4.4": {
        "title": "Link Purpose (In Context)",
        "level": "A",
        "category": "Navigable",
        "description": (
            "The purpose of each link can be determined from the link text alone, "
            "or from the link text together with its programmatically determined context."
        ),
        "pdf_guidance": (
            "Avoid generic link text such as 'click here', 'here', or bare URLs. "
            "Use descriptive text that explains the link destination."
        ),
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/link-purpose-in-context",
    },
    "2.4.5": {
        "title": "Multiple Ways",
        "level": "AA",
        "category": "Navigable",
        "description": (
            "More than one way is available to locate content within a set of pages."
        ),
        "pdf_guidance": (
            "Multi-page PDFs should have a bookmarks panel (table of contents) "
            "so users can navigate directly to sections."
        ),
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/multiple-ways",
    },
    "2.4.6": {
        "title": "Headings and Labels",
        "level": "AA",
        "category": "Navigable",
        "description": "Headings and labels describe topic or purpose.",
        "pdf_guidance": (
            "Use H1–H6 tags in the structure tree for headings, and TH tags for "
            "table header cells."
        ),
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/headings-and-labels",
    },
    "3.1.1": {
        "title": "Language of Page",
        "level": "A",
        "category": "Understandable",
        "description": (
            "The default human language of each page can be programmatically determined."
        ),
        "pdf_guidance": (
            "Set the document language in File > Properties > Advanced > Language, "
            "or via the PDF catalog /Lang entry (e.g. 'en-US')."
        ),
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/language-of-page",
    },
    "4.1.2": {
        "title": "Name, Role, Value",
        "level": "A",
        "category": "Robust",
        "description": (
            "For all user interface components, the name and role can be programmatically "
            "determined; states, properties, and values that can be set by the user can be "
            "programmatically set; and notification of changes is available to user agents."
        ),
        "pdf_guidance": (
            "All interactive form fields must have an accessible name (tooltip or label). "
            "Use the field's tooltip/alternate description property."
        ),
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/name-role-value",
    },
}

# Severity weights used for accessibility score calculation
SEVERITY_WEIGHTS = {
    "critical": 20,
    "serious": 12,
    "moderate": 6,
    "minor": 2,
}

# Ordered list of all criteria included in the score
SCORED_CRITERIA = list(WCAG_RULES.keys())
