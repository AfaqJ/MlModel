"""Offline, no DB, no network: August exact truth from the accountant ledger, joined to what
the rule engine (august_rules.json, from august_offline_rules.ts) decided per line."""
import json, re, unicodedata, collections
import openpyxl

ROOT = "/Users/afaq/Desktop/Mctech/ML-model/"
OUT = ROOT + "reports/overnight_2026_09_21/"


def norm(t):
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


cats = json.load(open(ROOT + "Data/current_context_2026_06_30/live_categories_map.json"))
name2code = {norm(v["name"]): k for k, v in cats.items()}
name2code[norm("Utiles y gastos de oficina.")] = "ADM-1.6"  # trailing period in the client's account name

ws = openpyxl.load_workbook(ROOT + "Data/ledger_2026_07_08/COMPRAS FORMATO 1.xlsx", read_only=True, data_only=True)["AGOSTO"]
rows = list(ws.iter_rows(values_only=True))
ledger = collections.defaultdict(list)
cur = None
for row in rows[8:]:
    c = [("" if v is None else str(v).strip()) for v in row]
    if c[1]:
        rut = re.sub(r"[^0-9kK]", "", c[3]).upper()
        cur = (rut, c[1].lstrip("0"))
    if cur and c[8]:
        try:
            amt = float(c[12] or 0) + float(c[13] or 0)
        except ValueError:
            amt = 0
        ledger[cur].append((c[8], c[9], amt))

acct_names = collections.Counter(n for v in ledger.values() for _, n, _ in v)
unmapped = {n for n in acct_names if norm(n) not in name2code}
print("ledger documents:", len(ledger), "| account names:", len(acct_names), "| unmapped:", unmapped)

data = json.load(open(OUT + "august_rules.json"))
by_doc = collections.defaultdict(list)
for r in data["rows"]:
    by_doc[(r["sellerRut"].upper(), r["folio"].lstrip("0"))].append(r)

print("rule-engine documents:", len(by_doc), "lines:", sum(len(v) for v in by_doc.values()))


def solve(lines, targets, tol=2):
    accts = list(targets)
    rem = {a: targets[a] for a in accts}
    order = sorted(range(len(lines)), key=lambda k: -lines[k])
    out = [None] * len(lines)
    calls = [0]

    def bt(pos):
        calls[0] += 1
        if calls[0] > 200000:
            return False
        if pos == len(order):
            return all(abs(rem[a]) <= tol for a in accts)
        k = order[pos]
        seen = set()
        for a in accts:
            key = round(rem[a])
            if (a, key) in seen:
                continue
            seen.add((a, key))
            if rem[a] - lines[k] >= -tol:
                rem[a] -= lines[k]
                out[k] = a
                if bt(pos + 1):
                    return True
                rem[a] += lines[k]
        return False

    return out if bt(0) else None


exact, stats = [], collections.Counter()
for key, lines in by_doc.items():
    if key not in ledger:
        stats["doc_not_in_ledger"] += len(lines)
        continue
    tg = collections.Counter()
    for _, name, amt in ledger[key]:
        tg[name] += amt
    tg = dict(tg)
    if len(tg) == 1:
        code = name2code.get(norm(next(iter(tg))))
        for r in lines:
            exact.append((r, code))
        stats["single_account"] += len(lines)
        continue
    amounts = [float(r["amount"] or 0) for r in lines]
    sol = solve(amounts, tg)
    if sol:
        for r, a in zip(lines, sol):
            exact.append((r, name2code.get(norm(a))))
        stats["multi_solved"] += len(lines)
    else:
        stats["multi_unsolved"] += len(lines)

print("line coverage:", dict(stats))
ok = [(r, c) for r, c in exact if c]
print("lines with exact truth:", len(ok), "of", sum(len(v) for v in by_doc.values()))

# rule engine vs accountants, on the lines the rules themselves settled
rule_hits = [(r, c) for r, c in ok if r["ruleCode"]]
right = sum(1 for r, c in rule_hits if r["ruleCode"] == c)
print(f"\nRULE ENGINE vs accountants (product/meter/business rules): {right}/{len(rule_hits)} right")
for r, c in rule_hits:
    if r["ruleCode"] != c:
        print(f"   DISAGREE  rule={r['ruleCode']:9} truth={c or '?':9} src={r['ruleSource']:14} {r['provider'][:26]:26} {str(r['itemText'])[:40]}")

model_facing = [(r, c) for r, c in ok if not r["ruleCode"]]
print(f"\nlines with no rule hit (go to the model): {len(model_facing)} (of {len(ok)} with truth)")
json.dump([{"itemText": r["itemText"], "description": r["description"], "provider": r["provider"],
            "transactionType": r["transactionType"], "truth": c, "forcedReviewReason": r["forcedReviewReason"],
            "sellerRut": r["sellerRut"], "folio": r["folio"], "lineNumber": r["lineNumber"]}
           for r, c in model_facing], open(OUT + "august_model_facing.json", "w"))
