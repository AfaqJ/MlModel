import json, re, unicodedata, collections, sys
import openpyxl

S = "/private/tmp/claude-501/-Users-afaq-Desktop-Mctech-ML-model/da960daa-a982-4f2d-8f8c-3ab725c62db0/scratchpad/"
inv = {i["invoice_id"]: i for i in json.load(open(S + "july_invoices.json"))}
items = json.load(open(S + "july_items.json"))
cats = json.load(open("/Users/afaq/Desktop/Mctech/ML-model/Data/current_context_2026_06_30/live_categories_map.json"))


def norm(t):
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


name2code = {norm(v["name"]): k for k, v in cats.items()}

# ---- ledger (FORMATO 1, JULIO): one row per document x account x cost centre
ws = openpyxl.load_workbook("/private/tmp/claude-501/-Users-afaq-Desktop-Mctech-ML-model/da960daa-a982-4f2d-8f8c-3ab725c62db0/scratchpad/lib/COMPRAS FORMATO 1.xlsx",
                            read_only=True, data_only=True)["JULIO"]
rows = list(ws.iter_rows(values_only=True))
ledger = collections.defaultdict(list)  # (rut, folio) -> [(acct_code, acct_name, centre, amount)]
docinfo = {}
cur = None
section = None
for row in rows[8:]:
    c = [("" if v is None else str(v).strip()) for v in row]
    if c[0] and not c[1] and not c[3]:
        section = c[0]
        continue
    if c[1]:  # new document
        rut = re.sub(r"[^0-9kK]", "", c[3]).upper()
        cur = (rut, c[1].lstrip("0"))
        docinfo[cur] = {"tipo": c[2], "prov": c[4], "section": section, "fecha": c[5], "total": c[19]}
    if cur and c[8]:
        try:
            amt = float(c[12] or 0) + float(c[13] or 0)
        except ValueError:
            amt = 0
        ledger[cur].append((c[8], c[9], c[11], amt))

print("ledger documents:", len(ledger), "sections:", collections.Counter(d["section"] for d in docinfo.values()))
acct_names = collections.Counter(n for v in ledger.values() for _, n, _, _ in v)
unmapped = {n: k for n, k in acct_names.items() if norm(n) not in name2code}
print("ledger account names:", len(acct_names), "not matching one of our category names:", len(unmapped))
for n, k in sorted(unmapped.items(), key=lambda x: -x[1])[:25]:
    print("   unmapped:", n, k)

# ---- DB side
by_doc = collections.defaultdict(list)
for it in items:
    i = inv[it["invoice_id"]]
    key = (i["seller_rut"].upper(), i["invoice_folio"].lstrip("0"))
    by_doc[key].append((i, it))
print("DB documents:", len(by_doc), "lines:", len(items))
found = [k for k in by_doc if k in ledger]
print("DB docs found in ledger by (rut, folio):", len(found))
missing = [k for k in by_doc if k not in ledger]
print("DB docs NOT in ledger:", len(missing), collections.Counter(by_doc[k][0][0]["document_type"] for k in missing))
print("ledger docs not in DB:", len([k for k in ledger if k not in by_doc]))

json.dump({"missing": [list(k) for k in missing]}, open(S + "missing.json", "w"))

# ---- states
print("\nline states (decision x source):")
c = collections.Counter((it["decision"], it["prediction_source"], it["needs_review"], it["reviewed"]) for it in items)
for k, v in sorted(c.items(), key=lambda x: -x[1]): print("  ", k, v)

# ---- correctness
res = []  # per line
for key in found:
    accts = [(name2code.get(norm(n)), n, amt) for _, n, _, amt in ledger[key]]
    codes = {a[0] for a in accts if a[0]}
    unknown = [a[1] for a in accts if not a[0]]
    single = len({a[1] for a in accts}) == 1
    for i, it in by_doc[key]:
        res.append({
            "key": key, "item": it["item_text"], "prov": i["seller_name"], "pred": it["predicted_code"], "final": it["final_code"],
            "decision": it["decision"], "source": it["prediction_source"], "score": it["top1_score"],
            "true_codes": codes, "unknown": unknown, "single": single,
            "top3": [t["code"] for t in (it["top3"] or [])],
            "amount": it["amount"],
        })

def ok(r): return r["pred"] in r["true_codes"]
print("\nlines compared (docs found in ledger):", len(res))
one = [r for r in res if r["single"] and not r["unknown"]]
print("  lines in single-account documents (clean truth):", len(one))
for label, pool in (("single-account docs", one), ("all compared lines (pred in any account of the doc)", [r for r in res if not r["unknown"]])):
    print("\n==", label, len(pool))
    for dec in ("auto_accept", "review_required"):
        p = [r for r in pool if r["decision"] == dec]
        if p:
            good = sum(ok(r) for r in p)
            top3 = sum(any(t in r["true_codes"] for t in r["top3"]) for r in p)
            print(f"  {dec:16} n={len(p):4}  top1 right={good:4} ({good/len(p):.0%})  top3 has it={top3} ({top3/len(p):.0%})  wrong={len(p)-good}")
    by = collections.defaultdict(lambda: [0, 0])
    for r in pool:
        by[(r["source"], r["decision"])][0] += 1
        by[(r["source"], r["decision"])][1] += ok(r)
    for k, (n, g) in sorted(by.items(), key=lambda x: -x[1][0]):
        print(f"     {k[0]:15} {k[1]:16} n={n:4} right={g:4} ({g/n:.0%})")

json.dump([{**r, "true_codes": sorted(r["true_codes"]), "key": list(r["key"])} for r in res], open(S + "compared.json", "w"), default=str)
