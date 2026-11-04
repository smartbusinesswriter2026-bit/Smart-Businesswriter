"""People & organisation shelf coverage analyser.

Reports, for every framework profile in the product layer, which wiring layers
are present. Read-only: it never writes to the repo.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "src"))

import bp.product.framework_profiles as fp  # noqa: E402
import bp.product.drafting as drafting  # noqa: E402
import bp.product.subjects as subjects  # noqa: E402
import bp.registry as registry  # noqa: E402
import bp.templates as templates  # noqa: E402


def main():
    worksheets_by_template = {}
    for key, ws in subjects.WORKSHEETS.items():
        tmpl = ws.get("template")
        if tmpl:
            worksheets_by_template.setdefault(tmpl, []).append(key)

    links_by_template = {}
    for key, tmpl in registry.TEMPLATE_LINKS.items():
        links_by_template.setdefault(tmpl, []).append(key)

    rows = []
    for tid in sorted(fp.PROFILES):
        profile = fp.PROFILES[tid]
        rows.append(
            {
                "template": tid,
                "label": profile.get("label"),
                "subject": profile.get("subject"),
                "blocks": len(profile.get("blocks") or []),
                "in_templates": tid in templates.TEMPLATES,
                "in_canvas": tid in templates.CANVAS_BLOCKS,
                "worksheet": ",".join(worksheets_by_template.get(tid, [])),
                "registry": ",".join(links_by_template.get(tid, [])),
                "drafting": tid in drafting.SCHEMAS,
                "profile": True,
            }
        )

    # Catalogue records with no worksheet at all (read-and-cite only).
    records_no_ws = []
    for row in subjects.records("people") if hasattr(subjects, "records") else []:
        records_no_ws.append(row)

    print("== profiles and their wiring layers ==")
    hdr = "%-38s %-26s %-10s %5s %4s %4s %-10s %-10s %4s" % (
        "TEMPLATE", "LABEL", "SUBJECT", "BLK", "TPL", "CNV", "WORKSHEET", "REGISTRY", "DRF")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(
            "%-38s %-26s %-10s %5d %4s %4s %-10s %-10s %4s"
            % (
                r["template"],
                (r["label"] or "")[:25],
                str(r["subject"]),
                r["blocks"],
                "y" if r["in_templates"] else "-",
                "y" if r["in_canvas"] else "-",
                (r["worksheet"] or "-")[:10],
                (r["registry"] or "-")[:10],
                "y" if r["drafting"] else "-",
            )
        )

    full = [r for r in rows if r["in_templates"] and r["worksheet"] and r["registry"] and r["drafting"]]
    partial = [r for r in rows if r not in full]
    print("")
    print("fully wired (template+worksheet+registry+drafting): %d" % len(full))
    print("not fully wired: %d -> %s" % (len(partial), [r["template"] for r in partial]))

    # People shelf
    detail = subjects.detail("people")
    print("")
    print("== people shelf tiles ==")
    for tile in detail.get("tiles", []):
        print(
            "  %-22s ws=%d rec=%d tools=%d  %s"
            % (
                tile["key"],
                len(tile.get("worksheets") or []),
                len(tile.get("records") or []),
                len(tile.get("tools") or []),
                tile.get("label"),
            )
        )
    print("  total worksheets=%d records=%d tools=%d" % (
        len(detail.get("worksheets") or []),
        len(detail.get("records") or []),
        len(detail.get("tools") or []),
    ))


if __name__ == "__main__":
    main()
