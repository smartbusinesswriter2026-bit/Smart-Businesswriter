"""Single source of truth for the conductor framework keys.

The paper-shape and dimensions still live in `chat.FRAMEWORKS`, because they are
the paper's structure.  This module carries only the registry-level facts that
other modules used to restate by hand — the labels, which frameworks retrieve
evidence, which need an evidence probe, and the alias words.  Adding a framework
means editing this file and `chat.FRAMEWORKS`, not every module that mentions it.

Standard library only.
"""
import re

#: key -> the label a reader sees.
LABELS = {
    "none": "No framework",
    "pestel": "PESTEL",
    "swot": "SWOT",
    "pestel_swot": "PESTEL and SWOT",
    "five_forces": "Five Forces",
    "five_forces_breakeven": "Five Forces and break-even",
    "value_chain": "Value Chain",
    "ansoff": "Ansoff Growth Matrix",
    "vrio": "VRIO",
    "breakeven": "Break-even",
}

#: Frameworks that retrieve external evidence and may carry a computation.
EVIDENCE = ("pestel", "swot", "pestel_swot", "five_forces", "five_forces_breakeven",
            "value_chain", "ansoff")

#: Frameworks whose brief must offer an external cue before the conductor runs.
#: A PESTEL brief with no market/country cue is refused rather than approximated.
PROBE = ("pestel",)

#: Framework ids and their single-name aliases.  Combination aliases stay in the
#: typed instruction reader, which needs its longest-first and negation rules.
ALIASES = {
    "pestel": ("pestel", "pestle", "pestel analysis", "pestle analysis"),
    "swot": ("swot", "tows", "swot analysis"),
    "pestel_swot": ("pestel and swot", "pestel + swot", "pestel & swot"),
    "five_forces": ("porter's five forces", "porters five forces", "porter's model",
                    "porter model", "5 forces", "five forces"),
    "five_forces_breakeven": ("five forces and break-even", "five forces and breakeven"),
    "value_chain": ("value chain", "porter's value chain", "porters value chain"),
    "ansoff": ("ansoff", "ansoff matrix", "ansoff growth matrix"),
    "vrio": ("vrio", "vrio framework"),
    "breakeven": ("break-even", "breakeven", "break even", "break-even analysis"),
    # Profile-backed frameworks (leadership, culture, ethics).  The alias list is
    # what lets the Home chat infer them without a second table elsewhere.
    "leadership_theory_comparison": ("leadership theory", "transformational leadership",
                                     "transactional leadership", "charismatic leadership",
                                     "servant leadership", "authentic leadership",
                                     "leadership comparison"),
    "situational_leadership": ("situational leadership", "contingency leadership", "fiedler",
                               "hersey", "blanchard", "path-goal", "path goal"),
    "leader_effectiveness": ("leader effectiveness", "leadership effectiveness"),
    "leadership_development": ("leadership development", "leadership training", "leadership plan"),
    "culture_framework_comparison": ("hofstede", "globe", "trompenaars", "cultural dimensions",
                                     "culture comparison", "cultural framework"),
    "cross_cultural_leadership": ("cross-cultural leadership", "cross cultural leadership"),
    "organisational_culture": ("organisational culture", "organizational culture", "schein",
                               "denison", "culture diagnosis"),
    "ethical_dilemma": ("ethical dilemma", "ethical analysis", "utilitarian", "deontology",
                        "deontological", "virtue ethics", "kantian"),
    "stakeholder_csr": ("stakeholder", "corporate social responsibility", "csr",
                        "triple bottom line", "shareholder primacy"),
    "ethical_decision_process": ("ethical decision", "moral intensity", "moral sensitivity"),
}

#: Words that name a framework, used to stop a dimension matcher scoring them.
WORDS = {word for _key, label in LABELS.items()
         for word in re.findall(r"[a-z][a-z0-9'-]+", label.lower())}


def label(key, default=None):
    """The reader-facing label for a framework key."""
    return LABELS.get(str(key or ""), default if default is not None else str(key or ""))


def retrieves_evidence(key):
    """Whether the framework is searched for external evidence."""
    return str(key or "") in EVIDENCE


def needs_probe(key):
    """Whether the brief must name an external cue before the framework runs."""
    return str(key or "") in PROBE
