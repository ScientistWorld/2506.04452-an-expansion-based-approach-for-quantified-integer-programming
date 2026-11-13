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
* MCN family (vaccination budget 1-3, attack 1-2, protection 2-3): exact
  optimum of each graph by the bitmask minimax over full-budget choices
  (``gt_mcn.py bitmask``) when it finishes within ``GT_BITMASK_CAP_S``; such
  graphs from 20 nodes up are cross-checked by an expansion-based CEGAR solver
  (CP-SAT backend) deciding K = optimum (TRUE) and K = optimum + 1 (FALSE), and
  any disagreement aborts the build.  Otherwise the optimum comes from a
  binary search over K with that CEGAR solver, every decision run to
  completion within ``GT_DECISION_CAP_S`` (``gt_mcn.py cegar``).  A slot whose
  graph cannot be certified takes the next seed (up to ``GT_TRIES_PER_SLOT``).
  The ladder is the longest prefix of ``MCN_SIZES`` whose slots are all
  certified on both splits within the build deadline; it is then frozen.
  Graphs are certified in parallel and cached in ``outputs/`` so that an
  interrupted build resumes.

The builder checks that the public generator in ``data/benchmark.py`` produces
byte-identical text to the hidden copy on the train split.

Idempotent: existing entries are reused, missing ones are filled in.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
sys.path.insert(0, str(HERE))

import qip_hidden_gen as gen  # noqa: E402

PARITY_SIZES = [10, 14, 18, 22, 26, 32, 40, 50, 64, 80, 100, 128, 160, 256, 400, 640, 1000]
PARITY_KINDS_PER_LEVEL = [
    "paper_false", "paper_true", "gen_true", "gen_true", "gen_false", "gen_false", "card_true", "card_false",
]
MCN_TAG = "mcn_v4"
MCN_SIZES = [16, 24, 32, 40, 48, 56, 64, 72, 80, 96]
MCN_ANSWERS_PER_LEVEL = [True, True, True, False, False, False]

GT_BITMASK_CAP_S = float(os.environ.get("QIP_GT_BITMASK_CAP_S", "60"))
GT_DECISION_CAP_S = float(os.environ.get("QIP_GT_DECISION_CAP_S", "200"))
GT_GRAPH_CAP_S = float(os.environ.get("QIP_GT_GRAPH_CAP_S", "900"))
GT_VERIFY_MIN_SIZE = 20
GT_TRIES_PER_SLOT = 3
GT_DEADLINE_S = float(os.environ.get("QIP_GT_DEADLINE_S", "9000"))
GT_WORKERS = max(1, min(8, len(os.sched_getaffinity(0))))

TEST_PATH = HERE / "instances.json"
TRAIN_PATH = WORKSPACE / "data" / "train_instances.json"
GT_CACHE = WORKSPACE / "outputs" / "gt_mcn_v4_cache.json"
GT_TOOL = HERE / "gt_mcn.py"
TRAIN_OFFSETS = {"qrandomparity_ladder": 11_000_000, "mcn_ladder": 23_000_000, MCN_TAG: 41_000_000}


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


def mcn_entry(size: int, answer: bool, seed: int, cert: dict) -> dict:
    opt = cert["opt"]
    threshold = opt if answer else opt + 1
    text = gen.mcn_instance(size, seed, threshold)
    entry = {
        "kind": "mcn_true" if answer else "mcn_false",
        "seed": seed,
        "answer": answer,
        "threshold": threshold,
        "optimum": opt,
        "ground_truth": cert["gt"],
        "sha256": gen.sha256_text(text),
    }
    if cert.get("crosscheck"):
        entry["crosscheck"] = cert["crosscheck"]
    return entry


def level_digest(exp: str, size: int, instances: list) -> str:
    h = hashlib.sha256()
    for spec in instances:
        text, _ = gen.materialize(exp, size, spec)
        h.update(gen.sha256_text(text).encode())
    return h.hexdigest()


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------


def load(path: Path) -> dict:
    table = json.loads(path.read_text()) if path.exists() else {}
    for stale in ("cpu_budget_s", "mcn_extension", "mcn_extension_v2", "mcn_v3"):
        table.pop(stale, None)
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


# --------------------------------------------------------------------------
# MCN ground truth
# --------------------------------------------------------------------------


class GroundTruth:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.cache = json.loads(GT_CACHE.read_text()) if GT_CACHE.exists() else {}
        self.start = time.time()

    def _save(self) -> None:
        GT_CACHE.parent.mkdir(parents=True, exist_ok=True)
        tmp = GT_CACHE.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.cache))
        tmp.replace(GT_CACHE)

    def _tool(self, args: list, timeout: float):
        try:
            out = subprocess.run([sys.executable, str(GT_TOOL)] + [str(a) for a in args], capture_output=True,
                                 text=True, timeout=timeout, cwd=str(WORKSPACE))
            lines = [l for l in out.stdout.splitlines() if l.strip()]
            return json.loads(lines[-1]) if out.returncode == 0 and lines else None
        except (subprocess.TimeoutExpired, ValueError):
            return None

    def certify(self, size: int, seed: int) -> dict:
        key = f"{size}:{seed}"
        with self.lock:
            if key in self.cache:
                return self.cache[key]
        t0 = time.time()
        bm = self._tool(["bitmask", size, seed], GT_BITMASK_CAP_S)
        if bm is not None:
            res = {"opt": bm["opt"], "gt": "bitmask_minimax"}
            if size >= GT_VERIFY_MIN_SIZE:
                v = self._tool(["verify", size, seed, bm["opt"], GT_DECISION_CAP_S], 2 * GT_DECISION_CAP_S + 60)
                if v is None or v["at_opt"] is None or v["above_opt"] is None:
                    res["crosscheck"] = "cegar_unfinished"
                elif v["at_opt"] is True and v["above_opt"] is False:
                    res["crosscheck"] = "cegar_agrees"
                else:
                    res = {"mismatch": True, "bitmask": bm, "cegar": v}
        else:
            cg = self._tool(["cegar", size, seed, GT_DECISION_CAP_S, GT_GRAPH_CAP_S], GT_GRAPH_CAP_S + 120)
            if cg is None or cg.get("failed"):
                res = {"failed": True}
            else:
                res = {"opt": cg["opt"], "gt": "cegar_cpsat"}
        res["wall_s"] = round(time.time() - t0, 1)
        with self.lock:
            self.cache[key] = res
            self._save()
        return res


def build_mcn(test: dict, train: dict, secret: int) -> None:
    meta = test.get(MCN_TAG, {})
    if meta.get("frozen"):
        log(f"MCN ladder frozen: {meta.get('stop_reason')}")
        return
    gt = GroundTruth()
    deadline = gt.start + GT_DEADLINE_S
    stop = {"size": None}
    slots = {}  # (split, size, j) -> entry or None

    def fill(split: str, li: int, size: int, j: int, answer: bool):
        for attempt in range(GT_TRIES_PER_SLOT):
            if stop["size"] is not None and size > stop["size"]:
                return None
            if time.time() > deadline:
                return None
            seed = test_seed(secret, MCN_TAG, li, j, attempt) if split == "test" else train_seed(MCN_TAG, li, j, attempt)
            cert = gt.certify(size, seed)
            if cert.get("mismatch"):
                raise RuntimeError(f"bitmask/CEGAR disagreement on MCN size {size} seed {seed}: {cert}")
            if not cert.get("failed"):
                return mcn_entry(size, answer, seed, cert)
            log(f"    {split} size {size} slot {j}: seed {seed} not certified ({cert['wall_s']}s)")
        return None

    def task(split, li, size, j, answer):
        entry = fill(split, li, size, j, answer)
        slots[(split, size, j)] = entry
        if entry is None and time.time() <= deadline:
            with gt.lock:
                if stop["size"] is None or size < stop["size"]:
                    stop["size"] = size
        elif entry is not None:
            log(f"  {split} size {size} slot {j}: opt={entry['optimum']} ({entry['ground_truth']}"
                f"{', ' + entry['crosscheck'] if entry.get('crosscheck') else ''})")

    jobs = [(split, li, size, j, answer)
            for li, size in enumerate(MCN_SIZES)
            for split in ("test", "train")
            for j, answer in enumerate(MCN_ANSWERS_PER_LEVEL)]
    with ThreadPoolExecutor(max_workers=GT_WORKERS) as pool:
        futures = [pool.submit(task, *job) for job in jobs]
        for f in futures:
            f.result()

    test_levels, train_levels = [], []
    stop_reason = "all sizes built"
    for size in MCN_SIZES:
        tl = [slots.get(("test", size, j)) for j in range(len(MCN_ANSWERS_PER_LEVEL))]
        rl = [slots.get(("train", size, j)) for j in range(len(MCN_ANSWERS_PER_LEVEL))]
        if any(e is None for e in tl + rl):
            stop_reason = f"size {size}: a slot could not be certified (caps or deadline)"
            break
        test_levels.append({"size": size, "instances": tl})
        train_levels.append({"size": size, "instances": rl})
    test["experiments"]["mcn_ladder"]["levels"] = test_levels
    train["experiments"]["mcn_ladder"]["levels"] = train_levels
    counts: dict = {}
    for lvl in test_levels + train_levels:
        for spec in lvl["instances"]:
            k = spec["ground_truth"] + ("/" + spec["crosscheck"] if spec.get("crosscheck") else "")
            counts[k] = counts.get(k, 0) + 1
    test[MCN_TAG] = {
        "frozen": True,
        "stop_reason": stop_reason,
        "elapsed_s": round(time.time() - gt.start),
        "ground_truth_counts": counts,
        "caps_s": {"bitmask": GT_BITMASK_CAP_S, "decision": GT_DECISION_CAP_S, "graph": GT_GRAPH_CAP_S},
    }
    log(f"MCN ladder built: sizes {[l['size'] for l in test_levels]} ({stop_reason}); ground truth {counts}")


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
    if not test.get(MCN_TAG, {}).get("frozen"):
        # MCN levels of earlier ladders (other budgets) are replaced
        test["experiments"]["mcn_ladder"]["levels"] = []
        train["experiments"]["mcn_ladder"]["levels"] = []
    save(TEST_PATH, test, hidden=True)
    save(TRAIN_PATH, train, hidden=False)

    if "--no-extend" not in sys.argv:
        build_mcn(test, train, secret)
        save(TEST_PATH, test, hidden=True)
        save(TRAIN_PATH, train, hidden=False)
    check_public_generator(train)

    for name, table in (("test", test), ("train", train)):
        for exp, exp_table in table["experiments"].items():
            total = sum(len(l["instances"]) for l in exp_table["levels"])
            n_true = sum(i["answer"] for l in exp_table["levels"] for i in l["instances"])
            sizes = [l["size"] for l in exp_table["levels"]]
            log(f"{name}: {exp}: {total} instances ({n_true} TRUE), sizes {sizes}")


if __name__ == "__main__":
    main()
