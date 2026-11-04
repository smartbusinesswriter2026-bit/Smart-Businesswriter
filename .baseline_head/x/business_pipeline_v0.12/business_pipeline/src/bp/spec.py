"""Problem Spec: drafted, user-confirmed, then frozen and hashed (section 5.2, App. A)."""
from dataclasses import dataclass, field
from .artifacts import sha

class SpecFrozen(Exception): pass

@dataclass
class ProblemSpec:
    objective: str
    method: str
    claims: list            # [{"id","text","type"}]
    inputs: dict            # id -> Tagged-ish dict
    assumptions: list
    sensitivity: dict       # assumption_id -> [min, max]
    thresholds: dict
    ambiguity_register: list = field(default_factory=list)
    decision_context: dict = field(default_factory=dict)
    checks: list = field(default_factory=list)
    data_manifest: list = field(default_factory=list)
    user_values: list = field(default_factory=list)
    framework: str | None = None
    fallbacks: dict = field(default_factory=dict)
    frameworks_selected: list = field(default_factory=list)   # user-confirmed registry selections, frozen with the spec (Stage 6)
    registry: dict = field(default_factory=dict)
    model_assistance: list = field(default_factory=list)   # hashes of model calls whose proposals the user used (Stage: model provider)
    version: int = 1
    hash: str | None = None
    amendments: list = field(default_factory=list)

    def content(self):
        d = dict(self.__dict__); d.pop("hash"); d.pop("amendments"); return d
    def freeze(self):
        self.hash = sha(self.content()); return self.hash
    def amend(self, reason: str, **changes) -> "ProblemSpec":
        """Changes create a new version; dependents must be recomputed (never silently reused)."""
        new = ProblemSpec(**{**self.content(), **changes, "version": self.version + 1})
        new.amendments = self.amendments + [{"from": self.version, "reason": reason}]
        return new
    def __setattr__(self, k, v):
        if self.__dict__.get("hash") and k not in ("hash",):
            raise SpecFrozen("spec is frozen; use amend()")
        object.__setattr__(self, k, v)
