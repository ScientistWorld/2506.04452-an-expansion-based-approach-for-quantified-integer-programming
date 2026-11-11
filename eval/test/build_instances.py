#!/usr/bin/env python3
"""Build the hidden test instance table and the public train instance table.

* ``eval/test/instances.json`` (hidden): secret seeds and answers for the test
  ladders, one text digest per level (no per-instance hashes).
* ``data/train_instances.json`` (public): the same ladders with public seeds
  and per-instance text hashes.

Ground truth
------------
* Parity family: the answer follows from the planted construction and is
  re-derived independently by GF(2) elimination (plus, for the cardinality
  kinds, the cardinality row evaluated on the variables the system pins).
* MCN family, sizes <= 40: exact bitmask minimax over full-budget choices.
* MCN family, larger sizes: exact optimum by binary search over the threshold
  with a hidden copy of an expansion-based CEGAR solver (CP-SAT backend), each
  decision run to completion within generous caps; graphs whose optimum is not
  certified within the caps are replaced by fresh seeds.  The CEGAR solver is
  cross-checked against the bitmask minimax on the largest exact levels first.
  The extended ladder grows until a level cannot be filled, a time budget is
  spent, or two consecutive levels are far beyond a 10 s CPU budget for the
  ground-truth solver itself.  Once finished, the extension is frozen.

The builder checks that the public generator in ``data/benchmark.py`` produces
byte-identical text to the hidden copy on the train split.

Idempotent: existing entries are reused, missing ones are filled in.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
sys.path.insert(0, str(HERE))

import qip_hidden_gen as gen  # noqa: E402

CPU_BUDGET_S = 10.0
PARITY_SIZES = [10, 14, 18, 22, 26, 32, 40, 50, 64, 80, 100, 128, 160, 256, 400, 640, 1000]
PARITY_KINDS_PER_LEVEL = [
    "paper_false", "paper_true", "gen_true", "gen_true", "gen_false", "gen_false", "card_true", "card_false",
]
MCN_EXACT_SIZES = [8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 36, 40]
MCN_EXTENDED_SIZES = [48, 56, 64, 80, 96, 112, 128, 160, 192, 256]
MCN_ANSWERS_PER_LEVEL = [True, True, False, False]

GT_DECISION_CAP_S = float(os.environ.get("QIP_GT_DECISION_CAP_S", "100"))
GT_GRAPH_CAP_S = float(os.environ.get("QIP_GT_GRAPH_CAP_S", "240"))
GT_TRIES_PER_SLOT = 3
GT_BEYOND_REACH_S = 3.0 * CPU_BUDGET_S
GT_DEADLINE_S = float(os.environ.get("QIP_GT_DEADLINE_S", "6000"))

TEST_PATH = HERE / "instances.json"
TRAIN_PATH = WORKSPACE / "data" / "train_instances.json"
GT_CACHE = HERE / ".gt_cache.json"
TRAIN_OFFSETS = {"qrandomparity_ladder": 11_000_000, "mcn_ladder": 23_000_000}


def log(msg: str) -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------------
# Seeds
# --------------------------------------------------------------------------


def test_seed(secret: int, exp: str, level_idx: int, j: int, attempt: int = 0) -> int:
    blob = f"{secret}:{exp}:{level_idx}:{j}:{attempt}".encode()
    return int.from_bytes(hashlib.sha256(blob).digest()[:6], "big")


def train_seed(exp: str, level_idx: int, j: int, attempt: int = 0) -> int:
    return TRAIN_OFFSETS[exp] + 1000 * level_idx + j + 100 * attempt


# --------------------------------------------------------------------------
# Entries
# --------------------------------------------------------------------------


def parity_entry(size: int, kind: str, seed: int) -> dict:
    answer = gen.parity_answer_by_gf2(size, kind, seed)
    text, answer2 = gen.parity_instance(size, kind, seed)
    assert answer == answer2
    return {"kind": kind, "seed": seed, "answer": answer, "sha256": gen.sha256_text(text)}


def mcn_entry(size: int, answer: bool, seed: int, opt: int, gt: str, gt_cpu=None) -> dict:
    threshold = opt if answer else opt + 1
    text = gen.mcn_instance(size, seed, threshold)
    entry = {
        "kind": "mcn_true" if answer else "mcn_false",
        "seed": seed,
        "answer": answer,
        "threshold": threshold,
        "optimum": opt,
        "ground_truth": gt,
        "sha256": gen.sha256_text(text),
    }
    if gt_cpu is not None:
        entry["gt_cpu_s"] = round(gt_cpu, 2)
    return entry


def level_digest(exp: str, size: int, instances: list) -> str:
    h = hashlib.sha256()
    for spec in instances:
        text, _ = gen.materialize(exp, size, spec)
        h.update(gen.sha256_text(text).encode())
    return h.hexdigest()


# --------------------------------------------------------------------------
# CEGAR ground truth for large MCN graphs
# --------------------------------------------------------------------------


class CegarTruth:
    def __init__(self) -> None:
        os.environ["EQUIPS_MIP_BACKEND"] = "cp-sat"
        sys.path.insert(0, str(WORKSPACE))
        sys.path.insert(0, str(HERE / "audit"))
        import equips_copy as eq  # noqa: E402
        from data.qlp import parse_qlp  # noqa: E402

        eq._solve_ip_feasible = eq._solve_cp_sat_feasible
        self.eq = eq
        self.parse = parse_qlp
        self.cache = json.loads(GT_CACHE.read_text()) if GT_CACHE.exists() else {}

    def save(self) -> None:
        GT_CACHE.write_text(json.dumps(self.cache))

    def decide(self, size: int, seed: int, threshold: int, cap: float):
        text = gen.mcn_instance(size, seed, threshold)
        with tempfile.NamedTemporaryFile("w", suffix=".qlp", delete=False) as fh:
            fh.write(text)
            path = fh.name
        try:
            problem = self.parse(path)
        finally:
            os.unlink(path)
        t0 = time.process_time()
        result = self.eq.solve_qip(problem, timeout_s=max(1.0, cap))
        cpu = time.process_time() - t0
        return {"SAT": True, "UNSAT": False}.get(result["status"]), cpu

    def optimum(self, size: int, seed: int):
        key = f"{size}:{seed}"
        if key in self.cache:
            return self.cache[key]
        params = gen.mcn_params(size, seed)
        lo, hi = 0, size - params["attack"] + 1  # K=0 is TRUE; K=hi is FALSE by counting
        times: dict = {}
        spent = 0.0
        result = None
        while hi - lo > 1:
            mid = (lo + hi) // 2
            cap = min(GT_DECISION_CAP_S, GT_GRAPH_CAP_S - spent)
            if cap < 1.0:
                break
            answer, cpu = self.decide(size, seed, mid, cap)
            spent += cpu
            if answer is None:
                break
            times[mid] = cpu
            if answer:
                lo = mid
            else:
                hi = mid
        else:
            result = {"opt": lo, "t_true": times.get(lo, 0.0), "t_false": times.get(hi, 0.0), "spent": spent}
        if result is None:
            result = {"failed": True, "spent": spent}
        self.cache[key] = result
        self.save()
        return result


def crosscheck(truth: CegarTruth, test: dict) -> bool:
    """CEGAR optimum must equal the exact bitmask optimum on the largest exact
    levels: no disagreement, and at least 8 of 12 graphs certified."""
    levels = {lvl["size"]: lvl for lvl in test["experiments"]["mcn_ladder"]["levels"]}
    agree = 0
    for size in (32, 36, 40):
        for spec in levels[size]["instances"]:
            res = truth.optimum(size, spec["seed"])
            if res.get("failed"):
                log(f"  crosscheck size {size}: not certified within caps")
                continue
            if res["opt"] != spec["optimum"]:
                log(f"  crosscheck size {size}: CEGAR optimum {res['opt']} != exact {spec['optimum']}")
                return False
            agree += 1
    log(f"CEGAR ground truth agrees with the exact minimax on {agree}/12 graphs of sizes 32-40")
    return agree >= 8


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------


def load(path: Path) -> dict:
    table = json.loads(path.read_text()) if path.exists() else {}
    table["cpu_budget_s"] = CPU_BUDGET_S
    table.setdefault("experiments", {})
    for exp in ("qrandomparity_ladder", "mcn_ladder"):
        table["experiments"].setdefault(exp, {"levels": []})
    return table


def save(path: Path, table: dict, hidden: bool) -> None:
    if hidden:
        out = json.loads(json.dumps(table))
        for exp, exp_table in out["experiments"].items():
            for lvl in exp_table["levels"]:
                lvl["digest"] = level_digest(exp, lvl["size"], lvl["instances"])
                for spec in lvl["instances"]:
                    spec.pop("sha256", None)
        path.write_text(json.dumps(out, indent=1) + "\n")
    else:
        path.write_text(json.dumps(table, indent=1) + "\n")


def fill_parity(table: dict, seed_fn) -> None:
    exp_table = table["experiments"]["qrandomparity_ladder"]
    existing = {lvl["size"]: lvl for lvl in exp_table["levels"]}
    levels = []
    for li, size in enumerate(PARITY_SIZES):
        lvl = existing.get(size, {"size": size, "instances": []})
        while len(lvl["instances"]) < len(PARITY_KINDS_PER_LEVEL):
            j = len(lvl["instances"])
            lvl["instances"].append(parity_entry(size, PARITY_KINDS_PER_LEVEL[j], seed_fn("qrandomparity_ladder", li, j)))
        for spec, kind in zip(lvl["instances"], PARITY_KINDS_PER_LEVEL):
            assert spec["kind"] == kind
        levels.append(lvl)
    exp_table["levels"] = levels


def fill_mcn_exact(table: dict, seed_fn) -> None:
    exp_table = table["experiments"]["mcn_ladder"]
    existing = {lvl["size"]: lvl for lvl in exp_table["levels"]}
    levels = []
    for li, size in enumerate(MCN_EXACT_SIZES):
        lvl = existing.get(size, {"size": size, "instances": []})
        while len(lvl["instances"]) < len(MCN_ANSWERS_PER_LEVEL):
            j = len(lvl["instances"])
            seed = seed_fn("mcn_ladder", li, j)
            opt = gen.mcn_optimum(gen.mcn_params(size, seed))
            lvl["instances"].append(mcn_entry(size, MCN_ANSWERS_PER_LEVEL[j], seed, opt, "bitmask_minimax"))
        for spec in lvl["instances"]:
            spec.setdefault("ground_truth", "bitmask_minimax")
        levels.append(lvl)
    # keep already-built extended levels
    levels.extend(lvl for lvl in exp_table["levels"] if lvl["size"] not in MCN_EXACT_SIZES)
    exp_table["levels"] = levels


def build_slot(truth: CegarTruth, size: int, answer: bool, seeds: list):
    for seed in seeds:
        res = truth.optimum(size, seed)
        if res.get("failed"):
            log(f"    seed {seed}: ground truth not certified within caps ({res['spent']:.0f}s)")
            continue
        cpu = res["t_true"] if answer else res["t_false"]
        return mcn_entry(size, answer, seed, res["opt"], "cegar_cpsat", cpu), res
    return None, None


def extend_mcn(test: dict, train: dict, secret: int) -> None:
    meta = test.setdefault("mcn_extension", {})
    if meta.get("frozen"):
        log(f"MCN extension frozen: {meta.get('stop_reason')}")
        return
    truth = CegarTruth()
    if not crosscheck(truth, test):
        meta.update({"frozen": True, "stop_reason": "CEGAR ground truth failed the cross-check; no extension"})
        log("MCN extension skipped: cross-check failed")
        return
    start = time.time()
    beyond_streak = 0
    test_levels = test["experiments"]["mcn_ladder"]["levels"]
    train_levels = train["experiments"]["mcn_ladder"]["levels"]
    built = {lvl["size"] for lvl in test_levels}
    stop_reason = "all extended sizes built"
    for k, size in enumerate(MCN_EXTENDED_SIZES):
        li = len(MCN_EXACT_SIZES) + k
        if size in built:
            times = [spec.get("gt_cpu_s", 0.0) for spec in next(l for l in test_levels if l["size"] == size)["instances"]]
            beyond_streak = beyond_streak + 1 if sorted(times)[len(times) // 2] > GT_BEYOND_REACH_S else 0
            continue
        if beyond_streak >= 2:
            stop_reason = f"two consecutive levels beyond {GT_BEYOND_REACH_S:.0f}s for the ground-truth solver"
            break
        log(f"=== MCN extended size {size} ===")
        new = {"test": [], "train": []}
        ok = True
        for split in ("test", "train"):
            for j, answer in enumerate(MCN_ANSWERS_PER_LEVEL):
                if time.time() - start > GT_DEADLINE_S:
                    ok = False
                    stop_reason = f"ground-truth time budget spent before size {size} was complete"
                    break
                if split == "test":
                    seeds = [test_seed(secret, "mcn_ladder", li, j, a) for a in range(GT_TRIES_PER_SLOT)]
                else:
                    seeds = [train_seed("mcn_ladder", li, j, a) for a in range(GT_TRIES_PER_SLOT)]
                entry, res = build_slot(truth, size, answer, seeds)
                if entry is None:
                    ok = False
                    stop_reason = f"no certified graph for a slot at size {size}"
                    break
                log(f"  {split} slot {j} ({'TRUE' if answer else 'FALSE'}): opt={res['opt']} "
                    f"decision cpu={entry['gt_cpu_s']}s (graph total {res['spent']:.0f}s)")
                new[split].append(entry)
            if not ok:
                break
        if not ok:
            break
        test_levels.append({"size": size, "instances": new["test"]})
        train_levels.append({"size": size, "instances": new["train"]})
        save(TEST_PATH, test, hidden=True)
        save(TRAIN_PATH, train, hidden=False)
        times = sorted(e["gt_cpu_s"] for e in new["test"])
        beyond_streak = beyond_streak + 1 if times[len(times) // 2] > GT_BEYOND_REACH_S else 0
        log(f"  size {size} done; test decision cpu {times}; elapsed {time.time() - start:.0f}s")
    meta.update({"frozen": True, "stop_reason": stop_reason, "elapsed_s": round(time.time() - start)})
    log(f"MCN extension finished: {stop_reason}")
    if GT_CACHE.exists():
        GT_CACHE.unlink()


def check_public_generator(train: dict) -> None:
    sys.path.insert(0, str(WORKSPACE))
    import data.benchmark as public  # noqa: E402

    for exp, exp_table in train["experiments"].items():
        for lvl in exp_table["levels"]:
            for spec in lvl["instances"]:
                text, answer = public.materialize(exp, lvl["size"], spec)
                if public.sha256_text(text) != spec["sha256"] or answer != spec["answer"]:
                    raise AssertionError(f"public generator drift: {exp} size={lvl['size']} seed={spec['seed']}")
    log("public generator matches hidden copy on the train split")


def main() -> None:
    import secrets

    test = load(TEST_PATH)
    train = load(TRAIN_PATH)
    if "seed_secret" not in test:
        test["seed_secret"] = secrets.randbits(64)
    secret = test["seed_secret"]

    fill_parity(test, lambda exp, li, j: test_seed(secret, exp, li, j))
    fill_parity(train, train_seed)
    fill_mcn_exact(test, lambda exp, li, j: test_seed(secret, exp, li, j))
    fill_mcn_exact(train, train_seed)
    save(TEST_PATH, test, hidden=True)
    save(TRAIN_PATH, train, hidden=False)
    check_public_generator(train)

    if "--freeze-extension" in sys.argv:
        meta = test.setdefault("mcn_extension", {})
        if not meta.get("frozen"):
            meta.update({"frozen": True, "stop_reason": "builder stopped abnormally; extension kept as built"})
        if GT_CACHE.exists():
            GT_CACHE.unlink()
        save(TEST_PATH, test, hidden=True)
    elif "--no-extend" not in sys.argv:
        extend_mcn(test, train, secret)
        save(TEST_PATH, test, hidden=True)
        save(TRAIN_PATH, train, hidden=False)

    for name, table in (("test", test), ("train", train)):
        for exp, exp_table in table["experiments"].items():
            total = sum(len(l["instances"]) for l in exp_table["levels"])
            n_true = sum(i["answer"] for l in exp_table["levels"] for i in l["instances"])
            sizes = [l["size"] for l in exp_table["levels"]]
            log(f"{name}: {exp}: {total} instances ({n_true} TRUE), sizes {sizes}")


if __name__ == "__main__":
    main()
