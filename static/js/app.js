/* PDF Accessibility Engine — frontend JavaScript */
"use strict";

// ---------------------------------------------------------------------------
// Upload page helpers
// ---------------------------------------------------------------------------
(function initUploadPage() {
  const form      = document.getElementById("upload-form");
  if (!form) return;

  const dropZone  = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const fileInfo  = document.getElementById("file-info");
  const fileName  = document.getElementById("file-name");
  const submitBtn = document.getElementById("submit-btn");
  const spinner   = document.getElementById("submit-spinner");
  const submitIcon = document.getElementById("submit-icon");

  function updateSelectedFile(file) {
    if (!file) return;
    fileName.textContent = file.name;
    fileInfo.classList.remove("d-none");
    submitBtn.removeAttribute("disabled");
  }

  // Drag & drop
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (file && file.type === "application/pdf") {
      const dt = new DataTransfer();
      dt.items.add(file);
      fileInput.files = dt.files;
      updateSelectedFile(file);
    }
  });

  // Click on drop zone => open file picker
  dropZone.addEventListener("click", (e) => {
    if (e.target !== fileInput) fileInput.click();
  });
  dropZone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) updateSelectedFile(fileInput.files[0]);
  });

  // Show spinner on submit
  form.addEventListener("submit", () => {
    submitBtn.setAttribute("disabled", "");
    spinner.classList.remove("d-none");
    submitIcon.classList.add("d-none");
  });
})();

// ---------------------------------------------------------------------------
// Report page helpers
// ---------------------------------------------------------------------------
(function initReportPage() {
  const dataEl = document.getElementById("report-data");
  if (!dataEl) return;

  const { sessionId, pageCount, pageDims, issues, score } = JSON.parse(dataEl.textContent);

  // -- DOM refs
  const pageImage      = document.getElementById("page-image");
  const overlayCanvas  = document.getElementById("overlay-canvas");
  const pageWrapper    = document.getElementById("page-wrapper");
  const btnPrev        = document.getElementById("btn-prev");
  const btnNext        = document.getElementById("btn-next");
  const currentPageEl  = document.getElementById("current-page");
  const toggleHL       = document.getElementById("toggle-highlights");
  const filterSev      = document.getElementById("filter-severity");
  const filterPage     = document.getElementById("filter-page");
  const issueCountEl   = document.getElementById("issue-count");
  const issueList      = document.getElementById("issue-list");

  let currentPage = 0;       // 0-based
  let showHighlights = true;

  // ---------------------------------------------------------------------------
  // Page navigation
  // ---------------------------------------------------------------------------
  function loadPage(pageNum) {
    currentPage = pageNum;
    pageImage.alt = `Page ${pageNum + 1}`;
    pageImage.src = `/page/${sessionId}/${pageNum}`;
    currentPageEl.textContent = pageNum + 1;
    btnPrev.disabled = pageNum === 0;
    btnNext.disabled = pageNum >= pageCount - 1;

    pageImage.onload = () => drawOverlay();
  }

  btnPrev.addEventListener("click", () => { if (currentPage > 0) loadPage(currentPage - 1); });
  btnNext.addEventListener("click", () => { if (currentPage < pageCount - 1) loadPage(currentPage + 1); });

  // "Go to page" buttons inside issues
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".goto-page");
    if (!btn) return;
    const page = parseInt(btn.dataset.page, 10);
    if (!isNaN(page)) loadPage(page - 1);
  });

  // ---------------------------------------------------------------------------
  // Overlay drawing
  // ---------------------------------------------------------------------------
  const SEV_COLORS = {
    critical: "rgba(220,53,69,0.55)",
    serious:  "rgba(253,126,20,0.50)",
    moderate: "rgba(255,193,7,0.45)",
    minor:    "rgba(108,117,125,0.35)",
  };
  const SEV_STROKE = {
    critical: "rgba(220,53,69,0.9)",
    serious:  "rgba(253,126,20,0.9)",
    moderate: "rgba(200,150,0,0.9)",
    minor:    "rgba(108,117,125,0.8)",
  };

  function drawOverlay(activeIssueId = null) {
    if (!overlayCanvas) return;

    const imgW = pageImage.naturalWidth;
    const imgH = pageImage.naturalHeight;
    const dispW = pageImage.offsetWidth;
    const dispH = pageImage.offsetHeight;

    overlayCanvas.width  = dispW;
    overlayCanvas.height = dispH;
    overlayCanvas.style.width  = dispW + "px";
    overlayCanvas.style.height = dispH + "px";

    const ctx = overlayCanvas.getContext("2d");
    ctx.clearRect(0, 0, dispW, dispH);
    if (!showHighlights) return;

    // PDF rendered at 1.5× scale, so pixmap coords = pdf_pts × 1.5
    // Display coords = pixmap coords × (dispW / imgW)
    const pdfDim = pageDims[currentPage];
    const pxPerPt = imgW / pdfDim.width;   // pixmap pixels per PDF point
    const scale   = dispW / imgW;           // display pixels per pixmap pixel

    const pageIssues = issues.filter(
      (iss) => iss.page === currentPage + 1 && iss.rect
    );

    for (const iss of pageIssues) {
      const [x0, y0, x1, y1] = iss.rect;
      const dx0 = x0 * pxPerPt * scale;
      const dy0 = y0 * pxPerPt * scale;
      const dw  = (x1 - x0) * pxPerPt * scale;
      const dh  = (y1 - y0) * pxPerPt * scale;

      ctx.fillStyle  = SEV_COLORS[iss.severity]  || "rgba(0,0,255,0.3)";
      ctx.strokeStyle = SEV_STROKE[iss.severity] || "blue";
      ctx.lineWidth  = iss.issue_id === activeIssueId ? 3 : 1.5;
      ctx.fillRect(dx0, dy0, dw, dh);
      ctx.strokeRect(dx0, dy0, dw, dh);
    }
  }

  toggleHL.addEventListener("change", () => {
    showHighlights = toggleHL.checked;
    drawOverlay();
  });

  window.addEventListener("resize", () => drawOverlay());
  pageImage.addEventListener("load", () => drawOverlay());

  // ---------------------------------------------------------------------------
  // Filtering
  // ---------------------------------------------------------------------------
  function applyFilters() {
    const sevFilter  = filterSev.value;
    const pageFilter = filterPage.value;
    let visible = 0;

    document.querySelectorAll(".issue-card").forEach((card) => {
      const matchSev  = !sevFilter  || card.dataset.severity === sevFilter;
      const matchPage = !pageFilter || card.dataset.page === pageFilter;
      const show = matchSev && matchPage;
      card.style.display = show ? "" : "none";
      if (show) visible++;
    });

    if (issueCountEl) {
      issueCountEl.textContent = `${visible} issue${visible !== 1 ? "s" : ""}`;
    }
  }

  filterSev.addEventListener("change", applyFilters);
  filterPage.addEventListener("change", applyFilters);

  // ---------------------------------------------------------------------------
  // Highlight issue card on click / collapse
  // ---------------------------------------------------------------------------
  document.addEventListener("click", (e) => {
    const toggleBtn = e.target.closest(".toggle-details");
    if (!toggleBtn) return;
    const card = toggleBtn.closest(".issue-card");
    if (!card) return;
    const issuePage = parseInt(card.dataset.page, 10);
    if (issuePage > 0 && issuePage !== currentPage + 1) {
      loadPage(issuePage - 1);
    }
    // Highlight card
    document.querySelectorAll(".issue-card.highlighted").forEach(
      (c) => c.classList.remove("highlighted")
    );
    card.classList.add("highlighted");
    drawOverlay(card.dataset.issueId);
  });

  // ---------------------------------------------------------------------------
  // Fix forms
  // ---------------------------------------------------------------------------
  document.querySelectorAll(".fix-form").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const action = form.dataset.action;
      const submitBtn = form.querySelector("[type=submit]");
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';

      const body = { action };
      if (action === "fix_title") {
        body.title = form.querySelector("[name=title]").value.trim();
      } else if (action === "fix_language") {
        body.language = form.querySelector("[name=language]").value;
      }

      try {
        const resp = await fetch(`/remediate/${sessionId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        const data = await resp.json();

        if (data.success) {
          // Show toast
          const toastEl = document.getElementById("fix-toast");
          const toastBody = document.getElementById("fix-toast-body");
          if (toastEl && toastBody) {
            toastBody.textContent = data.message;
            const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
            toast.show();
          }
          // Reload issues list
          if (data.issues) rebuildIssueList(data.issues, data.score);
        } else {
          alert("Error: " + (data.error || "Unknown error"));
        }
      } catch (err) {
        alert("Network error: " + err.message);
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="bi bi-check-lg me-1" aria-hidden="true"></i>Fix';
      }
    });
  });

  // ---------------------------------------------------------------------------
  // Rebuild issue list after a fix (lightweight, no page reload)
  // ---------------------------------------------------------------------------
  function rebuildIssueList(newIssues, newScore) {
    // Update score badge
    const scoreBadge = document.getElementById("score-badge");
    if (scoreBadge) {
      scoreBadge.textContent = newScore;
      scoreBadge.className = "score-badge " + (
        newScore >= 80 ? "score-pass" : newScore >= 50 ? "score-warn" : "score-fail"
      );
      scoreBadge.setAttribute("aria-label", `Accessibility score: ${newScore} out of 100`);
    }

    // Fully reload the page to reflect updated issue list reliably
    window.location.reload();
  }

  // ---------------------------------------------------------------------------
  // Initial draw
  // ---------------------------------------------------------------------------
  loadPage(0);
})();
