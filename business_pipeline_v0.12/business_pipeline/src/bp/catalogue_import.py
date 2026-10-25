"""Import the curated catalogue (markdown) into registry records (Build Charter Stage 6).
Deterministic: the same markdown always yields the same JSON. Nothing is invented: evidence status, limitations and
contraindications stay empty or 'unreviewed' until a human curates them."""
import hashlib, json, re, sys

SECTION_DISCIPLINE = {3: "strategy", 4: "change and organization", 5: "marketing and customers", 6: "operations and supply chain", 7: "risk and decision analysis",
                      8: "performance, projects and technology governance", 9: "people and learning", 10: "public, nonprofit and impact evaluation"}
Q_SUB = {"11.1": ("FIN", "finance, accounting and managerial economics"), "11.2": ("MKT", "market and customer analytics"), "11.3": ("STA", "statistics and empirical research"),
         "11.4": ("OPS", "operations, logistics and optimization"), "11.5": ("DEC", "decision analysis and risk quantification"), "11.6": ("EVL", "program and impact evaluation")}
# Entries whose edition, trademark or permissions the catalogue itself says must be verified before use (section 16 and the type column).
VERIFY_NAMES = re.compile(r"ISO 31000|SCOR|PMBOK|COBIT|ITIL", re.I)
TYPES = ("F", "M", "Q", "T")

def _norm(name): return re.sub(r"[^a-z0-9]+", "", name.lower())

def _split_type(raw):
    toks = [t.strip() for t in re.split(r"/|—|-{2,}", raw) if t.strip()]
    types = [t for t in toks if t in TYPES]; note = " ".join(t for t in toks if t not in TYPES)
    if not types: raise ValueError(f"unrecognised type {raw!r}")
    return types[0], types[1:], note

def _first_clause(text, limit=90):
    m = re.split(r";|\. | with | where | when | only | — ", text, maxsplit=1)[0].strip().rstrip(".:")
    return (m if len(m) <= limit else m[:limit].rsplit(" ", 1)[0]).strip()

def import_catalogue(path):
    raw = open(path, "rb").read(); lines = raw.decode("utf-8").splitlines()
    ver = next((re.search(r"\*\*Version:\*\*\s*([\d.]+)", l).group(1) for l in lines if "**Version:**" in l), None)
    records, section, sub, warnings = [], None, None, []
    rows = []
    for l in lines:
        h = re.match(r"##\s+(\d+)\.", l)
        if h: section, sub = int(h.group(1)), None
        s = re.match(r"###\s+(\d+\.\d+)", l)
        if s: sub = s.group(1)
        if re.match(r"\|\s*[A-Z]{2,5}-\d+\s*\|", l):
            c = [x.strip() for x in l.strip().strip("|").split("|")]
            if len(c) != 5: raise ValueError(f"bad table row: {l[:60]}")
            rows.append((section, c))
        elif section == 11 and sub in Q_SUB and l.startswith("- "): rows.append((("Q", sub), l[2:].strip()))
        elif section == 12 and l.startswith("- ") and "theor" in l.lower(): rows.append((("T", None), l[2:].strip()))
    byname = {}
    qn = {k: 0 for k in Q_SUB}; tn = 0
    for sec, c in rows:
        if isinstance(sec, tuple) and sec[0] == "Q":
            key, disc = Q_SUB[sec[1]]; qn[sec[1]] += 1; text = c.replace("**", "")
            label = re.match(r"\*\*([^*]+?):\*\*", c)
            name = label.group(1) if label else _first_clause(text)
            records.append({"id": f"QNT-{key}-{qn[sec[1]]:02d}", "name": name, "type": "Q", "secondary_types": [], "type_note": "group: one catalogue bullet, which may name several methods",
                            "disciplines": [disc], "aliases": [], "also_listed_as": [], "structures": "", "evidence_needs": "", "summary": text, "members": [],
                            "source_ref": f"catalogue section {sec[1]}, bullet {qn[sec[1]]}", "id_basis": "importer-assigned by bullet position; the catalogue gives Q items no IDs"})
        elif isinstance(sec, tuple) and sec[0] == "T":
            tn += 1; text = c.replace("**", ""); body = re.sub(r"\([^)]*\)", "", text).rstrip(".")
            members = [m.strip() for m in re.split(r",| and ", re.sub(r"\b(theories|theory|and other.*|when relevant.*)$", "", body, flags=re.I)) if m.strip()]
            records.append({"id": f"THE-{tn:02d}", "name": _first_clause(text, 70), "type": "T", "secondary_types": [], "type_note": "group: one catalogue bullet naming several theories",
                            "disciplines": ["supporting theory"], "aliases": [], "also_listed_as": [], "structures": "", "evidence_needs": "", "summary": text, "members": members,
                            "source_ref": f"catalogue section 12, bullet {tn}", "id_basis": "importer-assigned by bullet position", "members_note": "split heuristically from prose; verify before relying on the list"})
        else:
            rid, name, traw, struct, ev = c; ptype, sec_types, note = _split_type(traw); disc = SECTION_DISCIPLINE[sec]
            k = _norm(name)
            if k in byname:   # same item listed in two catalogue sections: one canonical record, both IDs kept
                r = byname[k]; r["also_listed_as"].append(rid)
                if disc not in r["disciplines"]: r["disciplines"].append(disc)
                if struct != r["structures"]: r.setdefault("structures_alt", []).append({"from": rid, "text": struct})
                if ev != r["evidence_needs"]: r.setdefault("evidence_needs_alt", []).append({"from": rid, "text": ev})
                warnings.append(f"{rid} duplicates {r['id']} ({name}); merged")
                continue
            r = {"id": rid, "name": name, "type": ptype, "secondary_types": sec_types, "type_note": note, "disciplines": [disc], "aliases": [], "also_listed_as": [],
                 "structures": struct, "evidence_needs": ev, "summary": struct, "members": [], "source_ref": f"catalogue section {sec}, row {rid}",
                 "verify_edition_and_permissions": bool(VERIFY_NAMES.search(name) or "reference" in note)}
            byname[k] = r; records.append(r)
            al = re.findall(r"\(([^)]+)\)", name)
            r["aliases"] = [a.strip() for a in al if len(a.strip()) <= 40] + [p.strip() for p in re.split(r"\s*/\s*", re.sub(r"\([^)]*\)", "", name)) if len(re.split(r"\s*/\s*", name)) > 1 and p.strip()]
            if "Five Forces" in name: r["aliases"].append("5 forces")
            lead = name.split()[0]
            if re.fullmatch(r"[A-Z]{3,6}", lead) and lead not in r["aliases"]: r["aliases"].append(lead)    # e.g. "BCG Growth-Share Matrix" -> BCG
    for r in records:
        r.update({"evidence_status": "unreviewed", "pipeline_status": "catalogued", "limitations": [], "when_not_to_use": [], "related": [], "licensing_review": "not_reviewed",
                  "catalogue_version": ver, "version": "0.1"})
    return {"schema_version": "1", "registry_version": "0.1.0", "source": {"file": path.replace("\\", "/").split("/")[-1], "catalogue_version": ver, "sha256": hashlib.sha256(raw).hexdigest()},
            "import_warnings": warnings, "records": records}

if __name__ == "__main__":
    out = import_catalogue(sys.argv[1]); json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    from collections import Counter; print(len(out["records"]), dict(Counter(r["type"] for r in out["records"])), out["import_warnings"])
