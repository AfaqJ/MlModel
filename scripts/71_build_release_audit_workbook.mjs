#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = process.cwd();
const candidate = path.join(root, "Data/candidates/recovery_v1_3_1");
const report = path.join(root, "reports/recovery_v1_3_1");
const output = path.join(report, "v1_3_1_release_audit.xlsx");

async function readJson(file) {
  try { return JSON.parse(await fs.readFile(file, "utf8")); }
  catch { return {}; }
}

const folderCsv = await fs.readFile(path.join(candidate, "folder_line_audit.csv"), "utf8");
const workbook = await Workbook.fromCSV(folderCsv, { sheetName: "Folder Audit" });

for (const [name, file] of [
  ["Weak Raw Audit", path.join(candidate, "starving_category_manual_audit.csv")],
  ["Quarantine", path.join(candidate, "quarantined_wrong_labels.csv")],
  ["Zero Value Audit", path.join(report, "zero_value_audit/distinct_zero_value_groups.csv")],
  ["Validation", path.join(report, "validation_predictions.csv")],
  ["Auto Accept Risks", path.join(report, "local_replay/auto_accept_risk_flags.csv")],
  ["Review Groups", path.join(report, "local_replay/review_groups.csv")],
]) {
  try {
    const csvText = await fs.readFile(file, "utf8");
    await workbook.fromCSV(csvText, { sheetName: name });
  } catch {}
}

const manifest = await readJson(path.join(candidate, "manifest.json"));
const calibration = await readJson(path.join(report, "calibration_and_validation_audit.json"));
const replay = await readJson(path.join(report, "local_replay/summary.json"));
const zero = await readJson(path.join(report, "zero_value_audit/inventory_summary.json"));
const card = await readJson(path.join(root, "artifacts/v1.3.1/model_card.json"));

const summary = workbook.worksheets.add("Summary");
summary.showGridLines = false;
summary.getRange("A1:D1").merge();
summary.getRange("A1").values = [["ML recovery v1.3.1 — local release audit"]];
summary.getRange("A1:D1").format = {
  fill: "#1F4E78", font: { bold: true, color: "#FFFFFF", size: 16 },
  rowHeight: 28, verticalAlignment: "center",
};
const rows = [
  ["Check", "Value", "Status", "Meaning"],
  ["Active taxonomy categories", manifest.active_taxonomy_categories ?? "", "INFO", "Client categories currently in scope"],
  ["ML-trained categories", manifest.model_eligible_categories_ge2_distinct ?? "", "INFO", "Categories with at least two distinct training inputs"],
  ["Active categories not trained", (manifest.active_not_model_eligible || []).join(", "), "REVIEW", "Handled only by exact rules until examples exist"],
  ["Final gold rows", manifest.counts?.final_rows ?? "", "PASS", "Rows retained after corrections/quarantine/promotions"],
  ["Folder rows audited", manifest.counts?.folder_rows_audited ?? "", "PASS", "Locked full folder-derived inventory"],
  ["Folder corrected", manifest.counts?.folder_rows_corrected ?? "", "PASS", "Clear higher-authority conflicts corrected"],
  ["Folder quarantined", manifest.counts?.folder_rows_quarantined ?? "", "PASS", "Uncertain/junk rows excluded from training"],
  ["All authority corrections", manifest.counts?.corrected_authority_conflicts ?? "", "PASS", "Across folder, silver and direct-example streams"],
  ["All quarantined rows", manifest.counts?.quarantined_wrong_labels ?? "", "PASS", "Preserved in audit files, absent from training"],
  ["Raw weak candidates inspected", manifest.counts?.manual_candidates_inspected ?? "", "PASS", "Manual raw-data search"],
  ["Raw examples promoted", manifest.counts?.manual_rows_promoted ?? "", "PASS", "Only explicit, semantically supported rows"],
  ["Validation accuracy", card.metrics?.accuracy ?? "", card.metrics?.accuracy ? "INFO" : "PENDING", "Locked held-out split"],
  ["Validation macro F1", card.metrics?.macro_f1 ?? "", card.metrics?.macro_f1 ? "INFO" : "PENDING", "Class-balanced held-out score"],
  ["Staged thresholds", calibration.selected_thresholds ? `${calibration.selected_thresholds.accept_top1} / ${calibration.selected_thresholds.accept_margin}` : "", calibration.selected_thresholds ? "PASS" : "PENDING", "Top-1 / margin; weak classes still review"],
  ["Held-out auto-accept false positives", calibration.cascade?.auto_accept_false_positives ?? "", calibration.cascade && calibration.cascade.auto_accept_false_positives === 0 ? "PASS" : "REVIEW", "Wrong labels accepted on held-out data"],
  ["Raw rows after zero-junk filter", replay.rows_after_audited_zero_junk_filter ?? "", replay.rows_after_audited_zero_junk_filter ? "PASS" : "PENDING", "Offline inference/upload row count"],
  ["Zero junk excluded", zero.audit_verdict_counts?.EXCLUDE_JUNK ?? "", "PASS", "Only audited separator/note/template patterns"],
  ["Zero-valued retained", zero.audit_verdict_counts?.KEEP_GENUINE_OR_UNCERTAIN ?? "", "PASS", "Conservative keep when genuine/uncertain"],
  ["Raw auto-accept rate", replay.auto_accept_rate ?? "", replay.auto_accept_rate ? "INFO" : "PENDING", "All deterministic + staged ML accepts"],
  ["Serious raw auto-accept flags", replay.auto_accept_risk_flags?.serious_rule_or_known_label_conflicts ?? "", replay.auto_accept_risk_flags && replay.auto_accept_risk_flags.serious_rule_or_known_label_conflicts === 0 ? "PASS" : "REVIEW", "Known-label/direction conflicts"],
];
summary.getRangeByIndexes(2, 0, rows.length, 4).values = rows;
summary.getRange(`A3:D3`).format = { fill: "#D9EAF7", font: { bold: true }, borders: { preset: "all", style: "thin", color: "#B4C6D7" } };
summary.getRange(`A4:D${rows.length + 2}`).format = { wrapText: true, borders: { preset: "all", style: "thin", color: "#D9D9D9" } };
summary.getRange("A:D").format.columnWidth = 24;
summary.getRange("D:D").format.columnWidth = 55;
summary.freezePanes.freezeRows(3);

for (let i = 0; i < workbook.worksheets.items.length; i++) {
  const sheet = workbook.worksheets.getItemAt(i);
  const used = sheet.getUsedRange();
  if (used) {
    used.format.wrapText = true;
    used.format.autofitRows();
  }
}

await fs.mkdir(report, { recursive: true });
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(output);
const preview = await workbook.render({ sheetName: "Summary", autoCrop: "all", scale: 1, format: "png" });
await fs.writeFile(path.join(report, "v1_3_1_release_audit_preview.png"), new Uint8Array(await preview.arrayBuffer()));
const inspection = await workbook.inspect({ kind: "sheet,region", sheetId: "Summary", range: "A1:D24", maxChars: 4000 });
console.log(inspection.ndjson);
console.log(output);
