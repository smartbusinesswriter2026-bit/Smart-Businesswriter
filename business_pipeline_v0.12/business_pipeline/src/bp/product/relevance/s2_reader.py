"""RRA Stage S2 — Reader.

Converts raw snapshots (from S1) into EvidenceRecords.  Gate: excerpt must
appear verbatim in the snapshot text; tier assigned by domain rules (not
by the model).  Paywalled sources are flagged, not bypassed.
"""
import hashlib
import re
from datetime import datetime, timezone

from .schemas import EvidenceRecord, TIER_T1, TIER_T2, TIER_T3, ACCESS_OPEN, ACCESS_PAYWALLED
from . import storage

# Domain → tier mapping (mirrors allowlist; T1 for school/accreditor/standard-setter)
_DOMAIN_TIER = {
    "aacsb.edu": TIER_T1, "efmd.org": TIER_T1, "amba-bga.com": TIER_T1,
    "gmac.com": TIER_T1, "ifrs.org": TIER_T1, "fasb.org": TIER_T1,
    "efrag.org": TIER_T1, "ec.europa.eu": TIER_T1, "eur-lex.europa.eu": TIER_T1,
    "poetsandquants.com": TIER_T2, "clearadmit.com": TIER_T2,
    "arxiv.org": TIER_T2, "ssrn.com": TIER_T2,
}
_SCHOOL_DOMAINS = {
    "insead.edu", "hbs.edu", "wharton.upenn.edu", "mitsloan.mit.edu",
    "chicagobooth.edu", "kellogg.northwestern.edu", "gsb.columbia.edu",
    "som.yale.edu", "darden.virginia.edu", "michiganross.umich.edu",
    "stanford.edu", "lbs.edu", "iese.edu", "hec.edu", "esade.edu",
    "sbs.ox.ac.uk", "jbs.cam.ac.uk", "imperial.ac.uk", "imd.org",
    "unibocconi.it", "rsm.nl", "unisg.ch", "frankfurt-school.de",
    "novasbe.pt", "vlerick.com",
}
_T2_DOMAINS = {"poetsandquants.com", "clearadmit.com", "arxiv.org", "ssrn.com"}


def _tier_for_domain(domain):
    domain = str(domain or "").lower()
    if domain in _DOMAIN_TIER:
        return _DOMAIN_TIER[domain]
    if domain in _SCHOOL_DOMAINS:
        return TIER_T1
    if domain in _T2_DOMAINS:
        return TIER_T2
    # Check allowlist file
    try:
        from pathlib import Path
        import json
        root = Path(__file__).resolve().parents[4]
        path = root / "qa" / "relevance" / "allowlist.json"
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                al = json.load(f)
            for entry in (al.get("allowed") or []):
                ad = str(entry.get("domain", "")).lower()
                if domain == ad or domain.endswith("." + ad):
                    tier = entry.get("tier", "T3")
                    if tier in ("T1", "T2", "T3"):
                        return tier
    except Exception:
        pass
    return TIER_T3


def _collapse_whitespace(value):
    """Reduce every run of whitespace to a single space.

    The model copies a passage as it reads it, and it reads a list as one
    line: the page carries ``Partial written exam: 40%`` and
    ``End-of-term written exam: 40%`` on separate lines, and the model
    returns them separated by a space.  The passage is the same passage.
    Comparing the two with the line breaks intact rejected it, and the
    reader fell back to the opening words — which on a course catalogue
    are the navigation menu, not the assessment rule.
    """
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _verify_excerpt_verbatim(excerpt, snapshot_text):
    """Check that the excerpt appears verbatim in the snapshot text.

    "Verbatim" means **the same words, in the same order, unchanged** — not
    a paraphrase and not an invention.  It does not mean "with the page's
    line breaks in the same places": the page's own layout is not part of
    what the reader quoted, and a passage the model copied across a line
    break is still that passage.  So the comparison is made on whitespace
    collapsed, and every other character still has to match.
    """
    excerpt = str(excerpt or "").strip()
    text = str(snapshot_text or "")
    if not excerpt:
        return False
    if excerpt in text:
        return True
    # The same words, the page's line breaks normalised away.
    return _collapse_whitespace(excerpt) in _collapse_whitespace(text)


def _html_to_text(raw):
    """Turn a fetched HTML page into readable text.  Stdlib only."""
    import re
    text = str(raw or "")
    if "<" not in text:
        return text
    text = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?is)<!--.*?-->", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|section|article)>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = (text.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&lt;", "<").replace("&gt;", ">")
                .replace("&quot;", '"').replace("&#39;", "'"))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


_EXTRACT_SYSTEM = (
    "You read a page from a business school, accreditor or standard-setter and "
    "return the one passage that matters for a curriculum-and-assessment study.\n"
    "Rules you must follow:\n"
    "1. Copy the passage EXACTLY as it appears. Do not paraphrase, do not correct, "
    "do not summarise, do not add or remove a single character.\n"
    "2. The passage must be at most 25 words.\n"
    "3. Prefer a passage that names required courses, core subjects, assessment "
    "forms, credit/weight rules, or a standard's name and date. If the page names "
    "none of these, say so with an empty excerpt.\n"
    "4. Answer with a JSON object only: {\"excerpt\": \"...\", \"topics\": [\"...\"], "
    "\"relevant\": true}\n"
    "5. If the passage is not about curriculum, assessment or a standard, set "
    "\"relevant\" to false and \"excerpt\" to \"\".\n"
    "6. Never invent a passage. An empty excerpt is always better than a wrong one."
)


def _model_excerpt(page_text, url):
    """Ask the model for the passage that matters.  Returns (excerpt, topics).

    The answer is a proposal.  The verbatim check in `snapshot_to_evidence`
    is done by code; a model answer that is not a literal substring of the
    page is discarded.
    """
    from . import model as _model
    text = _html_to_text(page_text)
    if not text:
        return "", []
    # Keep the prompt inside the input cap.
    limit = _model.max_input_chars()
    body = text[:max(1000, limit - 1200)]
    user = "URL: %s\n\nPAGE TEXT:\n%s\n\nJSON:" % (url, body)
    parsed, _record, err = _model.call_json(_EXTRACT_SYSTEM, user, task="relevance-extract")
    if err or not isinstance(parsed, dict):
        return "", []
    excerpt = str(parsed.get("excerpt") or "").strip()
    topics = parsed.get("topics")
    if not isinstance(topics, list):
        topics = []
    topics = [str(t).strip().lower() for t in topics if str(t).strip()][:8]
    # The excerpt must be a literal passage of the page.  A passage the
    # model copied across a line break is still that passage, so the check
    # is the same one the reader makes, with the page's line breaks
    # normalised away.
    if excerpt and not _verify_excerpt_verbatim(excerpt, text):
        return "", topics
    return excerpt, topics


def _first_words(text, count=25):
    """The first `count` words of a text, guaranteed to be a literal substring.

    The slice is taken from the original text (never rebuilt from split
    words), so the result is always found by a plain `in` test — whatever the
    whitespace is.
    """
    source = str(text or "")
    if not source.strip():
        return ""
    end = 0
    seen = 0
    for match in re.finditer(r"\S+", source):
        seen += 1
        if seen >= count:
            end = match.end()
            break
    else:
        end = len(source)
    if not end:
        return ""
    candidate = source[:end].strip()
    return candidate if candidate and candidate in source else ""


def _named_topics(page_text, limit=16):
    """The taxonomy topics whose name appears in a page.

    A derived fact, not a copy of the page: the reader stores a 25-word
    excerpt, and a course-catalogue page can name a framework outside its
    excerpt.  Without this the control set could not see the page, and every
    gap it should have promoted would be withheld.
    """
    text = str(page_text or "")
    if not text.strip():
        return []
    try:
        from .s0_scope import load_taxonomy
        taxonomy = load_taxonomy()
    except Exception:
        return []
    found = []
    for topic in (taxonomy.get("topics", []) if isinstance(taxonomy, dict) else []):
        label = str(topic.get("label", "")).strip()
        if not label:
            continue
        # A label too short to text-match safely is not evidence.  "5S"
        # stripped of punctuation is "5s", which appears by chance in almost
        # any long page; and a two-letter token matches course codes.  Such a
        # topic is evidenced by the catalogue, not by a page.
        if len(_squash(label)) < 4:
            continue
        # A topic may declare the other ways it is written.  The taxonomy
        # names the framework as the product knows it ("Porter's Five
        # Forces", "Ansoff Growth Matrix"), but a course page writes the
        # short name ("Five Forces", "Ansoff").  Without the alias the page
        # was read and the name was on it, and the control still scored
        # zero.  The aliases live in the owner-edited taxonomy, so the
        # spelling is data and not a special case in the code.
        aliases = [str(a).strip() for a in (topic.get("aliases") or []) if str(a).strip()]
        if any(_label_present(alias, text) for alias in aliases):
            found.append(label)
        elif _label_present(label, text):
            found.append(label)
        if len(found) >= limit:
            break
    return found


def _label_present(label, text):
    """Does a page carry a taxonomy label?

    A label may be written several ways, so several forms are tried:

    - the label itself ("Balanced Scorecard");
    - the label without its parenthetical ("OKR (Objectives and Key Results)"
      becomes "OKR", and the parenthetical on its own);
    - the label with the possessive dropped ("Porter's Five Forces" against a
      page's "Porter Five Forces").

    A **short** form is never compared with punctuation stripped: the stripped
    form of "5S" is "5s", which appears by chance in almost any long page
    ("...2015 students..."), and a label that matches everything matches
    nothing.  A short form must sit on a word boundary.

    A **long** form is compared with punctuation stripped, so "growth-share"
    and "growth share" are the same name.
    """
    squashed_text = _squash(text)
    for candidate in _label_forms(label):
        squashed = _squash(candidate)
        if not squashed:
            continue
        if len(squashed) >= 6:
            if squashed in squashed_text:
                return True
        else:
            try:
                if re.search(r"\b%s\b" % re.escape(candidate), text, re.I):
                    return True
            except re.error:
                continue
    # An acronym carried by a longer label is distinctive enough on its own:
    # a page writes "PESTEL" far more often than "PESTEL analysis".
    words = label.split()
    if len(words) >= 2:
        first = words[0].strip("(),.:;")
        if len(first) >= 3 and first.upper() == first and first.isalpha():
            try:
                return bool(re.search(r"\b%s\b" % re.escape(first), text))
            except re.error:
                return False
    return False


def _label_forms(label):
    """The ways a label may be written, most specific first."""
    forms = [label]
    head = label.split("(", 1)[0].strip()
    inside = ""
    if "(" in label and ")" in label:
        inside = label.split("(", 1)[1].rsplit(")", 1)[0].strip()
    if head and head != label:
        forms.append(head)
    if inside:
        forms.append(inside)
    if "'s " in label.lower() or label.lower().endswith("'s"):
        without = re.sub(r"'s\b", "", label, flags=re.I).strip()
        if without and without not in forms:
            forms.append(without)
    return [f for f in forms if f]


def _squash(value):
    """Lowercase and drop punctuation and spaces, so two spellings compare."""
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def snapshot_to_evidence(snapshot, school_or_body="", region="other",
                         program_level="", topic_tags=None, taxonomy_family="",
                         excerpt="", use_model=True):
    """Convert a snapshot dict into an EvidenceRecord.

    Returns (record, error).  When `excerpt` is empty the reader asks the
    model to pick the passage that matters (curriculum, assessment form,
    standard text); the excerpt is then checked **verbatim** against the
    fetched text by code, and a model answer that is not a literal substring
    is discarded.  With no model configured the first words of the page are
    used instead.
    """
    if not isinstance(snapshot, dict):
        return None, "snapshot must be a dict"

    url = snapshot.get("url", "")
    domain = snapshot.get("domain", "")
    fetched_at = snapshot.get("fetched_at", "")
    sha = snapshot.get("sha256", "")
    paywalled = snapshot.get("paywalled", False)
    # The fetched body (in memory only).  The scout keeps it under "_text".
    raw_text = snapshot.get("_text") or snapshot.get("_full_text") or snapshot.get("text_excerpt", "")
    # Read against the readable text (HTML stripped), so an excerpt is a
    # sentence a person can quote rather than a fragment of markup.
    full_text = _html_to_text(raw_text)

    if not url:
        return None, "snapshot missing url"
    if not sha:
        return None, "snapshot missing sha256 (fetch may have failed)"

    tier = _tier_for_domain(domain)

    if not excerpt and use_model and full_text:
        excerpt, tags = _model_excerpt(full_text, url)
        if tags and not topic_tags:
            topic_tags = tags

    if not excerpt:
        excerpt = _first_words(full_text, 25)

    if not excerpt:
        return None, "no excerpt could be extracted"

    # Verbatim check — code, not the model.
    if not _verify_excerpt_verbatim(excerpt, full_text):
        # The model's answer was not literal: fall back to the opening words.
        excerpt = _first_words(full_text, 25)
        if not excerpt or not _verify_excerpt_verbatim(excerpt, full_text):
            return None, "excerpt does not appear verbatim in snapshot text"

    access = ACCESS_PAYWALLED if paywalled else ACCESS_OPEN

    # Which taxonomy topics does this page name?  A derived fact, not a copy
    # of the page: the excerpt is 25 words, and a course-catalogue page can
    # name a framework outside its excerpt.  Without this the control set
    # could not see the page, and would withhold every gap it should have
    # promoted.
    mentions = _named_topics(full_text)

    rec = EvidenceRecord(
        id="",  # set by make_id after creation
        run_id="",  # set by caller
        school_or_body=school_or_body or domain,
        region=region,
        program_level=program_level,
        source_url=url,
        retrieved_at_utc=fetched_at or datetime.now(timezone.utc).isoformat(),
        sha256=sha,
        tier=tier,
        access=access,
        excerpt=excerpt,
        topic_tags=list(topic_tags or []),
        mentions=mentions,
        taxonomy_family=taxonomy_family,
    )
    rec.id = rec.make_id()
    # Validate (includes blocked domain check)
    ok, reason = rec.validate()
    if not ok:
        return None, reason
    return rec, ""


def snapshots_to_evidence(snapshots, run_id="", school_or_body="", region="other",
                          topic_tags=None, taxonomy_family="", use_model=True):
    """Convert a list of snapshots into EvidenceRecords.

    Returns (records_list, errors_list).  Records that fail validation are
    skipped and their errors collected.
    """
    records = []
    errors = []
    for snap in (snapshots or []):
        rec, err = snapshot_to_evidence(
            snap, school_or_body=school_or_body, region=region,
            topic_tags=topic_tags, taxonomy_family=taxonomy_family,
            use_model=use_model,
        )
        if err:
            errors.append({"url": snap.get("url", ""), "error": err})
            continue
        if rec is not None:
            rec.run_id = run_id
            ok, reason = rec.validate()
            if ok:
                records.append(rec)
            else:
                errors.append({"url": snap.get("url", ""), "error": reason})
    return records, errors
