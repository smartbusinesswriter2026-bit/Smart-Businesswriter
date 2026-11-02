"""Immutable hashed artifacts with metric/period/entity/scope labels (sections 5.4, 6, App. B)."""
import hashlib, json
from dataclasses import dataclass, field
from .quantity import Quantity

def sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

class RefMismatch(Exception): pass

@dataclass(frozen=True)
class Artifact:
    id: str
    value: Quantity
    labels: tuple  # (metric, period, entity, scope)
    spec_hash: str
    code_hash: str
    inputs_hash: str
    derivation: str
    produced_by: str
    env_hash: str = ""
    method_version: str = ""
    run_id: str = ""
    created_at: str = ""
    @property
    def metric(self): return self.labels[0]
    @property
    def period(self): return self.labels[1]

class ArtifactStore:
    def __init__(self): self._a: dict[str, Artifact] = {}
    def put(self, a: Artifact):
        if a.id in self._a: raise ValueError(f"artifact {a.id} is immutable")
        self._a[a.id] = a
    def resolve(self, id, metric, period) -> Artifact:
        a = self._a[id]
        if (a.metric, a.period) != (metric, period):
            raise RefMismatch(f"token wants {metric}/{period}, artifact is {a.metric}/{a.period}")
        return a
    def all(self): return list(self._a.values())

def env_hash() -> str:
    from .envpin import env_hash as _e
    return _e()
