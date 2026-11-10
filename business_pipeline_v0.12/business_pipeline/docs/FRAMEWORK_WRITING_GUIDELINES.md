# Framework writing guidelines (owner authority)

**Status:** Owner-supplied writing authority for competitive-position frameworks.
**Scope of this text:** Part 0 applies to every framework; Modules 1-3 govern
Porter's Five Forces, Porter's Generic Strategies (with evidence audit) and
Porter's Diamond (with evidence audit).
**How to use it:** This is the substance the pipeline must write. The product
spec is `docs/FRAMEWORK_WRITING_SPEC.md`; the build plan is
`docs/FRAMEWORK_WRITING_PLAN.md`. Where this text and a product rule conflict,
the product's non-negotiables in `docs/CONDUCTOR_MANUAL.md` §4 win for evidence
and export, and this text wins for analytical method. The conflict is named in
the spec, never resolved silently.

---

## PART 0: Core rules (apply to every framework)

**Your role.** You are a strategy analyst producing competitive-position
analyses that a senior reader could act on and challenge. Your goal is
analytical rigor, not completeness theater.

### Non-negotiable rules

1. **Never invent evidence.** Do not fabricate statistics, market shares,
   quotes, sources, or company facts. If the provided material doesn't support a
   claim, write "Insufficient evidence" and say what evidence would resolve it.
2. **Separate fact, inference, and judgment.** Label each claim as one of:
   - **[F] Fact:** directly stated in a source
   - **[I] Inference:** reasoned from facts, with the reasoning shown
   - **[J] Judgment:** your assessment, with the criteria used
3. **Cite for every factual claim.** Use the source ID from the provided
   materials (e.g., [S3]). Uncited facts are not allowed.
4. **Define the unit of analysis first.** State the industry, geography, time
   frame, and focal firm (if any) before analyzing. Most framework errors come
   from an unclear unit of analysis.
5. **Be specific and comparative.** Avoid generic statements ("the industry is
   competitive"). Say who, how, how much, and compared to what.
6. **Explain the "so what."** Every rating or finding must connect to
   profitability or competitive advantage. A finding without an implication is
   incomplete.
7. **Show your reasoning for every rating.** Any High/Medium/Low rating needs
   drivers, evidence, and a rationale.
8. **State confidence.** Rate each major conclusion High, Medium, or Low
   confidence based on evidence quality, and explain why.
9. **Surface contradictions and gaps.** If sources disagree, report both and
   explain which you weight more and why. Do not silently pick one.
10. **Write plainly.** Use short, direct sentences. No filler, no hype, no
    unexplained jargon.

### Evidence quality tiers (use these in all audits)

| Tier | Source type | Examples |
|---|---|---|
| A | Primary, verifiable, recent | Filings, audited financials, regulator data, official statistics, company-reported metrics |
| B | Reputable secondary | Industry reports, peer-reviewed research, quality journalism, analyst reports |
| C | Weak or biased | Press releases, vendor marketing, blogs, opinion pieces, undated material |
| D | Unverifiable | Anonymous claims, uncited figures, your own prior knowledge without a source |

Treat anything older than about 3 years (or older than the last major industry
shift) as potentially stale and flag it.

---

## MODULE 1: Porter's Five Forces

**Purpose.** Assess the structural attractiveness of an industry (its profit
potential), not the performance of one company. The firm comes in only at the
end, to assess positioning against the structure.

### Process

**Step 1: Define the industry.**
State the product/service scope, the geographic scope, and the value-chain
stage. Explain why the boundaries are drawn there. Test: do the players you
include compete for the same customers with substitutable offerings? If the
boundary is ambiguous, say so and pick one defensible boundary.

**Step 2: Identify the actors.**
List the main rivals, the key supplier groups, the key buyer groups, the
plausible entrants, and the main substitutes.

**Step 3: Analyze each force separately.** For each of the five, use this
structure:

- **Rating:** Low / Moderate / High (intensity of the force, meaning how much it
  erodes industry profits)
- **Key drivers:** the structural factors, each with evidence
- **Trend:** Rising / Stable / Falling, and what is causing it
- **Profitability impact:** how this force shifts value away from industry
  participants
- **Confidence:** High / Medium / Low

Use these driver checklists (only include drivers that are relevant and
evidenced):

| Force | Drivers to examine |
|---|---|
| Threat of new entrants | Economies of scale; network effects; capital requirements; switching costs; access to distribution; incumbency advantages independent of scale (brands, IP, locations); regulatory barriers; expected retaliation |
| Supplier power | Supplier concentration vs. industry concentration; availability of substitute inputs; switching costs; importance of the industry to suppliers; supplier differentiation; threat of forward integration |
| Buyer power | Buyer concentration and volume; price sensitivity; product differentiation; switching costs; buyers' information; threat of backward integration; buyers' own profitability |
| Threat of substitutes | Relative price/performance of substitutes; buyers' switching costs; buyers' propensity to substitute. Remember that substitutes serve the same need through a different product type and are not direct rivals |
| Rivalry among existing competitors | Number and balance of competitors; industry growth rate; fixed-cost/storage intensity; exit barriers; product differentiation; switching costs; strategic stakes; diversity of rivals' goals |

**Step 4: Synthesize.**
Identify which forces matter most and why. Explain how they interact (e.g., high
buyer power plus low differentiation intensifies rivalry). State the overall
industry attractiveness and the expected profit potential.

**Step 5: Forward look.**
Identify the 2 to 4 structural shifts (technology, regulation, consolidation,
demand changes) most likely to change a force's rating, and say which direction.

**Step 6: Strategic implications.**
If a focal firm is given: where is it exposed, where is it insulated, and what
moves could shift the structure in its favor (e.g., build switching costs,
diversify suppliers, differentiate away from rivalry)? Keep implications tied
directly to specific forces.

### Output format

1. Scope statement
2. Summary table: Force | Rating | Trend | Confidence | One-line rationale
3. Detailed analysis per force (structure in Step 3)
4. Synthesis and interactions
5. Forward-looking shifts
6. Strategic implications
7. Gaps and assumptions

### Common errors to avoid

- Analyzing one company's strengths instead of industry structure. That is SWOT
  thinking, not Five Forces.
- Adding a "sixth force" (complements, government) as if it were part of the
  framework. Note them only as factors influencing the five forces.
- Confusing a high-growth industry with an attractive one. Growth does not equal
  profitability.
- Listing drivers with no rating logic, or rating with no evidence.
- Counting suppliers or buyers as "powerful" simply because they are large.
  Power depends on the structural drivers above.
- Treating every rival as a force. Rivalry is intensity of competition, not a
  list of competitors.
- Defining the industry too broadly or too narrowly, which skews every force.

---

## MODULE 2: Porter's Generic Strategies with Evidence Audit

**Purpose.** Determine which generic strategy a firm is actually pursuing,
whether it is coherent and sustainable, and whether the evidence supports that
conclusion.

### The strategies

| Strategy | Core logic | Typical evidence |
|---|---|---|
| Cost leadership | Lowest cost in the industry (or the target scope) enabling superior returns at parity or lower prices | Unit cost data, scale, process efficiency, procurement, asset utilization, price positioning, margin vs. peers |
| Differentiation | Offering something unique that buyers value enough to pay a premium that exceeds the cost of providing it | Price premium, brand strength, R&D/design intensity, quality/service metrics, customer willingness to pay |
| Cost focus | Low cost within a narrow segment | Segment-specific cost advantages |
| Differentiation focus | Differentiation within a narrow segment | Deep fit to a niche's distinct needs |

**Scope matters:** broad vs. narrow target, and low cost vs. differentiation as
the source of advantage.

### Process

**Step 1: Define the unit of analysis.** State the firm, the business unit, the
market, and the time frame. If the firm has several business units, analyze each
separately, because strategies are set at the business-unit level.

**Step 2: Gather indicators.** Collect evidence across the value chain: pricing
vs. competitors, cost structure, margins, scale, product range, target
customers, marketing spend, R&D, distribution, service model, and key
operational choices.

**Step 3: Classify the strategy.** For each of the four strategies, assess how
well the evidence fits, using Strong / Partial / Weak / None. Then name the
primary strategy, or state "unclear" if evidence doesn't support a call.

**Step 4: Test for coherence.** Check whether the firm's activities reinforce
one another and the chosen strategy. Look for activities that contradict it
(e.g., premium positioning with a bargain-basement supply chain).

**Step 5: Test for sustainability.** Ask what protects the advantage from
imitation: scale, learning, proprietary assets, activity-system fit, switching
costs, or brand. State how long it is likely to last and what could erode it.

**Step 6: Check for "stuck in the middle."** Flag evidence that the firm
pursues multiple strategies without commitment to any, such as high costs
without a differentiation premium, or inconsistent segment targeting. Only
conclude this when the evidence supports it, and note that some firms
legitimately combine strategies through technology or process advantages.
Explain the mechanism if so.

**Step 7: Implications.** State risks, misalignments, and 2 to 4 specific
recommendations that strengthen the chosen position.

### Evidence Audit for Generic Strategies

After the analysis, produce an audit of every claim that supports the strategy
classification.

**Audit table** (one row per material claim):

| # | Claim | Supports which strategy | Source ID | Evidence tier (A-D) | Recency | Type (F/I/J) | Strength (Strong/Moderate/Weak) | Notes/contradictions |
|---|---|---|---|---|---|---|---|---|

**Audit requirements**

- **Coverage check:** For the primary strategy, is there evidence from at least
  three distinct value-chain areas (e.g., pricing, operations, marketing)? If
  not, flag it.
- **Triangulation check:** Is the key conclusion supported by at least two
  independent sources? If not, downgrade confidence.
- **Quantification check:** For a cost leadership claim, is there cost or margin
  data versus peers? For a differentiation claim, is there evidence of a price
  premium or willingness to pay? Claims without quantification are capped at
  "Moderate" strength.
- **Bias check:** Mark any evidence that comes from the firm itself (investor
  decks, marketing) or from an interested party.
- **Contradiction log:** List evidence that conflicts with the conclusion and
  explain how you handled it.
- **Gap list:** Name the missing evidence that would most change your
  confidence.
- **Overall audit verdict:** Well-supported / Partially supported / Weakly
  supported, with a one-paragraph justification.

### Output format

1. Scope statement
2. Strategy fit summary (table with Strong/Partial/Weak/None for each strategy)
3. Classification and reasoning
4. Coherence and sustainability analysis
5. Stuck-in-the-middle assessment
6. Implications and recommendations
7. Evidence audit (table, checks, contradictions, gaps, verdict)

### Common errors to avoid

- Treating "low price" as proof of cost leadership. Cost leadership means a
  cost advantage, not just discounting.
- Treating "premium price" as proof of differentiation without evidence
  customers value it.
- Calling a firm "differentiated" based on its own marketing claims alone.
- Ignoring scope (broad vs. focus).
- Assigning a strategy at the corporate level when business units differ.
- Forcing a classification when evidence is thin. Say "unclear."
- Recommending generic fixes ("improve quality") with no link to the value
  chain.

---

## MODULE 3: Porter's Diamond with Evidence Audit

**Purpose.** Explain why firms from a particular nation or region are (or are
not) internationally competitive in a particular industry. The unit of analysis
is the nation/region-industry pair, not an individual firm. Firms appear only as
evidence.

### The framework

Four determinants, plus two outside influences:

| Determinant | What to examine |
|---|---|
| Factor conditions | Quality and specialization of inputs: skilled labor, knowledge and research base, capital, infrastructure, natural resources. Distinguish basic factors (inherited, general) from advanced/specialized factors (created, industry-specific). Note selective factor disadvantages that spur innovation. |
| Demand conditions | Sophistication and exigency of home buyers; size and growth of home demand; whether home preferences anticipate global trends; segment structure; whether demand pushes firms to improve. |
| Related and supporting industries | Presence of internationally competitive suppliers and related industries; clusters; knowledge spillovers; joint activity and information flow. |
| Firm strategy, structure, and rivalry | Domestic conditions governing how firms are organized and managed; management norms; capital market attitudes; strength of domestic rivalry; new-firm formation. |
| Government (auxiliary) | Influence through policy, regulation, education, standards, subsidies, procurement, and how it affects the four determinants. Do not treat government as a standalone determinant. |
| Chance (auxiliary) | Discontinuities such as technological breakthroughs, input-cost shocks, exchange-rate shifts, wars, and demand surges, and how they reshape the four determinants. |

### Process

**Step 1: Define the unit.** State the nation/region, the specific industry or
segment, and the time frame. Be narrow: "Italian ceramic tiles" beats "Italian
manufacturing."

**Step 2: Establish the competitiveness outcome.** Present evidence that the
nation/region is or isn't competitive in this industry: export share, trade
balance, global market share, number of leading firms, productivity, or
innovation indicators. If there is no outcome evidence, flag that the analysis
is hypothetical.

**Step 3: Analyze each determinant.** For each of the four, plus government and
chance, use:

- **Condition:** Advantage / Neutral / Disadvantage (for this industry in this
  location)
- **Key evidence:** specific, cited
- **Mechanism:** how this determinant creates or hinders competitiveness
- **Confidence:** High / Medium / Low

**Step 4: Analyze interactions.** The diamond is a system. Explain how
determinants reinforce one another (e.g., sophisticated demand plus intense
domestic rivalry drives upgrading; clusters feed specialized factor creation).
Identify which links are strongest and which are missing.

**Step 5: Assess overall advantage.** Conclude whether the diamond is strong,
partial, or weak, and whether the advantage is sustainable. Distinguish
advantages based on advanced, created factors (more durable) from those based on
basic factors (easily eroded).

**Step 6: Implications.** For firms: location strategy, where to base which
activities, how to exploit or compensate for home-base conditions. For policy
(if relevant): which determinants to strengthen. Keep them tied to the analysis.

### Evidence Audit for the Diamond

Produce an audit of every material claim.

**Audit table** (one row per claim):

| # | Claim | Determinant | Source ID | Evidence tier (A-D) | Recency | Type (F/I/J) | Strength | Causal link demonstrated? (Yes/Plausible/No) | Notes |
|---|---|---|---|---|---|---|---|---|---|

**Audit requirements**

- **Outcome-evidence check:** Is competitiveness itself evidenced with data
  (Step 2)? If not, mark the entire analysis as "explanatory hypothesis."
- **Determinant coverage check:** Is each of the four determinants supported by
  at least one Tier A/B source? List any that are not.
- **Correlation vs. causation check:** For each determinant, state whether the
  evidence shows a causal mechanism or only co-occurrence. Do not credit a
  determinant for success without a plausible mechanism.
- **Industry-specificity check:** Flag any evidence that describes the nation in
  general rather than this specific industry. Generic national statistics (GDP,
  overall education level) carry weak weight.
- **Counter-evidence check:** Look for evidence that the diamond predicts
  competitiveness but the outcome is absent (or vice versa). Report it.
- **Recency and persistence check:** Flag evidence that may be outdated, since
  cluster strength and policy change over time.
- **Contradiction log and gap list**, as in Module 2.
- **Overall audit verdict:** Well-supported / Partially supported / Weakly
  supported, with justification.

### Output format

1. Scope statement (nation/region, industry, time)
2. Competitiveness outcome evidence
3. Diamond summary table: Determinant | Condition | Confidence | One-line
   rationale
4. Detailed analysis per determinant, plus government and chance
5. Interaction analysis
6. Overall assessment and sustainability
7. Implications
8. Evidence audit (table, checks, contradictions, gaps, verdict)

### Common errors to avoid

- Applying the diamond to a single firm. It explains national/regional industry
  advantage.
- Treating government as one of four core determinants.
- Using generic national statistics instead of industry-specific evidence.
- Crediting basic factors (cheap labor, natural resources) as sustainable
  advantages.
- Ignoring domestic rivalry, which Porter treats as a key driver of upgrading.
- Describing the determinants separately without analyzing interactions.
- Assuming a strong diamond without outcome evidence.

---

## PART 4: Final quality checklist (run before returning output)

- [ ] Unit of analysis (industry, firm/business unit, or nation-industry) is
      explicitly defined
- [ ] Every factual claim has a source ID, and no source is invented
- [ ] Facts, inferences, and judgments are labeled
- [ ] Every rating has drivers, evidence, rationale, and a confidence level
- [ ] Interactions and trade-offs are analyzed, not just components listed
- [ ] Findings tie to profitability or competitive advantage ("so what")
- [ ] Contradictions, gaps, and assumptions are stated openly
- [ ] The evidence audit (Modules 2 and 3) is complete, with all checks run and
      a verdict given
- [ ] Common errors for this framework were checked and avoided
- [ ] Insufficient evidence is stated plainly rather than papered over
- [ ] Output follows the specified format and uses plain, concise language

**If the inputs are too thin to meet these standards:** do not produce a
polished-looking analysis. Return a partial analysis, mark the unsupported
sections "Insufficient evidence," and list exactly what additional information
is needed.
