"""Score the agent against a hand-labelled set: python3 eval.py [path/to/eval_set.json]

Compares each predicted quadrant and action flag with the 'expected' labels and
prints every disagreement. The score is only meaningful when the labels were set
by people and the run used a live model (the mock model is a keyword heuristic).
"""
import json
import sys
from collections import Counter

import config
import digest
import llm


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else config.BASE_DIR / "samples" / "eval_set.json"
    with open(path, encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    res = digest.summarize(digest.load_emails({"emails": [c["email"] for c in cases]}))
    cat_ok = act_ok = 0
    confusion = Counter()
    failures = []
    for case, got in zip(cases, res["items"]):
        exp = case["expected"]
        c_ok = got["category"] == exp["category"]
        a_ok = got["action_needed"] == exp["action_needed"]
        cat_ok += c_ok
        act_ok += a_ok
        confusion[(exp["category"], got["category"])] += 1
        if not (c_ok and a_ok):
            failures.append((case["id"], case["email"]["subject"] or "(no subject)", exp, got))
    n = len(cases)
    print(f"Mode: {llm.mode()} | Provider: {res['provider']} | Cases: {n}")
    print(f"Quadrant accuracy: {cat_ok}/{n} ({cat_ok / n:.0%})")
    print(f"Action-needed accuracy: {act_ok}/{n} ({act_ok / n:.0%})")
    print("\nConfusion (rows = expected, cols = predicted):")
    print("      " + "  ".join(config.CATEGORY_ORDER))
    for e in config.CATEGORY_ORDER:
        print(f"  {e}  " + "  ".join(f"{confusion[(e, p)]:>2}" for p in config.CATEGORY_ORDER))
    for w in res["warnings"]:
        print("WARNING:", w)
    print(f"\nDisagreements ({len(failures)}):")
    for cid, subj, exp, got in failures:
        print(f"  {cid} {subj[:48]!r}: expected {exp['category']}/action={exp['action_needed']}, "
              f"got {got['category']}/action={got['action_needed']}"
              + (" [unclassified]" if got.get("unclassified") else ""))


if __name__ == "__main__":
    main()
