# Contributors' manual ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â rules for any human or model touching this repository

**Read this before your first edit.** It is the bridge between the project's rules (`docs/sources/business_pipeline_v0_3.md`, `docs/DECISIONS.md`) and the actual code. It is written for an AI model as much as for a person: if a rule below and a habit of yours conflict, the rule wins.

Companion documents: [`HOME.md`](HOME.md) (map of everything), [`WORKLOG.md`](WORKLOG.md) (what was done, when), [`DECISIONS.md`](DECISIONS.md) (why), [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) (what it cannot do), [`PRODUCT_GAP_MAP.md`](PRODUCT_GAP_MAP.md) (what is missing), [`PARKED_QUEUE.md`](PARKED_QUEUE.md) (what is deliberately parked and what un-parks it), [`BACKEND_CONTRACT.md`](BACKEND_CONTRACT.md) (the frozen core and the product-backend lane).

## 1. The eleven non-negotiables

1. **Numbers never come from a model.** A model may propose facts, alternatives and critique; code computes every number (`src/bp/assist.py`, `docs/MODEL_PROVIDER_REPORT.md`).
2. **No invented sources.** A citation is either resolved-and-verified by a retrieval source or labelled `unverified_user_supplied`. Never cite from memory (`src/bp/literature.py`, REW manual Ãƒâ€šÃ‚Â§2).
3. **The verifier is not yours to weaken.** Never loosen a tolerance, delete a check, skip a test, or edit an expected value to make a run green. See Ãƒâ€šÃ‚Â§4.
4. **Pre-declaration, not post-hoc.** Specs are frozen and hashed before computation (`src/bp/spec.py`); assumptions, diagnostics and thresholds are declared in the spec, not chosen after seeing results.
5. **Fail closed.** Unknown method, unavailable sandbox, failed assumption with no declared fallback, malformed input ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ stop with an explanation. Never guess a default silently.
6. **Synthetic data is labelled.** `synthetic` is a first-class provenance tag; it is never presented as observed (`src/bp/quantity.py`, `SYNTHETIC_NOTE` in the orchestrator).
7. **Claim wording follows the tier.** The claim ceiling (`src/bp/claims.py`) licenses the wording; T2 work never says "verified".
8. **No runtime third-party imports.** Runtime is the Python standard library only. `scipy`/`numpy` are used *offline* to generate golden fixtures and are never imported by `src/`.
9. **The supplied sources are read-only.** Anything under `docs/sources/` is authority material. Do not edit it; record your amendment in `DECISIONS.md`.
10. **Every change is traceable.** One increment = one commit = one CHANGELOG entry = one WORKLOG entry = (if it decides something) one B-xxx decision.
11. **The product is global.** It never names a home exchange or a home country. No PSE/PSEi name, no Philippine place name, no Philippine-specific example, currency or market claim; examples use neutral places and USD. Introduce no new country-specific default (B-177). The ISO 3418 country list used for geography detection and the ISO 4217 currency table are universal reference data, not a home-market reference: keep both complete.

## 1A. Model ownership: computation vs design (owner directive, B-066)

**This repository is split between two model owners.** Read this before touching anything, and do not cross the line without the owner's explicit instruction.

**The computation owner (DeepSeek) has exclusive domain over everything that produces or verifies a fact, number or rule.** Concretely:

- `src/bp/**` ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â the method library, orchestrator, spec, claims, quantities, artefacts, sandbox, ledger, schedules, reconciliation, statement exports, retrieval verification and citation rules, ingestion and type inference, model-boundary validation, re-performance.
- `tests/**` and `tests/fixtures/**` ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â the verification contract, goldens, trap tests.
- The factual content of `docs/**`: `DECISIONS.md`, `CHANGELOG.md`, `KNOWN_LIMITATIONS.md`, `PRODUCT_GAP_MAP.md`, `WORKLOG.md`, `RESEARCH_EVIDENCE_WORKFLOW.md`, `HANDOFF.md`, this file, and the rendered claim wording of any output.
- Any prompt change that can change what the system asserts or how a number is produced/validated.

**The design owner (MiniMax) has exclusive domain over presentation and aesthetics.** Concretely:

- The look and feel of the workbench (`web/`): layout, CSS, typography, colour, spacing, iconography, responsiveness, visual hierarchy, component styling and the visual presentation of results.
- Interaction affordances that do not change behaviour: labels, helper copy, empty states, ordering of controls, animations.
- Visual design of reports/exports (as presentation only; the numbers, wording ceilings and disclaimers stay computation-owned).

**Boundary rules, binding on both owners:**

1. **Design changes must not change any number, claim wording, threshold, check, schema meaning or test.** A restyled results panel still shows the same values, caveats and honesty notices.
2. **Computation changes must not silently restyle the UI.** Functional wiring (a new button that calls an existing endpoint) is allowed; choosing how it looks is the design owner's call.
3. **Neither owner edits the other's files to "fix" them.** Read everything; write only in your domain. If a change is genuinely needed in the other domain, say so in `WORKLOG.md` (tag the entry `[computation]` or `[design]`) and let the owner instruct it.
4. **Cross-domain work is split, not merged.** A feature with both halves lands as two commits by the two owners: the computation commit first (contract, endpoint, tests), then the design commit (UI) against that contract.
5. **Conflicts and ambiguities escalate to the owner.** Do not reinterpret this split in your own favour.
6. **The verification rules in Ãƒâ€šÃ‚Â§1 apply to both owners.** Design cannot weaken a caveat to look cleaner; computation cannot bypass a test to ship faster.

## 1B. The frozen core and the product-backend lane (B-079, B-080)

**The core deterministic backend is FROZEN.** Read [`BACKEND_CONTRACT.md`](BACKEND_CONTRACT.md) before touching anything in `src/bp/**` or the public surface. In short:

1. **Frozen:** the stage/flow contract, spec + hash, the public contract of every method (140 ids, tier, metric, unit, `test_names` order, claim ceiling, input names), the 142 presets, the 12 API route families, the delivery shape, and the verification invariants. `tests/test_frozen_contract.py` fails when the code diverges from `tests/fixtures/frozen_contract.json`.
2. **Never** edit `tests/fixtures/frozen_contract.json`, loosen a frozen check, or trim a contract field to make a UI/product change pass. That is an unfreeze, not a fix.
3. **Unfreeze** = owner approval ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ computation owner writes the B-decision, changes code + tests, and updates the fixture **in the same commit** (B-079). Bug fixes that restore declared behaviour ship with a trap test and need no unfreeze.
4. **Product backend (B-080)** is the design owner's lane: presentation/interaction plus *additive* product routes, modules, storage and workflows that consume the frozen core through its API. The design owner may not compute, round, re-derive or adjust any business number, threshold, rating, caveat, honesty notice, refusal message, tier label or claim wording, and may not edit frozen modules, `tests/**` or factual docs. Any genuinely needed core change is recorded in `WORKLOG.md` as a `[design]` request for the owner, never made directly.
5. Cross-domain features still land as two commits: computation contract first (if the owner unfreezes), presentation second (B-066 rule 4).

## 2. Five-minute orientation

```powershell
# from the project folder (business_pipeline_v0.12/business_pipeline)
$env:PYTHONPATH="src"
python -m unittest discover -s tests          # currently 3478 tests; the framework-completion build in flight still fails Ã¢â‚¬â€ see docs/OPEN_ISSUES.md
python -m bp.server 8000                     # workbench at http://127.0.0.1:8000
```

Read in this order: `README.md` ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ this file ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ `docs/HOME.md` ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ the module you will touch ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ its tests ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ the decision(s) behind it.

## 3. Adding a method (the full checklist)

The method library is the most rule-bound part of the code base. A method is not "added" until every step is done.

1. **Implementation** ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â `foo_impl(inp)` in `src/bp/methods.py`. Validate inputs with `_check`/`_num`; reject binary floats and silently-rounded values; return named outputs (exact arithmetic in `Decimal`, inferential statistics as floats with declared precision).
2. **Independent second route** ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â `_foo_ref(...)` computed a different way (different formula, or an independent float implementation). The pipeline's P3 rule is that a number is not trusted until it survives a second route.
3. **Property and wrong-implementation tests** ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â `foo_tests(inp, out)` returns `(name, ok, detail)` checks: invariants, boundary cases, symmetry/scaling where applicable, and at least one check that a **deliberately wrong implementation fails**. A check that cannot fail is not a check.
4. **Golden fixture** ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â `tests/fixtures/foo_golden.json`, generated **offline** with `scipy`/`numpy` (record the versions and the generator in the fixture). Never import scipy/numpy in `src/` or in the test suite.
5. **Test file** ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â `tests/test_foo.py` comparing goldens with relative tolerance `1e-9`; exact analytic identities to `1e-12`.
6. **Registration** ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â `Method(...)` entry in `LIBRARY` (`src/bp/methods.py`, ~line 1340) with the full contract: tier, impl, tests, profile, metric, unit, decision, `test_names`, category, `intended_use`, `unsupported_use`, `input_schema`, `defaults`, `assumptions`, `limitations`, `output_precision`, `default_period`, caveats, template, `claim_ceiling`, and ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â for inferential methods ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â `assumption_checks`/`assumption_check_names`/`fallbacks`/`default_thresholds`/`output_units`/`typing`.
7. **Sandbox parity** ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â add the case to `CASES` in `tests/test_sandbox.py`. `test_sandbox_outputs_equal_in_process_for_every_method` must pass; a method that cannot run sandboxed is not shippable.
8. **Workbench preset** ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â add an entry to `PRESETS` in `src/bp/server.py` so the method is reachable without hand-writing JSON.
9. **Docs** ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â new `B-xxx` decision (conventions used, what is `[UNVERIFIED]`), `CHANGELOG.md` entry, README method list, and `KNOWN_LIMITATIONS.md` for every unverified convention or unsupported use.
10. **Verification** ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â full suite green, then commit.

## 4. Fixing a bug

1. **Reproduce first.** Write the failing test before the fix. If the behaviour was wrong but the test asserted the wrong thing, say so explicitly.
2. **Fix the code, not the expectation.** Editing an expected value is allowed only when the expected value is itself wrong, and then only with an independent source or derivation quoted in the commit and a logged decision ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â never because the current output "looks fine".
3. **Add the trap.** The regression test must fail on the old code. A fix without a trap test is a rumour, not a fix.
4. **Never** delete or weaken checks, tolerances, sandbox guards, or claim ceilings to get green. If a check genuinely cannot fail (it was tautological), replacing it with one that can is the correct fix ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â that is what B-034 did with the rollforward check.
5. If the bug is an ambiguity in the authority manual, the fix is: amendment decision ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ manual-derived rule in the code ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ doc update in the **same** commit.

## 5. Changing a boundary (model, retrieval, ingestion, exports)

These are trust boundaries, not features. Order of work: **design note ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ refusal tests ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ happy path**.

- State the threat model: what is untrusted, what leaves the machine, what the system may now claim.
- Write tests that prove it **refuses** (missing consent, unresolvable DOI, unsupported source, inherited instruction in retrieved text) before writing the success path.
- Remote content is **data, never instructions**. No model call and no retrieval may change code behaviour.
- Keep retrieval auditable: source, UTC retrieval time, SHA-256 of the exact response bytes (B-054), and append every resolved retrieval to the durable log **before** returning it ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â an unwritable log must fail the retrieval closed (B-058).
- Update the claim wording, the privacy notice, `KNOWN_LIMITATIONS.md`, and the REW manual (`docs/RESEARCH_EVIDENCE_WORKFLOW.md`) in the same increment.

## 6. Testing contract

| Kind | What it proves | Where |
|---|---|---|
| Unit / property | The maths behaves under invariance, symmetry, boundary cases | `tests/test_*.py`, `foo_tests` |
| Wrong-implementation blocking | The test suite can detect a plausible wrong implementation | method `test_names` |
| Golden fixtures | Agreement with an independent reference implementation (scipy, offline) | `tests/fixtures/*.json` |
| Sandbox parity | In-process and sandboxed runs agree | `tests/test_sandbox.py` |
| Fail-closed | Unknown/invalid inputs block with a reason | `tests/test_pipeline.py`, per-method tests |
| Determinism | Same inputs, same outputs, same hashes | `tests/test_sandbox.py`, `test_stage5.py` |
| Re-performance | A delivered bundle re-runs and matches | `tests/test_sandbox.py`, `src/bp/reperform.py` |
| API / UI | Routes and the workbench expose the contract | `tests/test_session_api.py`, `test_literature_api.py` |

Rules: no network in the suite (use fake openers/sources); no sleeps; no reliance on wall-clock time (inject a clock, as the retrieval audit does); tests must pass in any order. **Report the truth**: "1844 tests OK" means the count and the word OK; a PowerShell `[exit code: 1]` on a green suite is the known ResourceWarning artefact ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â read the `OK` line.

## 7. Environment and known traps

- **Python 3.14**, standard library only at runtime. `python` from the project folder.
- **`PYTHONPATH=src`** is required for the suite, the server, `spike/` and `-m bp.reperform`. In PowerShell: `$env:PYTHONPATH="src"`.
- **Sandbox**: `python -S -s` child, `PYTHONHASHSEED=0`, `PYTHONIOENCODING=utf-8`, Windows `SYSTEMROOT` preserved; memory cap best-effort. Never run business logic outside it in production paths (`--no-sandbox` is development only).
- **Golden fixtures are generated offline**, on a machine with scipy/numpy; the versions and generator command belong in the fixture file. Regenerating a fixture is a *verified* event: quote the reference implementation and the versions.
- **Line endings**: CRLF warnings from git are harmless.
- **`docs/sources/` is read-only input**, not editable documentation.
- **Stage reports (`STAGE*_REPORT.md`) are historical snapshots** ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â do not rewrite them when reality changes; write the new truth in CHANGELOG, DECISIONS, limitations and WORKLOG.

## 8. Where each fact belongs

| Question | File |
|---|---|
| Why is it like this, and is it settled? | `docs/DECISIONS.md` (B-xxx with status) |
| What shipped, in order, at which build version? | `docs/CHANGELOG.md` |
| What can it not do? | `docs/KNOWN_LIMITATIONS.md` |
| What is missing versus the catalogue/manual? | `docs/PRODUCT_GAP_MAP.md` |
| What is deliberately parked, and what releases it? | `docs/PARKED_QUEUE.md` |
| What are the rules for the research capability? | `docs/RESEARCH_EVIDENCE_WORKFLOW.md` (ratified living manual, R11) |
| What is frozen, and how do I change it? | `docs/BACKEND_CONTRACT.md` (B-079/B-080) |
| What happened in this session and what is next? | `docs/WORKLOG.md` |
| How do I work on this repo without breaking it? | `CONTRIBUTORS.md` (this file) |
| Where is everything? | `docs/HOME.md` |
| What did the owner actually specify? | `docs/sources/*` (read-only) |

**Linking rules:** link, don't duplicate. A document that restates another document's content becomes wrong the moment the other changes. Historical entries (CHANGELOG, WORKLOG, stage reports) are **appended to, never rewritten**.

## 9. Commit discipline

- One increment per commit; do not mix unrelated changes or reformat untouched code.
- Message: one imperative subject line, then a body that says what changed, why, what verifies it, and the test count.
- The commit is not done until: suite green, CHANGELOG entry added, WORKLOG entry added, docs updated for anything that changed meaning.
- Never commit a PROPOSAL as if it were ratified, and never mark a gap `closed` in `PRODUCT_GAP_MAP.md` without the verification and a commit id.

## 10. Changes that will be rejected

- Adding a runtime dependency, or importing scipy/numpy/any third party in `src/`.
- Letting a model produce, choose or adjust a number, threshold, weight or rating.
- Silent rounding, coercion or dropping of data (the one declared exception is listwise deletion, which is disclosed).
- A method without an independent second route, a wrong-implementation trap and sandbox parity.
- Editing `docs/sources/`, golden expected values, or historical entries to make a problem disappear.
- Weakening the sandbox, the claim ceiling, the tier label, or any documented limitation.
- Inventing a citation, a reviewer, a convention, or an owner decision.
- Presenting a `[PROPOSAL]`/`[OPEN]` item as decided.

## 11. Stop and ask (do not decide these yourself)

These are owner decisions with live entries in `docs/DECISIONS.md`: **reviewer naming is not planned** (B-112; methods stay disclosed as not reviewed), choosing **next framework templates** (B-028), the **ledger engine** (B-032), and **taxation** (B-052). Also stop before: **starting any item parked in [`PARKED_QUEUE.md`](PARKED_QUEUE.md)** without the owner explicitly granting the frontier-model lane (a general "continue" does not release it, B-075), **unfreezing any part of the core** ([`BACKEND_CONTRACT.md`](BACKEND_CONTRACT.md), B-079) or satisfying a product need by editing the core/fixture instead of requesting the unfreeze (B-080), adding a new external API or model provider, touching personal data handling (B-038), changing the stage list or the mandatory checkpoints, or anything that would change what the product is allowed to claim.
