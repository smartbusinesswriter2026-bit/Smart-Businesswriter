"""Parent side of the sandbox: spawns the guarded child, enforces a timeout, parses typed results (manual 5.4)."""
import json, os, subprocess, sys, tempfile
from decimal import Decimal as D
from .methods import DataError
from .sandbox_child import MARK

class SandboxError(Exception): pass

_BOOT = "import sys; sys.path.insert(0, sys.argv[1]); import bp.sandbox_child as c; c.main()"
_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class SubprocessSandbox:
    def __init__(self, timeout: float = 60, memory_mb: int = 1024, python: str = sys.executable):
        self.timeout, self.memory_mb, self.python = timeout, memory_mb, python

    def _run(self, req: dict) -> dict:
        env = {"PYTHONHASHSEED": "0", "PYTHONIOENCODING": "utf-8"}
        if os.environ.get("SYSTEMROOT"): env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]     # required by Windows
        with tempfile.TemporaryDirectory(prefix="bp_sandbox_") as wd:
            payload = json.dumps({**req, "workdir": wd, "memory_mb": self.memory_mb}, default=str)
            try:
                p = subprocess.Popen([self.python, "-S", "-s", "-c", _BOOT, _SRC], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=wd, env=env, text=True, encoding="utf-8")
            except OSError as e: raise SandboxError(f"could not start the sandbox process: {e}")
            try: out, err = p.communicate(payload, timeout=self.timeout)
            except subprocess.TimeoutExpired:
                p.kill(); p.communicate(); raise SandboxError(f"timed out after {self.timeout:g} seconds")
        line = next((l for l in out.splitlines() if l.startswith(MARK)), None)
        if line is None: raise SandboxError("no result from the sandbox process: " + (err or out or "empty output").strip()[-400:])
        if len(line) > 5_000_000: raise SandboxError("result too large")
        data = json.loads(line[len(MARK):])
        if not data.get("ok"):
            if data.get("error_type") == "DataError": raise DataError(data["message"])
            raise SandboxError(f"{data.get('error_type')}: {data.get('message')}")
        return data

    def assumptions(self, method, inp, thresholds):
        d = self._run({"mode": "assumptions", "method": method, "inputs": inp, "thresholds": thresholds}); return [(n, ok, det) for n, ok, det in d["checks"]], d

    def verify_execute(self, method, inp):
        d = self._run({"mode": "verify_execute", "method": method, "inputs": inp})
        outputs = {k: D(str(v)) for k, v in d["outputs"].items()} if "outputs" in d else None
        return [(n, ok) for n, ok in d["results"]], outputs, {"env_hash": d["env_hash"], "fingerprint": d["fingerprint"], "policy": d["policy"], "code_hash": d["code_hash"], "appendix_extra": d.get("appendix_extra")}

    def template(self, kind, inp):
        d = self._run({"mode": "template", "kind": kind, "inputs": inp})
        return d["template"], {"env_hash": d["env_hash"], "fingerprint": d["fingerprint"], "policy": d["policy"], "code_hash": d["code_hash"]}

    def flip(self, method, inp, lo, hi):
        d = self._run({"mode": "flip", "method": method, "inputs": inp, "lo": str(lo), "hi": str(hi)}); return None if d["flip"] is None else D(d["flip"])

    def selftest(self, port: int = 9): return self._run({"mode": "selftest", "probe_port": port})["probes"]
    def spin(self): return self._run({"mode": "spin"})
