"""Management & Strategy audit: what the green tests do not check.

Reports, measured from the live registries:
  * worksheets whose template is absent from PROFILES (dead link)
  * worksheets not marked draftable (a student cannot complete them)
  * profiles reachable from no subject page
  * a template declared in BOTH CANVAS_BLOCKS and MATRIX_META (one form only)
  * each worksheet's declared form vs the form its blocks imply
"""
import json
import sys

sys.path.insert(0, "src")

from bp.product import framework_profiles as fp   # noqa: E402
from bp.product import subjects                   # noqa: E402
from bp import templates                          # noqa: E402

SUBJECT = "management"


def ids_from(container):
    if isinstance(container, dict):
        return set(container)
    return {getattr(item, "id", None) or getattr(item, "key", None) for item in container}


def main():
    detail = subjects.detail(SUBJECT)
    profiles = fp.PROFILES
    lines = []
    add = lines.append

    add("SHELF management: tools=%d worksheets=%d records=%d tiles=%d"
        % (len(detail["tools"]), len(detail["worksheets"]),
           len(detail["records"]), len(detail["tiles"])))

    # every worksheet on the shelf
    add("")
    add("WORKSHEETS ON THIS SHELF")
    dead, not_draftable = [], []
    for sheet in detail["worksheets"]:
        key = sheet.get("key") or sheet.get("id")
        template = sheet.get("template") or sheet.get("key")
        profile = profiles.get(template)
        draftable = bool(sheet.get("draftable", True))
        blocks = len((profile or {}).get("blocks") or []) if isinstance(profile, dict) else 0
        add("  %-9s template=%-28s profile=%-5s blocks=%-2s draftable=%s form=%s"
            % (key, template, "yes" if profile else "NO", blocks, draftable,
               sheet.get("form") or (profile or {}).get("form")))
        if profile is None:
            dead.append(key)
        if not draftable:
            not_draftable.append(key)

    # reachability across every shelf
    reachable = set()
    for row in getattr(subjects, "SUBJECT_DEFS", []) or []:
        for sheet in subjects.detail(row["id"])["worksheets"] or []:
            reachable.add(sheet.get("template") or sheet.get("key"))
    unreachable = sorted(set(profiles) - reachable)

    # double form declaration
    canvas = ids_from(getattr(templates, "CANVAS_BLOCKS", {}))
    matrix = ids_from(getattr(templates, "MATRIX_META", {}))
    both = sorted(canvas & matrix)

    add("")
    add("DEAD WORKSHEET LINKS (no profile): %s" % (dead or "none"))
    add("NOT DRAFTABLE: %s" % (not_draftable or "none"))
    add("PROFILES REACHABLE FROM NO PAGE: %d %s" % (len(unreachable), unreachable[:12]))
    add("TEMPLATES DECLARED IN BOTH CANVAS AND MATRIX: %s" % (both or "none"))

    text = "\n".join(lines)
    open("qa/baseline/_mgmt_audit.txt", "w", encoding="utf-8").write(text)
    print(text)


if __name__ == "__main__":
    main()
