"""Runs inside the sandbox process (python -S -s, minimal environment). Best-effort policy guards: no network,
no process spawning, writes only inside the work directory, fixed seed, optional memory cap. This is process
isolation for vetted T1 code. It is NOT a security boundary against hostile code (T2/T3 need an OS-level container)."""
import json, os, random, sys
MARK = "BPRESULT:"

class PolicyViolation(Exception): pass

def _deny(what):
    def f(*a, **k): raise PolicyViolation(f"{what} is not allowed in the sandbox")
    return f

def install_guards(wd):
    import socket, builtins, io, subprocess
    for attr in ("connect", "connect_ex", "bind", "listen", "sendto"): setattr(socket.socket, attr, _deny("network " + attr))
    socket.create_connection = _deny("network connection"); socket.getaddrinfo = _deny("name resolution"); socket.gethostbyname = _deny("name resolution")
    real_open = builtins.open; root = os.path.realpath(wd)
    def guarded(file, mode="r", *a, **k):
        if not isinstance(file, int) and any(c in mode for c in "wax+"):
            p = os.path.realpath(os.fspath(file))
            if not (p == root or p.startswith(root + os.sep)): raise PolicyViolation(f"writing outside the work directory ({p}) is not allowed in the sandbox")
        return real_open(file, mode, *a, **k)
    builtins.open = guarded; io.open = guarded
    for name in ("system", "popen", "fork", "forkpty", "startfile", "execv", "execve", "execl", "execle", "execlp", "execvp", "execvpe", "spawnl", "spawnle", "spawnv", "spawnve", "posix_spawn", "posix_spawnp"):
        if hasattr(os, name): setattr(os, name, _deny("process spawning"))
    subprocess.Popen = _deny("process spawning")

def apply_limits(mem_mb):
    try:
        import resource; lim = int(mem_mb) * 1024 * 1024; resource.setrlimit(resource.RLIMIT_AS, (lim, lim)); return int(mem_mb)
    except Exception: return None           # not available on Windows

def _selftest(port=9):
    import socket, subprocess
    probes = {
        "network_connect": lambda: socket.create_connection(("127.0.0.1", port), timeout=1),
        "name_resolution": lambda: socket.getaddrinfo("example.com", 80),
        "write_outside_workdir": lambda: open(os.path.join(os.path.dirname(os.getcwd()), "bp_sandbox_escape.txt"), "w"),
        "os_system": lambda: os.system("echo escaped"),
        "subprocess": lambda: subprocess.run([sys.executable, "-c", "print(1)"]),
    }
    res = {}
    for k, f in probes.items():
        try: f(); res[k] = "ALLOWED"
        except PolicyViolation: res[k] = "blocked"
        except Exception as e: res[k] = "error:" + type(e).__name__
    try:
        with open("inside.txt", "w") as fh: fh.write("ok")
        res["write_inside_workdir"] = "allowed (by design)"
    except Exception as e: res["write_inside_workdir"] = "error:" + type(e).__name__
    return res

def main():
    req = json.loads(sys.stdin.read()); wd = req["workdir"]; os.chdir(wd)
    from decimal import Decimal as D
    from bp import methods as M, envpin
    random.seed(0); fp = envpin.fingerprint(); mem = apply_limits(req.get("memory_mb")); install_guards(wd)
    policy = {"network": "blocked", "process_spawn": "blocked", "writes": "work directory only", "seed": 0, "memory_limit_mb": mem, "isolation": "separate process, python -S -s, minimal environment (best-effort guards, not a security boundary)"}
    out = {"ok": True, "policy": policy, "fingerprint": fp, "env_hash": envpin.env_hash(fp)}
    try:
        mode, inp = req["mode"], req.get("inputs")
        if mode == "selftest": out["probes"] = _selftest(int(req.get("probe_port", 9)))
        elif mode == "spin":
            while True: pass
        elif mode == "template":
            from bp import templates as T
            out["template"] = T.run_template(req["kind"], inp); out["code_hash"] = M.sha_source(T.TEMPLATES[req["kind"]]["build"])
        else:
            m = M.LIBRARY[req["method"]]
            if mode == "assumptions": out["checks"] = [[n, bool(ok), d] for n, ok, d in m.assumption_checks(inp, req.get("thresholds", {}))]
            elif mode == "verify_execute":
                import inspect
                res = m.tests(inp, m.impl); out["results"] = [[n, bool(ok)] for n, ok in res]
                if all(ok for _, ok in res):
                    raw = m.impl(inp)
                    if isinstance(raw, dict):
                        raw = dict(raw); out["appendix_extra"] = raw.pop("_appendix", None); raw.pop("_checks", None); out["outputs"] = raw
                    else: out["outputs"] = {m.metric: raw}
                out["code_hash"] = M.sha_source(m.impl)
            elif mode == "flip":
                f = M.decision_flip(m, m.impl, inp, D(req["lo"]), D(req["hi"])); out["flip"] = None if f is None else str(f)
            else: raise ValueError("unknown mode " + mode)
    except M.DataError as e: out = {**out, "ok": False, "error_type": "DataError", "message": str(e)}
    except PolicyViolation as e: out = {**out, "ok": False, "error_type": "PolicyViolation", "message": str(e)}
    except Exception as e: out = {**out, "ok": False, "error_type": type(e).__name__, "message": str(e)}
    sys.stdout.write(MARK + json.dumps(out, default=str) + "\n"); sys.stdout.flush()
