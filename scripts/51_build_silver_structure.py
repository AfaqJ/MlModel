"""Silver -> deduped 72 per-category working files + _index.csv. Re-runnable.

Dedup rule: within a category (grouped by the silver top1 label), a row is dropped only if
item_text+description+provider all match another (100% dup). Same item / different seller kept.
When deduping, an already-audited copy is preferred so audit status is retained.
Each row carries audited(Y/N) + verdict(true code or REJECT) from the audit ledger.
Also writes an optional xlsx per-... no: one _index.csv with total/audited/remaining/gold_now.
"""
import csv, re, unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CTX = ROOT / "Data" / "current_context_2026_06_30"
SILVER_SRC = ROOT / "data" / "targeted_recovery_2026_06_30" / "targeted_top3_silver_qwen3_14b.csv"
LINE_ITEMS = ROOT / "data" / "processed" / "line_items.csv"
LEDGER = ROOT / "Data" / "silver_audit_2026_06_30" / "audit_ledger.csv"
GOLDCOV = ROOT / "Data" / "gold" / "_coverage.csv"
OUT = ROOT / "Data" / "silver"
FIELDS = ["candidate_id","item_text","description","provider","giro","source","source_file","folio",
          "siblings","top1_conf","audited","verdict","audit_reason"]

def rd(p):
    with open(p, newline="", encoding="utf-8-sig") as fh: return list(csv.DictReader(fh))
def nz(t):
    s="" if t is None else str(t).lower(); s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode()
    return re.sub(r"[^a-z0-9 ]+"," ",s).strip()
def safe(s): return re.sub(r"[\\/:*?\"<>|]+","-", s).strip().rstrip(".")

tax = {r["new_code"]: r for r in rd(CTX / "taxonomy_from_plan.csv")}
gold_now = {r["category_code"]: int(r["gold_count"]) for r in rd(GOLDCOV)}
ledger = {r["candidate_id"]: r for r in rd(LEDGER)} if LEDGER.exists() else {}
silver = rd(SILVER_SRC)

sib = defaultdict(list)
for r in rd(LINE_ITEMS):
    k=(r.get("source_file",""), r.get("folio","")); nm=r.get("nmb_item",""); ds=r.get("dsc_item","")
    seg=re.sub(r"\s+"," "," - ".join(x for x in [nm,ds] if x)).strip()[:100]
    if k[0] and seg: sib[k].append(seg)
def siblings(r):
    k=(r.get("source_file",""), r.get("folio","")); cur=re.sub(r"\s+"," ",r.get("nmb_item","")).strip()[:100]; out=[]
    for s in sib.get(k,[]):
        if s!=cur and s not in out: out.append(s)
        if len(out)>=6: break
    return "; ".join(out)[:400]

by = defaultdict(list)
for r in silver:
    by[r.get("top1_code","")].append(r)

OUT.mkdir(parents=True, exist_ok=True)
for f in OUT.glob("*.csv"): f.unlink()

index=[]
for code in tax:
    rows = by.get(code, [])
    # dedup by (item+desc+provider); prefer an audited copy
    best={}
    for r in rows:
        key=(nz(r.get("nmb_item","")), nz(r.get("dsc_item","")), nz(r.get("provider","")))
        aud = r["candidate_id"] in ledger
        if key not in best or (aud and best[key]["candidate_id"] not in ledger):
            best[key]=r
    uniq=list(best.values())
    out_rows=[]
    n_aud=0
    for r in uniq:
        cid=r["candidate_id"]; led=ledger.get(cid)
        aud = "Y" if led else "N"
        if led: n_aud+=1
        verdict = (led.get("final_code") or ("REJECT" if (led.get("verdict","").upper() in ("WRONG","REJECT")) else "")) if led else ""
        out_rows.append({"candidate_id":cid,"item_text":re.sub(r"\s+"," ",r.get("nmb_item","")).strip(),
            "description":re.sub(r"\s+"," ",r.get("dsc_item","")).strip(),"provider":re.sub(r"\s+"," ",r.get("provider","")).strip(),
            "giro":re.sub(r"\s+"," ",r.get("giro","")).strip(),"source":r.get("source",""),
            "source_file":r.get("source_file",""),"folio":r.get("folio",""),"siblings":siblings(r),
            "top1_conf":r.get("top1_confidence_score",""),"audited":aud,"verdict":verdict,
            "audit_reason":(led.get("audit_reason","") if led else "")})
    fname=f"{code} {safe(tax[code]['leaf'])}.csv"
    with open(OUT/fname,"w",newline="",encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fieldnames=FIELDS); w.writeheader(); w.writerows(out_rows)
    index.append({"category_code":code,"leaf":tax[code]["leaf"],"silver_total_raw":len(rows),
        "silver_unique":len(uniq),"audited":n_aud,"remaining":len(uniq)-n_aud,"gold_now":gold_now.get(code,0)})
with open(OUT/"_index.csv","w",newline="",encoding="utf-8") as fh:
    w=csv.DictWriter(fh,fieldnames=["category_code","leaf","silver_total_raw","silver_unique","audited","remaining","gold_now"]); w.writeheader(); w.writerows(index)

print(f"silver rows {len(silver)} -> unique {sum(x['silver_unique'] for x in index)} across 72 files")
print("top cats by remaining-unaudited-unique silver (gold<15):")
for x in sorted(index,key=lambda x:-x["remaining"]):
    if x["gold_now"]<15 and x["remaining"]>0:
        print(f"  {x['category_code']:9s} gold={x['gold_now']:2d} unique={x['silver_unique']:3d} audited={x['audited']:3d} remaining={x['remaining']:3d}  {x['leaf']}")
