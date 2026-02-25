# PDF Accessibility Remediation Agent

A web-based tool that audits PDF documents for **WCAG 2.1 AA** accessibility compliance and helps remediate the issues it finds. Upload a PDF, receive an interactive report with an accessibility score, and apply fixes directly from the browser.

---

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [How to Audit a PDF for WCAG 2.1 AA Compliance](#how-to-audit-a-pdf-for-wcag-21-aa-compliance)
- [Understanding the Accessibility Report](#understanding-the-accessibility-report)
- [How to Remediate Accessibility Issues](#how-to-remediate-accessibility-issues)
- [WCAG 2.1 AA Checks Performed](#wcag-21-aa-checks-performed)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)

---

## Features

- **Automated WCAG 2.1 AA audit** — analyses PDFs against 10 accessibility criteria.
- **Accessibility score** — a 0–100 score based on severity-weighted deductions.
- **Interactive report** — split-panel view with a rendered PDF preview and a filterable issue list.
- **Issue highlighting** — visual overlays pinpoint exactly where problems appear on each page.
- **In-browser remediation** — fix document title and language metadata without leaving the app.
- **Detailed guidance** — every issue includes a description, remediation steps, and a link to the relevant WCAG Understanding document.
- **Download remediated PDF** — download the updated file after applying fixes.

---

## Prerequisites

- **Python 3.9** or later
- **pip** (Python package manager)

---

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/balajialg/PDF-remediation-agent.git
   cd PDF-remediation-agent
   ```

2. **Create and activate a virtual environment (recommended):**

   ```bash
   python -m venv venv
   source venv/bin/activate        # macOS / Linux
   # venv\Scripts\activate          # Windows
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

---

## Running the Application

Start the Flask development server:

```bash
python app.py
```

The application starts on **http://localhost:5000**. Open this URL in your browser to begin.

> **Tip:** Set the `SECRET_KEY` environment variable for a stable session secret:
>
> ```bash
> SECRET_KEY=my-secret-key python app.py
> ```

---

## How to Audit a PDF for WCAG 2.1 AA Compliance

Follow these steps to evaluate a PDF against WCAG 2.1 AA guidelines:

### Step 1 — Open the Application

Navigate to **http://localhost:5000** in your browser. You will see the **PDF Accessibility Engine** upload page.

### Step 2 — Upload Your PDF

- **Drag and drop** your PDF file onto the drop zone, or
- Click **Browse Files** and select a PDF from your file system.

The selected file name appears below the drop zone.

### Step 3 — Start the Audit

Click the **Evaluate Accessibility** button. The tool analyses the PDF against all 10 WCAG 2.1 AA checks and redirects you to an interactive report.

### Step 4 — Review the Report

The report page has two panels:

| Panel | Description |
|-------|-------------|
| **Left — PDF Viewer** | A rendered preview of each page. Use the **Previous / Next** buttons to navigate. Toggle **Highlights** to show or hide coloured overlays marking issue locations. |
| **Right — Issues List** | Every accessibility issue found, grouped by severity. Use the severity and page drop-downs to filter the list. |

At the top of the page you will see:

- **Accessibility Score** (0–100) — higher is better.
- **Issue counts** broken down by severity (Critical, Serious, Moderate, Minor).
- **Download PDF** and **New Upload** buttons.

### Step 5 — Inspect Individual Issues

Click the **expand** button (▾) on any issue card to see:

- A detailed **description** of the problem and why it matters.
- A **How to fix** section with step-by-step remediation instructions.
- A link to the official **WCAG Understanding** document for the criterion.
- An **auto-fix form** (for issues that can be fixed directly in the app).

---

## Understanding the Accessibility Report

### Accessibility Score

The score starts at 100. Points are deducted for each failing WCAG criterion based on the highest severity of its issues:

| Severity | Point Deduction |
|----------|-----------------|
| Critical | −20 |
| Serious | −12 |
| Moderate | −6 |
| Minor | −2 |

A score of **80–100** is considered good, **50–79** needs attention, and **below 50** indicates significant accessibility barriers.

### Severity Levels

| Severity | Meaning |
|----------|---------|
| **Critical** | Prevents assistive technology users from accessing content (e.g., untagged PDF, unlabelled form fields). |
| **Serious** | Significantly hinders accessibility (e.g., missing document title, missing alt text on images). |
| **Moderate** | Creates barriers but content is still partially accessible (e.g., no bookmarks, poor colour contrast). |
| **Minor** | Minor inconvenience that does not block access. |

---

## How to Remediate Accessibility Issues

### Auto-Fixable Issues (In-Browser)

The tool can automatically fix two common metadata issues directly from the report:

#### Fix Missing Document Title

1. In the issues list, expand the **Missing Document Title** issue card.
2. Type a descriptive title into the text field (e.g., *"2024 Annual Accessibility Report"*).
3. Click the **Fix** button.
4. The score updates immediately and the issue is removed from the list.

#### Fix Missing Document Language

1. In the issues list, expand the **Missing Document Language** issue card.
2. Select the document's primary language from the drop-down (e.g., *English (US)*).
3. Click the **Fix** button.
4. The score updates immediately and the issue is removed from the list.

After applying fixes, click **Download PDF** in the top bar to save the remediated file.

### Manual Remediation (External Tools)

Issues that cannot be auto-fixed require changes in the source document or in a PDF editor such as Adobe Acrobat Pro. The table below lists each check and how to fix it:

| Issue | How to Fix |
|-------|------------|
| **PDF is Not Tagged** | Re-export the source document (Word, InDesign, Google Docs) with accessibility or tagging enabled. Alternatively, use Adobe Acrobat Pro's *Accessibility Checker* to add tags automatically. |
| **No Bookmarks / Navigation** | In the source application, ensure headings are mapped to bookmarks on export. In Acrobat Pro, use *Tools ▸ Edit PDF ▸ More ▸ Add Bookmarks*. |
| **Image Missing Alternative Text** | In Acrobat Pro, open the *Reading Order* tool, select the image, and add alt text. In the source document, right-click the image and set alternative text before exporting. Mark purely decorative images as artifacts. |
| **Insufficient Colour Contrast** | Change the text or background colour in the source document so the contrast ratio meets 4.5:1 for normal text or 3:1 for large text (18 pt+, or 14 pt bold+). Use a contrast checker tool to verify. |
| **Form Field Missing Accessible Name** | In Acrobat Pro, right-click the form field ▸ *Properties* ▸ *General* ▸ *Tooltip* and add a descriptive label. |
| **Non-descriptive Link Text** | Replace generic link text such as *"click here"* or *"read more"* with descriptive text that explains the link's destination (e.g., *"Download the 2024 Annual Report"*). |
| **No Heading Structure Detected** | Apply heading styles (Heading 1–6) in the source document before exporting to PDF. In Acrobat Pro, use the *Reading Order* tool to assign heading tags. |
| **Tab Order Does Not Follow Structure** | In Acrobat Pro, open *Page Properties* and set the Tab Order to *"Use Document Structure"*. |

### Recommended Remediation Workflow

1. **Run the audit** to identify all issues.
2. **Apply auto-fixes first** (title and language) using the in-browser forms.
3. **Download the partially fixed PDF**.
4. **Open the PDF in Adobe Acrobat Pro** (or your preferred PDF editor) to address the remaining issues.
5. **Re-upload the updated PDF** to this tool to verify that the fixes resolved the issues.
6. **Repeat** until the accessibility score reaches your target (ideally 100).

---

## WCAG 2.1 AA Checks Performed

| # | WCAG Criterion | Title | Level | What Is Checked |
|---|---------------|-------|-------|-----------------|
| 1 | 1.1.1 | Non-text Content | A | Images have alternative text in the PDF structure tree. |
| 2 | 1.3.1 | Info and Relationships | A | The PDF is tagged with a structure tree (headings, paragraphs, lists, tables). |
| 3 | 1.3.2 | Meaningful Sequence | A | Tab order on each page follows the document structure order. |
| 4 | 1.4.3 | Contrast (Minimum) | AA | Text has a contrast ratio of at least 4.5:1 (3:1 for large text) against its background. |
| 5 | 2.4.2 | Page Titled | A | The PDF has a descriptive title in its metadata. |
| 6 | 2.4.4 | Link Purpose (In Context) | A | Link text is descriptive (not generic like "click here"). |
| 7 | 2.4.5 | Multiple Ways | AA | Multi-page PDFs have bookmarks for navigation. |
| 8 | 2.4.6 | Headings and Labels | AA | The document uses heading tags (H1–H6) for structure. |
| 9 | 3.1.1 | Language of Page | A | The document language is set in the PDF catalog. |
| 10 | 4.1.2 | Name, Role, Value | A | Form fields have accessible names (tooltips or labels). |

---

## API Reference

The application exposes the following HTTP endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Upload page. |
| `POST` | `/analyze` | Upload and analyse a PDF. Accepts `multipart/form-data` with a `file` field. Redirects to the report page. |
| `GET` | `/report/<session_id>` | Interactive accessibility report for a previously analysed PDF. |
| `GET` | `/page/<session_id>/<page_num>` | Rendered PNG image of a PDF page (0-based page number). |
| `POST` | `/remediate/<session_id>` | Apply an auto-fix. Send JSON with `action` (`fix_title` or `fix_language`) and the corresponding value (`title` or `language`). Returns updated score and issues. |
| `GET` | `/download/<session_id>` | Download the (possibly remediated) PDF. |

### Example: Fix Title via API

```bash
curl -X POST http://localhost:5000/remediate/<session_id> \
  -H "Content-Type: application/json" \
  -d '{"action": "fix_title", "title": "My Accessible Document"}'
```

### Example: Fix Language via API

```bash
curl -X POST http://localhost:5000/remediate/<session_id> \
  -H "Content-Type: application/json" \
  -d '{"action": "fix_language", "language": "en-US"}'
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **"No file part in the request"** error | Make sure the file input field is named `file` in your upload form or API call. |
| **"Please upload a valid PDF file"** error | Only `.pdf` files are accepted. Verify the file extension. |
| **Session not found** after navigating to a report | Sessions are stored in memory and are lost when the server restarts. Re-upload the PDF. |
| **Port 5000 already in use** | Stop the other process using port 5000, or start the app on a different port: `flask run --port 8080`. |
| **ModuleNotFoundError** on startup | Ensure you have activated your virtual environment and installed dependencies with `pip install -r requirements.txt`. |

---

## Running Tests

```bash
pytest tests/
```

---

## License

See the [LICENSE](LICENSE) file for details.
