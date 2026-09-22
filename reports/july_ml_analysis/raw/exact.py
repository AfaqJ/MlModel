import json, re, collections, unicodedata, openpyxl, sys
S="/private/tmp/claude-501/-Users-afaq-Desktop-Mctech-ML-model/da960daa-a982-4f2d-8f8c-3ab725c62db0/scratchpad/"
cats=json.load(open("/Users/afaq/Desktop/Mctech/ML-model/Data/current_context_2026_06_30/live_categories_map.json"))
def norm(t):
    t=unicodedata.normalize("NFKD",str(t or "")).encode("ascii","ignore").decode().lower(); return re.sub(r"[^a-z0-9]+"," ",t).strip()
name2code={norm(v["name"]):k for k,v in cats.items()}
ws=openpyxl.load_workbook(S+"lib/COMPRAS FORMATO 1.xlsx",read_only=True,data_only=True)["JULIO"]
rows=list(ws.iter_rows(values_only=True)); ledger=collections.defaultdict(lambda: collections.defaultdict(float)); cur=None; sec=None
for row in rows[8:]:
    c=[("" if v is None else str(v).strip()) for v in row]
    if c[0] and not c[1] and not c[3]: sec=c[0]; continue
    if c[1]: cur=(re.sub(r"[^0-9kK]","",c[3]).upper(), c[1].lstrip("0"))
    if cur and c[8]:
        try: a=float(c[12] or 0)+float(c[13] or 0)
        except: a=0
        ledger[cur][c[9]]+=a
inv={i["invoice_id"]:i for i in json.load(open(S+"july_invoices.json"))}
items=json.load(open(S+"july_items.json"))
bydoc=collections.defaultdict(list)
for it in items:
    i=inv[it["invoice_id"]]; bydoc[(i["seller_rut"].upper(),i["invoice_folio"].lstrip("0"))].append(it)

def solve(lines, targets, tol=2):
    # assign each line to one account so per-account sums match targets
    accts=list(targets); rem={a:targets[a] for a in accts}
    order=sorted(range(len(lines)), key=lambda k:-lines[k])
    out=[None]*len(lines); sys.setrecursionlimit(10000)
    calls=[0]
    def bt(pos):
        calls[0]+=1
        if calls[0]>200000: return False
        if pos==len(order): return all(abs(rem[a])<=tol for a in accts)
        k=order[pos]; seen=set()
        for a in accts:
            key=round(rem[a])
            if (a,key) in seen: continue
            if rem[a]-lines[k] >= -tol:
                rem[a]-=lines[k]; out[k]=a
                if bt(pos+1): return True
                rem[a]+=lines[k]
        return False
    return out if bt(0) else None

stats=collections.Counter(); exact=[]
for key,its in bydoc.items():
    if key not in ledger: continue
    tg=dict(ledger[key]); multi=len(tg)>1
    stats["multi" if multi else "single"]+=1
    if not multi:
        for it in its: exact.append((it, name2code.get(norm(next(iter(tg))))))
        continue
    lines=[float(it["amount"] or 0) for it in its]
    sol=solve(lines,tg)
    stats["multi_solved" if sol else "multi_unsolved"]+=1
    if sol:
        for it,a in zip(its,sol): exact.append((it,name2code.get(norm(a))))
print(dict(stats))
ok=[(it,c) for it,c in exact if c]
print("lines with exact truth:",len(ok),"of",len(items))
def rate(p): return f"{sum(1 for it,c in p if it['predicted_code']==c)}/{len(p)} ({sum(1 for it,c in p if it['predicted_code']==c)/max(1,len(p)):.0%})"
for src in ("model","product_lookup","meter_lookup","business_rule"):
    p=[x for x in ok if x[0]["prediction_source"]==src]
    if p:
        a=[x for x in p if x[0]["decision"]=="auto_accept"]; r=[x for x in p if x[0]["decision"]!="auto_accept"]
        print(f"  {src:15} n={len(p):3} top1 {rate(p)} | auto {rate(a) if a else '-'} | review {rate(r) if r else '-'}")
json.dump([{"item_id":it["item_id"],"true":c} for it,c in ok],open(S+"exact_truth.json","w"))
