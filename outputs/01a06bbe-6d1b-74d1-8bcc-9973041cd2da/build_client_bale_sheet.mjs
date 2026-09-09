import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = "/Users/afaq/Desktop/Mctech/ML-model";
const backup = `${root}/backups/supabase_20260903T054820Z`;
const output = `${root}/outputs/01a06bbe-6d1b-74d1-8bcc-9973041cd2da/Cristian_bale_lines_2026-09-04.xlsx`;
const previewPath = `${root}/outputs/01a06bbe-6d1b-74d1-8bcc-9973041cd2da/Cristian_bale_lines_2026-09-04.png`;

const excluded = new Set([
  "d4b2b201-97e6-43e7-b6d8-eccf930a6cdd", // repair of bale grab
  "c2464219-7a5a-4ecb-8c1d-9d48ca0f9db4", // bale film
  "2d9bf9d6-374d-4c93-9fc5-a10e245f0f0f", // movement of bales
  "46c014da-919c-40ab-8dd8-9e908c763f25", // transport of a silage bale
  "1d8a3fe0-2dee-43d2-8e10-2a751e537849", // travel/transport
  "fb8f2f97-2cea-4dde-8a43-6e479264119f", // travel/transport
  "92144bdf-308f-490d-94fa-bc36dc71e049", // transport
  "7c89819f-e3a6-4543-9d92-be1f17c32cb3", // transport
  "4afa0292-7ede-408d-a688-e50edfd58ff0", // bale netting
]);

function parseJsonl(text) {
  return text.trim().split("\n").map((line) => JSON.parse(line));
}

const [itemText, invoiceText] = await Promise.all([
  fs.readFile(`${backup}/invoice_items.jsonl`, "utf8"),
  fs.readFile(`${backup}/invoices.jsonl`, "utf8"),
]);
const invoices = new Map(parseJsonl(invoiceText).map((invoice) => [invoice.invoice_id, invoice]));
const items = parseJsonl(itemText)
  .filter((item) => item.decision === "review_required")
  .filter((item) => /\bbolos?\b/i.test(`${item.item_text ?? ""} ${item.description ?? ""}`))
  .filter((item) => !excluded.has(item.item_id))
  .map((item) => ({ ...item, invoice: invoices.get(item.invoice_id) }))
  .sort((a, b) =>
    (a.invoice?.seller_name ?? "").localeCompare(b.invoice?.seller_name ?? "", "es") ||
    (a.invoice?.invoice_date ?? "").localeCompare(b.invoice?.invoice_date ?? "") ||
    String(a.invoice?.invoice_folio ?? "").localeCompare(String(b.invoice?.invoice_folio ?? ""), "es", { numeric: true }) ||
    (a.invoice_line_number ?? 0) - (b.invoice_line_number ?? 0)
  );

const total = items.reduce((sum, item) => sum + Number(item.amount ?? 0), 0);
if (items.length !== 18 || total !== 56581822) {
  throw new Error(`Unexpected bale selection: ${items.length} lines, CLP ${total}`);
}
if (items.some((item) => !item.invoice)) {
  throw new Error("At least one selected item has no matching invoice");
}

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Bale lines");
sheet.showGridLines = false;
sheet.tabColor = "#1F4E78";

sheet.mergeCells("A1:J1");
sheet.getRange("A1").values = [["Bale-making lines to categorise"]];
sheet.getRange("A1:J1").format = {
  fill: "#1F4E78",
  font: { bold: true, color: "#FFFFFF", size: 18 },
  verticalAlignment: "center",
};
sheet.getRange("A1:J1").format.rowHeight = 34;

sheet.mergeCells("A2:J2");
sheet.getRange("A2").values = [["Antillanca - 18 unresolved invoice lines - CLP 56,581,822"]];
sheet.getRange("A2:J2").format = {
  fill: "#D9EAF7",
  font: { color: "#1F2937", italic: true },
  verticalAlignment: "center",
};
sheet.getRange("A2:J2").format.rowHeight = 24;

sheet.mergeCells("A3:J3");
sheet.getRange("A3").values = [["Please choose Bolos Silo or Bolos Heno in the yellow column. If neither is correct, choose Other and explain in Notes."]];
sheet.getRange("A3:J3").format = {
  fill: "#FFF2CC",
  font: { color: "#7F6000", bold: true },
  wrapText: true,
  verticalAlignment: "center",
};
sheet.getRange("A3:J3").format.rowHeight = 34;

sheet.getRange("A5:B5").values = [["Lines", null]];
sheet.getRange("B5").formulas = [["=COUNTA(A8:A25)"]];
sheet.getRange("D5:E5").values = [["Total CLP", null]];
sheet.getRange("E5").formulas = [["=SUM(F8:F25)"]];
sheet.getRange("A5:E5").format = { font: { bold: true, color: "#1F2937" } };
sheet.getRange("B5").format = { fill: "#E2F0D9", font: { bold: true, color: "#375623" }, horizontalAlignment: "center" };
sheet.getRange("E5").format = { fill: "#E2F0D9", font: { bold: true, color: "#375623" }, horizontalAlignment: "right" };
sheet.getRange("E5").setNumberFormat("#,##0");

const headers = [
  "Invoice date",
  "Invoice folio",
  "Contractor",
  "Invoice line",
  "Item",
  "Amount CLP",
  "Correct category",
  "Notes",
  "Quantity / unit",
  "Reference ID",
];
sheet.getRange("A7:J7").values = [headers];

const rows = items.map((item) => [
  new Date(`${item.invoice.invoice_date}T00:00:00Z`),
  String(item.invoice.invoice_folio ?? ""),
  item.invoice.seller_name ?? "",
  item.invoice_line_number ?? null,
  String(item.item_text ?? "").trim().toLowerCase() === "item"
    ? String(item.description ?? item.item_text ?? "").replaceAll("~", " ").split(",").slice(0, 2).join(",")
    : item.item_text ?? item.description ?? "",
  Number(item.amount ?? 0),
  "",
  "",
  [item.quantity, item.unit].filter((value) => value !== null && value !== undefined && value !== "").join(" "),
  item.item_id,
]);
sheet.getRange("A8:J25").values = rows;

const table = sheet.tables.add("A7:J25", true, "BaleLinesTable");
table.style = "TableStyleMedium2";
table.showBandedRows = true;
table.showFilterButton = true;

sheet.getRange("A8:A25").setNumberFormat("yyyy-mm-dd");
sheet.getRange("D8:D25").setNumberFormat("0");
sheet.getRange("F8:F25").setNumberFormat("#,##0");
sheet.getRange("G8:H25").format.fill = "#FFF2CC";
sheet.getRange("G8:G25").dataValidation = {
  rule: { type: "list", values: ["Bolos Silo", "Bolos Heno", "Other - explain in Notes"] },
};

sheet.getRange("A7:J25").format.borders = { preset: "all", style: "thin", color: "#D9E2F3" };
sheet.getRange("A7:J25").format.verticalAlignment = "center";
sheet.getRange("C8:C25").format.wrapText = true;
sheet.getRange("E8:E25").format.wrapText = true;
sheet.getRange("H8:H25").format.wrapText = true;

sheet.getRange("A:A").format.columnWidth = 13;
sheet.getRange("B:B").format.columnWidth = 13;
sheet.getRange("C:C").format.columnWidth = 25;
sheet.getRange("D:D").format.columnWidth = 12;
sheet.getRange("E:E").format.columnWidth = 38;
sheet.getRange("F:F").format.columnWidth = 15;
sheet.getRange("G:G").format.columnWidth = 22;
sheet.getRange("H:H").format.columnWidth = 28;
sheet.getRange("I:I").format.columnWidth = 16;
sheet.getRange("J:J").format.columnWidth = 38;
sheet.getRange("A8:J25").format.rowHeight = 38;
sheet.freezePanes.freezeRows(7);

sheet.mergeCells("A27:J27");
sheet.getRange("A27").values = [["Source: Supabase backup taken 2026-09-03 (invoice_items and invoices)."]];
sheet.getRange("A27:J27").format = { font: { italic: true, color: "#666666", size: 9 } };

const compact = await workbook.inspect({
  kind: "workbook,sheet,table,formula",
  maxChars: 6000,
  tableMaxRows: 8,
  tableMaxCols: 10,
});
console.log(compact.ndjson ?? compact);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 50 },
  maxChars: 4000,
});
console.log("FORMULA_ERROR_SCAN");
console.log(errors.ndjson ?? errors);

await fs.mkdir(output.slice(0, output.lastIndexOf("/")), { recursive: true });
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(output);
const exportedWorkbook = await SpreadsheetFile.importXlsx(await FileBlob.load(output));
const exportedErrors = await exportedWorkbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 50 },
  maxChars: 4000,
});
console.log("EXPORTED_FORMULA_ERROR_SCAN");
console.log(exportedErrors.ndjson ?? exportedErrors);
const preview = await exportedWorkbook.render({ sheetName: "Bale lines", autoCrop: "all", scale: 1, format: "png" });
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
console.log(JSON.stringify({ output, previewPath, rows: items.length, total }));
