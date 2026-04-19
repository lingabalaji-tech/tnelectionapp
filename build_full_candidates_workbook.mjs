import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const outputDir = path.join(__dirname, "outputs");
const siteDownloadsDir = path.join(__dirname, "site", "downloads");
const inputPath = path.join(outputDir, "full_candidates_2026.json");
const outputPath = path.join(outputDir, "full_candidates_2026.xlsx");
const fallbackOutputPath = path.join(outputDir, "full_candidates_2026_refreshed.xlsx");
const siteOutputPath = path.join(siteDownloadsDir, "full_candidates_2026.xlsx");
const fallbackSiteOutputPath = path.join(siteDownloadsDir, "full_candidates_2026_refreshed.xlsx");

function columnLetter(indexZeroBased) {
  let n = indexZeroBased + 1;
  let result = "";
  while (n > 0) {
    const remainder = (n - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    n = Math.floor((n - 1) / 26);
  }
  return result;
}

const rows = JSON.parse(await fs.readFile(inputPath, "utf8"));
const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Candidates 2026");
const notes = workbook.worksheets.add("Notes");

sheet.showGridLines = false;
notes.showGridLines = false;

const headers = Object.keys(rows[0]);
const matrix = [headers, ...rows.map((row) => headers.map((header) => row[header] ?? ""))];

sheet.getRange(`A1:${columnLetter(headers.length - 1)}${matrix.length}`).values = matrix;
sheet.freezePanes.freezeRows(1);

sheet.getRange(`A1:${columnLetter(headers.length - 1)}1`).format = {
  fill: "#9A3412",
  font: { bold: true, color: "#FFFFFF" },
  wrapText: true,
};
sheet.getRange(`A2:${columnLetter(headers.length - 1)}${matrix.length}`).format.wrapText = true;

for (let i = 0; i < headers.length; i += 1) {
  const letter = columnLetter(i);
  sheet.getRange(`${letter}:${letter}`).format.columnWidthPx = i < 4 ? 180 : 140;
}

sheet.tables.add(`A1:${columnLetter(headers.length - 1)}${matrix.length}`, true, "FullCandidates2026");

notes.getRange("A1:B7").values = [
  ["Tamil Nadu 2026 Full Candidate List", ""],
  ["Source", "Official district election pages listing 2026 contesting candidates"],
  ["Rows", rows.length],
  ["Coverage", "234 constituencies"],
  ["Gender note", "Gender is left blank unless present in the official source"],
  ["Symbol note", "Symbol is populated only where a stable party-level mapping was available"],
  ["Enrichment note", "Historical public facts are attached only when a deterministic 2021 match was found"],
];
notes.getRange("A1:B1").merge();
notes.getRange("A1").format = {
  fill: "#7C2D12",
  font: { bold: true, color: "#FFFFFF", size: 14 },
};
notes.getRange("A2:A7").format = {
  fill: "#FED7AA",
  font: { bold: true },
};
notes.getRange("A:B").format.columnWidthPx = 280;
notes.getRange("A1:B7").format.wrapText = true;

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(siteDownloadsDir, { recursive: true });

const inspect = await workbook.inspect({
  kind: "table",
  range: "Candidates 2026!A1:H8",
  include: "values",
  tableMaxRows: 8,
  tableMaxCols: 8,
});
console.log(inspect.ndjson);

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
let finalOutputPath = outputPath;
let finalSiteOutputPath = siteOutputPath;

try {
  await xlsx.save(outputPath);
} catch (error) {
  if (error?.code !== "EBUSY") throw error;
  finalOutputPath = fallbackOutputPath;
  finalSiteOutputPath = fallbackSiteOutputPath;
  await xlsx.save(finalOutputPath);
}

try {
  await fs.copyFile(finalOutputPath, finalSiteOutputPath);
} catch (error) {
  if (error?.code !== "EBUSY") throw error;
  finalSiteOutputPath = fallbackSiteOutputPath;
  await fs.copyFile(finalOutputPath, finalSiteOutputPath);
}

console.log(JSON.stringify({ outputPath: finalOutputPath, siteOutputPath: finalSiteOutputPath }));
