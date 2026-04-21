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

async function buildSnapshotBlob(target, options) {
  const clone = target.cloneNode(true);
  clone.classList.add("share-capture");
  clone.querySelectorAll(".roster-toolbar, .roster-feedback").forEach((node) => node.remove());
  const sandbox = document.createElement("div");
  sandbox.style.position = "fixed";
  sandbox.style.left = "-10000px";
  sandbox.style.top = "0";
  sandbox.style.width = "1200px";
  sandbox.style.pointerEvents = "none";
  sandbox.style.zIndex = "-1";
  sandbox.appendChild(clone);
  document.body.appendChild(sandbox);
  const width = Math.max(960, Math.min(1200, clone.scrollWidth || 1200));
  sandbox.style.width = width + "px";
  const height = Math.max(720, clone.scrollHeight + 32);
  const stylesText = await loadStylesheetText(options.relativePrefix || "");
  const markup = `
    <div xmlns="http://www.w3.org/1999/xhtml" style="padding:16px;background:#f5efe3;width:${width}px;">
      <style>${xmlEscape(stylesText)}</style>
      <style>.topbar,.lang-toggle,.roster-feedback,.roster-toolbar{display:none !important;} main.wrap{width:auto !important;margin:0 !important;}</style>
      ${clone.outerHTML}
    </div>
  `;
  document.body.removeChild(sandbox);
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
      <foreignObject width="100%" height="100%">${markup}</foreignObject>
    </svg>
  `;
  const svgBlob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(svgBlob);
  try {
    const image = await new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = url;
    });
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#f5efe3";
    ctx.fillRect(0, 0, width, height);
    ctx.drawImage(image, 0, 0);
    return await new Promise((resolve, reject) => {
      canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error("PNG generation failed")), "image/png");
    });
  } finally {
    URL.revokeObjectURL(url);
  }
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
      const blob = await buildSnapshotBlob(shareRoot, { relativePrefix: config.relativePrefix });
      const file = new File([blob], config.imageFilename, { type: "image/png" });
      if (navigator.share && navigator.canShare && navigator.canShare({ files: [file] })) {
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
