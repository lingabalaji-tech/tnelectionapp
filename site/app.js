window.SITE_META = {"generated_on": "2026-04-20 17:47 UTC", "relativePrefix": "../"};
function toggleLanguage() {
  const current = document.body.dataset.lang === "ta" ? "ta" : "en";
  const next = current === "en" ? "ta" : "en";
  document.body.dataset.lang = next;
  window.localStorage.setItem("tn2026_lang", next);
}
(function initLanguage() {
  const saved = window.localStorage.getItem("tn2026_lang");
  if (saved === "ta" || saved === "en") {
    document.body.dataset.lang = saved;
  }
})();

async function loadJson(path) {
  const response = await fetch(path);
  return response.json();
}

function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "—";
  return new Intl.NumberFormat("en-IN").format(Number(value));
}

function formatCurrency(value) {
  if (value === null || value === undefined || value === "") return "—";
  return "₹" + new Intl.NumberFormat("en-IN").format(Math.round(Number(value)));
}

function csvEscape(value) {
  const text = value === null || value === undefined ? "" : String(value);
  return /[",\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
}

function downloadBlob(filename, blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function loadStylesheetText(relativePrefix) {
  const fromDom = Array.from(document.styleSheets || []).map((sheet) => {
    try {
      return Array.from(sheet.cssRules || []).map((rule) => rule.cssText).join("\n");
    } catch (error) {
      return "";
    }
  }).filter(Boolean).join("\n");
  if (fromDom) return fromDom;
  try {
    const response = await fetch((relativePrefix || "") + "styles.css");
    return await response.text();
  } catch (error) {
    return "";
  }
}

function xmlEscape(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function drawRoundedRect(ctx, x, y, width, height, radius) {
  const safeRadius = Math.max(0, Math.min(radius || 0, width / 2, height / 2));
  if (typeof ctx.roundRect === "function") {
    ctx.beginPath();
    ctx.roundRect(x, y, width, height, safeRadius);
    return;
  }
  ctx.beginPath();
  ctx.moveTo(x + safeRadius, y);
  ctx.lineTo(x + width - safeRadius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + safeRadius);
  ctx.lineTo(x + width, y + height - safeRadius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - safeRadius, y + height);
  ctx.lineTo(x + safeRadius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - safeRadius);
  ctx.lineTo(x, y + safeRadius);
  ctx.quadraticCurveTo(x, y, x + safeRadius, y);
}

async function buildSnapshotBlob(target, options) {
  const summaryCards = Array.from(target.querySelectorAll(".meta .card")).map((card) => {
    const label = (card.querySelector(".meta-label .lang-en") || card.querySelector(".meta-label"))?.textContent?.trim() || "";
    const value = (card.querySelector(".meta-value")?.textContent || "").trim();
    return { label, value };
  }).filter((card) => card.label || card.value).slice(0, 4);
  const rows = Array.isArray(options.rows) ? options.rows : [];
  const title = options.snapshotTitle || (options.constituencyName ? `${options.constituencyName} (${options.constituencyNo || ""})` : "Candidate roster");
  const subtitle = [options.district, `${rows.length} visible candidates`].filter(Boolean).join(" • ");
  const topPartyText = target.querySelector(".notice .lang-en")?.textContent?.trim() || target.querySelector(".notice")?.textContent?.trim() || "";
  const columnDefs = [
    { key: "candidate_name", label: "Candidate", width: 280 },
    { key: "party_name", label: "Party", width: 250 },
    { key: "gender", label: "Gender", width: 100 },
    { key: "age", label: "Age", width: 80 },
    { key: "assets", label: "Assets", width: 180 },
    { key: "cases_flag", label: "Cases", width: 90 },
  ];
  const width = 1180;
  const padding = 36;
  const innerWidth = width - (padding * 2);
  const contentFont = "16px Arial, sans-serif";
  const smallFont = "13px Arial, sans-serif";
  const labelFont = "600 13px Arial, sans-serif";
  const titleFont = "700 34px Arial, sans-serif";
  const subtitleFont = "16px Arial, sans-serif";
  const rowLineHeight = 22;
  const rowVerticalPadding = 12;
  const cardGap = 14;
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas not supported");

  function wrapText(text, maxWidth, font) {
    const safeText = String(text || "—").replace(/\s+/g, " ").trim() || "—";
    ctx.font = font;
    const words = safeText.split(" ");
    const lines = [];
    let current = "";
    words.forEach((word) => {
      const next = current ? `${current} ${word}` : word;
      if (ctx.measureText(next).width <= maxWidth || !current) {
        current = next;
      } else {
        lines.push(current);
        current = word;
      }
    });
    if (current) lines.push(current);
    return lines.length ? lines : ["—"];
  }

  const preparedRows = rows.map((row) => {
    const cells = columnDefs.map((column) => wrapText(row[column.key] || "—", column.width - 18, contentFont));
    const lineCount = Math.max(...cells.map((lines) => lines.length), 1);
    const rowHeight = (lineCount * rowLineHeight) + (rowVerticalPadding * 2);
    return { row, cells, rowHeight };
  });

  const summaryCardWidth = Math.floor((innerWidth - cardGap) / 2);
  const summaryCardHeight = 74;
  const summaryRows = summaryCards.length ? Math.ceil(summaryCards.length / 2) : 0;
  const summaryHeight = summaryRows ? (summaryRows * summaryCardHeight) + ((summaryRows - 1) * cardGap) : 0;
  const topPartyLines = topPartyText ? wrapText(topPartyText, innerWidth - 28, smallFont) : [];
  const topPartyHeight = topPartyLines.length ? 30 + (topPartyLines.length * 18) : 0;
  const tableHeaderHeight = 44;
  const tableHeight = preparedRows.reduce((total, item) => total + item.rowHeight, 0);
  const height = padding + 54 + 28 + (subtitle ? 26 : 0) + (summaryHeight ? summaryHeight + 24 : 0) + (topPartyHeight ? topPartyHeight + 20 : 0) + tableHeaderHeight + tableHeight + 36;
  const scale = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.ceil(width * scale);
  canvas.height = Math.ceil(height * scale);
  ctx.scale(scale, scale);
  ctx.fillStyle = "#f5efe3";
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = "#fffaf1";
  ctx.strokeStyle = "#e7d7c2";
  ctx.lineWidth = 2;
  drawRoundedRect(ctx, 20, 20, width - 40, height - 40, 24);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "#9a3412";
  ctx.fillRect(32, 32, width - 64, 10);

  let cursorY = padding + 10;
  ctx.fillStyle = "#9a3412";
  ctx.font = titleFont;
  ctx.fillText(title, padding, cursorY + 24);
  cursorY += 48;
  if (subtitle) {
    ctx.fillStyle = "#475569";
    ctx.font = subtitleFont;
    ctx.fillText(subtitle, padding, cursorY);
    cursorY += 28;
  }

  if (summaryHeight) {
    summaryCards.forEach((card, index) => {
      const column = index % 2;
      const rowIndex = Math.floor(index / 2);
      const x = padding + (column * (summaryCardWidth + cardGap));
      const y = cursorY + (rowIndex * (summaryCardHeight + cardGap));
      ctx.fillStyle = "#ffffff";
      ctx.strokeStyle = "#e7d7c2";
      ctx.lineWidth = 1.5;
      drawRoundedRect(ctx, x, y, summaryCardWidth, summaryCardHeight, 18);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = "#64748b";
      ctx.font = labelFont;
      ctx.fillText(card.label || "Summary", x + 18, y + 26);
      ctx.fillStyle = "#1f2933";
      ctx.font = "700 20px Arial, sans-serif";
      ctx.fillText(card.value || "—", x + 18, y + 54);
    });
    cursorY += summaryHeight + 24;
  }

  if (topPartyHeight) {
    ctx.fillStyle = "#fff7ed";
    ctx.strokeStyle = "#fdba74";
    drawRoundedRect(ctx, padding, cursorY, innerWidth, topPartyHeight, 18);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = "#9a3412";
    ctx.font = labelFont;
    ctx.fillText("Top parties", padding + 16, cursorY + 22);
    ctx.fillStyle = "#7c2d12";
    ctx.font = smallFont;
    topPartyLines.forEach((line, lineIndex) => {
      ctx.fillText(line, padding + 16, cursorY + 44 + (lineIndex * 18));
    });
    cursorY += topPartyHeight + 20;
  }

  let currentX = padding;
  ctx.fillStyle = "#f1f5f9";
  ctx.strokeStyle = "#d7dde5";
  drawRoundedRect(ctx, padding, cursorY, innerWidth, tableHeaderHeight, 14);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "#334155";
  ctx.font = labelFont;
  columnDefs.forEach((column) => {
    ctx.fillText(column.label, currentX + 10, cursorY + 27);
    currentX += column.width;
  });
  cursorY += tableHeaderHeight;

  preparedRows.forEach((item, rowIndex) => {
    ctx.fillStyle = rowIndex % 2 === 0 ? "#fffaf1" : "#ffffff";
    ctx.fillRect(padding, cursorY, innerWidth, item.rowHeight);
    ctx.strokeStyle = "#e7d7c2";
    ctx.beginPath();
    ctx.moveTo(padding, cursorY + item.rowHeight);
    ctx.lineTo(padding + innerWidth, cursorY + item.rowHeight);
    ctx.stroke();
    let cellX = padding;
    item.cells.forEach((lines, columnIndex) => {
      ctx.fillStyle = "#1f2933";
      ctx.font = contentFont;
      lines.forEach((line, lineIndex) => {
        ctx.fillText(line, cellX + 10, cursorY + rowVerticalPadding + 16 + (lineIndex * rowLineHeight));
      });
      cellX += columnDefs[columnIndex].width;
    });
    cursorY += item.rowHeight;
  });

  return await new Promise((resolve, reject) => {
    canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error("PNG generation failed")), "image/png");
  });
}

function setRosterFeedback(element, html, isError) {
  if (!element) return;
  element.innerHTML = html || "";
  element.classList.toggle("error", !!isError);
}

window.initConstituencyRosterPage = function initConstituencyRosterPage(config) {
  const searchInput = document.getElementById(config.searchInputId);
  const exportButton = document.getElementById(config.exportButtonId);
  const shareButton = document.getElementById(config.shareButtonId);
  const feedback = document.getElementById(config.feedbackId);
  const shareRoot = document.getElementById(config.shareRootId);
  const rows = Array.from(document.querySelectorAll(config.rowSelector));
  if (shareRoot && shareRoot.dataset.rosterInit === "done") return;

  const visibleRows = () => rows.filter((row) => row.style.display !== "none");
  const rowPayload = (row) => ({
    candidate_name: row.dataset.candidateName || "",
    party_name: row.dataset.partyName || "",
    gender: row.dataset.gender || "",
    age: row.dataset.age || "",
    assets: row.dataset.assets || "",
    cases_flag: row.dataset.cases || "",
    affidavit_url: row.dataset.affidavitUrl || "",
    constituency_name: config.constituencyName || "",
    constituency_no: String(config.constituencyNo || ""),
    district: config.district || "",
  });

  function updateActionState() {
    const hasRows = visibleRows().length > 0;
    if (exportButton) exportButton.disabled = !hasRows;
    if (shareButton) shareButton.disabled = !hasRows;
    if (!hasRows) {
      feedback.dataset.state = "empty";
      setRosterFeedback(feedback, config.messages.noRows, true);
    } else if (feedback && feedback.dataset.state === "empty") {
      feedback.dataset.state = "";
      setRosterFeedback(feedback, "", false);
    }
  }

  function filterRows() {
    const query = (searchInput?.value || "").toLowerCase().trim();
    rows.forEach((row) => {
      row.style.display = !query || row.dataset.search.includes(query) ? "" : "none";
    });
    updateActionState();
  }

  async function handleCsvExport() {
    const data = visibleRows().map(rowPayload);
    if (!data.length) {
      feedback.dataset.state = "empty";
      setRosterFeedback(feedback, config.messages.noRows, true);
      return;
    }
    const header = ["candidate_name","party_name","gender","age","assets","cases_flag","affidavit_url","constituency_name","constituency_no","district"];
    const lines = [
      header.join(","),
      ...data.map((record) => header.map((key) => csvEscape(record[key])).join(",")),
    ];
    const blob = new Blob(["\ufeff" + lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
    downloadBlob(config.csvFilename, blob);
    setRosterFeedback(feedback, config.messages.csvReady, false);
  }

  async function handleShare() {
    if (!shareRoot) return;
    if (!visibleRows().length) {
      feedback.dataset.state = "empty";
      setRosterFeedback(feedback, config.messages.noRows, true);
      return;
    }
    try {
      setRosterFeedback(feedback, config.messages.sharePreparing, false);
      const blob = await buildSnapshotBlob(shareRoot, {
        relativePrefix: config.relativePrefix,
        snapshotTitle: config.shareTitle,
        constituencyName: config.constituencyName,
        constituencyNo: config.constituencyNo,
        district: config.district,
        rows: visibleRows().map(rowPayload),
      });
      const file = typeof File === "function" ? new File([blob], config.imageFilename, { type: "image/png" }) : null;
      if (file && navigator.share && navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({
          files: [file],
          title: config.shareTitle,
          text: config.shareText,
        });
        setRosterFeedback(feedback, config.messages.shareDone, false);
        return;
      }
      downloadBlob(config.imageFilename, blob);
      setRosterFeedback(feedback, config.messages.shareFallback, false);
    } catch (error) {
      console.error(error);
      setRosterFeedback(feedback, config.messages.shareError, true);
    }
  }

  searchInput?.addEventListener("input", filterRows);
  exportButton?.addEventListener("click", handleCsvExport);
  shareButton?.addEventListener("click", handleShare);
  updateActionState();
  if (shareRoot) shareRoot.dataset.rosterInit = "done";
};

function autoInitRosterPages() {
  const configNodes = Array.from(document.querySelectorAll('script[type="application/json"][id^="roster-config-"]'));
  configNodes.forEach((configNode) => {
    try {
      const config = JSON.parse(configNode.textContent || "{}");
      if (config && typeof window.initConstituencyRosterPage === "function") {
        window.initConstituencyRosterPage(config);
      }
    } catch (error) {
      console.error("Unable to initialize roster page", error);
    }
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", autoInitRosterPages, { once: true });
} else {
  autoInitRosterPages();
}
