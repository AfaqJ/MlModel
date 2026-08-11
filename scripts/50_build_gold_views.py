"""Gold master -> 72 per-category CSV views + coverage. Re-runnable, counts never drift.

Bootstraps Data/gold/_master_gold.csv from the legacy rule-compliant gold on first run
(remapping audit_source -> readable source), EXCLUDING quarantined raw sources.
Then regenerates the 72 "<CODE> <leaf> (<count>).csv" files + _coverage.csv from the master.
Append new audited rows to _master_gold.csv, then re-run this to refresh the views.
"""
import csv, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CTX = ROOT / "Data" / "current_context_2026_06_30"
GOLD = ROOT / "Data" / "gold"
MASTER = GOLD / "_master_gold.csv"
LEGACY = ROOT / "Data" / "recovered_gold_2026_06_30" / "gold_labels_recovered_conservative.csv"
FIELDS = ["gold_id","category_code","leaf","source","item_text","description","provider","farm","audit_reason","verify_flag"]
SRCMAP = {"client_row_example":"direct_client_example","client_product_rule":"client_product_rule",
          "folder_audited":"file_audit","polluted_folder_xml_confirmed":"file_audit",
          "polluted_folder_xml_clean_match":"file_audit","silver_audited_sonnet":"silver_audit",
          "silver_2step_audited":"silver_audit"}
QUARANTINE = {"high_precision_raw_rule","invoice_exact_product_rule_match"}

def rd(p):
    with open(p, newline="", encoding="utf-8-sig") as fh: return list(csv.DictReader(fh))
def safe(s): return re.sub(r"[\\/:*?\"<>|]+","-", s).strip().rstrip(".")

tax = {r["new_code"]: r for r in rd(CTX / "taxonomy_from_plan.csv")}
GOLD.mkdir(parents=True, exist_ok=True)

# bootstrap master from legacy if it doesn't exist yet
if not MASTER.exists():
    rows = []
    for r in rd(LEGACY):
        src = r.get("audit_source","")
        if src in QUARANTINE: continue
        rows.append({"gold_id": r.get("gold_id",""), "category_code": r["category_code"],
            "leaf": tax.get(r["category_code"],{}).get("leaf",""), "source": SRCMAP.get(src, src),
            "item_text": r.get("item_text",""), "description": r.get("description",""),
            "provider": r.get("provider",""), "farm": r.get("farm",""), "audit_reason": r.get("audit_reason","")})
    with open(MASTER,"w",newline="",encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    print(f"bootstrapped _master_gold.csv with {len(rows)} rows (quarantined raw excluded)")

master = rd(MASTER)
by = {}
for r in master: by.setdefault(r["category_code"], []).append(r)

# wipe old generated view files (keep master + coverage) so stale filenames don't linger
for f in GOLD.glob("*.csv"):
    if f.name not in ("_master_gold.csv","_coverage.csv"): f.unlink()

cov = []
for code, t in tax.items():
    rows = by.get(code, [])
    fname = f"{code} {safe(t['leaf'])} ({len(rows)}).csv"
    with open(GOLD / fname, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    st = "ok_30_plus" if len(rows)>=30 else ("usable_15_plus" if len(rows)>=15 else "starving_under_15")
    cov.append({"category_code":code,"leaf":t["leaf"],"gold_count":len(rows),"status":st})
with open(GOLD / "_coverage.csv","w",newline="",encoding="utf-8") as fh:
    w=csv.DictWriter(fh,fieldnames=["category_code","leaf","gold_count","status"]); w.writeheader(); w.writerows(cov)

tot=len(master); cov15=sum(1 for c in cov if c["gold_count"]>=15); covd=sum(1 for c in cov if c["gold_count"]>0); N=len(tax)
print(f"views rebuilt: {N} files | master rows {tot} | covered {covd}/{N} | >=15 {cov15}/{N}")
assert sum(c["gold_count"] for c in cov)==tot, "coverage total != master rows"
print("OK: filename counts and coverage match master.")
