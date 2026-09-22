import json,urllib.request,collections,ssl,certifi,sys
S="/private/tmp/claude-501/-Users-afaq-Desktop-Mctech-ML-model/da960daa-a982-4f2d-8f8c-3ab725c62db0/scratchpad/"
URL="https://mlmodel-ufmuwiq6ta-ew.a.run.app"
inv={i["invoice_id"]:i for i in json.load(open(S+"july_invoices.json"))}
items=json.load(open(S+"july_items.json")); tr={x["item_id"]:x["true"] for x in json.load(open(S+"exact_truth.json"))}
L=[it for it in items if it["prediction_source"]=="model" and it["item_id"] in tr]
ctx=ssl.create_default_context(cafile=certifi.where())
def call(batch):
    body=json.dumps({"items":batch,"top_k":3}).encode()
    req=urllib.request.Request(URL+"/predict-batch",data=body,headers={"Content-Type":"application/json"})
    return json.load(urllib.request.urlopen(req,timeout=180,context=ctx))
def run(with_provider):
    out={}
    for k in range(0,len(L),40):
        ch=L[k:k+40]
        payload=[{"input_id":it["item_id"],"item_text":(it["item_text"] or it["description"] or "-")[:500],"description":(it["description"] or "")[:500],
                  "provider":(inv[it["invoice_id"]]["seller_name"] if with_provider else "")[:250],"transaction_type":"COMPRAS"} for it in ch]
        r=call(payload)
        res=r.get("results") or r.get("items") or r
        for row in res:
            out[row["input_id"]]=row
    return out
a=run(True); b=run(False)
def top(row): return row["predictions"][0]["code"]
def sc(row): return row["predictions"][0]["score"]
n=len(L)
print("lines:",n)
same=sum(top(a[i["item_id"]])==i["predicted_code"] for i in L); print("sanity: live call with supplier reproduces the stored answer on",same,"of",n)
ra=sum(top(a[i["item_id"]])==tr[i["item_id"]] for i in L); rb=sum(top(b[i["item_id"]])==tr[i["item_id"]] for i in L)
print(f"right WITH supplier name: {ra}/{n} ({ra/n:.0%})   right with supplier name BLANKED: {rb}/{n} ({rb/n:.0%})")
ch=sum(top(a[i['item_id']])!=top(b[i['item_id']]) for i in L); print("answer changes when the supplier is blanked on",ch,"lines")
# only lines whose supplier is unseen in training vs seen? and by auto-accept
def dec(row): return row["decision"]
for lab,f in (("auto-accepted WITH supplier",lambda r:dec(a[r['item_id']])=='auto_accept'),("auto-accepted with supplier BLANKED",lambda r:dec(b[r['item_id']])=='auto_accept')):
    p=[i for i in L if f(i)]
    src=a if 'WITH' in lab else b
    right=sum(top(src[i['item_id']])==tr[i['item_id']] for i in p)
    print(f"  {lab:38} {len(p):3} lines, right {right} ({right/max(1,len(p)):.0%}), wrong {len(p)-right}")
dor=[i for i in L if 'DORIS' in inv[i['invoice_id']]['seller_name']]
print("Doris lines:",len(dor),"| with supplier ->",collections.Counter(top(a[i['item_id']]) for i in dor).most_common(2),"| blanked ->",collections.Counter(top(b[i['item_id']]) for i in dor).most_common(3),"| truth EXP-14.4 in",sum(tr[i['item_id']]=='EXP-14.4' for i in dor))
