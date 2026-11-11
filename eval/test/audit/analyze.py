#!/usr/bin/env python3
"""Summarise the hidden-test audit (no hidden answers are written).

Reads outputs/audit/*/{scores_test.json,meta.json,details.json} and the frozen
scoring/scores_test.json, and writes hardening/summary.json and
hardening/results_table.md with per-case metrics and illustrative ranks:

    rank = sum_e w_e * sum_m |c_m| * dir_m * (value - reference) / sigma_m

where sigma_m is the population standard deviation of metric m over the honest
cohort (reference reruns, better and weaker variants, frozen reference and
baseline).  The live ranking cohort is unknown; these ranks are illustrative.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
OUT = WORKSPACE / "outputs" / "audit"


def main() -> None:
    reference = json.loads((WORKSPACE / "scoring" / "reference.json").read_text())
    exps = {k: v for k, v in reference["experiments"].items() if not k.startswith("_")}
    frozen = json.loads((WORKSPACE / "scoring" / "scores_test.json").read_text())["experiments"]

    cases: dict = {}
    for name in ("equips", "search_enumeration"):
        if all(name in frozen[e]["results"] for e in exps):
            group = "frozen_reference" if name == "equips" else "baseline"
            cases[name if name != "equips" else "reference_frozen"] = {
                "group": group,
                "metrics": {e: frozen[e]["results"][name] for e in exps},
                "failed": False,
            }
    for case_dir in sorted(p for p in OUT.iterdir() if p.is_dir()) if OUT.exists() else []:
        scores_path = case_dir / "scores_test.json"
        if not scores_path.exists() or not (case_dir / "meta.json").exists():
            continue
        meta = json.loads((case_dir / "meta.json").read_text())
        scores = json.loads(scores_path.read_text())["experiments"]
        details = json.loads((case_dir / "details.json").read_text()) if (case_dir / "details.json").exists() else {}
        detail = next(iter(details.values()), {})
        name = next(iter(scores[next(iter(exps))]["results"]))
        cases[case_dir.name] = {
            "group": meta["group"],
            "metrics": {e: scores[e]["results"][name] for e in exps},
            "failed": bool(detail.get("failed")),
            "reason": detail.get("reason"),
            "per_level": {
                e: [(lvl["size"], lvl.get("solved", 0)) for lvl in detail.get("levels", {}).get(e, [])]
                for e in exps
            },
            "elapsed_s": meta.get("elapsed_s"),
        }

    ref = cases["reference_frozen"]["metrics"]
    honest = [c for c in cases.values() if c["group"] in ("frozen_reference", "reference", "better", "weaker", "baseline")]
    sigma = {}
    for e, exp in exps.items():
        for m in exp["metrics"]:
            values = [c["metrics"][e][m] for c in honest]
            sigma[(e, m)] = statistics.pstdev(values) if len(values) > 1 else 0.0

    for c in cases.values():
        total = 0.0
        parts = {}
        for e, exp in exps.items():
            for m, mdef in exp["metrics"].items():
                direction = 1.0 if mdef["higher_is_better"] else -1.0
                s = sigma[(e, m)] or 1.0
                contrib = exp["weight"] * abs(mdef["coefficient"]) * direction * (c["metrics"][e][m] - ref[e][m]) / s
                parts[f"{e}.{m}"] = round(contrib, 4)
                total += contrib
        c["rank"] = round(total, 4)
        c["rank_parts"] = parts

    summary = {
        "weights": {e: exps[e]["weight"] for e in exps},
        "sigma": {f"{e}.{m}": round(v, 4) for (e, m), v in sigma.items()},
        "cases": cases,
    }
    hard = WORKSPACE / "hardening"
    hard.mkdir(exist_ok=True)
    (hard / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")

    order = {"frozen_reference": 0, "reference": 1, "better": 2, "weaker": 3, "baseline": 4, "shortcut": 5}
    lines = [
        "| Case | Group | " + " | ".join(exps) + " | Failed | Illustrative rank |",
        "|---|---|" + "---:|" * len(exps) + "---|---:|",
    ]
    for name, c in sorted(cases.items(), key=lambda kv: (order.get(kv[1]["group"], 9), -kv[1]["rank"])):
        vals = " | ".join(str(c["metrics"][e]["instances_solved"]) for e in exps)
        lines.append(f"| {name} | {c['group']} | {vals} | {'yes: ' + c['reason'] if c['failed'] else 'no'} | {c['rank']:+.3f} |")
    (hard / "results_table.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
