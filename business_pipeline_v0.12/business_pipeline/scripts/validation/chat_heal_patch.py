# Append to chat_heal.py: code proposer

def propose_code_fix(finding, source_files=None):
    """Propose a code fix for a validation finding.

    `finding` is a finding dict (rule, subject, feature, section, message, ...).
    `source_files` is a list of {path, content} dicts (or paths) the model
    may read.  Returns (proposal: dict, error: str or None).  The proposal
    has keys: summary, diff, test, files.  It is NEVER applied automatically.
    """
    source_files = source_files or []
    # resolve paths to contents if strings were passed
    resolved = []
    for sf in source_files:
        if isinstance(sf, str):
            try:
                with open(sf, encoding="utf-8") as fh:
                    resolved.append({"path": sf, "content": fh.read()[:8000]})
            except OSError:
                continue
        elif isinstance(sf, dict):
            resolved.append({"path": sf.get("path", ""), "content": str(sf.get("content", ""))[:8000]})
    models = _models_for("code")
    if models is None:
        return None, "no model configured (set BP_HEAL_CODE_PROVIDER / BP_HEAL_CODE_MODEL)"
    system = (
        "You are a code proposer for a business analysis pipeline. "
        "Given a validation finding and the relevant source files, propose a "
        "minimal patch that addresses the finding. You may ONLY suggest changes "
        "to source files shown to you; never invent files. "
        "Return ONLY a JSON object with keys: "
        "\"summary\" (one sentence), "
        "\"diff\" (unified diff text), "
        "\"test\" (a pytest test that would fail before and pass after), "
        "\"files\" (list of paths touched). "
        "No markdown, no extra text."
    )
    user = json.dumps({"finding": finding, "source_files": resolved}, ensure_ascii=False)
    raw = _call_model(models, system, user)
    if raw is None:
        return None, "model call failed"
    try:
        data = json.loads(raw.strip().strip("`").strip())
        if isinstance(data, dict):
            return {
                "summary": str(data.get("summary", ""))[:300],
                "diff": str(data.get("diff", ""))[:8000],
                "test": str(data.get("test", ""))[:8000],
                "files": [str(p) for p in (data.get("files") or [])],
            }, None
    except (json.JSONDecodeError, AttributeError):
        pass
    return None, "could not parse model response"
PY