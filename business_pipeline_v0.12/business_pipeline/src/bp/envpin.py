"""Environment fingerprint: what actually ran (manual 5.4). Hashes interpreter, platform and the bp source itself."""
import hashlib, os, platform, sys
from .artifacts import sha

def source_hash() -> str:
    h = hashlib.sha256(); d = os.path.dirname(os.path.abspath(__file__))
    for f in sorted(os.listdir(d)):
        if f.endswith(".py"):
            h.update(f.encode()); h.update(open(os.path.join(d, f), "rb").read())
    return h.hexdigest()

def fingerprint() -> dict:
    return {"python": sys.version.split()[0], "implementation": platform.python_implementation(), "system": platform.system(), "machine": platform.machine(),
            "bp_source": source_hash(), "third_party_packages": [], "hashseed": os.environ.get("PYTHONHASHSEED", "unset")}

def env_hash(fp: dict | None = None) -> str: return sha(fp or fingerprint())
