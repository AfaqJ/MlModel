import json,csv,re,unicodedata,collections
S="/private/tmp/claude-501/-Users-afaq-Desktop-Mctech-ML-model/da960daa-a982-4f2d-8f8c-3ab725c62db0/scratchpad/"
G="/Users/afaq/Desktop/Mctech/ML-model/Data/candidates/retrain_2026_09_16/master_gold.csv"
def norm(t):
    t=unicodedata.normalize("NFKD",str(t or "")).encode("ascii","ignore").decode().lower(); return re.sub(r"[^a-z0-9]+"," ",t).strip()
lk={"live_product_lookup","client_product_rule","live_meter_lookup","live_business_rule"}
sup=collections.defaultdict(collections.Counter)
for r in csv.DictReader(open(G,encoding="utf-8")):
    if r["source"] in lk: continue           # lookups are the client's rules, not a mixed bag
    sup[norm(r["provider"])][r["category_code"]]+=1
def flag(name,minrows=8,topshare=0.70):
    c=sup.get(name)
    if not c: return False
    n=sum(c.values()); return n>=minrows and c.most_common(1)[0][1]/n<topshare
flagged={k for k in sup if flag(k)}
print("suppliers in old data (non-lookup rows):",len(sup),"| flagged 'mixed' (>=8 rows, no category above 70%):",len(flagged))
big=sorted(((sum(sup[k].values()),k,len(sup[k])) for k in flagged),reverse=True)[:8]
for n,k,d in big: print(f"   {k[:36]:36} rows={n:3} categories={d}")
inv={i["invoice_id"]:i for i in json.load(open(S+"july_invoices.json"))}
items=json.load(open(S+"july_items.json")); tr={x["item_id"]:x["true"] for x in json.load(open(S+"exact_truth.json"))}
L=[it for it in items if it["prediction_source"]=="model" and it["item_id"] in tr]
def sname(it): return norm(inv[it["invoice_id"]]["seller_name"])
F=[it for it in L if sname(it) in flagged]; N=[it for it in L if sname(it) not in flagged]
def ok(it): return it["predicted_code"]==tr[it["item_id"]]
print(f"\nJuly model lines: {len(L)}; from flagged suppliers: {len(F)}; others: {len(N)}")
print(f"  ML right on flagged: {sum(map(ok,F))}/{len(F)} ({sum(map(ok,F))/max(1,len(F)):.0%});  on others: {sum(map(ok,N))}/{len(N)} ({sum(map(ok,N))/len(N):.0%})")
A=[it for it in L if it["decision"]=="auto_accept"]
wrong=[it for it in A if not ok(it)]; right=[it for it in A if ok(it)]
fw=[it for it in wrong if sname(it) in flagged]; fr=[it for it in right if sname(it) in flagged]
print(f"  auto-accepted model lines: {len(A)} (right {len(right)}, wrong {len(wrong)})")
print(f"  'send flagged suppliers to review' would catch {len(fw)} of {len(wrong)} wrong auto-accepts, and cost {len(fr)} of {len(right)} correct auto-accepts")
unseen=[it for it in wrong if norm(inv[it['invoice_id']]['seller_name']) not in sup]
print(f"  wrong auto-accepts from suppliers never seen in old data: {len(unseen)} of {len(wrong)}")
print("  the wrong auto-accepts by supplier:",collections.Counter(inv[it['invoice_id']]['seller_name'][:24] for it in wrong).most_common(8))
