#!/usr/bin/env python3
"""Measure the category proposal against lines whose answer we already know.

Read-only. Nothing is written.

A category proposal is a precedent search: given a line's wording, look up how
comparable lines were filed before and propose that. This measures whether that
search is right, on the only honest test set available -- the 7,927 lines a
human confirmed.

The measurement is held out. Every line's OWN row is removed from its evidence
before the proposal is formed, which is the same rule the batch review already
follows: a batch may not cite itself.

The headline number is not accuracy. It is how often the proposal is CONFIDENTLY
WRONG -- wrong while resting on same-wording evidence, which is the case that
would talk Cristian into a bad decision. A proposal that abstains costs a
review; a proposal that is confidently wrong costs trust.

    .venv-backend/bin/python scripts/87_measure_precedent_quality.py [sample_size]
"""
from __future__ import annotations
import collections, json, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from supabase_rest import Rest, load_env  # noqa: E402


def main() -> None:
    sample_size = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    url, key = load_env()
    r = Rest(url, key)

    def rpc(fn, **args):
        _, body = r._request("POST", f"rpc/{fn}", body=args)
        return json.loads(body)

    truth = r.get("invoice_items", "item_id,item_text,catalog_item_id,meter_code,final_code",
                  "final_categories_id=not.is.null")
    print(f"{len(truth)} human-confirmed lines; sampling {sample_size}")
    random.seed(37)                      # fixed, so the number is reproducible
    sample = random.sample(truth, min(sample_size, len(truth)))

    stats = collections.Counter()
    confident_errors: list[tuple[str, str, str, int]] = []

    for line in sample:
        rows = rpc("yunt_category_precedent",
                   p_item_text=line["item_text"],
                   p_catalog_item_id=line["catalog_item_id"],
                   p_supplier_rut=None, p_meter_code=line["meter_code"],
                   p_batch_id=None, p_limit=12)
        # Hold out: a line may not be its own evidence.
        rows = [e for e in rows if e["evidence_item_id"] != line["item_id"]]
        if not rows:
            stats["abstained"] += 1
            continue

        # The proposal is the category most of the surviving evidence agrees on,
        # with exact-meter evidence outranking same wording and looser matches.
        weight: dict[str, float] = collections.defaultdict(float)
        for e in rows:
            weight[e["category_code"]] += {
                "same_meter": 9.0,
                "same_wording": 3.0,
            }.get(e["match_basis"], 1.0)
        proposal = max(weight, key=weight.get)

        same_meter = [e for e in rows if e["match_basis"] == "same_meter"]
        same_wording = [e for e in rows if e["match_basis"] == "same_wording"]
        confident = bool(same_meter or same_wording)

        if proposal == line["final_code"]:
            stats["correct_confident" if confident else "correct_weak"] += 1
        else:
            stats["wrong_confident" if confident else "wrong_weak"] += 1
            if confident:
                confident_errors.append(
                    (line["item_text"][:44], line["final_code"], proposal,
                     len(same_meter) + len(same_wording)))

    total = sum(stats.values())
    answered = total - stats["abstained"]
    correct = stats["correct_confident"] + stats["correct_weak"]
    print(f"\nof {total} lines")
    print(f"  abstained (no precedent)  {stats['abstained']:4}  {stats['abstained']/total:6.1%}")
    print(f"  proposed something        {answered:4}  {answered/total:6.1%}")
    if answered:
        print(f"\nof the {answered} proposals")
        print(f"  correct                 {correct:4}  {correct/answered:6.1%}")
        print(f"    on same wording       {stats['correct_confident']:4}")
        print(f"    on looser evidence    {stats['correct_weak']:4}")
        print(f"  wrong                   {answered-correct:4}  {(answered-correct)/answered:6.1%}")
        print(f"    on looser evidence    {stats['wrong_weak']:4}  (cheap: reads as a guess)")
        print(f"    CONFIDENTLY WRONG     {stats['wrong_confident']:4}  "
              f"{stats['wrong_confident']/answered:6.2%}  (expensive: reads as a fact)")

    # Remaining ambiguity after preserving the meter context that actually
    # decides the electricity account. Wording alone is not the domain key.
    byword: dict[tuple[str, str], collections.Counter] = collections.defaultdict(collections.Counter)
    for row in truth:
        key = ((row["item_text"] or "").strip().lower(), (row["meter_code"] or "").strip().upper())
        byword[key][row["final_code"]] += 1
    ambiguous = {w: c for w, c in byword.items() if len(c) > 1 and sum(c.values()) >= 3}
    covered = sum(sum(c.values()) for c in ambiguous.values())
    print(f"\nremaining context-level ambiguity")
    print(f"  wording + meter pairs filed under several categories  {len(ambiguous)}")
    print(f"  confirmed lines they cover                    {covered}  "
          f"{covered/len(truth):.1%}")
    worst = sorted(ambiguous.items(), key=lambda kv: -sum(kv[1].values()))[:5]
    for (word, meter), counter in worst:
        spread = ", ".join(f"{k}:{v}" for k, v in counter.most_common())
        print(f"    {word[:32]:34} meter={meter[:12]:12} {spread}")

    if confident_errors:
        print(f"\nthe confidently wrong ones, all {len(confident_errors)}:")
        print(f"  {'wording':46} {'truth':12} {'proposed':12} exact-context rows")
        for text, truth_code, proposal, n in confident_errors[:25]:
            print(f"  {text:46} {truth_code:12} {proposal:12} {n}")


if __name__ == "__main__":
    main()
