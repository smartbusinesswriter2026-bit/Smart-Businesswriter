"""What one framework knows about itself (product layer).

A framework is data, not code.  This module holds one profile per framework: the
dimensions it is made of, the words that find evidence for each, the rule that
decides what its unit of analysis is, the interpretive prose the deterministic
paper uses, the outline and the model prompts.  `bp.product.completion` runs the
pipeline; `bp.product.chat` reads the same words, so the same brief returns the
same evidence whichever surface the student uses.

Adding a framework means adding a profile here and a worksheet entry; it must not
mean a branch in completion, api or the served page.  A profile that is
incomplete is refused by `profile_for`, so an unfinished framework falls back to
its plain worksheet instead of producing a generic paper.

Nothing here is evidence.  The prose states what a dimension means and what the
evidence does not establish; it never supplies a fact, number, source or name.
"""

#: Porter's Five Forces ---------------------------------------------------------

FIVE_FORCES = {
    "template": "template_five_forces",
    "key": "five_forces",
    "label": "Porter's Five Forces",
    "title_prefix": "Porter's Five Forces",
    "unit": {
        "field": "industry",
        "label": "Industry or market",
        "help": "Required: Five Forces analyses an industry, not a company.",
        "example": "smartphones, grocery retail, banking",
        "refuse": ("Porter's Five Forces analyses an industry, not a company on its own. Name the industry or "
                   "market (for example smartphones, grocery retail or banking)."),
    },
    "ratings": True,
    "assumption": "case",
    "sites": "industry",
    "providers": ["brave", "deepseek", "firecrawl"],
    "gate": {"title_cue": True, "title_context": True, "require_geography": False},
    "blocks": [
        {"key": "rivalry", "label": "Industry rivalry", "prompt": "What evidence shows this force?",
         "cues": "competition competitive rival market share price war",
         "queries": ["competition intensity market share"], "category": None},
        {"key": "entrants", "label": "Threat of new entrants", "prompt": "What evidence shows this force?",
         "cues": "market entry barriers capital licence",
         "queries": ["entry barriers new entrants"], "category": None},
        {"key": "substitutes", "label": "Threat of substitutes", "prompt": "What evidence shows this force?",
         "cues": "substitute alternative switching",
         "queries": ["substitute products switching"], "category": None},
        {"key": "buyers", "label": "Buyer power", "prompt": "What evidence shows this force?",
         "cues": "buyer customer consumer bargaining concentration",
         "queries": ["buyer power consumer demand"], "category": "economic"},
        {"key": "suppliers", "label": "Supplier power", "prompt": "What evidence shows this force?",
         "cues": "supplier vendor procurement input",
         "queries": ["supplier power supply chain"], "category": "economic"},
    ],
    "outline": {
        "framework": "Five Forces",
        "context": "Case and industry context",
        "discussion": "What the evidence shows",
        "implications": "Implications for the decision",
        "limitations": "Limitations",
        "conclusion": "Conclusion",
        "lead": ("Porter's Five Forces assesses the attractiveness of an industry through five sources of "
                 "competitive pressure. Each force is treated in turn, first through the evidence accepted for "
                 "the case and then through what that evidence implies for the decision."),
    },
    #: Slots the shared prompts take.  The safety rules themselves live in
    #: completion.py, once, so a new framework cannot drop them.
    "voice": {
        "thesis_question": "whether the structure of the industry is attractive and why",
        "unit_noun": "industry",
        "block_plural": "forces",
        "lens": "structural terms (bargaining power, entry barriers, substitution, concentration)",
        "closing": "identifies the strongest and the weakest evidenced force",
        "intro_frame": ("The unit of analysis is the industry rather than the firm, because the forces describe "
                        "the structure within which any participant must operate."),
        "context_frame": ("The relevant industry is the market in which the product or service competes; the five "
                          "forces are properties of that market rather than of a single firm."),
        "interaction": ("Read together, the documented forces describe a structure in which the pressures supported "
                        "by evidence constrain the returns available, and a force without accepted evidence cannot "
                        "be treated as favourable."),
        "implication_frame": ("A viable position must satisfy the conditions the evidenced forces impose: the "
                              "margin must survive the pricing discipline of rivals and buyers, entry must be "
                              "possible at a cost the plan can carry, and supply must be secured on sustainable "
                              "terms."),
        "reference_heading": "References",
    },
    "notes": {
        "rivalry": {
            "analysis": ("Rivalry of this kind shapes returns through price and non-price competition. Where firms "
                         "compete on both price and features, a position depends on differentiating the offer rather "
                         "than matching rivals on cost alone. The relevant question for the decision is whether the "
                         "planned position can be defended against competitors that already compete on the same "
                         "dimensions."),
            "qualify": ("The evidence does not establish the number or concentration of competitors, the intensity "
                        "of rivalry within the named market specifically, or the relative weight of price and "
                        "feature competition, so the force is treated as strong rather than measured."),
            "short": ("Such competition implies that margins depend on differentiation rather than on cost alone, "
                      "and that a new position must justify its price against established rivals."),
        },
        "entrants": {
            "analysis": ("Entry conditions determine how quickly new capacity reaches the market. Where entrants "
                         "must secure distribution and build a brand, incumbents gain time to respond, but the same "
                         "requirement applies to the entrant under consideration. The relevant question for the "
                         "decision is whether entry can meet those requirements at a cost the plan can carry."),
            "qualify": ("The evidence does not quantify the cost or time required to secure distribution and "
                        "recognition, so the height of the entry barrier is inferred rather than measured."),
            "short": ("Entry therefore carries fixed costs in channels and recognition before any revenue is "
                      "earned, which raises the scale a viable entrant must reach."),
        },
        "substitutes": {
            "analysis": ("Substitutes place a ceiling on what buyers will pay for the product itself. When "
                         "alternatives cover part of the need, demand shifts at the margin rather than "
                         "disappearing, so pricing power is bounded by the next best option. The relevant question "
                         "for the decision is how much of the need the offer must serve to keep buyers from "
                         "switching."),
            "qualify": ("The evidence does not establish how often buyers actually select the alternatives, so the "
                        "constraint they impose is treated as partial rather than decisive."),
            "short": ("Substitution bounds the price the product can sustain, because buyers can meet part of the "
                      "need elsewhere."),
        },
        "buyers": {
            "analysis": ("Buyer power determines how far cost increases can be passed on. Where buyers compare "
                         "specifications and prices before switching, the offer must compete on visible value rather "
                         "than on habit or lock-in. The relevant question for the decision is whether the planned "
                         "offer gives buyers a reason to choose it on the terms they already use to compare."),
            "qualify": ("The evidence does not report buyer concentration or switching costs, so the extent of "
                        "buyer leverage is inferred from comparison behaviour rather than measured."),
            "short": ("Comparison behaviour transfers pricing discipline to buyers, so value must remain visible at "
                      "the point of purchase."),
        },
        "suppliers": {
            "analysis": ("Supplier power determines the cost and reliability of critical inputs. Where capacity in "
                         "key inputs is scarce, input terms can absorb the margin an entrant expects to earn. The "
                         "relevant question for the decision is whether supply can be secured on terms that keep the "
                         "plan viable."),
            "qualify": ("The evidence does not report the number of alternative suppliers or the duration of supply "
                        "contracts, so supplier leverage is inferred from scarcity rather than measured."),
            "short": ("Scarcity in critical inputs can absorb the margin an entrant expects, so access to supply is "
                      "a condition of viability."),
        },
    },
}

#: PESTEL ----------------------------------------------------------------------

PESTEL = {
    "template": "template_pestel",
    "key": "pestel",
    "label": "PESTEL",
    "title_prefix": "PESTEL Analysis",
    "unit": {
        "field": "country",
        "label": "Country or market",
        "help": ("PESTEL evidence is country-specific. Name the country, or type Global to analyse the "
                 "environment without a single country."),
        "example": "Saudi Arabia, Iran, Global",
        "refuse": ("PESTEL analyses the environment a decision sits in, and political, legal and economic evidence "
                   "is country-specific. Name the country or market, or type Global."),
    },
    "ratings": False,
    "assumption": "probe",
    "sites": None,
    "providers": None,
    "gate": {"title_context": False, "require_geography": True, "title_cue": False},
    "blocks": [
        {"key": "political", "label": "Political", "prompt": "Government policy, stability, regulation and trade posture",
         "cues": "government policy sanctions regulation trade stability",
         "queries": ["government policy regulation trade sanctions"],
         "category": "legal",
         "probe": "search for the policy, trade or sanctions instruments that apply to this market"},
        {"key": "economic", "label": "Economic",
         "prompt": "Growth, inflation, interest and exchange rates, and demand",
         "cues": "economic growth inflation interest exchange demand",
         "queries": ["economic growth inflation exchange rate demand"],
         "category": "economic",
         "probe": "search for official figures on growth, prices, interest or exchange rates for this market"},
        {"key": "social", "label": "Social",
         "prompt": "Demographics, culture, lifestyle and labour expectations",
         "cues": "demographic population youth internet social cultural labour consumer behaviour",
         "queries": ["demographics consumer behaviour labour market"],
         "category": "social",
         "probe": "search for demographic or survey evidence on the people this decision depends on"},
        {"key": "technological", "label": "Technological",
         "prompt": "New technology, automation, research and diffusion",
         "cues": "technology innovation digital automation research",
         "queries": ["technology adoption digital infrastructure innovation"],
         "category": None,
         "probe": "search for adoption or infrastructure evidence on the technology the decision relies on"},
        {"key": "environmental", "label": "Environmental",
         "prompt": "Climate, resources, emissions and physical risk",
         "cues": "climate environment sustainability emissions energy",
         "queries": ["climate emissions energy sustainability"],
         "category": None,
         "probe": "search for climate, resource or energy evidence specific to this market"},
        {"key": "legal", "label": "Legal",
         "prompt": "Laws, regulation, liability, licensing and compliance",
         "cues": "law legislation sanctions compliance export control regulation",
         "queries": ["legislation compliance licensing regulation law"],
         "category": "legal",
         "probe": "search for the legislation, licensing rules or court decisions that bind this market"},
    ],
    "outline": {
        "framework": "PESTEL",
        "context": "Case and country context",
        "discussion": "What the evidence shows",
        "implications": "Implications for the decision",
        "limitations": "Limitations",
        "conclusion": "Conclusion",
        "lead": ("PESTEL organises the external environment of a decision into political, economic, social, "
                 "technological, environmental and legal evidence. Each dimension is treated in turn, first through "
                 "the evidence accepted for the case and then through what that evidence implies for the decision."),
    },
    "voice": {
        "thesis_question": "whether the external environment is favourable or constraining for the decision",
        "unit_noun": "country and market",
        "block_plural": "dimensions",
        "lens": ("the mechanisms through which the dimension reaches the firm: cost, access, demand, compliance or "
                 "capability"),
        "closing": "identifies the dimension the decision depends on most and the one the evidence cannot settle",
        "intro_frame": ("The unit of analysis is the environment in which the decision would be taken, rather than "
                        "the firm itself, because these conditions apply to any participant in the market."),
        "context_frame": ("The relevant environment is the country or market named in the brief; the dimensions are "
                          "properties of that environment rather than of a single firm."),
        "interaction": ("Read together, the dimensions describe an environment in which some conditions are "
                        "evidenced and others are not, and a dimension without accepted evidence cannot be read as "
                        "neutral."),
        "implication_frame": ("A viable position must satisfy the conditions the evidenced dimensions impose: costs "
                              "must absorb the policy and price environment, access must survive the legal "
                              "requirements, and demand must be met on terms the market accepts."),
        "reference_heading": "References",
    },
    "notes": {
        "political": {
            "analysis": ("Political conditions reach the decision through policy, trade posture, sanctions and the "
                         "stability of the rules under which the firm would operate. Where the direction of policy "
                         "is contested, the cost of the decision includes exposure to a changed rule rather than "
                         "only the cost of entry. The relevant question is whether the plan can survive a change in "
                         "the conditions it relies on."),
            "qualify": ("The evidence does not establish the durability of the policy position, the likelihood of "
                        "change or the firm's exposure to any single instrument, so the dimension is read as a "
                        "condition on the decision rather than as a forecast."),
            "short": ("Policy conditions therefore enter the decision as a cost of change and a constraint on "
                      "access, not as background."),
            "probe": "search for the policy, trade or sanctions instruments that apply to this market",
        },
        "economic": {
            "analysis": ("Economic conditions set the prices the decision inherits: the cost of inputs, the interest "
                         "cost of funding, and the demand the offer can expect. Where growth and prices move "
                         "together, a plan built on current conditions carries the risk of a narrower margin. The "
                         "relevant question is how much of the plan depends on conditions that could move."),
            "qualify": ("The evidence does not establish the persistence of the reported conditions, their "
                        "distribution across the market, or the share of the plan exposed to them, so the dimension "
                        "is treated as context rather than as a forecast."),
            "short": ("Economic conditions therefore set the prices the decision inherits and the margin it can "
                      "expect to keep."),
            "probe": "search for official figures on growth, prices, interest or exchange rates for this market",
        },
        "social": {
            "analysis": ("Social conditions determine who the offer reaches and on what terms. Demography, "
                         "behaviour and labour expectations shape both the demand for the offer and the cost of "
                         "serving it, and a change in either moves the case for the decision. The relevant question "
                         "is whether the people the plan depends on exist in the numbers and with the expectations "
                         "the plan assumes."),
            "qualify": ("The evidence does not establish how the population in question behaves toward this offer, "
                        "and survey evidence describes stated rather than observed behaviour, so the dimension "
                        "informs the decision without settling demand."),
            "short": ("Social conditions determine who the offer reaches and at what cost it can be served."),
            "probe": "search for demographic or survey evidence on the people this decision depends on",
        },
        "technological": {
            "analysis": ("Technological conditions decide what is feasible and what is already standard. Adoption "
                         "and infrastructure determine whether a capability is a differentiator or a requirement, "
                         "and a plan that assumes the former when the market treats it as the latter carries a cost "
                         "it has not budgeted. The relevant question is whether the technology the decision relies "
                         "on is available, adopted and affordable in this market."),
            "qualify": ("The evidence does not establish adoption within the specific market, the cost of "
                        "implementation or the firm's capacity to operate the technology, so feasibility is inferred "
                        "rather than demonstrated."),
            "short": ("Technological conditions decide whether a capability differentiates the offer or is simply "
                      "a requirement of trading."),
            "probe": "search for adoption or infrastructure evidence on the technology the decision relies on",
        },
        "environmental": {
            "analysis": ("Environmental conditions reach the decision through physical risk, resource availability "
                         "and the regulation that follows both. Where climate, water or energy constraints bind, "
                         "they raise the cost of continuity and can interrupt supply. The relevant question is "
                         "whether the plan depends on conditions that are stable in the market it enters."),
            "qualify": ("The evidence does not establish the probability of a physical event, the firm's exposure "
                        "to it or the insurance and adaptation costs it implies, so the dimension is treated as a "
                        "standing risk rather than a measured one."),
            "short": ("Environmental conditions raise the cost of continuity where climate, water or energy "
                      "constraints bind."),
            "probe": "search for climate, resource or energy evidence specific to this market",
        },
        "legal": {
            "analysis": ("Legal conditions define what the firm may do and what it must show. Licensing, liability "
                         "and compliance determine whether the offer can be sold at all, and the cost of compliance "
                         "is a fixed charge on the plan. The relevant question is whether the plan can meet the "
                         "requirements that apply in this market."),
            "qualify": ("The evidence does not establish how the rules are applied in practice, the time a licence "
                        "takes or the cost of compliance, so the requirement is identified rather than costed."),
            "short": ("Legal conditions define whether the offer may be sold and what compliance costs it must "
                      "carry."),
            "probe": "search for the legislation, licensing rules or court decisions that bind this market",
        },
    },
}

PROFILES = {profile["template"]: profile for profile in (FIVE_FORCES, PESTEL)}

#: The default profile for a payload that predates the template field.
DEFAULT = "template_five_forces"


def has(template):
    return template in PROFILES


def get(template):
    """The profile for a template id, or None when the framework has none."""
    return PROFILES.get(str(template or DEFAULT))


def profile_for(template):
    """The profile, refused when it is incomplete.

    A framework without a profile is not completed at all: the worksheet stays a
    plain form.  A profile that exists must carry every block, its cues, its
    query phrase and its deterministic prose, because a half-filled profile would
    produce a generic paper with the framework's name on it.
    """
    profile = PROFILES.get(str(template or ""))
    if profile is None:
        raise KeyError(str(template or ""))
    missing = []
    for block in profile["blocks"]:
        if not block.get("cues"):
            missing.append("%s: cues" % block["key"])
        if not block.get("queries"):
            missing.append("%s: queries" % block["key"])
        notes = (profile.get("notes") or {}).get(block["key"]) or {}
        for field in ("analysis", "qualify", "short"):
            if not notes.get(field):
                missing.append("%s: %s" % (block["key"], field))
        if profile.get("assumption") == "probe":
            probe = notes.get("probe") or block.get("probe")
            if not probe:
                missing.append("%s: probe" % block["key"])
    for field in ("framework", "context", "discussion", "implications", "limitations", "conclusion", "lead"):
        if not (profile.get("outline") or {}).get(field):
            missing.append("outline: %s" % field)
    if missing:
        raise ValueError("incomplete framework profile: " + "; ".join(missing))
    return profile


def label_for(template):
    """The framework name stored with a paper, from the profile."""
    profile = get(template)
    return profile["label"] if profile else FIVE_FORCES["label"]


def phrase(key):
    """The first search phrase for a dimension key, whichever framework owns it.

    The chat asks for a phrase by dimension key; reading it from the profile keeps
    one copy of the words, so the two surfaces cannot drift apart.
    """
    for profile in PROFILES.values():
        for block in profile["blocks"]:
            if block["key"] == key and block.get("queries"):
                return block["queries"][0]
    return ""


def describe_extra(template):
    """What the served page needs to render the completion form, or None.

    The block labels and prompts stay the template's own; the profile adds the
    unit of analysis, whether ratings apply, the length bands and the wire keys.
    """
    profile = get(template)
    if profile is None:
        return None
    return {
        "template": profile["template"],
        "label": profile["label"],
        "title_prefix": profile["title_prefix"],
        "unit": dict(profile["unit"]),
        "ratings": bool(profile["ratings"]),
        "assumption": profile["assumption"],
        "styles": ["apa", "harvard"],
        "lengths": [{"key": "short", "label": "Short (600-1,200 words)"},
                    {"key": "mid", "label": "Mid (1,200-2,500 words)"},
                    {"key": "long", "label": "Long (2,500-5,000 words)"}],
        "blocks": [{"key": block["key"], "label": block["label"],
                    "prompt": block.get("prompt") or ""} for block in profile["blocks"]],
    }
