/**
 * Offline, no DB, no network: read August's DTE XMLs and run only the client's own
 * deterministic rules (rules.ts is pure — reads rules-data.json, calls no service).
 * Writes one JSON line per invoice line with what the rule engine decided, or nothing.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { readFiles } from "/Users/afaq/Desktop/Mctech/milk-company/src/lib/ingest/batch";
import { applyRules, documentGuardReason } from "/Users/afaq/Desktop/Mctech/milk-company/src/lib/ingest/rules";

const zipPath = process.argv[2];
const outPath = process.argv[3];
const bytes = readFileSync(zipPath);

readFiles([{ name: "z.zip", bytes: new Uint8Array(bytes) }], new Set()).then((r: any) => {
  const out: any[] = [];
  for (const doc of r.documents) {
    const guard = documentGuardReason(doc.documentType);
    for (const line of doc.lines) {
      const outcome = applyRules({
        itemText: line.itemText || line.description,
        description: line.description,
        provider: doc.sellerName,
        meterCode: doc.receiverInternalCode,
        transportPlate: doc.transportPlate,
        transactionType: doc.transactionType,
      });
      out.push({
        sellerRut: doc.sellerRut, folio: doc.folio, documentType: doc.documentType,
        lineNumber: line.lineNumber, itemText: line.itemText, description: line.description,
        provider: doc.sellerName, quantity: line.quantity, unit: line.unit,
        unitPrice: line.unitPrice, amount: line.amount, transactionType: doc.transactionType,
        ruleCode: outcome.hit?.code ?? null, ruleSource: outcome.hit?.source ?? null,
        forcedReviewReason: guard ?? outcome.forcedReviewReason ?? null,
      });
    }
  }
  writeFileSync(outPath, JSON.stringify({
    documents: r.documents.length, lines: r.lines, rejected: r.rejected, rows: out,
  }));
  console.log("documents", r.documents.length, "lines", r.lines, "rejected", r.rejected.length);
});
