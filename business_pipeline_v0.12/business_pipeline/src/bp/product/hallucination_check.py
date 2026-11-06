"""Hallucination detection for generated papers (product layer, stdlib only).

Checks generated prose against evidence items for:
  1. Relevance — sources must be relevant to the decision topic
  2. Claim traceability — every sentence must trace to an evidence item
  3. Recommendation guard — no unsupported "should/must/recommend"
  4. Context guard — no invented place names/countries
  5. Scope guard — no unsupported "all/always/never/every"

Uses rule-based checks (fast, deterministic) plus an optional model call
for deeper verification (slower, costs credits).

Returns a list of findings: {sentence, type, reason, severity}.
"""
import re
import json
import os

# ── Rule-based checks ──────────────────────────────────────────────────────

def _extract_sentences(text):
    """Split text into sentences."""
    # Simple sentence splitting
    parts = re.split(r'(?<=[.!?])\s+', str(text or ''))
    return [s.strip() for s in parts if s.strip() and len(s.strip()) > 10]


def _extract_evidence_text(items):
    """Extract all text from evidence items for matching."""
    texts = []
    for item in (items or []):
        if isinstance(item, dict):
            for key in ('quote', 'text', 'title', 'abstract', 'content', 'summary'):
                if item.get(key):
                    texts.append(str(item[key]))
            if item.get('source'):
                texts.append(str(item['source']))
        elif isinstance(item, str):
            texts.append(item)
    return ' '.join(texts).lower()


def _extract_topics(decision, items):
    """Extract topic keywords from the decision and evidence."""
    topics = set()
    # From decision
    for word in re.findall(r'[a-zA-Z]{4,}', str(decision or '')):
        topics.add(word.lower())
    # From evidence titles
    for item in (items or []):
        if isinstance(item, dict) and item.get('title'):
            for word in re.findall(r'[a-zA-Z]{4,}', str(item['title'])):
                topics.add(word.lower())
    return topics


def check_relevance(source_text, decision_topic, dimension_cue):
    """Check if a source is relevant to the decision topic.

    Returns (relevant: bool, reason: str).
    """
    source_lower = str(source_text or '').lower()
    topic_lower = str(decision_topic or '').lower()
    cue_lower = str(dimension_cue or '').lower()

    # Extract key topic words (4+ chars)
    topic_words = set(re.findall(r'[a-z]{4,}', topic_lower))
    source_words = set(re.findall(r'[a-z]{4,}', source_lower))

    # Check if source shares at least 2 topic words with the decision
    overlap = topic_words & source_words
    if len(overlap) < 2:
        return False, "Source shares only %d topic words with decision (need 2+): %s" % (
            len(overlap), ', '.join(sorted(overlap)) if overlap else 'none')

    # Check if source is about a completely different domain
    # (e.g., Canadian agriculture for EV charging)
    irrelevant_domains = {
        'agriculture': ['farm', 'crop', 'livestock', 'harvest', 'planting'],
        'healthcare': ['patient', 'hospital', 'clinical', 'medical', 'disease'],
        'education': ['student', 'school', 'university', 'curriculum', 'teacher'],
    }
    for domain, keywords in irrelevant_domains.items():
        if any(kw in source_lower for kw in keywords):
            if not any(kw in topic_lower for kw in keywords):
                return False, "Source appears to be about %s, not the decision topic" % domain

    return True, "OK"


def check_claim_traceability(sentence, evidence_text):
    """Check if a sentence's claims can be traced to evidence.

    Returns (traceable: bool, reason: str).
    """
    sentence_lower = str(sentence or '').lower()

    # Extract key claims (nouns and adjectives, 4+ chars)
    claim_words = set(re.findall(r'[a-z]{4,}', sentence_lower))
    # Remove common words
    common = {'that', 'this', 'with', 'from', 'have', 'been', 'were', 'their',
              'which', 'would', 'could', 'should', 'about', 'there', 'these',
              'those', 'other', 'more', 'most', 'some', 'such', 'only', 'also',
              'very', 'just', 'than', 'then', 'when', 'where', 'what', 'will',
              'into', 'over', 'after', 'before', 'between', 'through', 'during'}
    claim_words -= common

    if not claim_words:
        return True, "OK (no substantive claims)"

    # Check if at least 30% of claim words appear in evidence
    evidence_lower = str(evidence_text or '').lower()
    evidence_words = set(re.findall(r'[a-z]{4,}', evidence_lower))
    overlap = claim_words & evidence_words
    ratio = len(overlap) / len(claim_words) if claim_words else 1.0

    if ratio < 0.3:
        return False, "Only %.0f%% of claim words found in evidence (%d/%d): %s" % (
            ratio * 100, len(overlap), len(claim_words),
            ', '.join(sorted(claim_words - evidence_words)[:5]))

    return True, "OK"


def check_recommendation(sentence):
    """Check if a sentence makes an unsupported recommendation.

    Returns (ok: bool, reason: str).
    """
    sentence_lower = str(sentence or '').lower()
    rec_patterns = [
        r'\bshould\b', r'\bmust\b', r'\brecommend\b', r'\badvise\b',
        r'\bsuggest\b', r'\bought to\b', r'\bneed to\b',
    ]
    for pattern in rec_patterns:
        if re.search(pattern, sentence_lower):
            return False, "Unsupported recommendation: contains '%s'" % pattern.strip('\\b')
    return True, "OK"


def check_context(sentence, evidence_text, decision):
    """Check if a sentence invents place names or countries.

    Returns (ok: bool, reason: str).
    """
    sentence_lower = str(sentence or '').lower()
    evidence_lower = str(evidence_text or '').lower()
    decision_lower = str(decision or '').lower()

    # Common place/country names that might be invented
    # Check for capitalized words that look like place names
    places = re.findall(r'\b[A-Z][a-z]{3,}\b', str(sentence or ''))
    # Filter out words that are in evidence or decision
    combined = (evidence_lower + ' ' + decision_lower)
    invented = []
    for place in places:
        if place.lower() not in combined:
            # Check if it's a common English word
            if place.lower() not in {'the', 'this', 'that', 'these', 'those', 'with', 'from', 'into'}:
                invented.append(place)

    if invented:
        return False, "Invented place/context: %s (not in evidence or decision)" % ', '.join(invented[:5])
    return True, "OK"


def check_scope(sentence):
    """Check if a sentence makes unsupported universal claims.

    Returns (ok: bool, reason: str).
    """
    sentence_lower = str(sentence or '').lower()
    scope_patterns = [
        (r'\ball\b', 'universal "all"'),
        (r'\balways\b', 'universal "always"'),
        (r'\bnever\b', 'universal "never"'),
        (r'\bevery\b', 'universal "every"'),
        (r'\bnone\b', 'universal "none"'),
    ]
    for pattern, desc in scope_patterns:
        if re.search(pattern, sentence_lower):
            return False, "Unsupported scope claim: %s" % desc
    return True, "OK"


# ── Main check function ─────────────────────────────────────────────────────

def check(prose_text, evidence_items, decision=''):
    """Run all hallucination checks on generated prose.

    Returns (findings: list[dict], summary: dict).
    Each finding: {sentence, type, reason, severity}.
    """
    findings = []
    sentences = _extract_sentences(prose_text)
    evidence_text = _extract_evidence_text(evidence_items)

    for sentence in sentences:
        # Skip very short sentences
        if len(sentence) < 20:
            continue

        # 1. Claim traceability
        traceable, reason = check_claim_traceability(sentence, evidence_text)
        if not traceable:
            findings.append({
                'sentence': sentence[:200],
                'type': 'untraceable_claim',
                'reason': reason,
                'severity': 'moderate',
            })

        # 2. Recommendation guard
        ok, reason = check_recommendation(sentence)
        if not ok:
            findings.append({
                'sentence': sentence[:200],
                'type': 'unsupported_recommendation',
                'reason': reason,
                'severity': 'moderate',
            })

        # 3. Context guard
        ok, reason = check_context(sentence, evidence_text, decision)
        if not ok:
            findings.append({
                'sentence': sentence[:200],
                'type': 'invented_context',
                'reason': reason,
                'severity': 'severe',
            })

        # 4. Scope guard
        ok, reason = check_scope(sentence)
        if not ok:
            findings.append({
                'sentence': sentence[:200],
                'type': 'unsupported_scope',
                'reason': reason,
                'severity': 'light',
            })

    # Summary
    by_type = {}
    by_severity = {}
    for f in findings:
        by_type[f['type']] = by_type.get(f['type'], 0) + 1
        by_severity[f['severity']] = by_severity.get(f['severity'], 0) + 1

    summary = {
        'total_sentences': len(sentences),
        'total_findings': len(findings),
        'by_type': by_type,
        'by_severity': by_severity,
        'hallucination_rate': len(findings) / len(sentences) if sentences else 0,
    }

    return findings, summary


def check_relevance_batch(sources, decision_topic):
    """Check relevance of multiple sources against a decision topic.

    Returns list of (source, relevant: bool, reason: str).
    """
    results = []
    for source in sources:
        text = source if isinstance(source, str) else str(source.get('title', '') + ' ' + source.get('abstract', ''))
        relevant, reason = check_relevance(text, decision_topic, '')
        results.append({'source': source, 'relevant': relevant, 'reason': reason})
    return results


# ── Model-assisted deep check (optional) ───────────────────────────────────

def deep_check(prose_text, evidence_items, decision=''):
    """Use a model to verify prose against evidence (slower, more accurate).

    Returns (findings: list[dict], error: str or None).
    """
    from .. import llm
    # Fall back to DeepSeek if key is available but provider not set
    if not os.environ.get("BP_LLM_PROVIDER") and os.environ.get("DEEPSEEK_API_KEY"):
        os.environ["BP_LLM_PROVIDER"] = "deepseek"
        os.environ.setdefault("BP_LLM_MODEL", "deepseek-chat")
    models = llm.from_env()
    if models is None:
        return [], "no model configured"
    models.config.max_output_tokens = 4000
    models.config.max_input_chars = 30000

    evidence_text = _extract_evidence_text(evidence_items)
    system = (
        "You are a hallucination detector. Given generated prose and evidence items, "
        "check each sentence for: (1) claims not supported by evidence, (2) invented facts, "
        "(3) unsupported recommendations, (4) invented place names or contexts. "
        "Return ONLY a JSON object: {\"findings\": [{\"sentence\": \"...\", \"type\": \"...\", \"reason\": \"...\"}]}. "
        "If no hallucinations found, return {\"findings\": []}. No markdown."
    )
    user = json.dumps({
        'prose': str(prose_text)[:4000],
        'evidence': evidence_text[:4000],
        'decision': str(decision)[:500],
    }, ensure_ascii=False)

    try:
        raw = None
        try:
            result = models.call("builder", "hallucination_check", "v1", system, user, consent=True)
            raw = result[0] if isinstance(result, tuple) else str(result)
        except Exception as primary_err:
            # beam failed (rate limit / error) -> backup model (deepseek flash)
            from .chat_heal import _call_fallback
            raw = _call_fallback(system, user, task_label="hallucination_check")
            if raw is None:
                return [], str(primary_err)[:200]
        data = json.loads(raw.strip().strip('`').strip())
        findings = data.get('findings', []) if isinstance(data, dict) else []
        return findings, None
    except Exception as e:
        return [], str(e)[:200]