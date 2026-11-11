#!/usr/bin/env python3
"""Build the hidden test instance table and the public train instance table.

* ``eval/test/instances.json`` (hidden): secret seeds, answers and text hashes
  for the test ladders.  Seeds are drawn once from ``secrets`` and kept.
* ``data/train_instances.json`` (public): the same ladders with public seeds.

Parity answers follow from the planted construction and are re-verified by
GF(2) elimination; MCN thresholds are set from the exact optimum computed by
the hidden minimax.  The builder also checks that the public generator in
``data/benchmark.py`` produces byte-identical text to the hidden copy on the
train split, so train and test are drawn from the same distribution.

Idempotent: existing entries are reused, missing ones are filled in.
"""

from __future__ import annotations

import json
import secrets
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
sys.path.insert(0, str(HERE))

import qip_hidden_gen as gen  # noqa: E402

CPU_BUDGET_S = 10.0
PARITY_SIZES = [10, 14, 18, 22, 26, 32, 40, 50, 64, 80, 100, 128]
PARITY_KINDS_PER_LEVEL = ["paper_false", "paper_true", "gen_true", "gen_true", "gen_false", "gen_false"]
MCN_SIZES = [8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 36, 40]
MCN_ANSWERS_PER_LEVEL = [True, True, False, False]

TEST_PATH = HERE / "instances.json"
TRAIN_PATH = WORKSPACE / "data" / "train_instances.json"


def _parity_entry(size: int, kind: str, seed: int) -> dict:
    answer = gen.parity_answer_by_gf2(size, kind, seed)
    text, answer2 = gen.parity_instance(size, kind, seed)
    assert answer == answer2
    return {"kind": kind, "seed": seed, "answer": answer, "sha256": gen.sha256_text(text)}


def _mcn_entry(size: int, answer: bool, seed: int) -> dict:
    params = gen.mcn_params(size, seed)
    opt = gen.mcn_optimum(params)
    threshold = opt if answer else opt + 1
    text = gen.mcn_instance(size, seed, threshold)
    return {
        "kind": "mcn_true" if answer else "mcn_false",
        "seed": seed,
        "answer": answer,
        "threshold": threshold,
        "optimum": opt,
        "sha256": gen.sha256_text(text),
    }


def build(path: Path, seed_fn, public: bool) -> dict:
    table = json.loads(path.read_text()) if path.exists() else {}
    table.setdefault("cpu_budget_s", CPU_BUDGET_S)
    exps = table.setdefault("experiments", {})
    plan = {
        "qrandomparity_ladder": [(s, PARITY_KINDS_PER_LEVEL) for s in PARITY_SIZES],
        "mcn_ladder": [(s, MCN_ANSWERS_PER_LEVEL) for s in MCN_SIZES],
    }
    for exp, levels in plan.items():
        exp_table = exps.setdefault(exp, {"levels": []})
        existing = {lvl["size"]: lvl for lvl in exp_table["levels"]}
        new_levels = []
        for level_idx, (size, kinds) in enumerate(levels):
            lvl = existing.get(size, {"size": size, "instances": []})
            while len(lvl["instances"]) < len(kinds):
                j = len(lvl["instances"])
                seed = seed_fn(exp, level_idx, j)
                if exp == "qrandomparity_ladder":
                    entry = _parity_entry(size, kinds[j], seed)
                else:
                    entry = _mcn_entry(size, kinds[j], seed)
                lvl["instances"].append(entry)
            new_levels.append(lvl)
            print(f"[{path.name}] {exp} size={size}: {len(lvl['instances'])} instances", flush=True)
        exp_table["levels"] = new_levels
        path.write_text(json.dumps(table, indent=1) + "\n")
    return table


def check_public_generator(train: dict) -> None:
    sys.path.insert(0, str(WORKSPACE))
    import data.benchmark as public  # noqa: E402

    for exp, exp_table in train["experiments"].items():
        for lvl in exp_table["levels"]:
            for spec in lvl["instances"]:
                text, answer = public.materialize(exp, lvl["size"], spec)
                if public.sha256_text(text) != spec["sha256"] or answer != spec["answer"]:
                    raise AssertionError(f"public generator drift: {exp} size={lvl['size']} seed={spec['seed']}")
    print("public generator matches hidden copy on the train split", flush=True)


def main() -> None:
    test = build(TEST_PATH, lambda exp, li, j: secrets.randbits(48), public=False)
    offsets = {"qrandomparity_ladder": 11_000_000, "mcn_ladder": 23_000_000}
    train = build(TRAIN_PATH, lambda exp, li, j: offsets[exp] + 1000 * li + j, public=True)
    check_public_generator(train)
    for name, table in (("test", test), ("train", train)):
        for exp, exp_table in table["experiments"].items():
            total = sum(len(l["instances"]) for l in exp_table["levels"])
            n_true = sum(i["answer"] for l in exp_table["levels"] for i in l["instances"])
            print(f"{name}: {exp}: {total} instances ({n_true} TRUE)")


if __name__ == "__main__":
    main()
