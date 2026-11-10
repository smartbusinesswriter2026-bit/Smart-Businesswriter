# Integration Note — Exo (arXiv 2611.00463) vs. Growth Loop

**Status:** Study note only. No code changed. For a future model to decide whether/how to integrate.
**Store location:** D:\SMART BUSINESSWRITER\plans\ (move out of C:\ after creation)
**Companion:** D:\SMART BUSINESSWRITER\plans\eval-spec.md (Direction 3)

---

## 1. What Exo is (one paragraph)

Exo is a runtime architecture where an agent edits its own harness (tools, prompts, context assembly, compaction, memory, and even its improvement strategy) *during* a task, instead of an external optimizer proposing candidates on benchmarks. It partitions the system into a **protected mechanism layer** (append-only history, credential store, sandbox API, an independent guardian that gates policy replacement) and an **evolvable policy layer** (everything else). Safety comes from: history can't be erased, a faulty edit can't bypass the guardian, and rollback preserves evidence. Measured gains are on open-world game / SRE / coding workloads (12–53% standalone, 45–82% transfer, 35–61% held-out), with an "intelligence floor" (weak models get no benefit) and a "specialization cost" (upfront premium, only repaid on repetitive work).

## 2. What this pipeline already has (don't rebuild)

- **Protected mechanism vs. evolvable policy, in spirit:** frozen core (`src/bp/**`) = mechanism; product layer = policy. `CONTRIBUTORS.md` already enforces this via B-079/B-197 and the computation/design owner split.
- **Guardian:** `case_runner` replay passing = activation gate. `auto_resolve` marks a fix verified only when replay passes. Growth loop is human-gated (PROVISIONAL scaffold, human writes logic).
- **Append-ish history:** `ops_log` (errors), `case_store`, run manifests under `state/`.
- **Cost accounting:** repair loop runs on OpenCode Go flash→pro; `BP_ENABLE_DEEPSEEK` gates platform.deepseek.com only.

## 3. The risk to the in-flight growth loop

The growth loop is mid-build and human-gated by design (HANDOFF §10). Injecting Exo mid-work could:
- Blur the policy/mechanism boundary and tempt the loop to "fix" cases by editing core logic (violates non-negotiable #3).
- Add self-editing surface area before the growth loop's own scaffold/verify flow is proven.
- Spend tokens on specialization that doesn't amortize (one-off capabilities).

**Therefore: integration must be additive and gated, not a rewrite.** The growth loop ships first, unchanged. Exo ideas attach as optional layers behind switches that default off (consistent with the "loops and capabilities" panel: everything off by default).

## 4. Safe integration points (additive, gated)

Each is a *new* capability behind a switch; none changes existing growth-loop behavior when off.

| # | Idea | Where it attaches | Owner lane | Gate |
|---|---|---|---|---|
| A | Declare policy-layer vs mechanism-layer artifact list (what may self-evolve) | New doc + `capabilities` metadata | Computation | Switch + human review |
| B | Cost/token annotations on `ops_log` and run manifests | `ops_log`, run manifests | Computation | Always on (observability only) |
| C | Forked-trial guardian: apply proposed fix to sandboxed `qa/cases/` copy, replay before activation | `auto_resolve`, `case_runner` (sandbox copy) | Computation | Switch; replay must pass |
| D | Append-only history (no overwrite/delete of error/case records; keep prior versions) | `ops_log`, `case_store` | Computation | Switch |
| E | Reuse promotion: when a tile case passes N times, promote its pattern into a capability entry (human-gated) | Growth loop | Computation → design | Switch + human approval |
| F | Runtime legibility report (spending, cached-input share, repeated calls, context composition) | New report over a run | Design | Switch |
| G | Reuse-count gate: only run self-editing when ≥N similar tiles exist | Growth loop / repair loop | Computation | Config threshold |

## 5. What must NOT change

- Do not let any loop edit `src/bp/**` core logic autonomously. Fixes stay: replay-verified code changes by the computation owner, or human-written logic for growth scaffolds.
- Do not weaken tolerances/checks to make a fix pass (non-negotiable #3).
- Do not auto-activate a grown capability without human approval (HANDOFF §10).
- Do not make self-editing the default; default off, like all loops.

## 6. Suggested order (non-disruptive)

1. Ship the growth loop as designed (no Exo influence).
2. Add observability only (B): cost annotations. Zero behavior change.
3. Add safety layer (C, D): forked guardian + append-only history. Still default off.
4. Add reuse promotion (E, G) behind switches, human-gated.
5. Only then consider policy-layer self-editing (A) as an opt-in experiment, measured by the eval (Direction 3).

## 7. Open questions for the owner (B-decisions)

- B-Exo-1: Is the policy/mechanism boundary declaration worth a B-number, or is it already implied by B-079? (Suggest: log it, since it names what may self-evolve.)
- B-Exo-2: Should forked-trial guardian be the default for the repair loop, or opt-in? (Suggest: opt-in first, default after measured.)
- B-Exo-3: Reuse threshold N for promotion (suggest 3 consecutive passes).
- B-Exo-4: Should self-editing of policy layer ever be allowed without human approval? (Suggest: no — keep human gate, matching growth loop.)

## 8. How another model should use this note

- Read this + `eval-spec.md` + `HANDOFF.md` §8/§10 + `CAUSE_LOOP.md`.
- Treat §4 as candidate tasks; expand into Step 3 (acceptance criteria + allowed files) only after owner approves.
- Respect ownership (§7 of eval-spec): computation lane for A–E, G; design lane for F.
- Do not start implementation until the growth loop itself is green and stable.
