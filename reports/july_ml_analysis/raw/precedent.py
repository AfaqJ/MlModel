import json,re,collections,unicodedata
S="/private/tmp/claude-501/-Users-afaq-Desktop-Mctech-ML-model/da960daa-a982-4f2d-8f8c-3ab725c62db0/scratchpad/"
B="/Users/afaq/Desktop/Mctech/ML-model/backups/yunt_team_handover_20260913/"
def norm(t):
    t=unicodedata.normalize("NFKD",str(t or "")).encode("ascii","ignore").decode().lower(); return re.sub(r"[^a-z0-9]+"," ",t).strip()
hi=json.load(open(B+"invoices.json")); hit=json.load(open(B+"invoice_items.json"))
rut={i["invoice_id"]:i["seller_rut"].upper() for i in hi}
sup=collections.defaultdict(collections.Counter); sw=collections.defaultdict(collections.Counter); wd=collections.defaultdict(collections.Counter)
for x in hit:
    if x["final_code"] and x["prediction_source"]!="model":     # settled labels only, never the model's own guesses
        r=rut[x["invoice_id"]]; w=norm(x["item_text"])
        sup[r][x["final_code"]]+=1; sw[(r,w)][x["final_code"]]+=1; wd[w][x["final_code"]]+=1
jinv={i["invoice_id"]:i for i in json.load(open(S+"july_invoices.json"))}
items=json.load(open(S+"july_items.json")); tr={x["item_id"]:x["true"] for x in json.load(open(S+"exact_truth.json"))}
L=[it for it in items if it["prediction_source"]=="model" and it["item_id"] in tr]
print("July model lines with exact truth:",len(L))
def top(c,minn,share):
    if not c: return None
    n=sum(c.values()); k,v=c.most_common(1)[0]
    return k if n>=minn and v/n>=share else None
def run(name,fn):
    ans=[(it,fn(it)) for it in L]
    prec=[(it,a) for it,a in ans if a]
    right=sum(a==tr[it["item_id"]] for it,a in prec)
    print(f"  {name:52} covers {len(prec):3} lines, right {right:3} ({right/max(1,len(prec)):.0%})")
    return ans
def ml(it): return it["predicted_code"]
def s_sup(it): return top(sup.get(jinv[it["invoice_id"]]["seller_rut"].upper()),3,0.8)
def s_sw(it): return top(sw.get((jinv[it["invoice_id"]]["seller_rut"].upper(),norm(it["item_text"]))),1,1.0)
def s_wd(it): return top(wd.get(norm(it["item_text"])),2,1.0)
print("\nHow good is each source of precedent on its own (only where it has an answer)?")
run("A. what this SUPPLIER was filed under before (>=80%)",s_sup)
run("B. this SUPPLIER + this exact WORDING seen before",s_sw)
run("C. this exact WORDING seen before (any supplier)",s_wd)
print("  (for comparison) the ML model on ALL these lines: right",sum(ml(it)==tr[it['item_id']] for it in L),"of",len(L))
def combo(it): return s_sw(it) or s_sup(it) or s_wd(it)
def comb_ml(it): return combo(it) or ml(it)
print("\nWhole system on these lines, if precedent goes first and ML is the fallback:")
a=[(it,comb_ml(it)) for it in L]; print(f"   right {sum(x==tr[it['item_id']] for it,x in a)} of {len(L)} ({sum(x==tr[it['item_id']] for it,x in a)/len(L):.0%})   [ML alone: {sum(ml(it)==tr[it['item_id']] for it in L)/len(L):.0%}]")
c=[(it,combo(it)) for it in L if combo(it)]
print(f"   the precedent part covers {len(c)} lines and is right on {sum(x==tr[it['item_id']] for it,x in c)} ({sum(x==tr[it['item_id']] for it,x in c)/len(c):.0%})")
d=[it for it in L if not combo(it)]
print(f"   the rest ({len(d)} lines) has no precedent; ML right on {sum(ml(it)==tr[it['item_id']] for it in d)} ({sum(ml(it)==tr[it['item_id']] for it in d)/len(d):.0%})")
# where they disagree
dis=[it for it in c if 0] 
both=[(it,x) for it,x in c]
agree=[(it,x) for it,x in both if x==ml(it)]; disag=[(it,x) for it,x in both if x!=ml(it)]
print(f"\nWhen precedent and ML agree ({len(agree)}): right {sum(x==tr[it['item_id']] for it,x in agree)} ({sum(x==tr[it['item_id']] for it,x in agree)/max(1,len(agree)):.0%})")
print(f"When they disagree ({len(disag)}): precedent right {sum(x==tr[it['item_id']] for it,x in disag)}, ML right {sum(ml(it)==tr[it['item_id']] for it,x in disag)}")
# the auto-accept idea: auto-accept only when they agree
print("\nRule 'auto-file only when precedent AND ML agree; everything else -> review':")
print(f"   would auto-file {len(agree)} lines; wrong {len(agree)-sum(x==tr[it['item_id']] for it,x in agree)}   (current system: auto-filed {sum(it['decision']=='auto_accept' for it in L)} model lines, wrong {sum(it['decision']=='auto_accept' and it['predicted_code']!=tr[it['item_id']] for it in L)})")
# Doris breakdown
dor=[(it,x) for it,x in c if 'DORIS' in jinv[it['invoice_id']]['seller_name']]
print(f"\n(of the precedent lines, Doris Castillo: {len(dor)} lines, right {sum(x==tr[it['item_id']] for it,x in dor)} -- the supplier whose July booking changed)")

print("\n===== SAME NUMBERS WITHOUT DORIS CASTILLO (the one supplier whose booking changed in July) =====")
L2=[it for it in L if 'DORIS' not in jinv[it['invoice_id']]['seller_name']]
def okk(it,x): return x==tr[it['item_id']]
print("lines:",len(L2)," ML alone right:",sum(okk(it,ml(it)) for it in L2),f"({sum(okk(it,ml(it)) for it in L2)/len(L2):.0%})")
c2=[(it,combo(it)) for it in L2 if combo(it)]
print(f"precedent covers {len(c2)}, right {sum(okk(it,x) for it,x in c2)} ({sum(okk(it,x) for it,x in c2)/len(c2):.0%});  ML on those same lines right {sum(okk(it,ml(it)) for it,x in c2)} ({sum(okk(it,ml(it)) for it,x in c2)/len(c2):.0%})")
ag=[(it,x) for it,x in c2 if x==ml(it)]
print(f"precedent AND ML agree: {len(ag)} lines, right {sum(okk(it,x) for it,x in ag)} ({sum(okk(it,x) for it,x in ag)/len(ag):.0%})")
dg=[(it,x) for it,x in c2 if x!=ml(it)]
print(f"they disagree: {len(dg)} lines; precedent right {sum(okk(it,x) for it,x in dg)}, ML right {sum(okk(it,ml(it)) for it,x in dg)}")
whole=sum(okk(it,comb_ml(it)) for it in L2); print(f"whole system precedent-first: {whole}/{len(L2)} ({whole/len(L2):.0%})")
cur=[it for it in L2 if it['decision']=='auto_accept']; print(f"current auto-accepted model lines: {len(cur)}, wrong {sum(not okk(it,ml(it)) for it in cur)} ({sum(okk(it,ml(it)) for it in cur)/len(cur):.0%} right)")
