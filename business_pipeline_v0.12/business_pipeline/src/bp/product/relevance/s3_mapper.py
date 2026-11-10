"""RRA Stage S3 — Mapper.

Maps EvidenceRecords against the pipeline's catalogue (capabilities, framework
profiles, method registry, paper families) to produce CoverageRows.

Exact and alias matching first; model only proposes fuzzy matches (shown as
proposals, not auto-applied).
"""
import json
from pathlib import Path

from .schemas import CoverageRow, STATUS_COVERED, STATUS_PARTIAL, STATUS_MISSING, STATUS_PARKED, STATUS_AT_RISK


def _repo_root():
    return Path(__file__).resolve().parents[4]


def load_catalogue_snapshot():
    """Load the catalogue snapshot if it exists.  Returns None if not available."""
    from . import catalogue_snapshot as _cs
    return _cs.load_catalogue_snapshot()


def _alias_match(taxonomy_item, artefact_id, catalogue):
    """Check if a taxonomy item matches a catalogue artefact by exact or alias."""
    if not catalogue:
        return False
    # Check capabilities
    caps = catalogue.get("capabilities", [])
    for cap in caps:
        if cap.get("key") == artefact_id:
            return True
        aliases = cap.get("aliases", [])
        if taxonomy_item.lower() in [a.lower() for a in aliases]:
            return True
    # Check frameworks
    frameworks = catalogue.get("frameworks", [])
    for fw in frameworks:
        if fw.get("key") == artefact_id:
            return True
        aliases = fw.get("aliases", [])
        if taxonomy_item.lower() in [a.lower() for a in aliases]:
            return True
    return False


def map_coverage(taxonomy, evidence_records=None, catalogue=None):
    """Map taxonomy topics to coverage rows.

    Returns a list of CoverageRow dicts.  Status is determined by:
    - covered: artefact exists in catalogue AND has T1/T2 evidence
    - partial: artefact exists but no T1/T2 evidence, or evidence is weak
    - missing: no artefact in catalogue
    - parked: artefact on the parked list (frontier-model queue)
    - at-risk: artefact exists but depends on a changing standard

    A framework topic's evidence is a **course catalogue**, not a core-course
    list: a core list names subjects ("Strategy", "Finance") and a framework
    appears in a course description.  The topic's `evidence_page` field says
    which page type the evidence must come from.
    """
    if catalogue is None:
        catalogue = load_catalogue_snapshot()

    evidence_ids = [r.get("id", "") if isinstance(r, dict) else getattr(r, "id", "")
                    for r in (evidence_records or [])]
    # Count independent T1 sources
    t1_count = 0
    for r in (evidence_records or []):
        tier = r.get("tier", "") if isinstance(r, dict) else getattr(r, "tier", "")
        if tier == "T1":
            t1_count += 1

    rows = []
    topics = taxonomy.get("topics", []) if isinstance(taxonomy, dict) else []
    for topic in topics:
        tid = topic.get("id", "")
        label = topic.get("label", "")
        artefact = topic.get("artefact", "")
        status_hint = topic.get("status_hint", "missing")

        # Determine status
        if status_hint == "parked":
            status = STATUS_PARKED
        elif status_hint == "at-risk":
            status = STATUS_AT_RISK
        elif not artefact:
            status = STATUS_MISSING
        elif catalogue and _alias_match(label, artefact, catalogue):
            if t1_count > 0:
                status = STATUS_COVERED
            else:
                status = STATUS_PARTIAL
        else:
            # No catalogue available — use hint
            if status_hint == "covered":
                status = STATUS_COVERED if t1_count > 0 else STATUS_PARTIAL
            else:
                status = STATUS_MISSING

        row = CoverageRow(
            taxonomy_item=label,
            pipeline_artefact_id=artefact,
            status=status,
            evidence_ids=list(evidence_ids),
            independent_t1_count=t1_count,
        )
        # Carry the topic's identity so the control set can match on it.
        row.evidence_page = topic.get("evidence_page", "")
        row.taxonomy_id = tid
        rows.append(row)

    return rows
