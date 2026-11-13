#!/usr/bin/env python3
"""Self-test of the solver sandbox on this machine (audit only).

Runs small probe programs through eval/test/sandbox.py and prints whether the
instruction counter is available and deterministic, and whether the isolation
holds (counter cannot be paused; eval/test/ unreadable; no writes outside the
run directory; no network sockets; no System V IPC).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST_DIR = HERE.parent
WORKSPACE = HERE.parents[2]

PROBE = r'''
import ctypes, json, os, socket, sys
libc = ctypes.CDLL(None, use_errno=True)
out = {}
def t(name, f):
    try:
        f(); out[name] = "allowed"
    except Exception as e:
        out[name] = "denied:" + type(e).__name__
if sys.argv[1] == "loop":
    s = 0
    for i in range(2000000): s += i
else:
    t("read_eval_test", lambda: open(sys.argv[2] + "/instances.json").read(1))
    t("read_public", lambda: open(sys.argv[3] + "/data/benchmark.py").read(1))
    t("write_workspace", lambda: open(sys.argv[3] + "/method/.sandbox_probe", "w").write("x"))
    t("write_tmp", lambda: open("/tmp/.sandbox_probe", "w").write("x"))
    t("write_run_dir", lambda: open(os.path.join(os.environ["TMPDIR"], "x"), "w").write("x"))
    t("inet_socket", lambda: socket.socket(socket.AF_INET, socket.SOCK_STREAM))
    out["perf_disable_prctl"] = "allowed" if libc.prctl(31, 0, 0, 0, 0) == 0 else "denied"
    out["sysv_shmget"] = "allowed" if libc.syscall(29, 4242, 4096, 0o1000 | 0o600) >= 0 else "denied"
    for p in ("/home/user/method/.sandbox_probe", "/tmp/.sandbox_probe"):
        try: os.unlink(p)
        except OSError: pass
print(json.dumps(out))
'''


def run(mode: str, scratch: Path) -> tuple[dict, dict]:
    run_dir = Path(tempfile.mkdtemp(dir=str(scratch)))
    probe = scratch / "probe.py"
    probe.write_text(PROBE)
    job = {
        "command": [sys.executable, str(probe), mode, str(TEST_DIR), str(WORKSPACE)],
        "cwd": str(WORKSPACE),
        "env": {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONHASHSEED": "0", "TMPDIR": str(run_dir), "HOME": str(run_dir)},
        "log": str(scratch / f"{mode}.log"), "budget": 10**11, "wall_limit_s": 60, "cpu_limit_s": 60,
        "hide": [str(TEST_DIR)], "writable": [str(run_dir)],
    }
    proc = subprocess.run([sys.executable, "-I", str(TEST_DIR / "sandbox.py")], input=json.dumps(job), capture_output=True, text=True)
    res = json.loads(proc.stdout.strip().splitlines()[-1])
    try:
        probe_out = json.loads((scratch / f"{mode}.log").read_text().strip().splitlines()[-1])
    except (OSError, ValueError, IndexError):
        probe_out = {}
    return res, probe_out


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp)
        counts = []
        for _ in range(3):
            res, _ = run("loop", scratch)
            counts.append(res["instructions"])
        res, _ = run("loop", scratch)
        _, iso = run("isolation", scratch)
    spread = (max(counts) - min(counts)) / max(1, min(counts))
    report = {"mode": res["mode"], "landlock": res["landlock"], "loop_instructions": counts,
              "relative_spread": spread, "cpu_s": res["cpu_s"], "isolation": iso}
    print(json.dumps(report, indent=1))
    ok = res["mode"] == "perf" and spread < 1e-3 and iso.get("read_eval_test", "").startswith("denied") \
        and iso.get("perf_disable_prctl") == "denied" and iso.get("write_workspace", "").startswith("denied")
    print("SANDBOX CHECK:", "OK" if ok else "DEGRADED (see report)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
