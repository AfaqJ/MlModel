#!/usr/bin/env bash
#
# docs/TEST_CHECKLIST.md "Before deploying", as a runnable gate rather than a
# list someone reads. Run it against the live revision straight after a deploy:
#
#   scripts/88_prove_deploy.sh https://mlmodel-ufmuwiq6ta-ew.a.run.app
#
# It is only evidence if it can fail, so it was validated first against a
# service built from current source on localhost, where all seven pass, and
# against the pre-2026-09-10 revision, where `transport_plate accepted` fails.
#
# Rolling back is a traffic shift, not a rebuild:
#   gcloud run services update-traffic mlmodel --region europe-west1 \
#     --to-revisions <REVISION>=100
set -uo pipefail
URL="${1:?usage: smoke.sh <service-url>}"
fail=0
ok(){ echo "PASS  $1"; }
no(){ echo "FAIL  $1"; fail=1; }

echo "--- /artifact-check"
curl -s -m 30 "$URL/artifact-check" | python3 -c '
import json,sys
d=json.load(sys.stdin)
f=d["files"]["model.onnx"]
print("model.onnx", f["size_bytes"], "lfs_pointer", f["looks_like_lfs_pointer"], "local", 278181947)
sys.exit(0 if f["looks_like_lfs_pointer"] is False and f["size_bytes"]==278181947 and all(
    not v["looks_like_lfs_pointer"] for v in d["files"].values()) else 1)' && ok "artifact-check" || no "artifact-check"

p(){ curl -s -m 60 -X POST "$URL/predict" -H 'Content-Type: application/json' -d "$1"; }

echo "--- business_rule: VENTA DE LECHE / VENTAS -> ING-0.1, auto_accept (the incident path)"
r=$(p '{"item_text":"VENTA DE LECHE","description":"","provider":"X","transaction_type":"VENTAS"}')
echo "$r" | head -c 300; echo
echo "$r" | python3 -c '
import json,sys
d=json.load(sys.stdin)
sys.exit(0 if d["predictions"][0]["code"]=="ING-0.1" and d["decision"]=="auto_accept" else 1)' && ok "business_rule" || no "business_rule"

echo "--- direction guard: VENTA DE LECHE / COMPRAS -> no ING- code"
r=$(p '{"item_text":"VENTA DE LECHE","description":"","provider":"X","transaction_type":"COMPRAS"}')
echo "$r" | head -c 300; echo
echo "$r" | python3 -c '
import json,sys
d=json.load(sys.stdin)
sys.exit(0 if not any(x["code"].startswith("ING-") for x in d["predictions"]) else 1)' && ok "direction guard" || no "direction guard"

echo "--- transport_plate is accepted (the reason for this deploy)"
r=$(curl -s -m 60 -o /dev/null -w '%{http_code}' -X POST "$URL/predict-batch" -H 'Content-Type: application/json' \
  -d '{"items":[{"input_id":"t1","item_text":"PRUEBA","description":"","provider":"P","meter_code":null,"transport_plate":null,"transaction_type":"COMPRAS"}]}')
echo "http $r"; [ "$r" = "200" ] && ok "transport_plate accepted" || no "transport_plate accepted"

echo "--- product_lookup -> EXP-2.3"
r=$(p '{"item_text":"VACUNA BRUCELLA ABORTUS CEPA RB-51","description":"","provider":"COLUN","transaction_type":"COMPRAS"}')
echo "$r" | head -c 260; echo
echo "$r" | python3 -c '
import json,sys
d=json.load(sys.stdin)
sys.exit(0 if d["predictions"][0]["code"]=="EXP-2.3" else 1)' && ok "product_lookup" || no "product_lookup"

echo "--- meter_lookup -> EXP-9.1"
r=$(p '{"item_text":"CONSUMO","description":"","provider":"CIA ELECTRICA OSORNO S A","meter_code":"12145473","transaction_type":"COMPRAS"}')
echo "$r" | head -c 260; echo
echo "$r" | python3 -c '
import json,sys
d=json.load(sys.stdin)
sys.exit(0 if d["predictions"][0]["code"]=="EXP-9.1" else 1)' && ok "meter_lookup" || no "meter_lookup"

echo "--- /predict-batch with 250 rows -> 0 errors"
# curl, not urllib: python's trust store does not carry the CA here and the
# resulting SSL error looks exactly like a service failure.
python3 -c '
import json
items=[{"input_id":"b%d"%i,"item_text":"SAL MINERAL SACO","description":"","provider":"PROVEEDOR",
        "meter_code":None,"transport_plate":None,"transaction_type":"COMPRAS"} for i in range(250)]
open("/tmp/.smoke250.json","w").write(json.dumps({"items":items}))'
curl -s -m 240 -X POST "$URL/predict-batch" -H 'Content-Type: application/json' --data-binary @/tmp/.smoke250.json | python3 -c '
import json,sys
d=json.load(sys.stdin); s=d["summary"]
print("count",s["count"],"errors",s["errors"],"latency_ms",d.get("latency_ms"))
sys.exit(0 if s["errors"]==0 and s["count"]==250 else 1)' && ok "predict-batch 250" || no "predict-batch 250"

echo
[ $fail -eq 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECKS FAILED"
exit $fail
