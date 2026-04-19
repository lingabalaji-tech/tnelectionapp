window.SITE_META = {"generated_on": "2026-04-19 13:27 UTC", "relativePrefix": "../"};
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
