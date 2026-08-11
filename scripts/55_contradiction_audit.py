"""Contradiction audit for gold — read-only. Flags near-identical INPUT TEXT mapped to
different category codes, which corrupts SetFit's contrastive fine-tuning (same text can't be
pulled toward two clusters, and it degrades neighbouring categories via contrastive negatives).

Reports collisions at three exact/normalized keys (item_text ; item_text+description ;
item_text+description+provider) and — if sentence-transformers + a cached multilingual model are
available — embedding near-duplicate cross-category pairs. Writes Data/gold/_contradiction_report.csv.

Re-run after ANY gold change (new folder/silver import, relabels) before training. Nothing is
modified in gold; this only reports. Intentionally-kept adjacency cases (e.g. the three electricity
buckets resolved by top-3 at inference) will still show here — read them as expected, not new bugs.

Usage:  python3 scripts/55_contradiction_audit.py [--cosine 0.90]
"""
import csv, re, sys, unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "Data" / "gold" / "_master_gold.csv"
TAX = ROOT / "Data" / "current_context_2026_06_30" / "taxonomy_from_plan.csv"
OUT = ROOT / "Data" / "gold" / "_contradiction_report.csv"
COSINE = 0.90
if "--cosine" in sys.argv:
    COSINE = float(sys.argv[sys.argv.index("--cosine") + 1])

def rd(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))

def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def norm(s):
    s = strip_accents((s or "").upper())
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

M = rd(GOLD)
leaf = {r["new_code"]: r["leaf"] for r in rd(TAX)}
print(f"gold rows: {len(M)}")

report_rows = []

def sweep(keyfn, label):
    groups = defaultdict(list)
    for r in M:
        k = keyfn(r)
        if not k or k == ".":
            continue
        groups[k].append(r)
    conflicts = {k: v for k, v in groups.items() if len({x["category_code"] for x in v}) > 1}
    nrows = sum(len(v) for v in conflicts.values())
    print(f"\n### {label}: {len(conflicts)} colliding groups / {nrows} rows")
    for k, v in sorted(conflicts.items()):
        cats = defaultdict(list)
        for r in v:
            cats[r["category_code"]].append(r)
        cat_str = " | ".join(
            f"{c}={leaf.get(c,'?')} x{len(rs)} [{','.join(sorted({x['source'] for x in rs}))}]"
            for c, rs in cats.items()
        )
        print(f"  [{k[:55]}]  {cat_str}")
        for r in v:
            report_rows.append({
                "check": label, "key": k, "gold_id": r["gold_id"],
                "category_code": r["category_code"], "leaf": r["leaf"],
                "source": r["source"], "item_text": r["item_text"],
                "description": r["description"], "provider": r["provider"],
            })
    return conflicts

sweep(lambda r: norm(r["item_text"]), "A_item_text")
sweep(lambda r: norm(r["item_text"] + " " + r["description"]), "B_item_text+description")
sweep(lambda r: norm(r["item_text"] + " " + r["description"] + " " + r["provider"]),
      "C_item_text+description+provider")

# --- optional embedding near-duplicate sweep ---
try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    # prefer the real base model if cached; else the cached MiniLM proxy
    for name in ("sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
                 "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        try:
            model = SentenceTransformer(name)
            break
        except Exception:
            model = None
    if model is None:
        raise RuntimeError("no cached multilingual model")
    print(f"\n### D_embedding_near_dup (cosine >= {COSINE}) using {name.split('/')[-1]}")
    texts = {}
    for r in M:
        t = norm(r["item_text"])
        if len(t) < 3 or t == ".":
            continue
        texts.setdefault(t, defaultdict(list))[r["category_code"]].append(r["gold_id"])
    distinct = list(texts)
    emb = np.asarray(model.encode(distinct, batch_size=64, normalize_embeddings=True,
                                  show_progress_bar=False), dtype=np.float32)
    sims = emb @ emb.T
    iu = np.triu_indices(len(distinct), k=1)
    pairs = []
    for i, j in zip(*iu):
        s = float(sims[i, j])
        if s < COSINE:
            continue
        ci, cj = set(texts[distinct[i]]), set(texts[distinct[j]])
        if ci != cj:
            pairs.append((s, distinct[i], sorted(ci), distinct[j], sorted(cj)))
    pairs.sort(reverse=True)
    print(f"  {len(pairs)} cross-category near-duplicate text pairs")
    for s, t1, c1, t2, c2 in pairs:
        report_rows.append({
            "check": "D_embedding_near_dup", "key": f"cos={s:.3f}",
            "gold_id": "", "category_code": ",".join(c1 + c2), "leaf": "",
            "source": "", "item_text": t1, "description": t2, "provider": "",
        })
except Exception as e:
    print(f"\n### D_embedding_near_dup skipped ({e})")

with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["check", "key", "gold_id", "category_code", "leaf",
                                       "source", "item_text", "description", "provider"])
    w.writeheader()
    w.writerows(report_rows)
print(f"\nwrote {OUT} ({len(report_rows)} rows)")
