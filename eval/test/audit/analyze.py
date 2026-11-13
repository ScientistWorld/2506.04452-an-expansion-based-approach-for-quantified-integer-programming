#!/usr/bin/env python3
"""Summarise the hidden-test audit (no hidden answers or seeds are written).

Reads outputs/audit/*/{details.json,meta.json} (frozen reference:
outputs/audit/reference_frozen/details.json; train: outputs/audit/train_details.json)
and writes hardening/summary.json and hardening/results_table.md.

Every evaluation records, per instance, the instruction count and whether the
answer given within the budget was correct.  The solvers in this audit do not
read the budget, so their runs are the same under any budget up to the one
they ran with; ``--budget B`` rescoring applies the evaluator's rules (solved
iff correct and within B; a wrong decision within B fails the run; two
consecutive empty levels end a ladder) to the recorded counts.

    rank = sum_e w_e * |c_e| * (value_e - reference_e) / sigma_e

sigma_e is the population standard deviation of experiment e over the honest
cohort (frozen reference, reference reruns, better and weaker variants,
baseline).  The live ranking cohort is unknown; these ranks are illustrative.
Subset cases (scored on a few ladder levels only) are compared with the frozen
reference on the same levels instead of being ranked.

``--write-scores`` regenerates scoring/scores_test.json and
scoring/scores_train.json (and scoring/scores.json) from the frozen reference
and train runs at the given budget.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
OUT = WORKSPACE / "outputs" / "audit"
EXPS = ("qrandomparity_ladder", "mcn_ladder")
ZERO_LEVELS_BEFORE_STOP = 2


def rescore(detail: dict, budget: int, subset: bool = False) -> dict:
    """Metrics, per-level counts and failure of one solver at ``budget``."""
    out = {"failed": bool(detail.get("failed")), "reason": detail.get("reason"), "metrics": {}, "per_level": {}}
    if detail.get("failed") and not detail.get("levels"):
        out["metrics"] = {e: 0 for e in EXPS}
        out["per_level"] = {e: [] for e in EXPS}
        return out
    for e in EXPS:
        total, streak, rows = 0, 0, []
        for lvl in detail.get("levels", {}).get(e, []):
            if lvl.get("skipped") or (streak >= ZERO_LEVELS_BEFORE_STOP and not subset):
                rows.append([lvl["size"], 0])
                continue
            recs = lvl.get("instances") or []
            if not recs:
                rows.append([lvl["size"], lvl.get("solved", 0)])
                total += lvl.get("solved", 0)
                streak = streak + 1 if lvl.get("solved", 0) == 0 else 0
                continue
            within = [r for r in recs if r.get("correct") is not None and (r.get("instructions") or 0) <= budget]
            if any(r["correct"] is False for r in within):
                out["failed"] = True
                out["reason"] = out["reason"] or f"wrong decision on {e} at size {lvl['size']}"
            solved = sum(1 for r in within if r["correct"])
            rows.append([lvl["size"], solved])
            total += solved
            streak = streak + 1 if solved == 0 else 0
        out["metrics"][e] = total
        out["per_level"][e] = rows
    if out["failed"]:
        out["metrics"] = {e: 0 for e in EXPS}
    return out


def instance_vector(detail: dict, budget: int) -> dict:
    """{(exp, size, slot): (solved, instructions)} for paired comparisons."""
    vec = {}
    for e in EXPS:
        for lvl in detail.get("levels", {}).get(e, []):
            for i, r in enumerate(lvl.get("instances") or []):
                ok = r.get("correct") is True and (r.get("instructions") or 0) <= budget
                vec[(e, lvl["size"], i)] = (ok, r.get("instructions"))
    return vec


def load_details(path: Path) -> dict:
    data = json.loads(path.read_text())
    return data.get("solvers", data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget", type=int, default=None, help="instructions (default: the evaluator's budget)")
    parser.add_argument("--write-scores", action="store_true")
    args = parser.parse_args()
    import importlib.util

    spec = importlib.util.spec_from_file_location("hidden_evaluate", HERE.parent / "evaluate.py")
    ev = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ev)
    budget = args.budget or ev.BUDGET_INSTRUCTIONS

    reference = json.loads((WORKSPACE / "scoring" / "reference.json").read_text())
    exps = {k: v for k, v in reference["experiments"].items() if not k.startswith("_")}

    cases: dict = {}
    raw: dict = {}
    frozen = load_details(OUT / "reference_frozen" / "details.json")
    for name, label, group in (("equips", "reference_frozen", "frozen_reference"), ("search_enumeration", "search_enumeration", "baseline")):
        if name in frozen:
            cases[label] = rescore(frozen[name], budget) | {"group": group}
            raw[label] = frozen[name]
    for case_dir in sorted(p for p in OUT.iterdir() if p.is_dir()) if OUT.exists() else []:
        if case_dir.name == "reference_frozen" or not (case_dir / "meta.json").exists():
            continue
        meta = json.loads((case_dir / "meta.json").read_text())
        if meta.get("returncode") != 0 or not (case_dir / "details.json").exists():
            continue
        detail = next(iter(load_details(case_dir / "details.json").values()), {})
        cases[case_dir.name] = rescore(detail, budget, subset=bool(meta.get("subset"))) | {
            "group": meta["group"], "elapsed_s": meta.get("elapsed_s"), "legacy_evaluator": meta.get("legacy_evaluator")}
        raw[case_dir.name] = detail

    ref = cases["reference_frozen"]["metrics"]
    honest = [c for c in cases.values() if c["group"] in ("frozen_reference", "reference", "better", "weaker", "baseline")]
    sigma = {e: (statistics.pstdev([c["metrics"][e] for c in honest]) if len(honest) > 1 else 0.0) for e in exps}

    ref_vec = instance_vector(raw["reference_frozen"], budget)
    ref_levels = cases["reference_frozen"]["per_level"]
    for name, c in cases.items():
        if c["group"] == "shortcut_subset":
            comparison = {}
            for e in exps:
                sizes = {s for s, _ in c["per_level"][e]}
                comparison[e] = {"case": sum(v for _, v in c["per_level"][e]),
                                 "reference_same_levels": sum(v for s, v in ref_levels.get(e, []) if s in sizes)}
            c["subset_comparison"] = comparison
            c["rank"] = None
            continue
        total, parts = 0.0, {}
        for e, exp in exps.items():
            mdef = exp["metrics"]["instances_solved"]
            direction = 1.0 if mdef["higher_is_better"] else -1.0
            contrib = exp["weight"] * abs(mdef["coefficient"]) * direction * (c["metrics"][e] - ref[e]) / (sigma[e] or 1.0)
            parts[e] = round(contrib, 4)
            total += contrib
        c["rank"] = round(total, 4)
        c["rank_parts"] = parts
        if not c["failed"] and name != "reference_frozen":
            vec = instance_vector(raw[name], budget)
            paired = {}
            for e in exps:
                keys = [k for k in ref_vec if k[0] == e and k in vec]
                paired[e] = {"only_case": sum(1 for k in keys if vec[k][0] and not ref_vec[k][0]),
                             "only_reference": sum(1 for k in keys if ref_vec[k][0] and not vec[k][0])}
            c["paired_vs_reference"] = paired

    # determinism: unchanged reference rerun vs frozen run, per instance
    determinism = None
    if "reference_rerun" in raw:
        rv = instance_vector(raw["reference_rerun"], budget)
        diffs, flips = [], 0
        for k, (ok, ins) in ref_vec.items():
            if k in rv and ins and rv[k][1]:
                diffs.append(abs(rv[k][1] - ins) / ins)
                flips += ok != rv[k][0]
        determinism = {"instances_compared": len(diffs), "solved_flips": flips,
                       "max_relative_instruction_diff": max(diffs) if diffs else None,
                       "median_relative_instruction_diff": statistics.median(diffs) if diffs else None}

    # cross-node: the frozen run of an earlier job (another compute node) on the
    # levels both runs share (the parity ladder did not change between jobs)
    cross = None
    prev_path = OUT / "job1_reference_frozen_details.json"
    if prev_path.exists():
        prev = load_details(prev_path)
        cross = {}
        for name in ("equips", "search_enumeration"):
            if name not in prev or name not in frozen:
                continue
            a = instance_vector(prev[name], budget)
            b = instance_vector(frozen[name], budget)
            keys = [k for k in a if k in b and k[0] == "qrandomparity_ladder" and a[k][1] and b[k][1]]
            diffs = [abs(a[k][1] - b[k][1]) / a[k][1] for k in keys]
            cross[name] = {"instances_compared": len(keys), "solved_flips": sum(a[k][0] != b[k][0] for k in keys),
                           "solved_earlier_job": sum(a[k][0] for k in keys), "solved_this_job": sum(b[k][0] for k in keys),
                           "median_relative_instruction_diff": statistics.median(diffs) if diffs else None,
                           "max_relative_instruction_diff": max(diffs) if diffs else None}

    # calibration: instructions per CPU-second of the frozen reference
    rates, modes = [], set()
    for e in EXPS:
        for lvl in raw["reference_frozen"].get("levels", {}).get(e, []):
            for r in lvl.get("instances") or []:
                modes.add(r.get("mode"))
                if r.get("correct") and r.get("cpu_s") and r["cpu_s"] > 0.5 and r.get("instructions"):
                    rates.append(r["instructions"] / r["cpu_s"])
    calibration = {"median_instructions_per_cpu_s": statistics.median(rates) if rates else None,
                   "instances": len(rates), "modes": sorted(m for m in modes if m)}

    train = None
    if (OUT / "train_details.json").exists():
        td = load_details(OUT / "train_details.json")
        train = {name: rescore(d, budget)["metrics"] for name, d in td.items()}

    summary = {
        "budget_instructions": budget,
        "weights": {e: exps[e]["weight"] for e in exps},
        "sigma": {e: round(v, 4) for e, v in sigma.items()},
        "determinism_rerun": determinism,
        "determinism_cross_node": cross,
        "calibration": calibration,
        "train": train,
        "cases": cases,
    }
    hard = WORKSPACE / "hardening"
    hard.mkdir(exist_ok=True)
    (hard / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")

    order = {"frozen_reference": 0, "reference": 1, "better": 2, "weaker": 3, "baseline": 4, "shortcut": 5, "shortcut_subset": 6}
    lines = [
        f"Budget: {budget:.3g} user-space instructions per instance.  sigma: "
        + ", ".join(f"{e} {sigma[e]:.2f}" for e in exps),
        "",
        "| Case | Group | " + " | ".join(exps) + " | Failed | Illustrative rank | Paired vs reference (only case / only ref) |",
        "|---|---|" + "---:|" * len(exps) + "---|---:|---|",
    ]
    ranked = sorted(cases.items(), key=lambda kv: (order.get(kv[1]["group"], 9), -(kv[1]["rank"] or 0)))
    for name, c in ranked:
        if c["group"] == "shortcut_subset":
            vals = " | ".join(f"{c['subset_comparison'][e]['case']} (ref {c['subset_comparison'][e]['reference_same_levels']})" for e in exps)
            rank = "subset" + (" (legacy evaluator)" if c.get("legacy_evaluator") else "")
        else:
            vals = " | ".join(str(c["metrics"][e]) for e in exps)
            rank = f"{c['rank']:+.3f}"
        paired = c.get("paired_vs_reference")
        ptxt = "; ".join(f"{e.split('_')[0]} {paired[e]['only_case']}/{paired[e]['only_reference']}" for e in exps) if paired else ""
        failed = "yes: " + str(c["reason"]) if c["failed"] else "no"
        lines.append(f"| {name} | {c['group']} | {vals} | {failed} | {rank} | {ptxt} |")
    lines += ["", f"Determinism (unchanged reference rerun vs frozen run): {determinism}",
              f"Cross-node (frozen run of the earlier job vs this one, parity ladder): {cross}",
              f"Calibration: {calibration}", f"Train (same budget): {train}", "",
              "Per-level solved counts (size:solved):", ""]
    for name, c in ranked:
        for e in exps:
            lines.append(f"- {name} / {e}: " + " ".join(f"{s}:{v}" for s, v in c["per_level"][e]))
    (hard / "results_table.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

    if args.write_scores:
        def scores_from(details: dict) -> dict:
            res = {n: rescore(d, budget)["metrics"] for n, d in details.items()}
            return {"experiments": {e: {"results": {n: {"instances_solved": m[e]} for n, m in res.items()}} for e in EXPS}}

        (WORKSPACE / "scoring" / "scores_test.json").write_text(json.dumps(scores_from(frozen), indent=2) + "\n")
        if (OUT / "train_details.json").exists():
            st = scores_from(load_details(OUT / "train_details.json"))
            for name in ("scores_train.json", "scores.json"):
                (WORKSPACE / "scoring" / name).write_text(json.dumps(st, indent=2) + "\n")
        print(f"scores rewritten at budget {budget}")


if __name__ == "__main__":
    main()
