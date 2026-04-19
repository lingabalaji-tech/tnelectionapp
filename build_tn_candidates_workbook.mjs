import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const outputDir = path.join(__dirname, "outputs");
const outputPath = path.join(outputDir, "tamilnadu-election-candidates.xlsx");

const raw = await fs.readFile(path.join(__dirname, "tn_candidates.json"), "utf8");
const data = JSON.parse(raw);

const workbook = Workbook.create();
const candidatesSheet = workbook.worksheets.add("Candidates");
const notesSheet = workbook.worksheets.add("Notes");

candidatesSheet.showGridLines = false;
notesSheet.showGridLines = false;

const headers = [["Candidate", "Party", "Constituency", "Gender"]];
const rows = data.rows.map((row) => [
  row.candidate,
  row.party,
  row.constituency,
  row.gender,
]);

candidatesSheet.getRange(`A1:D${rows.length + 1}`).values = [...headers, ...rows];
candidatesSheet.freezePanes.freezeRows(1);

const titleRange = candidatesSheet.getRange("A1:D1");
titleRange.format = {
  fill: "#9A3412",
  font: { bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
};

candidatesSheet.getRange(`A2:D${rows.length + 1}`).format = {
  verticalAlignment: "center",
};

candidatesSheet.getRange(`A1:D${rows.length + 1}`).format.wrapText = true;
candidatesSheet.getRange(`A1:A${rows.length + 1}`).format.columnWidthPx = 240;
candidatesSheet.getRange(`B1:B${rows.length + 1}`).format.columnWidthPx = 120;
candidatesSheet.getRange(`C1:C${rows.length + 1}`).format.columnWidthPx = 190;
candidatesSheet.getRange(`D1:D${rows.length + 1}`).format.columnWidthPx = 120;

const genderSummary = [
  ["Gender", "Count"],
  ...Object.entries(
    data.rows.reduce((acc, row) => {
      acc[row.gender] = (acc[row.gender] ?? 0) + 1;
      return acc;
    }, {}),
  ),
];

notesSheet.getRange("A1:B6").values = [
  ["Tamil Nadu Assembly Election Candidates (2026)", null],
  ["Source", data.source],
  ["Rows exported", data.row_count],
  ["Coverage", "Two candidate entries per constituency from the parsed candidate table"],
  ["Gender note", "Gender is inferred from public naming patterns and should be verified before publication"],
  [null, null],
];
notesSheet.getRange("A1:B5").format.wrapText = true;
notesSheet.getRange("A1:B1").merge();
notesSheet.getRange("A1").format = {
  fill: "#7C2D12",
  font: { bold: true, color: "#FFFFFF", size: 14 },
  horizontalAlignment: "center",
  verticalAlignment: "center",
};
notesSheet.getRange("A2:A5").format = {
  font: { bold: true },
  fill: "#FED7AA",
};
notesSheet.getRange("A1:B6").format.columnWidthPx = 280;
notesSheet.getRange("D2:E4").values = genderSummary;
notesSheet.getRange("D2:E2").format = {
  fill: "#9A3412",
  font: { bold: true, color: "#FFFFFF" },
};

candidatesSheet.tables.add(`A1:D${rows.length + 1}`, true, "TamilNaduCandidates");

await fs.mkdir(outputDir, { recursive: true });

const inspect = await workbook.inspect({
  kind: "table",
  range: `Candidates!A1:D10`,
  include: "values",
  tableMaxRows: 10,
  tableMaxCols: 4,
});
console.log(inspect.ndjson);

const renderBlob = await workbook.render({
  sheetName: "Candidates",
  range: "A1:D25",
  scale: 1,
  format: "png",
});
await fs.writeFile(
  path.join(outputDir, "tamilnadu-election-candidates-preview.png"),
  new Uint8Array(await renderBlob.arrayBuffer()),
);

const exported = await SpreadsheetFile.exportXlsx(workbook);
await exported.save(outputPath);

console.log(outputPath);
