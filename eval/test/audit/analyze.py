#!/usr/bin/env python3
"""Summarise the hidden-test audit (no hidden answers or seeds are written).

Reads outputs/audit/*/{scores_test.json,meta.json,details.json}, the frozen
scoring/scores_test.json (+ outputs/audit/reference_frozen/details.json) and
writes hardening/summary.json and hardening/results_table.md:

    rank = sum_e w_e * sum_m |c_m| * dir_m * (value - reference) / sigma_m

sigma_m is the population standard deviation of metric m over the honest
cohort (frozen reference, reference reruns, better and weaker variants,
baseline).  The live ranking cohort is unknown; these ranks are illustrative.
Subset cases (scored on a few ladder levels only) are compared with the frozen
reference on the same levels instead of being ranked.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
OUT = WORKSPACE / "outputs" / "audit"


def per_level(detail: dict, exps) -> dict:
    return {
        e: [[lvl["size"], lvl.get("solved", 0)] for lvl in detail.get("levels", {}).get(e, [])]
        for e in exps
    }


def main() -> None:
    reference = json.loads((WORKSPACE / "scoring" / "reference.json").read_text())
    exps = {k: v for k, v in reference["experiments"].items() if not k.startswith("_")}
    frozen = json.loads((OUT / "reference_frozen" / "scores_test.json").read_text())["experiments"]
    frozen_details = {}
    if (OUT / "reference_frozen" / "details.json").exists():
        frozen_details = json.loads((OUT / "reference_frozen" / "details.json").read_text())

    cases: dict = {}
    for name, label, group in (("equips", "reference_frozen", "frozen_reference"), ("search_enumeration", "search_enumeration", "baseline")):
        if all(name in frozen[e]["results"] for e in exps):
            cases[label] = {
                "group": group,
                "metrics": {e: frozen[e]["results"][name] for e in exps},
                "failed": bool(frozen_details.get(name, {}).get("failed")),
                "reason": frozen_details.get(name, {}).get("reason"),
                "per_level": per_level(frozen_details.get(name, {}), exps),
            }
    for case_dir in sorted(p for p in OUT.iterdir() if p.is_dir()) if OUT.exists() else []:
        if case_dir.name == "reference_frozen":
            continue
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
            "per_level": per_level(detail, exps),
            "elapsed_s": meta.get("elapsed_s"),
        }

    ref = cases["reference_frozen"]["metrics"]
    honest = [c for c in cases.values() if c["group"] in ("frozen_reference", "reference", "better", "weaker", "baseline")]
    sigma = {}
    for e, exp in exps.items():
        for m in exp["metrics"]:
            values = [c["metrics"][e][m] for c in honest]
            sigma[(e, m)] = statistics.pstdev(values) if len(values) > 1 else 0.0

    ref_levels = cases["reference_frozen"]["per_level"]
    for c in cases.values():
        if c["group"] == "shortcut_subset":
            comparison = {}
            for e in exps:
                sizes = {s for s, _ in c["per_level"][e]}
                ref_on_subset = sum(v for s, v in ref_levels.get(e, []) if s in sizes)
                comparison[e] = {"case": sum(v for _, v in c["per_level"][e]), "reference_same_levels": ref_on_subset}
            c["subset_comparison"] = comparison
            c["rank"] = None
            continue
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

    order = {"frozen_reference": 0, "reference": 1, "better": 2, "weaker": 3, "baseline": 4, "shortcut": 5, "shortcut_subset": 6}
    lines = [
        "| Case | Group | " + " | ".join(exps) + " | Failed | Illustrative rank |",
        "|---|---|" + "---:|" * len(exps) + "---|---:|",
    ]
    for name, c in sorted(cases.items(), key=lambda kv: (order.get(kv[1]["group"], 9), -(kv[1]["rank"] or 0))):
        if c["group"] == "shortcut_subset":
            vals = " | ".join(f"{c['subset_comparison'][e]['case']} (ref {c['subset_comparison'][e]['reference_same_levels']})" for e in exps)
            rank = "subset"
        else:
            vals = " | ".join(str(c["metrics"][e]["instances_solved"]) for e in exps)
            rank = f"{c['rank']:+.3f}"
        failed = "yes: " + str(c["reason"]) if c["failed"] else "no"
        lines.append(f"| {name} | {c['group']} | {vals} | {failed} | {rank} |")
    lines.append("")
    lines.append("Per-level solved counts (size:solved):")
    lines.append("")
    for name, c in sorted(cases.items(), key=lambda kv: (order.get(kv[1]["group"], 9), -(kv[1]["rank"] or 0))):
        for e in exps:
            row = " ".join(f"{s}:{v}" for s, v in c["per_level"][e])
            lines.append(f"- {name} / {e}: {row}")
    (hard / "results_table.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
