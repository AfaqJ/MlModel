import json, re, csv, unicodedata, collections

S = "/private/tmp/claude-501/-Users-afaq-Desktop-Mctech-ML-model/da960daa-a982-4f2d-8f8c-3ab725c62db0/scratchpad/"
B = "/Users/afaq/Desktop/Mctech/ML-model/backups/yunt_team_handover_20260913/"
G = "/Users/afaq/Desktop/Mctech/ML-model/Data/candidates/retrain_2026_09_16/master_gold.csv"


def norm(t):
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


res = json.load(open(S + "compared.json"))
jinv = {i["invoice_id"]: i for i in json.load(open(S + "july_invoices.json"))}
jitems = json.load(open(S + "july_items.json"))
# attach supplier RUT / name to compared lines via (rut, folio)
rut_of = {(i["seller_rut"].upper(), i["invoice_folio"].lstrip("0")): i for i in jinv.values()}
for r in res:
    r["rut"] = r["key"][0]

# history (before July): settled lines only, by supplier RUT
hi = json.load(open(B + "invoices.json"))
hit = json.load(open(B + "invoice_items.json"))
rut_by_inv = {i["invoice_id"]: i["seller_rut"].upper() for i in hi}
hist = collections.defaultdict(collections.Counter)
for x in hit:
    if x["final_code"] and x["prediction_source"] != "model":
        hist[rut_by_inv[x["invoice_id"]]][x["final_code"]] += 1

# training corpus: providers and wordings seen
train_prov, train_word, train_cls = set(), set(), collections.Counter()
with open(G, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        train_prov.add(norm(row["provider"]))
        train_word.add(norm(row["item_text"]))
        train_cls[row["category_code"]] += 1

# July ledger: distinct accounts per supplier (across documents)
sup_accts = collections.defaultdict(set)
for r in res:
    sup_accts[r["rut"]] |= set(r["true_codes"])

NOISE = re.compile(r"^(total|fecha[- ]gu[ií]a|item|[-_=\s]+|nombre [ií]tem \d*|varios|servicio|producto)$", re.I)


def ok(r): return r["pred"] in r["true_codes"]


model = [r for r in res if r["source"] == "model" and not r["unknown"]]
print("model lines analysed:", len(model))

for r in model:
    h = hist.get(r["rut"])
    r["hist_n"] = sum(h.values()) if h else 0
    r["hist_top"], r["hist_share"] = (h.most_common(1)[0][0], h.most_common(1)[0][1] / r["hist_n"]) if h else (None, 0)
    r["seen_word"] = norm(r["item"]) in train_word
    r["seen_supplier"] = r["hist_n"] > 0
    r["n_accts_july"] = len(sup_accts[r["rut"]])
    it = str(r["item"] or "")
    if NOISE.match(it.strip()):
        r["bucket"] = "1 not a product (Total / Item / dashes)"
    elif re.search(r"gasolina|petroleo|diesel|combustible", it, re.I):
        r["bucket"] = "2 fuel (plate decides)"
    elif r["hist_n"] >= 3 and r["hist_share"] >= 0.8:
        r["bucket"] = "3 supplier is consistent in history (>=80% one category)"
    elif r["hist_n"] >= 3:
        r["bucket"] = "4 supplier is split in history (context needed)"
    elif r["hist_n"] == 0:
        r["bucket"] = "5 supplier never seen before"
    else:
        r["bucket"] = "6 supplier seen < 3 times"

print("\nBUCKETS (model lines, ledger truth):")
print(f"{'bucket':62} {'lines':>5} {'in review':>9} {'ML top1':>8} {'ML top3':>8} {'supplier-history guess':>22}")
for b in sorted({r["bucket"] for r in model}):
    p = [r for r in model if r["bucket"] == b]
    rev = sum(r["decision"] == "review_required" for r in p)
    t1 = sum(map(ok, p))
    t3 = sum(any(t in r["true_codes"] for t in r["top3"]) for r in p)
    hg = [r for r in p if r["hist_top"]]
    hgr = f"{sum(r['hist_top'] in r['true_codes'] for r in hg)}/{len(hg)}" if hg else "-"
    print(f"{b:62} {len(p):5} {rev:9} {t1:4}/{len(p):<3} {t3:4}/{len(p):<3} {hgr:>22}")

# seen vs unseen wording
print("\nwording seen exactly in training data?")
for label, f in (("seen", lambda r: r["seen_word"]), ("never seen", lambda r: not r["seen_word"])):
    p = [r for r in model if f(r)]
    print(f"   {label:11} lines={len(p):4}  ML top1 right={sum(map(ok, p))}/{len(p)} ({sum(map(ok, p)) / max(1, len(p)):.0%})  auto={sum(r['decision'] == 'auto_accept' for r in p)}")
print("supplier seen in training/history?")
for label, f in (("seen", lambda r: r["seen_supplier"]), ("never seen", lambda r: not r["seen_supplier"])):
    p = [r for r in model if f(r)]
    print(f"   {label:11} lines={len(p):4}  ML top1 right={sum(map(ok, p))}/{len(p)} ({sum(map(ok, p)) / max(1, len(p)):.0%})")

# supplier-history baseline vs ML on lines with a consistent supplier
cons = [r for r in model if r["hist_n"] >= 3 and r["hist_share"] >= 0.8]
print(f"\nSUPPLIER-HISTORY RULE (supplier >=80% one category in past, >=3 lines): covers {len(cons)} of {len(model)} model lines")
print(f"   supplier-history guess right: {sum(r['hist_top'] in r['true_codes'] for r in cons)}/{len(cons)}   ML top1 right on the same lines: {sum(map(ok, cons))}/{len(cons)}")

# July: how split is each supplier in the ledger itself?
by_sup = collections.defaultdict(lambda: {"docs": set(), "accts": set(), "name": ""})
for r in model:
    d = by_sup[r["rut"]]; d["docs"].add(r["key"][1]); d["accts"] |= set(r["true_codes"]); d["name"] = r["prov"][:30]
multi = [d for d in by_sup.values() if len(d["accts"]) >= 3]
print(f"\nsuppliers with model lines: {len(by_sup)}; booked to >=3 different accounts in July alone: {len(multi)}")
lines_multi = sum(1 for r in model if len(sup_accts[r['rut']]) >= 3)
print(f"   lines belonging to those suppliers: {lines_multi} of {len(model)}; ML top1 there: {sum(ok(r) for r in model if len(sup_accts[r['rut']]) >= 3)}/{lines_multi}")
print("   biggest split suppliers:")
for d in sorted(by_sup.values(), key=lambda d: -len(d["accts"]))[:8]:
    print(f"     {d['name']:30} docs={len(d['docs']):3} accounts={len(d['accts'])}")

# where the model is wrong on consistent suppliers (the ones that look fixable)
print("\nModel wrong although the supplier is consistent in history (fixable by precedent):")
bad = [r for r in cons if not ok(r)]
cnt = collections.Counter((r["prov"][:28], r["pred"], r["hist_top"], round(r["hist_share"], 2), ",".join(r["true_codes"])) for r in bad)
for k, v in cnt.most_common(14): print("  ", v, k)

# per true-category: how the model does, and how much training it had
print("\nWORST true categories for the model (July, lines>=6):")
byc = collections.defaultdict(lambda: [0, 0])
for r in model:
    for c in r["true_codes"] if r["single"] else []:
        byc[c][0] += 1; byc[c][1] += ok(r)
for c, (n, g) in sorted(byc.items(), key=lambda x: (x[1][1] / x[1][0], -x[1][0])):
    if n >= 6: print(f"   {c:9} lines={n:3} right={g:3} ({g / n:.0%})  training examples={train_cls.get(c, 0)}")
