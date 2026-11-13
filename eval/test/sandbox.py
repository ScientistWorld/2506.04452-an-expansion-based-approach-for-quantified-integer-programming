#!/usr/bin/env python3
"""Run one solver process tree under an instruction budget (hidden-test copy).

Usage (by the evaluator): ``python3 -I sandbox.py`` with a JSON job on stdin::

    {"command": [...], "cwd": "...", "env": {...}, "log": "path",
     "budget": <instructions>, "wall_limit_s": <s>, "cpu_limit_s": <s>,
     "hide": ["/abs/dir", ...], "writable": ["/abs/run_dir"]}

and one JSON result line on stdout.

Budget
------
The budget is counted, not timed: a hardware performance counter
(``PERF_COUNT_HW_INSTRUCTIONS``, user space only) is attached to the solver
before it starts and is inherited by every thread and process it creates, so
the count covers the whole process tree.  The count does not depend on the
speed or load of the machine, which makes results reproducible across compute
nodes.  The tree is killed as soon as the count passes the budget.

Isolation (applied to the solver before ``exec``)
-------------------------------------------------
* seccomp: ``perf_event_open`` and ``prctl(PR_TASK_PERF_EVENTS_DISABLE/ENABLE)``
  fail with EPERM, so the solver cannot pause the counter; System V IPC, POSIX
  message queues and kernel keyrings (state that outlives a process) and
  network sockets are refused; foreign syscall ABIs (i386, x32) are refused.
* Landlock: no file under the ``hide`` directories can be opened (directory
  listing stays allowed); every other file is read-only; only the
  ``writable`` directories (the run's private working directory, deleted
  afterwards) and /dev/null can be written.  A solver therefore keeps no
  state from one instance to the next and cannot exchange data with other
  runs.  With Landlock ABI >= 6 it also cannot signal or reach abstract
  sockets of processes outside its sandbox.
* This launcher is non-dumpable (its /proc entries are closed to the solver)
  and a child subreaper: detached or orphaned descendants are re-parented
  here, killed when the solver exits, and their instructions counted.
* ASLR is disabled for the solver and its environment is fixed by the
  evaluator, so repeated runs execute the same instructions.

If the kernel offers no instruction counter, the launcher falls back to CPU
time (user + system) times a nominal rate and reports ``mode: "cpu"``.
"""

from __future__ import annotations

import ctypes
import json
import os
import resource
import signal
import struct
import sys
import time

NOMINAL_INSTRUCTIONS_PER_CPU_S = 5.0e9  # fallback only (mode "cpu")
POLL_S = 0.02

_libc = ctypes.CDLL(None, use_errno=True)
_libc.syscall.restype = ctypes.c_long

SYS_PERF_EVENT_OPEN = 298
SYS_LANDLOCK_CREATE_RULESET = 444
SYS_LANDLOCK_ADD_RULE = 445
SYS_LANDLOCK_RESTRICT_SELF = 446

PR_SET_DUMPABLE = 4
PR_SET_SECCOMP = 22
PR_SET_CHILD_SUBREAPER = 36
PR_SET_NO_NEW_PRIVS = 38
SECCOMP_MODE_FILTER = 2
ADDR_NO_RANDOMIZE = 0x0040000


# --------------------------------------------------------------------------
# perf counter
# --------------------------------------------------------------------------


class _PerfAttr(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint32), ("size", ctypes.c_uint32), ("config", ctypes.c_uint64),
        ("sample_period", ctypes.c_uint64), ("sample_type", ctypes.c_uint64), ("read_format", ctypes.c_uint64),
        ("flags", ctypes.c_uint64), ("wakeup_events", ctypes.c_uint32), ("bp_type", ctypes.c_uint32),
        ("config1", ctypes.c_uint64), ("config2", ctypes.c_uint64), ("branch_sample_type", ctypes.c_uint64),
        ("sample_regs_user", ctypes.c_uint64), ("sample_stack_user", ctypes.c_uint32), ("clockid", ctypes.c_int32),
        ("sample_regs_intr", ctypes.c_uint64), ("aux_watermark", ctypes.c_uint32), ("sample_max_stack", ctypes.c_uint16),
        ("_reserved_2", ctypes.c_uint16), ("aux_sample_size", ctypes.c_uint32), ("_reserved_3", ctypes.c_uint32),
        ("sig_data", ctypes.c_uint64),
    ]


def open_instruction_counter(pid: int):
    """Counter of user-space instructions of ``pid`` and all its future
    descendants, enabled when ``pid`` calls exec.  Returns an fd or None."""
    attr = _PerfAttr()
    attr.type = 0  # PERF_TYPE_HARDWARE
    attr.size = ctypes.sizeof(_PerfAttr)
    attr.config = 1  # PERF_COUNT_HW_INSTRUCTIONS
    attr.read_format = 1 | 2  # TOTAL_TIME_ENABLED | TOTAL_TIME_RUNNING
    # disabled, inherit, exclude_kernel, exclude_hv, enable_on_exec
    attr.flags = (1 << 0) | (1 << 1) | (1 << 5) | (1 << 6) | (1 << 12)
    fd = _libc.syscall(SYS_PERF_EVENT_OPEN, ctypes.byref(attr), pid, -1, -1, 8)  # PERF_FLAG_FD_CLOEXEC
    return int(fd) if fd >= 0 else None


def read_counter(fd: int):
    value, enabled, running = struct.unpack("QQQ", os.read(fd, 24))
    if running and running < enabled:  # multiplexed: scale (standard perf estimate)
        return int(value * enabled / running), True
    return int(value), False


# --------------------------------------------------------------------------
# seccomp
# --------------------------------------------------------------------------


class _SockFilter(ctypes.Structure):
    _fields_ = [("code", ctypes.c_uint16), ("jt", ctypes.c_uint8), ("jf", ctypes.c_uint8), ("k", ctypes.c_uint32)]


class _SockFprog(ctypes.Structure):
    _fields_ = [("len", ctypes.c_uint16), ("filter", ctypes.POINTER(_SockFilter))]


# Syscalls refused outright (x86_64 numbers): the perf interface, System V
# IPC and POSIX message queues (state that outlives a process), kernel
# keyrings (per-user state).
_BLOCKED_SYSCALLS = (
    SYS_PERF_EVENT_OPEN,
    29, 30, 31, 64, 65, 66, 68, 69, 70, 71, 220,  # shmget..msgctl, semtimedop
    240, 241, 242, 243, 244, 245,                 # mq_*
    248, 249, 250,                                # add_key, request_key, keyctl
)
_SYS_PRCTL = 157
_SYS_SOCKET = 41


def _seccomp_program():
    ld, jeq, jge, ret = 0x20, 0x15, 0x35, 0x06
    allow, deny = 0x7FFF0000, 0x00050000 | 1  # SECCOMP_RET_ERRNO | EPERM
    prog = [
        (ld, 0, 0, 4),                    # A = arch
        (jeq, 1, 0, 0xC000003E),          # x86_64: skip the next instruction
        ("DENY",),                        # foreign ABI (i386, ...)
        (ld, 0, 0, 0),                    # A = syscall nr
        (jge, "DENY", None, 0x40000000),  # x32 ABI
    ]
    for nr in _BLOCKED_SYSCALLS:
        prog.append((jeq, "DENY", None, nr))
    prog += [
        (jeq, "PRCTL", None, _SYS_PRCTL),
        (jeq, "SOCKET", None, _SYS_SOCKET),
        ("ALLOW",),
        ("label", "PRCTL"),
        (ld, 0, 0, 16),                   # A = args[0] (low 32 bits)
        (jeq, "DENY", None, 31),          # PR_TASK_PERF_EVENTS_DISABLE
        (jeq, "DENY", None, 32),          # PR_TASK_PERF_EVENTS_ENABLE
        ("ALLOW",),
        ("label", "SOCKET"),
        (ld, 0, 0, 16),                   # A = domain
        (jeq, "ALLOW_", None, 1),         # AF_UNIX only (no network)
        ("DENY",),
        ("label", "ALLOW_"),
        ("ALLOW",),
        ("label", "DENY"),
        ("DENY",),
    ]
    # resolve labels into BPF jump offsets
    flat, labels = [], {}
    for item in prog:
        if item[0] == "label":
            labels[item[1]] = len(flat)
        else:
            flat.append(item)
    code = []
    for i, item in enumerate(flat):
        if item == ("ALLOW",):
            code.append((ret, 0, 0, allow))
        elif item == ("DENY",):
            code.append((ret, 0, 0, deny))
        else:
            op, jt, jf, k = item
            if isinstance(jt, str):
                jt = labels[jt] - i - 1
            jf = 0 if jf is None else jf
            code.append((op, jt, jf, k))
    arr = (_SockFilter * len(code))(*[_SockFilter(*p) for p in code])
    return _SockFprog(len(code), ctypes.cast(arr, ctypes.POINTER(_SockFilter))), arr


def install_seccomp() -> bool:
    fprog, _keep = _seccomp_program()
    return _libc.prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, ctypes.byref(fprog), 0, 0) == 0


# --------------------------------------------------------------------------
# Landlock
# --------------------------------------------------------------------------

_FS_EXECUTE = 1 << 0
_FS_WRITE_FILE = 1 << 1
_FS_READ_FILE = 1 << 2
_FS_V1_DIR_ONLY = sum(1 << b for b in range(4, 13))  # remove_*, make_*
_FS_REFER = 1 << 13
_FS_TRUNCATE = 1 << 14
_SCOPE_ABSTRACT_UNIX_SOCKET = 1 << 0
_SCOPE_SIGNAL = 1 << 1


class _PathBeneath(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int32)]


class _RulesetAttr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64), ("handled_access_net", ctypes.c_uint64),
                ("scoped", ctypes.c_uint64)]


def _add_rule(ruleset: int, path: str, rights: int) -> None:
    try:
        fd = os.open(path, os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError:
        return
    try:
        rule = _PathBeneath(rights, fd)
        _libc.syscall(SYS_LANDLOCK_ADD_RULE, ruleset, 1, ctypes.byref(rule), 0)
    finally:
        os.close(fd)


def build_landlock_ruleset(hidden: list, writable: list):
    """Ruleset fd for the solver: files beneath ``hidden`` directories cannot
    be opened at all; everything else is read-only (read and execute); the
    ``writable`` directories (the run's private working directory) and
    /dev/null can also be written.  On ABI >= 6 the solver can neither signal
    nor reach abstract sockets of processes outside its own sandbox.
    Returns None if Landlock is unavailable."""
    abi = _libc.syscall(SYS_LANDLOCK_CREATE_RULESET, None, 0, 1)  # VERSION
    if abi < 1:
        return None
    read = _FS_EXECUTE | _FS_READ_FILE
    file_write = _FS_WRITE_FILE | (_FS_TRUNCATE if abi >= 3 else 0)
    everything = read | file_write | _FS_V1_DIR_ONLY | (_FS_REFER if abi >= 2 else 0)
    attr = _RulesetAttr(everything, 0, (_SCOPE_ABSTRACT_UNIX_SOCKET | _SCOPE_SIGNAL) if abi >= 6 else 0)
    size = 24 if abi >= 6 else 8
    ruleset = _libc.syscall(SYS_LANDLOCK_CREATE_RULESET, ctypes.byref(attr), size, 0)
    if ruleset < 0:
        return None
    for path in writable:
        _add_rule(ruleset, path, everything)
    _add_rule(ruleset, os.devnull, read | file_write)
    hidden = [os.path.realpath(h) for h in hidden if os.path.exists(h)]
    if not hidden:
        _add_rule(ruleset, "/", read)
        return int(ruleset)
    on_path = set()
    for h in hidden:
        p = h
        while True:
            on_path.add(p)
            if p == "/":
                break
            p = os.path.dirname(p)
    hidden_set = set(hidden)
    ancestors = sorted(p for p in on_path if p not in hidden_set)
    for anc in ancestors:
        try:
            entries = os.listdir(anc)
        except OSError:
            continue
        for name in entries:
            path = os.path.join(anc, name)
            if path in on_path:
                continue  # an ancestor (handled in its own turn) or a hidden dir
            _add_rule(ruleset, path, read)
    return int(ruleset)


# --------------------------------------------------------------------------
# Process tree
# --------------------------------------------------------------------------


def _children_of(pid: int) -> list:
    out = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/stat") as fh:
                stat = fh.read()
            if int(stat.rsplit(")", 1)[1].split()[1]) == pid:
                out.append(int(entry))
        except (OSError, ValueError, IndexError):
            continue
    return out


def _kill_tree(pgid: int) -> None:
    """Kill the solver's session and every other descendant (re-parented to
    this subreaper), then reap them all."""
    me = os.getpid()
    for _ in range(20000):
        try:
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            while os.waitpid(-1, os.WNOHANG)[0]:
                pass
        except ChildProcessError:
            return  # no descendant left
        for kid in _children_of(me):
            try:
                os.kill(kid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        time.sleep(0.005)


def _child(job: dict, go_r: int, ruleset) -> None:
    """Runs in the forked child: isolate, wait for the counter, exec."""
    try:
        os.setsid()
        _libc.personality(ADDR_NO_RANDOMIZE)
        cpu = int(job.get("cpu_limit_s", 120))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        null = os.open(os.devnull, os.O_RDONLY)
        log = os.open(job["log"], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        os.dup2(null, 0)
        os.dup2(log, 1)
        os.dup2(log, 2)
        os.chdir(job["cwd"])
        if _libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
            os._exit(121)
        if ruleset is not None and _libc.syscall(SYS_LANDLOCK_RESTRICT_SELF, ruleset, 0) != 0:
            os._exit(122)
        if not install_seccomp():
            os._exit(123)
        os.read(go_r, 1)
        os.closerange(3, 65536)
        os.execvpe(job["command"][0], job["command"], job["env"])
    except BaseException:  # noqa: BLE001
        pass
    os._exit(127)


def run(job: dict) -> dict:
    _libc.prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0)
    budget = int(job["budget"])
    wall_limit = float(job["wall_limit_s"])
    ruleset = build_landlock_ruleset(job.get("hide", []), job.get("writable", []))
    go_r, go_w = os.pipe()
    start = time.monotonic()
    pid = os.fork()
    if pid == 0:
        os.close(go_w)
        _child(job, go_r, ruleset)
    os.close(go_r)
    if ruleset is not None:
        os.close(ruleset)
    # The counter needs the child to be dumpable (it still is: it inherited
    # this process's state at fork); only then is the launcher itself made
    # non-dumpable, before the solver is allowed to exec.
    fd = open_instruction_counter(pid)
    mode = "perf" if fd is not None else "cpu"
    _libc.prctl(PR_SET_DUMPABLE, 0, 0, 0, 0)
    os.write(go_w, b"g")
    os.close(go_w)

    over_budget = wall_killed = multiplexed = False
    status = None
    while True:
        done, st = os.waitpid(pid, os.WNOHANG)
        if done:
            status = st
            break
        if fd is not None:
            count, mux = read_counter(fd)
            multiplexed |= mux
            if count > budget:
                over_budget = True
                break
        else:
            usage = resource.getrusage(resource.RUSAGE_CHILDREN)
            # the main child is not reaped yet: read its own CPU time
            try:
                with open(f"/proc/{pid}/stat") as fh:
                    fields = fh.read().rsplit(")", 1)[1].split()
                ticks = os.sysconf("SC_CLK_TCK")
                cpu_now = (int(fields[11]) + int(fields[12])) / ticks + usage.ru_utime + usage.ru_stime
            except (OSError, ValueError, IndexError):
                cpu_now = 0.0
            if cpu_now * NOMINAL_INSTRUCTIONS_PER_CPU_S > budget:
                over_budget = True
                break
        if time.monotonic() - start > wall_limit:
            wall_killed = True
            break
        time.sleep(POLL_S)
    _kill_tree(pid)
    wall = time.monotonic() - start
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu_s = usage.ru_utime + usage.ru_stime
    if fd is not None:
        instructions, mux = read_counter(fd)
        multiplexed |= mux
        os.close(fd)
    else:
        instructions = int(cpu_s * NOMINAL_INSTRUCTIONS_PER_CPU_S)
    if instructions > budget:
        over_budget = True
    returncode = None
    if status is not None:
        returncode = os.waitstatus_to_exitcode(status)
    return {
        "mode": mode,
        "instructions": instructions,
        "over_budget": over_budget,
        "wall_killed": wall_killed,
        "multiplexed": multiplexed,
        "cpu_s": round(cpu_s, 3),
        "wall_s": round(wall, 3),
        "returncode": returncode,
        "landlock": ruleset is not None,
    }


def main() -> None:
    job = json.loads(sys.stdin.read())
    result = run(job)
    sys.stdout.write(json.dumps(result) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
