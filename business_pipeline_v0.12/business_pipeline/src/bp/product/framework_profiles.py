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

#: SIPOC ------------------------------------------------------------------------

#: SIPOC and the value stream map are **process** frameworks: the facts they

#: organise are the student's own process, which no database observes.  Their

#: blocks therefore carry a `fill` policy, which the completion engine honours:

#:   research - retrieve external evidence as the market frameworks do;

#:   quote    - take the student's own words from the instruction or the notes

#:              that were attached to it, verbatim, so a block the brief already

#:              states is never re-typed;

#:   gap      - nothing the pipeline may supply: only the process owner can

#:              state it, and it stays a named gap until they do.

#: Nothing here observes the process, times a step, measures capacity or reads a

#: machine.  The paper carries what was stated and what was researched, and says

#: plainly that the process evidence is declared rather than measured.

SIPOC = {

    "template": "template_sipoc",

    "key": "sipoc",

    "label": "SIPOC",

    "title_prefix": "SIPOC Analysis",

    "subject": "operations",

    "unit": {

        "field": "process",

        "label": "The process you are mapping",

        "help": ("SIPOC bounds one process. Name it in a few words, for example the lunch service at the meal "

                 "counter or the returns process at the warehouse."),

        "example": "the lunch service at the meal counter",

        "refuse": ("SIPOC bounds one process. Name the process you are mapping, for example the lunch service at "

                   "the meal counter or the returns process at the warehouse."),

    },

    "ratings": False,

    "assumption": "probe",

    "sites": None,

    "providers": None,

    "gate": {"title_context": False, "require_geography": False, "title_cue": False},

    "blocks": [

        {"key": "suppliers", "label": "Suppliers", "prompt": "Who supplies the process, and what each supplies",

         "fill": "research",

         "cues": "supplier vendor farm bakery distributor provider delivers mill producer",

         "queries": ["supplier of the input this process depends on"], "category": None,

         "probe": "name the supplier the process depends on, and what they deliver to it"},

        {"key": "inputs", "label": "Inputs", "prompt": "What the process consumes: material, information, people, equipment",

         "fill": "research",

         "cues": "input raw material ingredients stock packaging staff equipment licence permit consumption",

         "queries": ["supply and cost of the input this process consumes"], "category": None,

         "probe": "name each input the process consumes, and where it comes from"},

        {"key": "process", "label": "Process steps", "prompt": "The steps of the process, in the order they happen",

         "fill": "quote",

         "cues": "process step order first then next finally prepare assemble pack take order serve collect receive store",

         "probe": "state the steps of the process in the brief, in the order they happen"},

        {"key": "outputs", "label": "Outputs", "prompt": "What the process produces and hands on",

         "fill": "quote",

         "cues": "output product meal order parcel report service produces delivers hands result document",

         "probe": "state what the process produces and hands on"},

        {"key": "customers", "label": "Customers", "prompt": "Who receives the output, inside or outside the organisation",

         "fill": "quote",

         "cues": "customer client patient student passenger guest student affairs department team receives collects",

         "probe": "state who receives the output of the process"},

    ],

    "outline": {

        "framework": "SIPOC",

        "context": "The process and its boundary",

        "discussion": "What the evidence shows about the process",

        "implications": "Implications for the decision the process must serve",

        "limitations": "Limitations",

        "conclusion": "Conclusion",

        "lead": ("A SIPOC bounds one process: the suppliers that feed it, the inputs it consumes, the steps in the "

                 "order they happen, the output it hands on and the customer that receives it. Each part is treated "

                 "in turn, first through the evidence accepted for the case and then through what that evidence "

                 "implies for the decision the process must serve."),

    },

    "voice": {

        "thesis_question": "whether the declared boundary of the process is the one the decision turns on",

        "unit_noun": "process",

        "block_plural": "parts",

        "lens": "the flow of material, information and people across the boundary the map declares",

        "closing": "identifies the part the process depends on most and the part the evidence cannot settle",

        "intro_frame": ("The unit of analysis is the process rather than the firm, because a SIPOC is a statement of "

                        "boundary: what enters, what happens and what leaves."),

        "context_frame": ("The relevant process is the one named in the brief; the parts are properties of that "

                          "process rather than of the organisation as a whole."),

        "interaction": ("Read together, the parts describe a boundary in which some conditions are evidenced and "

                        "others are not, and a part without accepted evidence cannot be treated as present."),

        "implication_frame": ("A decision the process must serve has to satisfy the boundary the map declares: the "

                              "inputs must be available on the terms the plan assumes, the steps must be the ones "

                              "that actually happen, and the output must reach the customer the plan names."),

        "reference_heading": "References",

    },

    "notes": {

        "suppliers": {

            "analysis": ("A supplier determines what the process may consume and on what terms. Where a critical "

                         "input arrives from a single source, the continuity of the process depends on that source "

                         "rather than on the firm's own planning. The relevant question for the decision is whether "

                         "the named suppliers can supply the process at the rate the plan assumes."),

            "qualify": ("The evidence does not establish the supplier's capacity, lead time, contract terms or "

                        "alternatives, so the relationship is identified rather than evaluated."),

            "short": ("A single source for a critical input makes continuity of supply a condition of the decision, "

                      "not a background fact."),

        },

        "inputs": {

            "analysis": ("Inputs set what the process has to work with: the material, the information, the people "

                         "and the equipment the steps consume. Where an input is licensed, seasonal or bought in a "

                         "single market, the cost and availability of the process move with it. The relevant "

                         "question is whether every input the process consumes is available on the terms the plan "

                         "assumes."),

            "qualify": ("The evidence does not establish the price, quantity or variability of the inputs, so "

                        "availability is identified rather than measured."),

            "short": ("Availability and cost of the named inputs are conditions of the decision, because a step "

                      "cannot run without what it consumes."),

        },

        "process": {

            "analysis": ("The steps are what the process actually does, in the order it does them. Where the steps "

                         "are stated in sequence, the boundary of the process is testable: a step that is not in the "

                         "map is outside the scope of the decision. The relevant question is whether the stated "

                         "sequence is the one the output depends on."),

            "qualify": ("The evidence does not establish the time each step takes, the capacity of the line or the "

                        "variation between runs, so the sequence is declared rather than measured."),

            "short": ("The declared sequence bounds what the decision may change, because a change outside the "

                      "sequence is a change to a different process."),

        },

        "outputs": {

            "analysis": ("The output is what the process hands on and what the decision is judged on. Where the "

                         "output is a product, a service or a document, its specification determines what the "

                         "customer receives. The relevant question is whether the declared output is what the plan "

                         "promises."),

            "qualify": ("The evidence does not establish the quantity produced, the quality achieved or the "

                        "capacity available, so the output is named rather than sized."),

            "short": ("The declared output is the object of the decision, so any promise about it must be traceable "

                      "to the step that produces it."),

        },

        "customers": {

            "analysis": ("The customer is who receives the output, inside or outside the organisation. Where the "

                         "customer is named, the requirement the process must meet can be stated; where the "

                         "recipient is another function, the hand-off is an internal service relationship with its "

                         "own expectation. The relevant question is whether the declared customer is the one the "

                         "decision serves."),

            "qualify": ("The evidence does not establish the customer's requirement, volume or alternatives, so the "

                        "relationship is identified rather than specified."),

            "short": ("Naming the customer turns the output into a requirement the process must meet."),

        },

    },

}

#: Value stream mapping ----------------------------------------------------------

VALUE_STREAM_MAP = {

    "template": "template_value_stream_map",

    "key": "vsm",

    "label": "Value stream mapping",

    "title_prefix": "Value Stream Mapping Analysis",

    "subject": "operations",

    "unit": {

        "field": "process",

        "label": "The value stream you are mapping",

        "help": ("A value stream map follows one flow of one product or service family from request to delivery. "

                 "Name it in a few words, for example the lunch orders at the meal counter."),

        "example": "the lunch orders at the meal counter",

        "refuse": ("A value stream map follows one flow of one product or service family. Name the value stream "

                   "you are mapping, for example the lunch orders at the meal counter."),

    },

    "ratings": False,

    "assumption": "probe",

    "sites": None,

    "providers": None,

    "gate": {"title_context": False, "require_geography": False, "title_cue": False},

    "blocks": [

        {"key": "process_steps", "label": "Process steps", "prompt": "Each step of the flow, in the order it happens",

         "fill": "quote",

         "cues": "step order prepare assemble pack take order collect deliver receive store flow process",

         "probe": "state the steps of the flow in the brief, in the order they happen"},

        {"key": "cycle_and_lead_times", "label": "Cycle and lead times",

         "prompt": "The time each step takes, and the time the whole flow takes",

         "fill": "quote",

         "cues": "cycle time lead time minutes seconds hours per unit waiting queue turnaround day week takes",

         "probe": "state the times you observed or were given, naming the step each one belongs to"},

        {"key": "inventory_wip", "label": "Inventory and work in progress",

         "prompt": "What waits between steps, and how much of it",

         "fill": "quote",

         "cues": "inventory stock wip work in progress batch backlog pile storage waiting freezer shelf",

         "probe": "state what waits between the steps, and how much of it"},

        {"key": "waits_delays", "label": "Waits and delays",

         "prompt": "Where the flow stops: queues, batches, hand-offs, approvals",

         "fill": "quote",

         "cues": "wait waiting delay queue batch handoff hand-off approval bottleneck idle stalled stop",

         "probe": "state where the flow waits, and what causes each wait"},

        {"key": "value_added", "label": "Value-added assessment",

         "prompt": "Which steps the customer would pay for, and which they would not",

         "fill": "gap",

         "cues": "value added non value waste necessary",

         "probe": "judge each step yourself: the customer pays for the steps that change the offer, and this "

                  "judgement is yours to state and to defend"},

        {"key": "improvements", "label": "Improvement opportunities",

         "prompt": "The changes you propose, and the measure that would show the effect",

         "fill": "gap",

         "cues": "improve improvement change reduce shorten eliminate level kanban",

         "probe": "propose the changes yourself, each with the measure that would show whether it worked"},

    ],

    "outline": {

        "framework": "Value stream mapping",

        "context": "The value stream and its boundary",

        "discussion": "What the evidence shows about the flow",

        "implications": "Implications for the decision the improvement must serve",

        "limitations": "Limitations",

        "conclusion": "Conclusion",

        "lead": ("A value stream map follows one flow from request to delivery: the steps in order, the time each "

                 "takes, what waits between them, which steps the customer would pay for, and the improvements "

                 "proposed against a measure. Each element is treated in turn, first through the evidence accepted "

                 "for the case and then through what that evidence implies for the decision."),

    },

    "voice": {

        "thesis_question": "whether the waits the evidence shows account for the performance the decision must change",

        "unit_noun": "value stream",

        "block_plural": "elements",

        "lens": "the flow of material and information, and the places where it waits",

        "closing": "identifies the wait the improvement should address first and the element the evidence cannot settle",

        "intro_frame": ("The unit of analysis is one flow rather than the firm, because a value stream map is a "

                        "statement of what happens to one offer between request and delivery."),

        "context_frame": ("The relevant flow is the one named in the brief; the elements are properties of that flow "

                          "rather than of the organisation as a whole."),

        "interaction": ("Read together, the elements describe a flow in which some conditions are evidenced and "

                        "others are not, and an element without accepted evidence cannot be treated as favourable."),

        "implication_frame": ("An improvement decision has to answer the waits the evidence shows: the time a step "

                              "takes must be the time the plan assumes, the inventory between steps must be "

                              "affordable, and any change must be judged against a measure the flow already has."),

        "reference_heading": "References",

    },

    "notes": {

        "process_steps": {

            "analysis": ("The steps are what happens to the offer between request and delivery. Where they are "

                         "stated in order, the flow becomes testable: a step outside the map is outside the scope of "

                         "the improvement. The relevant question is whether the stated order is the one the offer "

                         "actually follows."),

            "qualify": ("The evidence does not establish the capacity of each step or the variation between runs, "

                        "so the sequence is declared rather than measured."),

            "short": ("The declared sequence bounds what the improvement may change, because a change outside the "

                      "sequence changes a different flow."),

        },

        "cycle_and_lead_times": {

            "analysis": ("Times turn a sequence into a flow. A cycle time is what one step takes for one unit; a "

                         "lead time is what the whole flow takes for one order. Where both are declared, the part "

                         "of the lead time spent waiting can be located. The relevant question is whether the "

                         "declared times describe a normal period rather than a best case."),

            "qualify": ("The evidence does not establish how the times were observed, over how many observations, "

                        "or what variation they cover, so the times are treated as declared observations rather "

                        "than as measurements."),

            "short": ("Declared times locate the waiting in the flow, but only an observed time can support a claim "

                      "about how long the flow takes."),

        },

        "inventory_wip": {

            "analysis": ("Inventory between steps is work that has been received or started and not yet passed on. "

                         "It protects the next step from variability and ties up cash at the same time. The "

                         "relevant question is whether the declared stock is what the plan can afford to hold."),

            "qualify": ("The evidence does not establish the value of the stock, its turnover or the service level "

                        "it supports, so it is described rather than valued."),

            "short": ("Stock between steps buys continuity at the cost of cash, and the plan must state which of "

                      "the two it is buying."),

        },

        "waits_delays": {

            "analysis": ("A wait is where the flow stops: a queue in front of a step, a batch that must be completed "

                         "before the next step starts, a hand-off or an approval. Where a wait is declared, the "

                         "improvement has somewhere to act. The relevant question is which declared wait accounts "

                         "for most of the lead time."),

            "qualify": ("The evidence does not establish the length or the cause of each wait, so the waits are "

                        "identified rather than sized."),

            "short": ("A declared wait locates the improvement, because removing a wait shortens the flow by the "

                      "time it occupies."),

        },

        "value_added": {

            "analysis": ("The value-added judgement separates the steps the customer pays for from the steps the "

                         "process needs. It is a judgement about the offer, not a measurement, and two analysts can "

                         "defend different answers on the same flow."),

            "qualify": ("The judgement is the student's. The evidence does not establish what any specific customer "

                        "would pay for, so it is recorded as a declared judgement and not as a finding about the "

                        "customer."),

            "short": ("The value-added judgement is a declared position the improvement must defend, not a "

                      "measurement of the customer."),

        },

        "improvements": {

            "analysis": ("An improvement is a declared change with a declared measure. Without the measure the "

                         "change cannot be shown to have worked; without the declaration the change cannot be "

                         "reviewed. The relevant question is whether the measure already exists in the flow."),

            "qualify": ("The evidence does not establish that a proposed change will work, what it costs or what "

                        "else it affects, so the proposals are recorded as declared intentions rather than as "

                        "results."),

            "short": ("An improvement without a measure is an intention; the measure is what turns it into a claim "

                      "the next review can test."),

        },

    },

}

#: Theory of Constraints ---------------------------------------------------------

TOC = {

    "template": "template_toc",

    "key": "toc",

    "label": "Theory of Constraints",

    "title_prefix": "Theory of Constraints Analysis",

    "subject": "operations",

    "unit": {

        "field": "process",

        "label": "The system you are focusing on",

        "help": ("The five focusing steps apply to one system: a line, a service, a whole plant. Name it in a few "

                 "words, for example the lunch service at the meal counter."),

        "example": "the lunch service at the meal counter",

        "refuse": ("The five focusing steps apply to one system. Name the system you are focusing on, for example "

                   "the lunch service at the meal counter."),

    },

    "ratings": False,

    "assumption": "probe",

    "sites": None,

    "providers": None,

    "gate": {"title_context": False, "require_geography": False, "title_cue": False},

    "blocks": [

        {"key": "identify", "label": "Identify the constraint",

         "prompt": "The resource or step that limits the whole system, and how you know",

         "fill": "auto",

         "cues": "constraint bottleneck limit capacity throughput slowest queue backlog oven machine station",

         "queries": ["bottleneck capacity constraint in this process"], "category": None,

         "probe": "name the step you believe limits the system, and the observation that shows it"},

        {"key": "exploit", "label": "Exploit the constraint",

         "prompt": "How the constraint is kept working on what only it can do",

         "fill": "auto",

         "cues": "exploit keep running uptime changeover idle starve block setup bottleneck losses reduced",

         "queries": ["losses at the bottleneck step and how they are reduced"], "category": None,

         "probe": "state what the constraint should never be doing, and what you will stop it doing"},

        {"key": "subordinate", "label": "Subordinate everything else",

         "prompt": "How the other steps are paced to the constraint",

         "fill": "auto",

         "cues": "subordinate pace release schedule buffer drum rope upstream downstream flow",

         "queries": ["pacing and release policy around a capacity constraint"], "category": None,

         "probe": "state how the steps before the constraint are paced to it rather than to their own capacity"},

        {"key": "elevate", "label": "Elevate the constraint",

         "prompt": "The capacity you add, and the evidence that it raises the system's output",

         "fill": "auto",

         "cues": "elevate invest capacity add equipment staff outsource shift capex",

         "queries": ["adding capacity at a bottleneck and its effect on throughput"], "category": None,

         "probe": "state the capacity you would add and the evidence that the system's output would rise"},

        {"key": "reassess", "label": "Reassess",

         "prompt": "Where the constraint moved, and the next constraint",

         "fill": "auto",

         "cues": "reassess next constraint moved inertia repeat review",

         "queries": ["constraint migration after a capacity change"], "category": None,

         "probe": "state where the constraint would move once the change took hold"},

    ],

    "outline": {

        "framework": "Theory of Constraints",

        "context": "The system and its constraint",

        "discussion": "What the evidence shows about the constraint",

        "implications": "Implications for the decision the constraint imposes",

        "limitations": "Limitations",

        "conclusion": "Conclusion",

        "lead": ("The theory of constraints treats one system at a time: the step that limits output is identified, "

                 "exploited, protected by the pacing of everything else, elevated if it still binds, and reassessed "

                 "once it moves. Each step is treated in turn, first through the evidence accepted for the case and "

                 "then through what that evidence implies for the decision."),

    },

    "voice": {

        "thesis_question": "whether the declared constraint is the one the decision must relieve",

        "unit_noun": "system",

        "block_plural": "steps",

        "lens": "the flow of work through the constraint and the losses around it",

        "closing": "identifies the step the system depends on most and the step the evidence cannot settle",

        "intro_frame": ("The unit of analysis is the system rather than the firm, because a constraint is a property "

                        "of the whole flow: relieving any other step does not raise output."),

        "context_frame": ("The relevant system is the one named in the brief; the steps are properties of that flow "

                          "rather than of the organisation as a whole."),

        "interaction": ("Read together, the steps describe a system in which some conditions are evidenced and others "

                        "are not, and a step without accepted evidence cannot be treated as done."),

        "implication_frame": ("A decision that would raise output has to answer the constraint the evidence shows: "

                              "the constraint must be kept working, the rest of the flow paced to it, and any added "

                              "capacity must be shown to move the system rather than a step."),

        "reference_heading": "References",

    },

    "notes": {

        "identify": {

            "analysis": ("The constraint is the step whose capacity limits what the system can deliver. A step that "

                         "is merely busy is not a constraint; the test is whether more capacity elsewhere would raise "

                         "output. The relevant question is whether the named step satisfies that test."),

            "qualify": ("The evidence does not establish throughput, queue lengths or utilisation at each step, so "

                        "the constraint is identified from the declared observation rather than measured."),

            "short": ("A constraint is proved by where work waits, not by where people are busiest."),

            "probe": "name the step you believe limits the system, and the observation that shows it",

        },

        "exploit": {

            "analysis": ("Exploiting the constraint means it never waits for work, never runs the wrong work and "

                         "never stops for a reason the system controls. The losses to remove are the ones at that step, "

                         "not the ones elsewhere. The relevant question is what the constraint currently does that "

                         "only it can do."),

            "qualify": ("The evidence does not establish the constraint's uptime, changeover or blocking time, so the "

                        "losses are identified rather than measured."),

            "short": ("Every minute lost at the constraint is lost to the whole system, and a minute saved elsewhere "

                      "is not."),

            "probe": "state what the constraint should never be doing, and what you will stop it doing",

        },

        "subordinate": {

            "analysis": ("Subordinating the rest means pacing release and work to the constraint rather than to each "

                         "step's own capacity. Where steps upstream run ahead, work in progress grows without raising "

                         "output. The relevant question is whether the flow is released at the constraint's rate."),

            "qualify": ("The evidence does not establish the release policy or the buffers in place, so the pacing is "

                        "declared rather than observed."),

            "short": ("Running upstream steps at their own capacity only builds inventory in front of the constraint."),

            "probe": "state how the steps before the constraint are paced to it rather than to their own capacity",

        },

        "elevate": {

            "analysis": ("Elevating adds capacity at the constraint: equipment, people, a shift, an outsourced step. "

                         "It is the expensive step, so it follows exploitation rather than replacing it. The relevant "

                         "question is whether the added capacity actually moves the system's output."),

            "qualify": ("The evidence does not establish the cost, lead time or realised capacity of the addition, so "

                        "the change is declared rather than costed."),

            "short": ("Adding capacity is the last of the first four steps, because it costs money and the earlier "

                      "steps do not."),

            "probe": "state the capacity you would add and the evidence that the system's output would rise",

        },

        "reassess": {

            "analysis": ("Once the constraint moves, the system has a new one, and the five steps repeat. A change "

                         "that is not reassessed can leave the system optimised around a constraint that is no longer "

                         "binding. The relevant question is where the constraint moves to."),

            "qualify": ("The evidence does not establish the new constraint, because it depends on the change that "

                        "has not happened yet, so the reassessment is declared rather than observed."),

            "short": ("A moved constraint is not the end of the method; it is the next iteration of it."),

            "probe": "state where the constraint would move once the change took hold",

        },

    },

}

#: A3 problem solving ------------------------------------------------------------

A3 = {

    "template": "template_a3",

    "key": "a3",

    "label": "A3 problem solving",

    "title_prefix": "A3 Problem-Solving Analysis",

    "subject": "operations",

    "unit": {

        "field": "process",

        "label": "The process the problem sits in",

        "help": ("An A3 works one problem in one process. Name it in a few words, for example the lunch service at "

                 "the meal counter or the returns process at the warehouse."),

        "example": "the lunch service at the meal counter",

        "refuse": ("An A3 works one problem in one process. Name the process the problem sits in, for example the "

                   "lunch service at the meal counter."),

    },

    "ratings": False,

    "assumption": "probe",

    "sites": None,

    "providers": None,

    "gate": {"title_context": False, "require_geography": False, "title_cue": False},

    "blocks": [

        {"key": "problem", "label": "Problem", "prompt": "The problem, stated as the gap between what happens and what should",

         "fill": "auto", "cues": "problem waste defect delay error complaint target gap",

         "queries": ["operational problem delay defect in this process"], "category": None,

         "probe": "state the problem as a measurable gap, in one sentence"},

        {"key": "current_condition", "label": "Current condition",

         "prompt": "What actually happens now, and the evidence for it",

         "fill": "auto", "cues": "current now today delay queue time defect rate observe data",

         "queries": ["current performance and causes of delay in this process"], "category": None,

         "probe": "state what happens now, with the observation or figure that shows it"},

        {"key": "target", "label": "Target condition", "prompt": "What success looks like, and the measure that shows it",

         "fill": "auto", "cues": "target goal reduce increase within by measure standard",

         "queries": ["performance target and benchmark for this process"], "category": None,

         "probe": "state the target and the measure that will show it was met"},

        {"key": "causes", "label": "Root causes", "prompt": "The causes you can evidence, not the symptoms",

         "fill": "auto", "cues": "cause root why because reason driver factor",

         "queries": ["root causes of delay or defect in this process"], "category": None,

         "probe": "state each cause with the evidence that establishes it"},

        {"key": "countermeasures", "label": "Countermeasures",

         "prompt": "The specific changes proposed against each evidenced cause",

         "fill": "auto", "cues": "countermeasure change action fix redesign separate combine simplify",

         "queries": ["countermeasures that reduce delay or defect in this process"], "category": None,

         "probe": "state the change proposed for each evidenced cause"},

        {"key": "plan", "label": "Plan and owners", "prompt": "Who does what, by when, and what each step depends on",

         "fill": "auto", "cues": "plan owner responsible by when week month step depend",

         "queries": ["implementation plan and ownership for a process improvement"], "category": None,

         "probe": "state who does what, by when, and what it depends on"},

        {"key": "follow_up", "label": "Follow-up",

         "prompt": "When the effect is checked, on what measure, and what would trigger a rethink",

         "fill": "auto", "cues": "follow up review check measure verify sustain audit next",

         "queries": ["follow-up measurement of a process improvement"], "category": None,

         "probe": "state when the effect is checked and on what measure"},

    ],

    "outline": {

        "framework": "A3 problem solving",

        "context": "The process and the problem",

        "discussion": "What the evidence shows about the problem",

        "implications": "Implications for the decision the evidence supports",

        "limitations": "Limitations",

        "conclusion": "Conclusion",

        "lead": ("An A3 works one problem in one process: the problem as a gap, the current condition, the target, "

                 "the causes that can be evidenced, the countermeasures proposed, the plan with owners, and the "

                 "follow-up that tests the effect. Each section is treated in turn, first through the evidence "

                 "accepted for the case and then through what that evidence implies for the decision."),

    },

    "voice": {

        "thesis_question": "whether the evidenced causes support the countermeasures the decision proposes",

        "unit_noun": "process",

        "block_plural": "sections",

        "lens": "the gap between the current condition and the target, and what closes it",

        "closing": "identifies the cause the evidence supports most and the section the evidence cannot settle",

        "intro_frame": ("The unit of analysis is the process the problem sits in, because an A3 is a statement about "

                        "one gap in one flow rather than about the organisation as a whole."),

        "context_frame": ("The relevant process is the one named in the brief; the sections are properties of that "

                          "problem rather than of the firm."),

        "interaction": ("Read together, the sections describe a problem in which some conditions are evidenced and "

                        "others are not, and a section without accepted evidence cannot be treated as settled."),

        "implication_frame": ("A countermeasure has to answer the cause the evidence shows: the current condition "

                              "must be the one the gap describes, the cause must be supported rather than assumed, and "

                              "the follow-up must measure the effect the target names."),

        "reference_heading": "References",

    },

    "notes": {

        "problem": {

            "analysis": ("The problem is the gap between what happens and what should, stated so that it can be "

                         "tested. A problem stated as a solution ('we need a second oven') hides the gap. The relevant "

                         "question is whether the gap is stated in terms someone could measure."),

            "qualify": ("The evidence does not establish the size or frequency of the gap, so the problem is stated "

                        "rather than sized."),

            "short": ("A problem stated as a solution cannot be tested, because nothing in it says what is wrong."),

            "probe": "state the problem as a measurable gap, in one sentence",

        },

        "current_condition": {

            "analysis": ("The current condition is what the process does now, with the observation that shows it. It "

                         "is the baseline the target is measured against, and without it an improvement cannot be "

                         "shown. The relevant question is whether the baseline is described rather than assumed."),

            "qualify": ("The evidence does not establish the reliability of the observation, the period it covers or "

                        "its variation, so the condition is described rather than measured."),

            "short": ("Without a baseline the target cannot be shown to have been reached."),

            "probe": "state what happens now, with the observation or figure that shows it",

        },

        "target": {

            "analysis": ("The target is what success looks like, with the measure that shows it. A target without a "

                         "measure is an aspiration; a measure without a target cannot say whether the change worked. "

                         "The relevant question is whether the target is one the follow-up could test."),

            "qualify": ("The evidence does not establish that the target is achievable or by when, so it is declared "

                        "rather than forecast."),

            "short": ("A target without a measure cannot be tested, and a measure without a target cannot be judged."),

            "probe": "state the target and the measure that will show it was met",

        },

        "causes": {

            "analysis": ("Causes are the reasons the gap exists, each supported by evidence rather than by plausibility. "

                         "A cause that cannot be evidenced is a hypothesis, and a countermeasure built on it may fix "

                         "nothing. The relevant question is which causes the evidence actually supports."),

            "qualify": ("The evidence does not establish causation, only association, so the causes are recorded as "

                        "supported hypotheses rather than as proven mechanisms."),

            "short": ("A countermeasure built on an unevidenced cause may fix nothing and still cost the change."),

            "probe": "state each cause with the evidence that establishes it",

        },

        "countermeasures": {

            "analysis": ("A countermeasure is a specific change aimed at an evidenced cause. Where a cause has no "

                         "countermeasure, the gap remains; where a countermeasure has no cause, it is a solution "

                         "looking for a problem. The relevant question is whether each change answers a stated cause."),

            "qualify": ("The evidence does not establish that a countermeasure will work, what it costs or what else "

                        "it affects, so the changes are recorded as proposals rather than as results."),

            "short": ("A countermeasure without a cause is a solution looking for a problem."),

            "probe": "state the change proposed for each evidenced cause",

        },

        "plan": {

            "analysis": ("The plan turns a proposal into work: what is done, by whom, by when, and what it depends on. "

                         "An action without an owner is a wish, and one without a date cannot be reviewed. The "

                         "relevant question is whether every action has both."),

            "qualify": ("The evidence does not establish that the dates or owners are agreed, so the plan is recorded "

                        "as declared rather than as committed."),

            "short": ("An action with no owner and no date cannot be reviewed, so it cannot fail visibly either."),

            "probe": "state who does what, by when, and what it depends on",

        },

        "follow_up": {

            "analysis": ("The follow-up is when the effect is checked, on the measure the target named. Without it the "

                         "A3 ends at the proposal, and the next problem is diagnosed from memory. The relevant "

                         "question is whether the check could show the change failed."),

            "qualify": ("The evidence does not establish when the effect would be visible, because it depends on the "

                        "change that has not happened yet, so the check is declared rather than scheduled."),

            "short": ("A follow-up that could not show failure is not a check; it is a formality."),

            "probe": "state when the effect is checked and on what measure",

        },

    },

}

#: SCOR -------------------------------------------------------------------------

SCOR = {

    "template": "template_scor",

    "key": "scor",

    "label": "SCOR",

    "title_prefix": "SCOR Supply-Chain Analysis",

    "subject": "operations",

    "unit": {

        "field": "process",

        "label": "The supply chain you are mapping",

        "help": "Name the chain or the part of it in scope, for example the meal counter's supply chain.",

        "example": "the meal counter's supply chain",

        "refuse": ("SCOR maps one supply chain. Name the chain or the part of it in scope, for example the meal "

                   "counter's supply chain."),

    },

    "ratings": False,

    "assumption": "probe",

    "sites": None,

    "providers": None,

    "gate": {"title_context": False, "require_geography": False, "title_cue": False},

    "blocks": [

        {"key": "plan", "label": "Plan", "prompt": "How demand and supply are balanced", "fill": "auto",

         "cues": "plan forecast demand balance schedule replenish",

         "queries": ["demand and supply planning in this chain"], "category": None,

         "probe": "state how demand is planned and how supply is set against it"},

        {"key": "source", "label": "Source", "prompt": "How inputs and goods are procured, and from whom", "fill": "auto",

         "cues": "supplier procurement purchasing source buy vendor contract",

         "queries": ["procurement and supplier management in this chain"], "category": None,

         "probe": "name what is bought, from whom, and on what terms"},

        {"key": "make", "label": "Make", "prompt": "How the product or service is produced", "fill": "auto",

         "cues": "make production assembly manufacturing prepare build",

         "queries": ["production process in this chain"], "category": None,

         "probe": "state how the product or service is produced"},

        {"key": "deliver", "label": "Deliver", "prompt": "How the finished offer reaches the customer", "fill": "auto",

         "cues": "deliver distribution transport logistics shipping customer",

         "queries": ["distribution and delivery in this chain"], "category": None,

         "probe": "state how the finished offer reaches the customer"},

        {"key": "return", "label": "Return", "prompt": "How returns, defects and reverse flows are handled", "fill": "auto",

         "cues": "return reverse defect recall warranty credit",

         "queries": ["returns and reverse logistics in this chain"], "category": None,

         "probe": "state what comes back and how it is handled"},

        {"key": "enable", "label": "Enable", "prompt": "The rules, data, contracts and people behind the other five", "fill": "auto",

         "cues": "enable governance data compliance contract training system",

         "queries": ["governance and enabling processes in this chain"], "category": None,

         "probe": "state the rules, data or contracts the other five depend on"},

    ],

    "outline": {

        "framework": "SCOR", "context": "The supply chain and its scope",

        "discussion": "What the evidence shows about the chain",

        "implications": "Implications for the decision the chain must serve",

        "limitations": "Limitations", "conclusion": "Conclusion",

        "lead": ("SCOR describes a supply chain through six processes - plan, source, make, deliver, return and "

                 "enable. Each is treated in turn, first through the evidence accepted for the case and then "

                 "through what that evidence implies for the decision."),

    },

    "voice": {

        "thesis_question": "whether the declared chain can meet the demand the decision assumes",

        "unit_noun": "supply chain", "block_plural": "processes",

        "lens": "the flow of goods, information and money across the chain",

        "closing": "identifies the process the chain depends on most and the process the evidence cannot settle",

        "intro_frame": ("The unit of analysis is the chain rather than the firm, because a supply chain is a "

                        "sequence of processes that only works when each hands on to the next."),

        "context_frame": ("The relevant chain is the one named in the brief; the processes are properties of that "

                          "chain rather than of the organisation as a whole."),

        "interaction": ("Read together, the processes describe a chain in which some conditions are evidenced and "

                        "others are not, and a process without accepted evidence cannot be treated as sound."),

        "implication_frame": ("A decision the chain must serve has to satisfy the processes the evidence shows: "

                              "demand must be planned against supply, sourcing must hold, and delivery must reach "

                              "the customer the plan names."),

        "reference_heading": "References",

    },

    "notes": {

        "plan": {"analysis": ("Planning is where demand and supply are reconciled. Without it each process optimises "

                              "itself and the chain holds inventory instead of information. The relevant question is "

                              "whether a plan exists and what it is based on."),

                 "qualify": ("The evidence does not establish the planning horizon, the forecast method or its error, "

                             "so the plan is described rather than tested."),

                 "short": ("Without a plan the chain coordinates through stock, which is the expensive substitute."),

                 "probe": "state how demand is planned and how supply is set against it"},

        "source": {"analysis": ("Sourcing determines what the chain may consume and on what terms. A single source for "

                                "a critical input moves the chain's risk onto that supplier. The relevant question is "

                                "whether the declared sourcing can hold at the rate the plan assumes."),

                   "qualify": ("The evidence does not establish supplier capacity, lead time or alternatives, so the "

                               "relationship is identified rather than evaluated."),

                   "short": ("A single source for a critical input is a shared risk, not a purchasing detail."),

                   "probe": "name what is bought, from whom, and on what terms"},

        "make": {"analysis": ("Making turns inputs into the offer. Its capacity and quality set what the chain can "

                              "promise downstream. The relevant question is whether making can deliver what the plan "

                              "sells."),

                 "qualify": ("The evidence does not establish capacity, yield or changeover, so making is described "

                             "rather than measured."),

                 "short": ("What is made sets what can be promised, so a sales promise is also a production claim."),

                 "probe": "state how the product or service is produced"},

        "deliver": {"analysis": ("Delivery moves the offer to the customer, and its reliability is what the customer "

                                 "experiences. The relevant question is whether delivery can meet the promise the "

                                 "plan makes."),

                    "qualify": ("The evidence does not establish delivery time, cost or reliability, so the process is "

                                "described rather than measured."),

                    "short": ("Delivery is where the chain's promise becomes visible to the customer."),

                    "probe": "state how the finished offer reaches the customer"},

        "return": {"analysis": ("Returns close the loop: defects, recalls and credits. A chain without a return path "

                                "pays for them somewhere else. The relevant question is what comes back and whether "

                                "the chain can absorb it."),

                   "qualify": ("The evidence does not establish return volume or cost, so the path is identified "

                               "rather than sized."),

                   "short": ("A return path that is not designed is a cost that is discovered later."),

                   "probe": "state what comes back and how it is handled"},

        "enable": {"analysis": ("Enabling processes - rules, data, contracts, people - are what let the other five "

                                "work together. The relevant question is whether the enabling layer is in place."),

                   "qualify": ("The evidence does not establish how decisions are governed or how data is shared, so "

                               "the layer is described rather than assessed."),

                   "short": ("The enabling layer is invisible until it fails, and then every process fails with it."),

                   "probe": "state the rules, data or contracts the other five depend on"},

    },

}

#: 5S ----------------------------------------------------------------------------

FIVE_S = {

    "template": "template_5s",

    "key": "five_s",

    "label": "5S",

    "title_prefix": "5S Workplace Analysis",

    "subject": "operations",

    "unit": {

        "field": "process",

        "label": "The workplace you are auditing",

        "help": "Name the area in scope, for example the meal counter or the packing bench.",

        "example": "the meal counter",

        "refuse": "5S audits one workplace. Name the area in scope, for example the meal counter.",

    },

    "ratings": False,

    "assumption": "probe",

    "sites": None,

    "providers": None,

    "gate": {"title_context": False, "require_geography": False, "title_cue": False},

    "blocks": [

        {"key": "sort", "label": "Sort", "prompt": "What is removed because it is not needed", "fill": "auto",

         "cues": "sort remove unnecessary clutter messy unused broken excess discard red tag",

         "queries": ["workplace organisation and sorting"],

         "category": None, "probe": "state what was removed and why it was not needed"},

        {"key": "set_in_order", "label": "Set in order", "prompt": "Where each thing belongs, and how that place is marked",

         "fill": "auto", "cues": "place location label mark arrangement layout tools left find",

         "queries": ["workplace layout and visual location marking"], "category": None,

         "probe": "state where each thing belongs and how the place is marked"},

        {"key": "shine", "label": "Shine", "prompt": "What is cleaned, inspected and restored, and how often",

         "fill": "auto", "cues": "clean inspect maintenance wash wipe schedule dirty spill service",

         "queries": ["cleaning and inspection routine in a workplace"], "category": None,

         "probe": "state what is cleaned or inspected, and how often"},

        {"key": "standardize", "label": "Standardize", "prompt": "The standard that keeps the first three in place",

         "fill": "auto", "cues": "standard procedure checklist photo instruction informal nobody",

         "queries": ["standard work and visual standards in a workplace"], "category": None,

         "probe": "state the standard, who wrote it and where it is visible"},

        {"key": "sustain", "label": "Sustain", "prompt": "The audit, habit and owner that keep the standard alive",

         "fill": "auto", "cues": "audit habit sustain owner review discipline",

         "queries": ["sustaining a workplace standard through audits"], "category": None,

         "probe": "state who audits, how often, and what happens when the standard slips"},

    ],

    "outline": {

        "framework": "5S", "context": "The workplace and its scope",

        "discussion": "What the evidence shows about the workplace",

        "implications": "Implications for the decision the workplace must support",

        "limitations": "Limitations", "conclusion": "Conclusion",

        "lead": ("5S organises one workplace through five steps - sort, set in order, shine, standardize and "

                 "sustain. Each is treated in turn, first through the evidence accepted for the case and then "

                 "through what that evidence implies."),

    },

    "voice": {

        "thesis_question": "whether the declared workplace disciplines are in place and hold",

        "unit_noun": "workplace", "block_plural": "steps",

        "lens": "what a person finds, reaches for and puts back in the area",

        "closing": "identifies the step the workplace depends on most and the step the evidence cannot settle",

        "intro_frame": ("The unit of analysis is one workplace, because 5S is a statement about what a person "

                        "finds and does in a specific area rather than about the organisation."),

        "context_frame": ("The relevant area is the one named in the brief; the steps are properties of that area."),

        "interaction": ("Read together, the steps describe a workplace in which some disciplines are evidenced and "

                        "others are not, and a step without evidence cannot be treated as done."),

        "implication_frame": ("A decision about the area has to answer the steps the evidence shows: what is "

                              "removed, where things belong, what is kept clean, and who keeps it that way."),

        "reference_heading": "References",

    },

    "notes": {

        "sort": {"analysis": ("Sorting removes what the work does not need, so the area shows only what it uses. "

                              "The relevant question is whether what remains is there because it is needed."),

                 "qualify": ("The evidence does not establish how much was removed or where it went, so the step is "

                             "described rather than measured."),

                 "short": ("An area that holds only what the work needs is easier to keep in order."),

                 "probe": "state what was removed and why it was not needed"},

        "set_in_order": {"analysis": ("Setting in order gives each thing a place and marks it, so the place teaches "

                                      "the standard. The relevant question is whether a person who did not arrange "

                                      "the area could put something back correctly."),

                         "qualify": ("The evidence does not establish how the marking is maintained, so the "

                                     "arrangement is described rather than tested."),

                         "short": ("A place that is marked teaches the standard without a supervisor."),

                         "probe": "state where each thing belongs and how the place is marked"},

        "shine": {"analysis": ("Shining is cleaning used as inspection: the area is restored and faults are seen "

                               "early. The relevant question is whether cleaning is scheduled rather than occasional."),

                  "qualify": ("The evidence does not establish frequency or who does it, so the routine is described "

                              "rather than measured."),

                  "short": ("Cleaning that is scheduled finds faults before they stop the work."),

                  "probe": "state what is cleaned or inspected, and how often"},

        "standardize": {"analysis": ("Standardizing writes down what the first three steps require, so the state can "

                                     "be repeated by anyone. The relevant question is whether the standard is visible "

                                     "where the work happens."),

                        "qualify": ("The evidence does not establish whether the standard is followed, so it is "

                                    "described rather than audited."),

                        "short": ("A standard kept in an office is a document; one kept at the workplace is a method."),

                        "probe": "state the standard, who wrote it and where it is visible"},

        "sustain": {"analysis": ("Sustaining is the audit and the habit that keep the standard alive after attention "

                                 "moves elsewhere. The relevant question is whether a slip would be noticed."),

                    "qualify": ("The evidence does not establish the audit frequency or its record, so the habit is "

                                "described rather than measured."),

                    "short": ("A standard with no audit decays at the speed of the next busy week."),

                    "probe": "state who audits, how often, and what happens when the standard slips"},

    },

}

#: Root cause analysis -----------------------------------------------------------

ROOT_CAUSE = {

    "template": "template_root_cause",

    "key": "root_cause",

    "label": "Root cause analysis",

    "title_prefix": "Root Cause Analysis",

    "subject": "operations",

    "unit": {

        "field": "process",

        "label": "The process the problem sits in",

        "help": "Name the process and the problem in a few words, for example the noon queue at the meal counter.",

        "example": "the noon queue at the meal counter",

        "refuse": ("Root cause analysis works one problem in one process. Name the process and the problem, for "

                   "example the noon queue at the meal counter."),

    },

    "ratings": False,

    "assumption": "probe",

    "sites": None,

    "providers": None,

    "gate": {"title_context": False, "require_geography": False, "title_cue": False},

    "blocks": [

        {"key": "problem", "label": "Problem", "prompt": "The effect, with where and when it happens", "fill": "auto",

         "cues": "problem defect error delay fail complaint", "queries": ["causes of delay or defect in this process"],

         "category": None, "probe": "state the effect, where and when it happens"},

        {"key": "people", "label": "People", "prompt": "Causes rooted in skills, staffing, training or behaviour",

         "fill": "auto", "cues": "people staff human factors training skill shift handover error", "queries": ["human factors in process error"],

         "category": None, "probe": "state any cause you can evidence in people, training or staffing"},

        {"key": "process", "label": "Process / method", "prompt": "Causes rooted in the way the work is designed",

         "fill": "auto", "cues": "process method procedure step sequence workflow", "queries": ["process design causes of delay"],

         "category": None, "probe": "state any cause you can evidence in how the work is designed"},

        {"key": "equipment", "label": "Equipment", "prompt": "Causes rooted in machines, tools or maintenance",

         "fill": "auto", "cues": "equipment machine tool maintenance breakdown capacity", "queries": ["equipment reliability and capacity limits"],

         "category": None, "probe": "state any cause you can evidence in equipment or maintenance"},

        {"key": "materials", "label": "Materials", "prompt": "Causes rooted in inputs, specifications or supply",

         "fill": "auto", "cues": "material input specification supply quality stock", "queries": ["input quality and supply causes"],

         "category": None, "probe": "state any cause you can evidence in inputs or supply"},

        {"key": "measurement", "label": "Measurement", "prompt": "Causes rooted in how the work is measured or judged",

         "fill": "auto", "cues": "measurement metric calibration inspection standard gauge", "queries": ["measurement error and inspection design"],

         "category": None, "probe": "state any cause you can evidence in how the work is measured"},

        {"key": "environment", "label": "Environment", "prompt": "Causes rooted in the surroundings", "fill": "auto",

         "cues": "environment layout light heat noise space", "queries": ["workplace environment effects on performance"],

         "category": None, "probe": "state any cause you can evidence in the surroundings"},

        {"key": "root_cause", "label": "Root cause", "prompt": "The cause the evidence supports, and the test that showed it",

         "fill": "auto", "cues": "root cause verified evidence test confirmed why", "queries": ["established causes of this process problem"],

         "category": None, "probe": "state the cause the evidence supports, and the test that showed it"},

    ],

    "outline": {

        "framework": "Root cause analysis", "context": "The process and the problem",

        "discussion": "What the evidence shows about the causes",

        "implications": "Implications for the decision the cause supports",

        "limitations": "Limitations", "conclusion": "Conclusion",

        "lead": ("Root cause analysis separates the effect from its causes and tests the candidates until one is "

                 "supported. The problem is stated first, the candidate causes are gathered under the fishbone "

                 "categories, and the root cause is recorded only where the evidence supports it."),

    },

    "voice": {

        "thesis_question": "whether the evidenced cause explains the effect the problem describes",

        "unit_noun": "problem", "block_plural": "categories",

        "lens": "the mechanism that links each candidate cause to the observed effect",

        "closing": "identifies the cause the evidence supports most and the category the evidence cannot settle",

        "intro_frame": ("The unit of analysis is one problem in one process, because a cause is only a cause of a "

                        "specific effect in a specific flow."),

        "context_frame": ("The relevant process is the one named in the brief; the categories are properties of that "

                          "problem rather than of the organisation."),

        "interaction": ("Read together, the categories describe a problem in which some causes are evidenced and "

                        "others are not, and a category without evidence cannot be treated as cleared."),

        "implication_frame": ("A remedy has to answer the cause the evidence supports: a cause that is only a "

                              "hypothesis may be worth testing, but it is not yet a reason to change the process."),

        "reference_heading": "References",

    },

    "notes": {

        "problem": {"analysis": ("The problem is the effect, stated with where and when it happens. A problem stated "

                                 "without a location or a time cannot be checked against the process. The relevant "

                                 "question is whether the statement could be observed."),

                    "qualify": ("The evidence does not establish the frequency or size of the effect, so it is stated "

                                "rather than measured."),

                    "short": ("An effect with no location or time cannot be traced to a step."),

                    "probe": "state the effect, where and when it happens"},

        "people": {"analysis": ("People causes are about skills, staffing and handover rather than about blame. The "

                                "relevant question is whether the evidence points to a capability or a behaviour, and "

                                "which."),

                   "qualify": ("The evidence does not establish the individual or team involved, so any people cause "

                               "is a hypothesis about capability rather than a finding about a person."),

                   "short": ("A people cause is a claim about capability, not about who is at fault."),

                   "probe": "state any cause you can evidence in people, training or staffing"},

        "process": {"analysis": ("Process causes are in the design of the work: sequence, hand-offs, batching. The "

                                 "relevant question is whether the step as designed can produce the effect."),

                    "qualify": ("The evidence does not establish the timing of each step, so the design is described "

                                "rather than measured."),

                    "short": ("A process that can produce the effect will produce it again."),

                    "probe": "state any cause you can evidence in how the work is designed"},

        "equipment": {"analysis": ("Equipment causes are capacity, reliability and maintenance. A machine at its limit "

                                   "makes the effect structural rather than occasional. The relevant question is "

                                   "whether the equipment can meet the demand placed on it."),

                      "qualify": ("The evidence does not establish the equipment's rated capacity or failure history, "

                                  "so the limit is inferred rather than measured."),

                      "short": ("Equipment at its limit turns an occasional effect into a routine one."),

                      "probe": "state any cause you can evidence in equipment or maintenance"},

        "materials": {"analysis": ("Material causes are in the inputs: specification, quality, supply. The relevant "

                                   "question is whether the input the process receives is the one it was designed for."),

                      "qualify": ("The evidence does not establish incoming inspection or specification, so the input "

                                  "is described rather than tested."),

                      "short": ("An input outside its specification makes a sound process produce a bad result."),

                      "probe": "state any cause you can evidence in inputs or supply"},

        "measurement": {"analysis": ("Measurement causes are in how the work is judged: the gauge, the inspection, "

                                     "the standard. A measure that is wrong makes the problem look like something "

                                     "else. The relevant question is whether the measure can see the effect."),

                        "qualify": ("The evidence does not establish the measurement system's error, so the measure "

                                    "is described rather than assessed."),

                        "short": ("A measure that cannot see the effect sends the investigation to the wrong step."),

                        "probe": "state any cause you can evidence in how the work is measured"},

        "environment": {"analysis": ("Environment causes are layout, light, heat, noise and space. The relevant "

                                     "question is whether the surroundings make the work harder than it need be."),

                        "qualify": ("The evidence does not establish the conditions at the workplace, so the "

                                    "surroundings are described rather than measured."),

                        "short": ("Surroundings that fight the work produce errors that look like carelessness."),

                        "probe": "state any cause you can evidence in the surroundings"},

        "root_cause": {"analysis": ("The root cause is the one the evidence supports, with the test that showed it. "

                                    "A cause that has not been tested is the strongest hypothesis, not the answer. "

                                    "The relevant question is what would have shown the cause to be wrong."),

                       "qualify": ("The evidence establishes association rather than mechanism, so the cause is "

                                   "recorded as the best-supported explanation rather than a proven one."),

                       "short": ("A cause nobody tried to falsify is a hypothesis with a confident tone."),

                       "probe": "state the cause the evidence supports, and the test that showed it"},

    },

}

#: FMEA --------------------------------------------------------------------------

FMEA = {

    "template": "template_fmea",

    "key": "fmea",

    "label": "FMEA",

    "title_prefix": "Failure Mode and Effects Analysis",

    "subject": "operations",

    "unit": {

        "field": "process",

        "label": "The process or product you are analysing",

        "help": "Name the process or product in scope, for example the meal counter's lunch service.",

        "example": "the meal counter's lunch service",

        "refuse": ("FMEA analyses one process or product. Name it in a few words, for example the meal counter's "

                   "lunch service."),

    },

    "ratings": False,

    "assumption": "probe",

    "sites": None,

    "providers": None,

    "gate": {"title_context": False, "require_geography": False, "title_cue": False},

    "blocks": [

        {"key": "failure_modes", "label": "Failure modes", "prompt": "The ways the process or product can fail",

         "fill": "auto", "cues": "failure mode defect error wrong missing late", "queries": ["failure modes in this process"],

         "category": None, "probe": "state each way the process can fail"},

        {"key": "effects", "label": "Effects", "prompt": "What each failure does to the customer or the next step",

         "fill": "auto", "cues": "effect impact customer consequence waste delay", "queries": ["effects of failure on the customer"],

         "category": None, "probe": "state what each failure does to the customer or the next step"},

        {"key": "causes", "label": "Causes", "prompt": "Why each failure mode happens", "fill": "auto",

         "cues": "cause reason failure source because", "queries": ["causes of failure in this process"],

         "category": None, "probe": "state why each failure happens"},

        {"key": "controls", "label": "Current controls", "prompt": "What already detects or prevents it",

         "fill": "auto", "cues": "control prevention detection inspection check", "queries": ["prevention and detection controls"],

         "category": None, "probe": "state what already prevents or detects each failure"},

        {"key": "actions", "label": "Recommended actions", "prompt": "The change proposed for the highest-risk modes",

         "fill": "auto", "cues": "action reduce mitigate improve redesign", "queries": ["risk reduction actions for this process"],

         "category": None, "probe": "state the change proposed, and which failure it addresses"},

        {"key": "owners", "label": "Owners and review", "prompt": "Who acts, by when, and when the risk is reviewed again",

         "fill": "auto", "cues": "owner review date responsible follow assigning ownership actions", "queries": ["assigning ownership for risk actions"],

         "category": None, "probe": "state who acts, by when, and when the risk is reviewed again"},

    ],

    "outline": {

        "framework": "Failure mode and effects analysis", "context": "The process and its failure modes",

        "discussion": "What the evidence shows about the failure modes",

        "implications": "Implications for the decision the risk imposes",

        "limitations": "Limitations", "conclusion": "Conclusion",

        "lead": ("An FMEA lists the ways a process or product can fail, what each failure does, why it happens and "

                 "what already controls it, then records the actions proposed and who owns them. Each part is "

                 "treated in turn, first through the evidence accepted for the case and then through what it implies."),

    },

    "voice": {

        "thesis_question": "whether the evidenced failure modes are controlled well enough for the decision",

        "unit_noun": "process", "block_plural": "parts",

        "lens": "the path from a cause through a failure to its effect on the customer",

        "closing": "identifies the failure mode the evidence supports most and the part the evidence cannot settle",

        "intro_frame": ("The unit of analysis is the process or product in scope, because a failure mode is a "

                        "property of a specific flow rather than of the organisation."),

        "context_frame": ("The relevant process is the one named in the brief; the parts are properties of that "

                          "process rather than of the firm."),

        "interaction": ("Read together, the parts describe a process in which some risks are evidenced and others "

                        "are not, and a part without evidence cannot be treated as controlled."),

        "implication_frame": ("A decision about the process has to answer the failures the evidence shows: each "

                              "cause must be prevented or detected, and each action must have an owner."),

        "reference_heading": "References",

    },

    "notes": {

        "failure_modes": {"analysis": ("A failure mode is a way the process departs from what it should do. It is "

                                       "stated as what goes wrong, not as its cause. The relevant question is whether "

                                       "each mode could be observed."),

                          "qualify": ("The evidence does not establish the frequency of each mode, so they are listed "

                                      "rather than ranked."),

                          "short": ("A mode stated as a cause hides the effect the customer actually sees."),

                          "probe": "state each way the process can fail"},

        "effects": {"analysis": ("The effect is what the failure does to the customer or the next step. Effects that "

                                 "reach the customer matter more than ones caught internally. The relevant question "

                                 "is where each failure is felt."),

                    "qualify": ("The evidence does not establish severity, so effects are described rather than "

                                "graded."),

                    "short": ("An effect caught internally and one felt by the customer are different problems."),

                    "probe": "state what each failure does to the customer or the next step"},

        "causes": {"analysis": ("Causes explain why the mode happens. A mode with no evidenced cause cannot be "

                                "prevented, only detected. The relevant question is whether a cause is known or only "

                                "suspected."),

                   "qualify": ("The evidence does not establish causation, so causes are recorded as supported "

                               "hypotheses."),

                   "short": ("Without a cause the best available answer is detection, not prevention."),

                   "probe": "state why each failure happens"},

        "controls": {"analysis": ("Controls are what already prevents or detects the failure. A control that relies "

                                  "on someone noticing is weaker than one built into the step. The relevant question "

                                  "is whether each mode has a control at all."),

                     "qualify": ("The evidence does not establish how reliably each control works, so controls are "

                                 "recorded rather than tested."),

                     "short": ("A mode with no control is unmanaged, whether or not it has failed yet."),

                     "probe": "state what already prevents or detects each failure"},

        "actions": {"analysis": ("Actions reduce the risk of the modes that matter. An action aimed at no evidenced "

                                 "mode is a general improvement, not a control. The relevant question is which mode "

                                 "each action addresses."),

                    "qualify": ("The evidence does not establish that an action will work or what it costs, so "

                                "actions are proposals rather than results."),

                    "short": ("An action that names no failure mode cannot be shown to have reduced any risk."),

                    "probe": "state the change proposed, and which failure it addresses"},

        "owners": {"analysis": ("Ownership turns an action into work: someone is accountable and a review date "

                                "exists. The relevant question is whether each action has both."),

                   "qualify": ("The evidence does not establish that the owner has accepted or the date agreed, so "

                               "ownership is recorded as declared."),

                   "short": ("An action with no owner and no review date cannot fail visibly."),

                   "probe": "state who acts, by when, and when the risk is reviewed again"},

    },

}

#: Kraljic -----------------------------------------------------------------------

KRALJIC = {

    "template": "template_kraljic",

    "key": "kraljic",

    "label": "Kraljic purchasing portfolio",

    "title_prefix": "Kraljic Purchasing Portfolio",

    "subject": "operations",

    "unit": {

        "field": "process",

        "label": "The purchasing portfolio you are classifying",

        "help": "Name what the portfolio covers, for example the meal counter's purchases.",

        "example": "the meal counter's purchases",

        "refuse": ("Kraljic classifies one purchasing portfolio. Name what it covers, for example the meal "

                   "counter's purchases."),

    },

    "ratings": False,

    "assumption": "probe",

    "sites": None,

    "providers": None,

    "gate": {"title_context": False, "require_geography": False, "title_cue": False},

    "blocks": [

        {"key": "criteria", "label": "Criteria", "prompt": "How you judge profit impact and supply risk, and the cut-offs",

         "fill": "auto", "cues": "criteria impact risk threshold spend score", "queries": ["supply risk and profit impact criteria"],

         "category": None, "probe": "state how you judge each axis, and the cut-off you use"},

        {"key": "strategic", "label": "Strategic items", "prompt": "High impact, high risk: what they are and how they are managed",

         "fill": "auto", "cues": "strategic partnership critical sole source", "queries": ["strategic supplier management"],

         "category": None, "probe": "name the items in this quadrant, and how each is managed"},

        {"key": "leverage", "label": "Leverage items", "prompt": "High impact, low risk: what they are and how they are managed",

         "fill": "auto", "cues": "leverage tender price competition many suppliers", "queries": ["competitive tendering for leverage items"],

         "category": None, "probe": "name the items in this quadrant, and how each is managed"},

        {"key": "bottleneck", "label": "Bottleneck items", "prompt": "Low impact, high risk: what they are and how they are managed",

         "fill": "auto", "cues": "bottleneck scarce security supply single source", "queries": ["managing scarce supply and bottlenecks"],

         "category": None, "probe": "name the items in this quadrant, and how each is managed"},

        {"key": "non_critical", "label": "Non-critical items", "prompt": "Low impact, low risk: what they are and how they are managed",

         "fill": "auto", "cues": "non critical routine standard catalogue", "queries": ["efficient purchasing of routine items"],

         "category": None, "probe": "name the items in this quadrant, and how each is managed"},

    ],

    "outline": {

        "framework": "Kraljic purchasing portfolio", "context": "The portfolio and its criteria",

        "discussion": "What the evidence shows about the portfolio",

        "implications": "Implications for the sourcing decision",

        "limitations": "Limitations", "conclusion": "Conclusion",

        "lead": ("The Kraljic portfolio classifies purchases by their profit impact and their supply risk, then "

                 "records how each class is managed. The criteria are declared first, then each quadrant, first "

                 "through the evidence accepted for the case and then through what it implies."),

    },

    "voice": {

        "thesis_question": "whether the declared classification supports the sourcing the decision proposes",

        "unit_noun": "portfolio", "block_plural": "quadrants",

        "lens": "the trade-off between profit impact and supply risk for each item",

        "closing": "identifies the quadrant the portfolio depends on most and the quadrant the evidence cannot settle",

        "intro_frame": ("The unit of analysis is the purchasing portfolio, because the matrix classifies items "

                        "rather than the firm."),

        "context_frame": ("The relevant portfolio is the one named in the brief; the quadrants are properties of "

                          "those items rather than of the organisation."),

        "interaction": ("Read together, the quadrants describe a portfolio in which some items are evidenced and "

                        "others are not, and a quadrant without evidence cannot be treated as covered."),

        "implication_frame": ("A sourcing decision has to answer the class the evidence supports: strategic items "

                              "need partnership, leverage items need competition, bottleneck items need security."),

        "reference_heading": "References",

    },

    "notes": {

        "criteria": {"analysis": ("The two axes are judgements, so the criteria and their cut-offs have to be "

                                  "declared before the placement means anything. The relevant question is whether the "

                                  "cut-off is stated."),

                     "qualify": ("The evidence does not establish spend or risk scores, so the criteria are declared "

                                 "rather than measured."),

                     "short": ("A placement with no declared cut-off is an opinion about a grid."),

                     "probe": "state how you judge each axis, and the cut-off you use"},

        "strategic": {"analysis": ("Strategic items are high impact and high risk: they matter to the offer and "

                                   "their supply is not secure. They call for partnership and joint planning. The "

                                   "relevant question is whether the named items meet both tests."),

                      "qualify": ("The evidence does not establish the spend or the alternatives, so the class is "

                                  "declared rather than measured."),

                      "short": ("Strategic items are managed through the relationship, not through the price list."),

                      "probe": "name the items in this quadrant, and how each is managed"},

        "leverage": {"analysis": ("Leverage items are high impact but low risk: several sources can supply them, so "

                                  "competition is available. The relevant question is whether the competition is "

                                  "actually used."),

                     "qualify": ("The evidence does not establish how many suppliers could serve, so the class is "

                                 "declared rather than measured."),

                     "short": ("Leverage exists only where the buyer actually runs the competition."),

                     "probe": "name the items in this quadrant, and how each is managed"},

        "bottleneck": {"analysis": ("Bottleneck items are low impact but high risk: few sources, and a shortage stops "

                                    "something. They call for security of supply rather than price. The relevant "

                                    "question is whether a substitute or a buffer exists."),

                       "qualify": ("The evidence does not establish the probability or cost of a shortage, so the "

                                   "class is declared rather than measured."),

                       "short": ("A bottleneck is managed by securing supply, not by negotiating the price down."),

                       "probe": "name the items in this quadrant, and how each is managed"},

        "non_critical": {"analysis": ("Non-critical items are low impact and low risk: routine buying is enough. The "

                                      "relevant question is whether the effort spent on them exceeds their value."),

                         "qualify": ("The evidence does not establish spend or volume, so the class is declared "

                                     "rather than measured."),

                         "short": ("Routine items are managed by making them cheap to buy, not by studying them."),

                         "probe": "name the items in this quadrant, and how each is managed"},

    },

}

#: Sales and operations planning -------------------------------------------------

SALES_AND_OPERATIONS = {

    "template": "template_sop",

    "key": "sop",

    "label": "Sales and operations planning",

    "title_prefix": "Sales and Operations Planning Analysis",

    "subject": "operations",

    "unit": {

        "field": "process",

        "label": "The plan you are reconciling",

        "help": "Name the product, service or line the plan covers, for example the meal counter's lunch service.",

        "example": "the meal counter's lunch service",

        "refuse": ("S&OP reconciles one plan. Name the product, service or line it covers, for example the meal "

                   "counter's lunch service."),

    },

    "ratings": False,

    "assumption": "probe",

    "sites": None,

    "providers": None,

    "gate": {"title_context": False, "require_geography": False, "title_cue": False},

    "blocks": [

        {"key": "demand_plan", "label": "Demand plan", "prompt": "The demand the chain is planning for, and its basis",

         "fill": "auto", "cues": "demand forecast sales volume customers", "queries": ["demand planning and forecast basis"],

         "category": None, "probe": "state the demand you plan for, and what it is based on"},

        {"key": "supply_plan", "label": "Supply plan", "prompt": "What supply can deliver, and the constraints on it",

         "fill": "auto", "cues": "supply production capacity deliver constraint", "queries": ["supply planning and constraints"],

         "category": None, "probe": "state what supply can deliver, and what limits it"},

        {"key": "inventory_plan", "label": "Inventory plan", "prompt": "The stock the plan holds, and why",

         "fill": "auto", "cues": "inventory stock buffer safety days", "queries": ["inventory policy and buffers"],

         "category": None, "probe": "state the stock the plan holds, and why"},

        {"key": "capacity_plan", "label": "Capacity plan", "prompt": "The capacity the plan assumes, and where it binds",

         "fill": "auto", "cues": "capacity resource hours equipment staffing", "queries": ["capacity planning and bottlenecks"],

         "category": None, "probe": "state the capacity assumed, and where it binds"},

        {"key": "financial_plan", "label": "Financial plan", "prompt": "The revenue, cost and margin the plan implies",

         "fill": "auto", "cues": "revenue cost margin budget profit financial plan", "queries": ["financial plan implied by an operations plan"],

         "category": None, "probe": "state the revenue, cost and margin the plan implies"},

        {"key": "decisions", "label": "Gaps and decisions", "prompt": "Where the plans disagree, and the decision taken",

         "fill": "auto", "cues": "gap conflict decision reconcile reconciling demand supply plans trade off", "queries": ["reconciling demand and supply plans"],

         "category": None, "probe": "state where the plans disagree, and the decision you took"},

    ],

    "outline": {

        "framework": "Sales and operations planning", "context": "The plan and its scope",

        "discussion": "What the evidence shows about the plan",

        "implications": "Implications for the decision the plan requires",

        "limitations": "Limitations", "conclusion": "Conclusion",

        "lead": ("Sales and operations planning reconciles five plans - demand, supply, inventory, capacity and "

                 "financial - into one set of decisions. Each is treated in turn, then the disagreements are named "

                 "and the decision recorded."),

    },

    "voice": {

        "thesis_question": "whether the five plans can be reconciled without the decision the case avoids",

        "unit_noun": "plan", "block_plural": "plans",

        "lens": "the fit between demand, supply, inventory, capacity and the financial result",

        "closing": "identifies the plan that constrains the others and the plan the evidence cannot settle",

        "intro_frame": ("The unit of analysis is one plan, because S&OP reconciles the functions of one product or "

                        "line rather than the firm as a whole."),

        "context_frame": ("The relevant plan is the one named in the brief; the plans are properties of that product "

                          "or line rather than of the organisation."),

        "interaction": ("Read together, the plans describe a decision in which some figures are evidenced and others "

                        "are not, and a plan without evidence cannot be treated as agreed."),

        "implication_frame": ("A decision has to reconcile the plans the evidence shows: demand must be met by "

                              "supply, capacity must exist where it binds, and the financial result must survive."),

        "reference_heading": "References",

    },

    "notes": {

        "demand_plan": {"analysis": ("The demand plan is the quantity the other plans are sized against. Its basis "

                                     "matters more than its precision. The relevant question is whether it is a "

                                     "forecast or a hope."),

                        "qualify": ("The evidence does not establish the forecast error, so the plan is described "

                                    "rather than tested."),

                        "short": ("A demand plan with no basis is a target wearing a forecast's clothes."),

                        "probe": "state the demand you plan for, and what it is based on"},

        "supply_plan": {"analysis": ("The supply plan is what the operation can actually deliver. Where it is set by "

                                     "a constraint, the constraint is the plan. The relevant question is whether "

                                     "supply can meet demand."),

                        "qualify": ("The evidence does not establish yield or lead time, so supply is described rather "

                                    "than measured."),

                        "short": ("Supply is a capability statement, not an intention."),

                        "probe": "state what supply can deliver, and what limits it"},

        "inventory_plan": {"analysis": ("Inventory buffers the gap between demand and supply, at a cost. The "

                                        "relevant question is whether the stock held is the cheapest way to cover the "

                                        "variability the plan faces."),

                           "qualify": ("The evidence does not establish holding cost or service level, so the stock "

                                       "is described rather than costed."),

                           "short": ("Inventory buys continuity with cash, and the plan should say which it is buying."),

                           "probe": "state the stock the plan holds, and why"},

        "capacity_plan": {"analysis": ("Capacity is what the operation can produce in the period. Where one resource "

                                       "binds, the plan is only as large as that resource. The relevant question is "

                                       "whether capacity exists where the demand falls."),

                          "qualify": ("The evidence does not establish the capacity of each resource, so the plan is "

                                      "described rather than measured."),

                          "short": ("Capacity that exists in the wrong period is capacity the plan cannot use."),

                          "probe": "state the capacity assumed, and where it binds"},

        "financial_plan": {"analysis": ("The financial plan is the revenue, cost and margin the operations plan "

                                        "implies. A plan that operations can deliver but finance cannot fund is not "

                                        "reconciled. The relevant question is whether the margin survives the plan."),

                           "qualify": ("The evidence does not establish prices or costs, so the result is described "

                                       "rather than projected."),

                           "short": ("A plan operations can deliver and finance cannot fund is not a plan."),

                           "probe": "state the revenue, cost and margin the plan implies"},

        "decisions": {"analysis": ("The decision is where the plans disagree and someone chooses. Naming the "

                                   "disagreement is the point of the exercise; hiding it is what the meeting exists "

                                   "to prevent. The relevant question is whether the decision is recorded with its "

                                   "trade-off."),

                      "qualify": ("The evidence does not establish who decided or on what authority, so the decision "

                                  "is recorded as declared."),

                      "short": ("A disagreement left unnamed is a decision made by default."),

                      "probe": "state where the plans disagree, and the decision you took"},

    },

}

#: PDCA --------------------------------------------------------------------------

PDCA = {

    "template": "template_pdca",

    "key": "pdca",

    "label": "PDCA",

    "title_prefix": "PDCA Improvement Analysis",

    "subject": "operations",

    "unit": {

        "field": "process",

        "label": "The change you are testing",

        "help": "Name the change and where it is tried, for example moving packing away from the order point.",

        "example": "moving packing away from the order point",

        "refuse": ("PDCA tests one change. Name the change and where it is tried, for example moving packing away "

                   "from the order point."),

    },

    "ratings": False,

    "assumption": "probe",

    "sites": None,

    "providers": None,

    "gate": {"title_context": False, "require_geography": False, "title_cue": False},

    "blocks": [

        {"key": "plan", "label": "Plan", "prompt": "The problem, the target and the change you will try",

         "fill": "auto", "cues": "plan problem target hypothesis change try", "queries": ["planning a process change and its target"],

         "category": None, "probe": "state the problem, the target and the change you will try"},

        {"key": "do", "label": "Do", "prompt": "What was actually done, on what scale, and when",

         "fill": "auto", "cues": "do trial pilot implement ran week scale", "queries": ["running a small-scale process trial"],

         "category": None, "probe": "state what was done, on what scale, and when"},

        {"key": "check", "label": "Check", "prompt": "What the measure showed, against the target",

         "fill": "auto", "cues": "check measure measuring result compare data before after effect change", "queries": ["measuring the effect of a process change"],

         "category": None, "probe": "state what the measure showed, against the target"},

        {"key": "act", "label": "Act", "prompt": "What is standardised, changed or abandoned, and what happens next",

         "fill": "auto", "cues": "act standardise adopt abandon next scale", "queries": ["standardising or abandoning a process change"],

         "category": None, "probe": "state what is standardised, changed or abandoned, and what happens next"},

    ],

    "outline": {

        "framework": "PDCA", "context": "The change and where it is tried",

        "discussion": "What the evidence shows about the change",

        "implications": "Implications for the decision the result supports",

        "limitations": "Limitations", "conclusion": "Conclusion",

        "lead": ("PDCA tests one change: the plan states the problem, target and change; the do records what was "

                 "actually tried; the check compares the measure with the target; the act standardises or abandons. "

                 "Each stage is treated in turn, first through the evidence accepted for the case."),

    },

    "voice": {

        "thesis_question": "whether the measured effect supports standardising the change",

        "unit_noun": "change", "block_plural": "stages",

        "lens": "the distance between the target and what the measure actually showed",

        "closing": "identifies the stage the evidence supports most and the stage the evidence cannot settle",

        "intro_frame": ("The unit of analysis is one change, because PDCA tests a specific intervention in a "

                        "specific flow rather than a programme."),

        "context_frame": ("The relevant change is the one named in the brief; the stages are properties of that "

                          "trial rather than of the organisation."),

        "interaction": ("Read together, the stages describe a trial in which some conditions are evidenced and "

                        "others are not, and a stage without evidence cannot be treated as complete."),

        "implication_frame": ("A decision to standardise has to answer the stages the evidence shows: the plan must "

                              "state a target, the check must measure it, and the act must follow the result."),

        "reference_heading": "References",

    },

    "notes": {

        "plan": {"analysis": ("The plan states the problem, the target and the change, so the trial can fail "

                              "usefully. A plan with no target cannot be checked. The relevant question is whether "

                              "the target is measurable."),

                 "qualify": ("The evidence does not establish the target's basis, so it is declared rather than "

                             "forecast."),

                 "short": ("A trial with no target cannot fail, and therefore cannot teach anything."),

                 "probe": "state the problem, the target and the change you will try"},

        "do": {"analysis": ("The do records what was actually done, on what scale and when, because a trial that "

                            "drifts from its plan tests something else. The relevant question is whether the record "

                            "matches the plan."),

               "qualify": ("The evidence does not establish that the trial ran as designed, so what was done is "

                           "recorded as declared."),

               "short": ("A trial that changed two things at once has tested neither."),

               "probe": "state what was done, on what scale, and when"},

        "check": {"analysis": ("The check compares the measure with the target on the same basis as the baseline. "

                               "A comparison on a different basis proves nothing. The relevant question is whether "

                               "the measure is the one the target named."),

                  "qualify": ("The evidence establishes an association between the change and the measure, not "

                              "causation, because other things also changed."),

                  "short": ("A measure compared on a different basis from the baseline is not a comparison."),

                  "probe": "state what the measure showed, against the target"},

        "act": {"analysis": ("The act decides the next state: standardise, adjust and repeat, or abandon. The "

                             "relevant question is whether the decision follows the result."),

                "qualify": ("The evidence does not establish that the effect will hold at a larger scale, so the "

                            "decision is declared rather than proven."),

                "short": ("A result that is not standardised, adjusted or abandoned has not been acted on."),

                "probe": "state what is standardised, changed or abandoned, and what happens next"},

    },

}

#: SWOT / TOWS -----------------------------------------------------------------

SWOT = {

    "template": "template_swot",

    "key": "swot",

    "label": "SWOT / TOWS",

    "title_prefix": "SWOT Analysis",

    "subject": "management",

    "unit": {

        "field": "industry",

        "label": "Industry or market",

        "help": "SWOT is written against an industry or market, not a company alone.",

        "example": "smartphones, grocery retail, banking",

        "refuse": ("SWOT analyses an industry or market. Name the industry or market, or the company and the market it "

                   "competes in."),

    },

    "ratings": False,

    "assumption": "probe",

    "sites": "industry",

    "providers": ["brave", "deepseek", "firecrawl"],

    "gate": {"title_cue": True, "title_context": True, "require_geography": False},

    "blocks": [

        {"key": "S", "label": "Strengths", "prompt": "Internal strengths", "fill": "quote",

         "cues": "strength advantage capability resource brand loyal efficient leader patent quality skill",

         "probe": "state the strengths you can evidence from your own position"},

        {"key": "W", "label": "Weaknesses", "prompt": "Internal weaknesses", "fill": "quote",

         "cues": "weakness disadvantage constraint shortage cost debt dependency capacity inefficiency gap",

         "probe": "state the weaknesses you can evidence from your own position"},

        {"key": "O", "label": "Opportunities", "prompt": "External opportunities", "fill": "auto",

         "cues": "opportunity growth demand expansion trend technology policy support market",

         "queries": ["growth and demand opportunities in this industry"], "category": "economic",

         "probe": "state the opportunity and the evidence behind it"},

        {"key": "T", "label": "Threats", "prompt": "External threats", "fill": "auto",

         "cues": "threat competitor competition substitute regulation risk downturn tariff entry",

         "queries": ["threats and competitive pressure in this industry"], "category": None,

         "probe": "state the threat and the evidence behind it"},

    ],

    "outline": {

        "framework": "SWOT", "context": "The case and its market",

        "discussion": "What the evidence shows",

        "implications": "Implications for the decision",

        "limitations": "Limitations", "conclusion": "Conclusion",

        "lead": ("SWOT organises the internal strengths and weaknesses and the external opportunities and threats "

                 "of a case. Each quadrant is treated in turn, first through the evidence accepted and then through "

                 "what it implies."),

    },

    "voice": {

        "thesis_question": "whether the evidence supports the position the case proposes",

        "unit_noun": "market", "block_plural": "quadrants",

        "lens": "the fit between what the case can do and what the market offers or threatens",

        "closing": "identifies the quadrant the case depends on most and the one the evidence cannot settle",

        "intro_frame": ("The unit of analysis is the market the case competes in, because strengths and "

                        "weaknesses only matter against the opportunities and threats that exist."),

        "context_frame": ("The relevant market is the one named in the brief; the quadrants are properties of "

                          "that case in that market rather than of either alone."),

        "interaction": ("Read together, the quadrants describe a position in which some conditions are "

                        "evidenced and others are not, and a quadrant without evidence carries no weight."),

        "implication_frame": ("A viable position must answer the conditions the evidenced quadrants impose: "

                              "strengths used against threats, weaknesses addressed by opportunities."),

        "reference_heading": "References",

    },

    "notes": {

        "S": {"analysis": ("Strengths are internal capabilities the case can deploy. They only matter against the "

                           "market's opportunities and threats. The relevant question is whether the strength is "

                           "one the market values."),

              "qualify": ("The evidence does not establish how the strength performs against rivals, so it is "

                          "recorded rather than proven."),

              "short": ("A strength the market does not value is a capability, not an advantage."),

              "probe": "state the strengths you can evidence from your own position"},

        "W": {"analysis": ("Weaknesses are internal gaps the case must close or work around. The relevant "

                           "question is whether the weakness is one a competitor or a market condition would "

                           "exploit."),

              "qualify": ("The evidence does not establish the cost of the weakness, so it is recorded rather than "

                          "costed."),

              "short": ("A weakness a competitor can exploit is a constraint on the plan."),

              "probe": "state the weaknesses you can evidence from your own position"},

        "O": {"analysis": ("Opportunities are external conditions the case could use. They are not strengths until "

                           "the case can act on them. The relevant question is whether the opportunity is one the "

                           "case can reach."),

              "qualify": ("The evidence does not establish the timing or the size of the opportunity, so it is "

                          "described rather than forecast."),

              "short": ("An opportunity the case cannot reach is a description of the market, not a plan."),

              "probe": "state the opportunity and the evidence behind it"},

        "T": {"analysis": ("Threats are external conditions that could harm the case. They are not weaknesses "

                           "until the case is exposed to them. The relevant question is whether the threat is one "

                           "the plan can survive."),

              "qualify": ("The evidence does not establish the likelihood or the timing of the threat, so it is "

                          "described rather than forecast."),

              "short": ("A threat the plan cannot survive is a limit on what the plan can promise."),

              "probe": "state the threat and the evidence behind it"},

    },

}

#: Value Chain -------------------------------------------------------------------

VALUE_CHAIN = {

    "template": "template_value_chain",

    "key": "value_chain",

    "label": "Porter's Value Chain",

    "title_prefix": "Porter's Value Chain",

    "subject": "management",

    "unit": {

        "field": "industry",

        "label": "Industry or market",

        "help": "Value chain evidence is industry-specific. Name the industry or market.",

        "example": "smartphones, grocery retail, banking",

        "refuse": ("Value chain analysis examines an industry's activities. Name the industry or market."),

    },

    "ratings": False,

    "assumption": "probe",

    "sites": "industry",

    "providers": ["brave", "deepseek", "firecrawl"],

    "gate": {"title_cue": True, "title_context": True, "require_geography": False},

    "blocks": [

        {"key": "firm_infrastructure", "label": "Firm infrastructure", "prompt": "Planning, finance, legal, quality",

         "fill": "research", "cues": "infrastructure support overhead administrative firm planning finance legal "

                  "quality governance management",

         "queries": ["firm infrastructure and support activities",

                     "administrative overhead and support functions in this industry"], "category": None,

         "probe": "state the evidence about infrastructure in this industry"},

        {"key": "human_resource_management", "label": "Human resource management", "prompt": "Recruiting, developing, rewarding",

         "fill": "research", "cues": "human resource labour recruitment training skill wage",

         "queries": ["human resource management and skills in this industry"], "category": None,

         "probe": "state the evidence about people and skills in this industry"},

        {"key": "technology_development", "label": "Technology development", "prompt": "Product, process and information technology",

         "fill": "research", "cues": "technology innovation research development automation digital",

         "queries": ["technology and innovation in this industry"], "category": "technological",

         "probe": "state the evidence about technology in this industry"},

        {"key": "procurement", "label": "Procurement", "prompt": "How inputs are bought",

         "fill": "research", "cues": "procurement purchasing sourcing supplier cost",

         "queries": ["procurement and sourcing in this industry"], "category": None,

         "probe": "state the evidence about procurement in this industry"},

        {"key": "inbound_logistics", "label": "Inbound logistics", "prompt": "Receiving, storing and moving inputs",

         "fill": "research", "cues": "inbound logistics receiving storage transport supply",

         "queries": ["inbound logistics in this industry"], "category": None,

         "probe": "state the evidence about inbound logistics in this industry"},

        {"key": "operations", "label": "Operations", "prompt": "Turning inputs into the product or service",

         "fill": "research", "cues": "operations production manufacturing assembly process",

         "queries": ["operations and production in this industry"], "category": None,

         "probe": "state the evidence about operations in this industry"},

        {"key": "outbound_logistics", "label": "Outbound logistics", "prompt": "Storing and delivering the finished offer",

         "fill": "research", "cues": "outbound logistics distribution delivery warehouse",

         "queries": ["outbound logistics and distribution in this industry"], "category": None,

         "probe": "state the evidence about outbound logistics in this industry"},

        {"key": "marketing_and_sales", "label": "Marketing and sales", "prompt": "Winning customers and setting the offer",

         "fill": "research", "cues": "marketing sales customer acquisition pricing channel",

         "queries": ["marketing and sales in this industry"], "category": None,

         "probe": "state the evidence about marketing and sales in this industry"},

        {"key": "service", "label": "Service", "prompt": "Installing, supporting and keeping the offer working",

         "fill": "research", "cues": "service support maintenance customer care",

         "queries": ["service and support in this industry"], "category": None,

         "probe": "state the evidence about service in this industry"},

    ],

    "outline": {

        "framework": "Porter's Value Chain", "context": "Case and market context",

        "discussion": "What the evidence shows",

        "implications": "Implications for the decision",

        "limitations": "Limitations", "conclusion": "Conclusion",

        "lead": ("Porter's Value Chain examines the primary and support activities through which an industry "

                 "creates value. Each activity is treated in turn, first through the evidence accepted and then "

                 "through what it implies."),

    },

    "voice": {

        "thesis_question": "whether the activities the evidence supports give the case a position",

        "unit_noun": "industry", "block_plural": "activities",

        "lens": "the activities through which value is created and where it is lost",

        "closing": "identifies the activity the case depends on most and the one the evidence cannot settle",

        "intro_frame": ("The unit of analysis is the industry rather than the firm, because the value chain "

                        "describes the activities any competitor must perform."),

        "context_frame": ("The relevant industry is the one named in the brief; the activities are properties of "

                          "that industry rather than of a single firm."),

        "interaction": ("Read together, the activities describe an industry in which some are evidenced and "

                        "others are not, and an activity without evidence carries no weight."),

        "implication_frame": ("A position must be built on the activities the evidence shows: the ones that "

                              "create value and the ones that destroy it."),

        "reference_heading": "References",

    },

    "notes": {

        block: {

            "analysis": ("This activity is one of the nine through which the industry creates value. The relevant "

                         "question is whether the evidence shows it as a source of advantage or of cost."),

            "qualify": ("The evidence does not establish the cost or the contribution of this activity, so it is "

                        "described rather than measured."),

            "short": ("An activity described without evidence is a label, not a finding."),

            "probe": "state the evidence about this activity in this industry",

        }

        for block in ("firm_infrastructure", "human_resource_management", "technology_development",

                      "procurement", "inbound_logistics", "operations", "outbound_logistics",

                      "marketing_and_sales", "service")

    },

}

#: Ansoff ----------------------------------------------------------------------

ANSOFF = {

    "template": "template_ansoff",

    "key": "ansoff",

    "label": "Ansoff Growth Matrix",

    "title_prefix": "Ansoff Growth Matrix Analysis",

    "subject": "management",

    "unit": {

        "field": "industry",

        "label": "Industry or market",

        "help": "Ansoff places growth options on a market. Name the industry or market.",

        "example": "smartphones, grocery retail, banking",

        "refuse": ("Ansoff classifies growth options against a market. Name the industry or market."),

    },

    "ratings": False,

    "assumption": "probe",

    "sites": "industry",

    "providers": ["brave", "deepseek", "firecrawl"],

    "gate": {"title_cue": True, "title_context": True, "require_geography": False},

    "blocks": [

        {"key": "market_penetration", "label": "Market penetration", "prompt": "Existing products in existing markets",

         "fill": "research", "cues": "penetration share promotion pricing existing customers frequency",

         "queries": ["market penetration strategy in this industry"], "category": None,

         "probe": "state the evidence for penetrating the existing market further"},

        {"key": "market_development", "label": "Market development", "prompt": "Existing products in new markets",

         "fill": "research", "cues": "development new market export segment expansion distribution",

         "queries": ["market development and new market entry in this industry"], "category": None,

         "probe": "state the evidence for taking the product to new markets"},

        {"key": "product_development", "label": "Product development", "prompt": "New products in existing markets",

         "fill": "research", "cues": "product development innovation research development feature",

         "queries": ["product development and innovation in this industry"], "category": None,

         "probe": "state the evidence for developing new products for this market"},

        {"key": "diversification", "label": "Diversification", "prompt": "New products in new markets",

         "fill": "research", "cues": "diversification new business acquisition unrelated",

         "queries": ["diversification strategy in this industry"], "category": None,

         "probe": "state the evidence for diversifying into new markets"},

    ],

    "outline": {

        "framework": "Ansoff", "context": "The case and its market",

        "discussion": "What the evidence shows",

        "implications": "Implications for the decision",

        "limitations": "Limitations", "conclusion": "Conclusion",

        "lead": ("Ansoff classifies growth options by whether they use existing or new products and existing or "

                 "new markets. Each cell is treated in turn, first through the evidence and then through what it "

                 "implies."),

    },

    "voice": {

        "thesis_question": "whether the evidence supports the growth option the decision proposes",

        "unit_noun": "market", "block_plural": "cells",

        "lens": "the product and market each option uses, and the risk it carries",

        "closing": "identifies the option the evidence supports most and the one it cannot settle",

        "intro_frame": ("The unit of analysis is the market, because the matrix classifies options against the "

                        "market the case already serves."),

        "context_frame": ("The relevant market is the one named in the brief; the cells are properties of the "

                          "options available in that market."),

        "interaction": ("Read together, the cells describe options in which some are evidenced and others are "

                        "not, and an option without evidence cannot be treated as viable."),

        "implication_frame": ("A growth decision has to answer the cell the evidence supports: penetrating, "

                              "developing, product or diversification."),

        "reference_heading": "References",

    },

    "notes": {

        block: {

            "analysis": ("This cell places a growth option on the product and market it uses. The relevant "

                         "question is whether the evidence shows the option to be available and attractive."),

            "qualify": ("The evidence does not establish the size or the risk of the option, so it is described "

                        "rather than measured."),

            "short": ("A cell with no evidence is an option that has not been tested."),

            "probe": "state the evidence for this growth option",

        }

        for block in ("market_penetration", "market_development", "product_development", "diversification")

    },
}


#: VRIO ----------------------------------------------------------------

VRIO = {
    "template": "template_vrio",
    "key": "vrio",
    "label": "VRIO",
    "title_prefix": "VRIO Analysis",
    "subject": "management",
    "unit": {
        "field": "industry",
        "label": "Industry or market",
        "help": "VRIO evaluates resources against an industry's competitors. Name the industry or market.",
        "example": "smartphones, grocery retail, banking",
        "refuse": ("VRIO evaluates resources against an industry's competitors. Name the industry or market."),
    },
    "ratings": False,
    "assumption": "probe",
    "sites": "industry",
    "providers": ["brave", "deepseek", "firecrawl"],
    "gate": {"title_cue": True, "title_context": True, "require_geography": False},
    "blocks": [
        {"key": "valuable", "label": "Valuable", "prompt": "Does the resource enable the firm to exploit an opportunity or neutralise a threat?",
         "fill": "research", "cues": "valuable resource opportunity threat exploit competitive advantage",
         "queries": ["valuable resources and capabilities in this industry"],
         "category": None, "probe": "state the resource and the opportunity or threat it addresses"},
        {"key": "rare", "label": "Rare", "prompt": "Is it held by few current or potential competitors?",
         "fill": "research", "cues": "rare resource competitors scarcity uncommon",
         "queries": ["rare resources and capabilities in this industry"],
         "category": None, "probe": "state the resource and how few competitors hold it"},
        {"key": "costly_to_imitate", "label": "Costly to imitate", "prompt": "Would competitors face a cost or difficulty in imitating it?",
         "fill": "research", "cues": "costly to imitate difficult copy barrier entry",
         "queries": ["costly-to-imitate resources and capabilities in this industry"],
         "category": None, "probe": "state the resource and why it is hard to imitate"},
        {"key": "organized", "label": "Organized to capture value", "prompt": "Do the firm's structure and processes let it capture the value?",
         "fill": "research", "cues": "organized capture value structure process management",
         "queries": ["organization and structure to capture value in this industry"],
         "category": None, "probe": "state how the firm is organized to capture the value"},
    ],    "outline": {
        "framework": "VRIO", "context": "The case and its industry",
        "discussion": "What the evidence shows",
        "implications": "Implications for the decision",
        "limitations": "Limitations", "conclusion": "Conclusion",
        "lead": ("VRIO evaluates a firm's resources against four tests - valuable, rare, costly to imitate and organized to capture value. "
                 "Each test is treated in turn, first through the evidence and then through what it implies."),
    },
    "voice": {
        "thesis_question": "whether the evidence supports the resources the decision relies on",
        "unit_noun": "industry", "block_plural": "tests",
        "lens": "the resources a firm holds, and how each passes the four tests",
        "closing": "identifies the test the evidence supports most and the one it cannot settle",
        "intro_frame": ("The unit of analysis is the industry, because VRIO evaluates resources against an industry's competitors."),
        "context_frame": ("The relevant industry is the one named in the brief; the tests are properties of the resource in that industry."),
        "interaction": ("Read together, the tests describe a resource in which some evidence is present and some is not, "
                        "and a test without evidence carries no weight."),
        "implication_frame": ("A sustained advantage has to answer the tests the evidence supports: what is valuable, rare, "
                              "costly to imitate and organized to capture value."),
        "reference_heading": "References",
    },
    "notes": {
        "valuable": {"analysis": ("Valuable means the resource enables the firm to exploit an opportunity or neutralise a threat. "
                                  "The relevant question is whether the evidence shows it doing either."),
                     "qualify": ("The evidence does not establish the size of the opportunity or threat, so the resource is "
                                 "described rather than measured."),
                     "short": ("A resource is valuable only relative to an opportunity or a threat."),
                     "probe": "state the resource and the opportunity or threat it addresses"},
        "rare": {"analysis": ("Rare means the resource is held by few current or potential competitors. The relevant question "
                              "is whether the evidence shows scarcity."),
                 "qualify": ("The evidence does not establish how many competitors hold it, so rarity is declared rather than counted."),
                 "short": ("A resource that everyone holds is a condition of competing, not an advantage."),
                 "probe": "state the resource and how few competitors hold it"},
        "costly_to_imitate": {"analysis": ("Costly to imitate means competitors face a cost or difficulty in copying the resource. "
                                           "The relevant question is whether the evidence shows such a barrier."),
                            "qualify": ("The evidence does not establish the cost of imitation, so the barrier is described "
                                        "rather than measured."),
                            "short": ("A resource that is easy to copy is a temporary advantage."),
                            "probe": "state the resource and why it is hard to imitate"},
        "organized": {"analysis": ("Organized to capture value means the firm's structure and processes let it exploit the resource. "
                                   "The relevant question is whether the evidence shows such organization."),
                      "qualify": ("The evidence does not establish how decisions are made or how value is captured, so the "
                                  "organization is described rather than assessed."),
                      "short": ("A valuable resource that the firm cannot capture is a missed opportunity."),
                      "probe": "state how the firm is organized to capture the value"},
    },
}

ADKAR = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'awareness change needed why now',
             'fill': 'research',
             'key': 'awareness',
             'label': 'Awareness',
             'probe': 'state the evidence why the change is needed',
             'prompt': 'Why the change is needed and why now',
             'queries': ['awareness and why the change is needed']},
            {'category': None,
             'cues': 'desire benefit gain adopt',
             'fill': 'research',
             'key': 'desire',
             'label': 'Desire',
             'probe': 'state the evidence for desire',
             'prompt': 'Why change matters and what people gain',
             'queries': ['desire and benefits of change']},
            {'category': None,
             'cues': 'knowledge know how taught training',
             'fill': 'research',
             'key': 'knowledge',
             'label': 'Knowledge',
             'probe': 'state the evidence for knowledge',
             'prompt': 'What people need to know and how they are taught',
             'queries': ['knowledge and skills needed for change']},
            {'category': None,
             'cues': 'ability do differently skills enable',
             'fill': 'research',
             'key': 'ability',
             'label': 'Ability',
             'probe': 'state the evidence for ability',
             'prompt': 'What people must do differently',
             'queries': ['ability and enabling factors for change']},
            {'category': None,
             'cues': 'reinforcement sustain change stick',
             'fill': 'research',
             'key': 'reinforcement',
             'label': 'Reinforcement',
             'probe': 'state the evidence for reinforcement',
             'prompt': 'What makes the change stick',
             'queries': ['reinforcement and sustainment for change']}],
 'gate': {'require_geography': False, 'title_context': False, 'title_cue': False},
 'key': 'adkar',
 'label': 'ADKAR',
 'notes': {
           'ability': {
                       'analysis': 'Ability is the practical capacity to do the new work: the time, the tools, the '
                                   'authority and the resources it takes. A person can understand a change, support '
                                   'it and still be unable to perform it. The relevant question is whether the '
                                   'evidence shows that the people affected have the means to act.',
                       'probe': 'state what people need in order to act and what they have',
                       'qualify': 'The evidence does not establish what people are able to do, so ability is '
                                  'described rather than measured.',
                       'short': 'Willingness without capacity is a change that stalls on the first person asked to do '
                                'it differently.'},
           'awareness': {
                         'analysis': 'Awareness is the point at which a person understands that a change is coming '
                                     'and what it will mean for their own work. A programme that begins without it '
                                     'produces resistance that is usually read as reluctance rather than as the '
                                     'absence of understanding. The relevant question is whether the evidence shows '
                                     'that people know the change is coming.',
                         'probe': 'state what people have been told about the change and how they know',
                         'qualify': 'The evidence does not establish what people have been told, so awareness is '
                                    'described rather than tested.',
                         'short': 'A change announced to people who were never told is not met with resistance; it is '
                                  'met with indifference.'},
           'desire': {
                      'analysis': 'Desire is the willingness to support a change rather than to comply with it. '
                                  'People will perform a new process they are obliged to follow and will not sustain '
                                  'one they have no reason to support. The relevant question is whether the evidence '
                                  'shows what the change offers the people who are affected.',
                      'probe': 'state what the change offers the people affected and what they have said about it',
                      'qualify': 'The evidence does not establish what people want from the change, so desire is '
                                 'described rather than measured.',
                      'short': 'Compliance is what a change gets when the people affected see nothing in it for '
                               'themselves.'},
           'knowledge': {
                         'analysis': 'Knowledge is the command of what the new way of working requires. It is learned '
                                     'before the change and it is lost when the people who hold it move on. The '
                                     'relevant question is whether the evidence shows what people have been taught '
                                     'and how well they can do it.',
                         'probe': 'state what people have been taught about the new way of working and what they can '
                                  'show',
                         'qualify': 'The evidence does not establish what people have learned, so knowledge is '
                                    'described rather than tested.',
                         'short': 'A change taught once and never practised is a change waiting to fail at the first '
                                  'difficulty.'},
           'reinforcement': {
                             'analysis': 'Reinforcement is what keeps the new practice in place after the programme '
                                         'ends: the measures, the routines, the recognition and the consequences that '
                                         'follow it. Without it the change depends on the attention of the people who '
                                         'introduced it. The relevant question is whether the evidence shows what has '
                                         'been written into the way the organisation works.',
                             'probe': 'state what in the day-to-day working now carries the change',
                             'qualify': 'The evidence does not establish which routines and measures have changed, so '
                                        'reinforcement is described rather than confirmed.',
                             'short': 'A change that lives in a programme team dies with the programme team.'}
          },
 'outline': {'conclusion': 'Conclusion',
             'context': 'The change and the decision',
             'discussion': 'What the evidence shows',
             'framework': 'ADKAR',
             'implications': 'Implications for the decision',
             'lead': 'ADKAR is a five-step change model: awareness, desire, knowledge, ability and reinforcement. Each '
                     'step is examined in turn, first through the evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': None,
 'ratings': False,
 'sites': None,
 'subject': 'people',
 'template': 'template_adkar',
 'title_prefix': 'ADKAR Change Analysis',
 'unit': {'field': 'process',
          'label': 'The change you are planning',
          'help': 'A readiness review reads one programme of change. Name it in a few words, for example moving '
                  'the campus meal card to a contactless system or the restructuring of the ward rota.',
          'example': 'moving the campus meal card to a contactless system',
          'refuse': 'A readiness review reads one programme of change. Name the change you are planning, for '
                    'example moving the campus meal card to a contactless system or the restructuring of the ward '
                    'rota.'},
 'voice': {'thesis_question': 'whether the evidence supports the readiness the change depends on',
           'unit_noun': 'change',
           'block_plural': 'elements',
           'lens': 'the five elements an individual has to move through for a change to hold',
           'closing': 'identifies the element the change depends on and the element the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the change rather than the firm, because ADKAR follows one '
                          "person's movement through a change rather than the organisation's change activity in "
                          'general.',
           'context_frame': 'The relevant change is the one named in the brief; the elements belong to that change '
                            'rather than to change management in general.',
           'interaction': 'Read together, the elements show where the people affected by the change stand, and a '
                          'change can be well resourced and still fail because one element is missing.',
           'implication_frame': 'A decision about the change has to match the element the people have not reached: '
                                'investment that treats the later elements as done before the earlier ones hold '
                                'cannot be relied on.',
           'reference_heading': 'References'}}


LEWIN = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'unfreeze prepare change status quo',
             'fill': 'research',
             'key': 'unfreeze',
             'label': 'Unfreeze',
             'probe': 'state the evidence for unfreezing',
             'prompt': 'Prepare the organisation for change by undermining the existing status quo',
             'queries': ['unfreezing and preparing for change']},
            {'category': None,
             'cues': 'change move new state transition',
             'fill': 'research',
             'key': 'change',
             'label': 'Change',
             'probe': 'state the evidence for the change',
             'prompt': 'Move the organisation to a new state through the steps the change requires',
             'queries': ['change and transition']},
            {'category': None,
             'cues': 'refreeze anchor routine sustain',
             'fill': 'research',
             'key': 'refreeze',
             'label': 'Refreeze',
             'probe': 'state the evidence for refreezing',
             'prompt': 'Anchor the new state in daily routines so the change sticks',
             'queries': ['refreezing and sustaining change']}],
 'gate': {'require_geography': False, 'title_context': False, 'title_cue': False},
 'key': 'lewin',
 'label': 'Lewin',
 'notes': {
           'change': {
                      'analysis': 'Changing is the stage in which the organisation moves to the new state: the new '
                                  'processes, roles, measures and behaviours are introduced while the old ones are '
                                  'still in place. It is the least stable stage, because the organisation is carrying '
                                  'two ways of working at once. The relevant question is whether the evidence shows '
                                  'the transition.',
                      'probe': 'state the evidence for the transition and how the two states were carried together',
                      'qualify': 'The evidence does not establish the transition, so the change is described rather '
                                 'than measured.',
                      'short': 'A change without a transition plan is a proposal that people cannot act on.'},
           'refreeze': {
                        'analysis': 'Refreezing is the stage in which the new practice becomes the ordinary one: it '
                                    'is written into routines, budgets, measures and standards, and stops being '
                                    'described as new. A change that is not refrozen drifts back to the old practice. '
                                    'The relevant question is whether the evidence shows what now carries the change.',
                        'probe': 'state what anchors the new practice in daily routines',
                        'qualify': 'The evidence does not establish the reinforcement, so refreezing is described '
                                   'rather than measured.',
                        'short': 'A change without refreezing will drift back to the old way.'},
           'unfreeze': {
                        'analysis': 'Unfreezing is the stage in which the case for change is made and the existing '
                                    'practice is questioned. It is the stage most often skipped, because the pressure '
                                    'to move on to the new way of working makes the old one look settled. The '
                                    'relevant question is whether the evidence shows why the existing practice has to '
                                    'give way.',
                        'probe': 'state the evidence for unfreezing and what is at stake',
                        'qualify': 'The evidence does not establish what would be lost by not changing, so the case '
                                   'for change is described rather than sized.',
                        'short': 'A change that begins without unfreezing meets resistance at exactly the point where '
                                 'it costs most.'}
          },
 'outline': {'conclusion': 'Conclusion',
             'context': 'The change and the decision',
             'discussion': 'What the evidence shows',
             'framework': 'Lewin',
             'implications': 'Implications for the decision',
             'lead': 'Lewin"s three-step change model: unfreeze, change and refreeze. Each step is examined in turn, '
                     'first through the evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': None,
 'ratings': False,
 'sites': None,
 'subject': 'people',
 'template': 'template_lewin',
 'title_prefix': 'Lewin Change Analysis',
 'unit': {'field': 'process',
          'label': 'The change you are planning',
          'help': 'A change review reads one programme of change. Name it in a few words, for example moving the '
                  'campus meal card to a contactless system or the restructuring of the ward rota.',
          'example': 'moving the campus meal card to a contactless system',
          'refuse': 'A change review reads one programme of change. Name the change you are planning, for example '
                    'moving the campus meal card to a contactless system or the restructuring of the ward rota.'},
 'voice': {'thesis_question': 'whether the evidence supports the change programme the decision depends on',
           'unit_noun': 'change',
           'block_plural': 'stages',
           'lens': 'the three stages a change passes through: unfreezing, changing and refreezing',
           'closing': 'identifies the stage the change depends on and the stage the evidence cannot settle',
           'intro_frame': "The unit of analysis is the change rather than the firm, because Lewin's model follows "
                          'one programme through three ordered stages rather than describing change activity in '
                          'general.',
           'context_frame': 'The relevant change is the one named in the brief; the stages belong to that '
                            "programme rather than to the organisation's change activity in general.",
           'interaction': 'Read together, the stages show where the programme stands rather than a programme that '
                          'must be followed, and a change may be stalled at a stage without having failed at it.',
           'implication_frame': 'A decision about the change has to match the stage the programme has reached: the '
                                'support a programme needs at one stage is not the support it needs at another.',
           'reference_heading': 'References'}}


THEORY_OF_CHANGE = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'inputs resources conditions change effort',
             'fill': 'research',
             'key': 'inputs',
             'label': 'Inputs',
             'probe': 'state the evidence for inputs',
             'prompt': 'The resources and conditions brought to the change effort',
             'queries': ['inputs and resources for change']},
            {'category': None,
             'cues': 'activities actions interventions change',
             'fill': 'research',
             'key': 'activities',
             'label': 'Activities',
             'probe': 'state the evidence for activities',
             'prompt': 'The actions and interventions the change will carry out',
             'queries': ['activities and actions for change in this programme']},
            {'category': None,
             'cues': 'outputs products quantity results',
             'fill': 'research',
             'key': 'outputs',
             'label': 'Outputs',
             'probe': 'state the evidence for outputs',
             'prompt': 'The direct products of the activities, in expected quantity',
             'queries': ['outputs and results of change activities']},
            {'category': None,
             'cues': 'outcomes results impact change',
             'fill': 'research',
             'key': 'outcomes',
             'label': 'Outcomes',
             'probe': 'state the evidence for outcomes',
             'prompt': 'The short, medium and long-term results the change aims to achieve',
             'queries': ['outcomes and impact of change']},
            {'category': None,
             'cues': 'impact long term contribution legacy systems wellbeing sustainability',
             'fill': 'research',
             'key': 'impact',
             'label': 'Impact',
             'probe': 'state the longer-term change the programme contributes to and the evidence of its '
                      'contribution',
             'prompt': 'The longer-term change the programme is intended to contribute to',
             'queries': ['impact and long term contribution of a change programme']},
            {'category': None,
             'cues': 'assumption condition dependency external factor preconditions if not',
             'fill': 'research',
             'key': 'assumptions',
             'label': 'Assumptions',
             'probe': 'state what has to be true for each link to hold and the evidence that it does',
             'prompt': 'The conditions each link in the chain depends on',
             'queries': ['assumptions and external conditions a change programme depends on']}],
 'gate': {'require_geography': False, 'title_context': False, 'title_cue': False},
 'key': 'theory_of_change',
 'label': 'Theory of Change',
 'notes': {
           'activities': {
                          'analysis': 'Activities are the actions the programme carries out: what is done, with whom '
                                      'and how often. The relevant question is whether the evidence shows what is '
                                      'done as planned.',
                          'probe': 'state what the programme does, with whom and how often',
                          'qualify': 'The evidence does not establish what the programme actually does, so the '
                                     'pathway is described rather than assumed.',
                          'short': 'The activity in the plan and the activity delivered are often different '
                                   'activities with the same name.'},
           'assumptions': {
                           'analysis': 'Assumptions are the conditions that must hold for each link in the chain to '
                                       'work: that the people reached are the ones who need the programme, that the '
                                       'activity is delivered as designed, and that nothing else changes at the same '
                                       'time. They are the part of a theory of change most often left unstated and '
                                       'most often found to be false. The relevant question is whether the evidence '
                                       'shows the conditions that have to hold.',
                           'probe': 'state what has to be true for each link to hold and the evidence that it does',
                           'qualify': 'The evidence does not establish whether the conditions hold, so each '
                                      'assumption is named as a hypothesis rather than confirmed.',
                           'short': 'An untested assumption is a link in the chain that has never been checked and '
                                    'cannot fail loudly.'},
           'impact': {
                      'analysis': 'Impact is the longer-term change the programme is intended to contribute to, '
                                  'beyond the period it runs for and beyond the people it reaches directly. It is the '
                                  'part of the chain the programme has least control over. The relevant question is '
                                  'whether the evidence shows the contribution being made towards it.',
                      'probe': 'state the longer-term change the programme contributes to and the evidence of its '
                               'contribution',
                      'qualify': 'The evidence does not establish the contribution to the wider change, so impact is '
                                 'described rather than attributed.',
                      'short': 'A programme that claims the impact it can only contribute to will be judged on what '
                               'it did not do alone.'},
           'inputs': {
                      'analysis': 'Inputs are the resources the programme commits: the people, the money, the time, '
                                  'the partners and the premises it puts in. They say what the programme is willing '
                                  'to commit before it produces anything. The relevant question is whether the '
                                  'evidence shows what is actually committed.',
                      'probe': 'state what the programme commits and what is actually in place',
                      'qualify': 'The evidence does not establish what the programme has committed, so the pathway is '
                                 'described rather than costed.',
                      'short': 'An input that is assumed rather than committed is the first place a causal chain '
                               'quietly fails.'},
           'outcomes': {
                        'analysis': 'Outcomes are the changes the outputs are meant to have produced in the people or '
                                    'systems the programme touches: what is different for a participant, and how that '
                                    'difference is measured. The relevant question is whether the evidence shows the '
                                    'change and the measure that reads it.',
                        'probe': 'state what is different for the people the programme touches and how that is '
                                 'measured',
                        'qualify': 'The evidence does not establish the change in behaviour or wellbeing, so the '
                                   'outcome is described rather than claimed.',
                        'short': 'An output that no participant noticed is not an outcome, however well it is '
                                 'counted.'},
           'outputs': {
                       'analysis': 'Outputs are the things the activities produce and can count: sessions held, meals '
                                   'served, referrals made. They are within the programme\'s control and they are not '
                                   'yet changes in anyone\'s life. The relevant question is whether the evidence shows '
                                   'the deliverables and whether they were counted.',
                       'probe': 'state what the activities produced and whether it was counted',
                       'qualify': 'The evidence does not establish what was produced, so the pathway is described '
                                  'rather than reported.',
                       'short': 'Outputs are what the programme controls; only what follows them is a result.'}
          },
 'outline': {'conclusion': 'Conclusion',
             'context': 'The programme and the decision',
             'discussion': 'What the evidence shows',
             'framework': 'Theory of Change',
             'implications': 'Implications for the decision',
             'lead': 'A theory of change links inputs, activities, outputs and outcomes into a chain of expected '
                     'results. Each link is examined in turn, first through the evidence and then through what it '
                     'implies.',
             'limitations': 'Limitations'},
 'providers': None,
 'ratings': False,
 'sites': None,
 'subject': 'people',
 'template': 'template_theory_of_change',
 'title_prefix': 'Theory of Change Analysis',
 'unit': {'field': 'process',
          'label': 'The programme you are describing',
          'help': 'A theory of change describes one programme or intervention. Name it in a few words, for example '
                  'the campus mentoring programme or the community health outreach.',
          'example': 'the campus mentoring programme',
          'refuse': 'A theory of change describes one programme or intervention. Name the programme you are '
                    'describing, for example the campus mentoring programme or the community health outreach.'},
 'voice': {'thesis_question': 'whether the evidence supports the causal pathway the decision depends on',
           'unit_noun': 'programme',
           'block_plural': 'links',
           'lens': 'the causal links from activities through outputs and outcomes to impact, and the assumptions '
                   'each link rests on',
           'closing': 'identifies the link the pathway depends on and the link the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the programme rather than the sector, because a theory of '
                          'change is a claim about one intervention and its consequences rather than about the '
                          'field it sits in.',
           'context_frame': 'The relevant programme is the one named in the brief; the links belong to that '
                            'programme rather than to impact work in general.',
           'interaction': 'Read together, the links are a hypothesis to be tested rather than a result that has '
                          'been measured: a link with no evidence behind it is a claim the case has not earned.',
           'implication_frame': 'A decision about the programme has to match the link the evidence supports, '
                                'because a weak link in the middle of the chain makes the outcome at the end '
                                'unreachable however well the activities are run.',
           'reference_heading': 'References'}}


PDSA = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'plan change measure predict',
             'fill': 'research',
             'key': 'plan',
             'label': 'Plan',
             'probe': 'state the evidence for the plan',
             'prompt': 'What change is planned and what will be measured',
             'queries': ['planning a change and what to measure']},
            {'category': None,
             'cues': 'do carry out implement scale',
             'fill': 'research',
             'key': 'do',
             'label': 'Do',
             'probe': 'state the evidence for what was done',
             'prompt': 'What was carried out and on what scale',
             'queries': ['implementing a change and on what scale']},
            {'category': None,
             'cues': 'study results learn measure',
             'fill': 'research',
             'key': 'study',
             'label': 'Study',
             'probe': 'state the evidence for what was learned',
             'prompt': 'What the results show and what was learned',
             'queries': ['studying results and learning from change']},
            {'category': None,
             'cues': 'act adopt adapt abandon',
             'fill': 'research',
             'key': 'act',
             'label': 'Act',
             'probe': 'state the evidence for what was decided',
             'prompt': 'What is adopted, adapted or abandoned as a result',
             'queries': ['acting on results and adopting or adapting']}],
 'gate': {'require_geography': False, 'title_context': False, 'title_cue': False},
 'key': 'pdsa',
 'label': 'PDSA',
 'notes': {
           'act': {
                   'analysis': 'Acting means adopting the change, adapting it and trying again, or abandoning it, and '
                               'recording which was chosen so that the next cycle starts from a decision rather than '
                               'from the same place. The relevant question is whether the evidence shows what was '
                               'decided and what the next cycle will test.',
                   'probe': 'state what was adopted, adapted or abandoned and what the next cycle will test',
                   'qualify': 'The evidence does not establish what was decided after the cycle, so the action is '
                              'described rather than confirmed.',
                   'short': 'Without an act, a cycle ends where it began and the same test is run again next month.'},
           'do': {
                  'analysis': 'Doing the test means carrying it out as planned on a small scale, and recording what '
                              'happened as it happened rather than reconstructing it afterwards. The relevant '
                              'question is whether the evidence shows the test as it was actually run, including the '
                              'parts that were altered on the way.',
                  'probe': 'state how the test was run and what changed while it was running',
                  'qualify': 'The evidence does not establish how the test was run, so the cycle is described rather '
                             'than confirmed.',
                  'short': 'A test that is quietly changed on the day is no longer the test that was planned.'},
           'plan': {
                    'analysis': 'Planning a test means writing down what will be changed, what will be measured, what '
                                'result would count as an improvement and how long the test will run. A test with no '
                                'stated expectation cannot be learned from, because any result can be read as '
                                'success. The relevant question is whether the evidence shows the prediction that was '
                                'made before the test began.',
                    'probe': 'state what was to be changed, what was to be measured and what result was expected',
                    'qualify': 'The evidence does not establish the prediction that was set before the test, so the '
                               'cycle is described rather than judged.',
                    'short': 'A test without a prediction before it starts cannot fail, and a test that cannot fail '
                             'teaches nothing.'},
           'study': {
                     'analysis': 'Studying the results means comparing what happened with what was predicted, and '
                                 'deciding whether the difference is the test or something else. The relevant '
                                 'question is whether the evidence shows the comparison and whether the measures were '
                                 'complete enough to support it.',
                     'probe': 'state what was measured, what the prediction was and what the comparison shows',
                     'qualify': 'The evidence does not establish the comparison or whether the measures were '
                                'adequate, so the learning is described rather than claimed.',
                     'short': 'A study that cannot tell a real result from a busy week is a record, not a learning.'}
          },
 'outline': {'conclusion': 'Conclusion',
             'context': 'The test and the decision',
             'discussion': 'What the evidence shows',
             'framework': 'PDSA',
             'implications': 'Implications for the decision',
             'lead': 'PDSA is a four-step improvement cycle: plan, do, study and act. Each step is examined in turn, '
                     'first through the evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': None,
 'ratings': False,
 'sites': None,
 'subject': 'people',
 'template': 'template_pdsa',
 'title_prefix': 'PDSA Cycle Analysis',
 'unit': {'field': 'process',
          'label': 'The change you are testing',
          'help': 'A PDSA cycle tests one change. Name it in a few words, for example moving the campus meal card '
                  'to a contactless system or the new triage order in the ward.',
          'example': 'moving the campus meal card to a contactless system',
          'refuse': 'A PDSA cycle tests one change. Name the change you are testing, for example moving the campus '
                    'meal card to a contactless system or the new triage order in the ward.'},
 'voice': {'thesis_question': 'whether the evidence supports the test the decision depends on',
           'unit_noun': 'change',
           'block_plural': 'steps',
           'lens': 'the four steps of one improvement cycle, from the plan to the act that follows what the study '
                   'found',
           'closing': 'identifies the step the cycle depends on and the step the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the change rather than the firm, because PDSA tests one small '
                          'change at a time rather than assessing a programme of change as a whole.',
           'context_frame': 'The relevant change is the one named in the brief; the steps belong to that cycle '
                            'rather than to improvement activity in general.',
           'interaction': 'Read together, the steps describe one cycle of learning rather than a finished '
                          'improvement: a plan that was studied and not adopted is still a completed cycle.',
           'implication_frame': 'A decision about the change has to match what the study actually found, because a '
                                'cycle whose study was skipped leaves the next cycle resting on an untested '
                                'prediction.',
           'reference_heading': 'References'}}


DMAIC = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'define problem scope goal improvement',
             'fill': 'research',
             'key': 'define',
             'label': 'Define',
             'probe': 'state the evidence for the problem definition',
             'prompt': 'The problem, the scope and the goal of the improvement',
             'queries': ['defining the problem and scope for improvement']},
            {'category': None,
             'cues': 'measure baseline current performance data',
             'fill': 'research',
             'key': 'measure',
             'label': 'Measure',
             'probe': 'state the evidence for the measurement',
             'prompt': 'The baseline, the current performance and the data collected',
             'queries': ['measuring baseline and current performance']},
            {'category': None,
             'cues': 'analyze root cause evidence',
             'fill': 'research',
             'key': 'analyze',
             'label': 'Analyze',
             'probe': 'state the evidence for the analysis',
             'prompt': 'The root causes and the evidence behind them',
             'queries': ['analyzing root causes']},
            {'category': None,
             'cues': 'improve changes tested results',
             'fill': 'research',
             'key': 'improve',
             'label': 'Improve',
             'probe': 'state the evidence for the improvement',
             'prompt': 'The changes tested and the results they produced',
             'queries': ['improving and testing changes']},
            {'category': None,
             'cues': 'control sustain hold improvement',
             'fill': 'research',
             'key': 'control',
             'label': 'Control',
             'probe': 'state the evidence for control',
             'prompt': 'How the improvement is held in place going forward',
             'queries': ['controlling and sustaining improvement']}],
 'gate': {'require_geography': False, 'title_context': False, 'title_cue': False},
 'key': 'dmaic',
 'label': 'DMAIC',
 'notes': {
           'analyze': {
                       'analysis': 'Analyzing means finding the cause behind the measurement, by separating what the '
                                   'data shows from what is assumed about it. The relevant question is whether the '
                                   'evidence shows the root cause and the reasoning that connects it to the '
                                   'measurement.',
                       'probe': 'state what causes the measured result and what evidence connects the cause to it',
                       'qualify': 'The evidence does not establish the cause, so the analysis is described rather '
                                  'than concluded.',
                       'short': 'A cause that cannot explain the measurement is a story about the measurement.'},
           'control': {
                       'analysis': 'Controlling means putting the improved process in place and holding it: the '
                                   'measures that watch it, the standard it is held to and the person who acts when '
                                   'it drifts. The relevant question is whether the evidence shows what will hold the '
                                   'improvement once the team has moved on.',
                       'probe': 'state the measure, the standard and who acts when it drifts',
                       'qualify': 'The evidence does not establish the control measures or who acts on them, so the '
                                  'control is described rather than confirmed.',
                       'short': 'An improvement without a control is a change that only lasts while the team is '
                                'watching it.'},
           'define': {
                      'analysis': 'Defining the problem means stating what is wrong, where it is wrong, how big it is '
                                  'and who it affects, and setting the boundary of the improvement. A problem stated '
                                  'as a solution in disguise carries its own assumptions into every later step. The '
                                  'relevant question is whether the evidence shows the problem as it has been stated.',
                      'probe': 'state what is wrong, where, how much and for whom',
                      'qualify': 'The evidence does not establish the problem or its boundary, so the cycle is '
                                 'described rather than asserted.',
                      'short': 'A problem written as a solution cannot be improved, only implemented.'},
           'improve': {
                       'analysis': 'Improving means designing and testing the change that addresses the cause, and '
                                   'choosing between options on evidence rather than preference. The relevant '
                                   'question is whether the evidence shows the options considered and the reasons for '
                                   'the one chosen.',
                       'probe': 'state the options considered and the evidence behind the one chosen',
                       'qualify': 'The evidence does not establish the options considered, so the improvement is '
                                  'described rather than defended.',
                       'short': 'The strongest option is often the one that was tried, and the weakest the one that '
                                'was.'},
           'measure': {
                       'analysis': 'Measuring means establishing what happens now, in a form that can be compared '
                                   'later: the baseline, the definition of the measure and the conditions under which '
                                   'it was taken. The relevant question is whether the evidence shows the baseline '
                                   'and the measure it was taken from.',
                       'probe': 'state the baseline, the measure and the conditions it was taken under',
                       'qualify': 'The evidence does not establish the baseline or how it was measured, so the cycle '
                                  'is described rather than quantified.',
                       'short': 'An improvement measured against a baseline that was never recorded cannot be '
                                'demonstrated.'}
          },
 'outline': {'conclusion': 'Conclusion',
             'context': 'The process and the decision',
             'discussion': 'What the evidence shows',
             'framework': 'DMAIC',
             'implications': 'Implications for the decision',
             'lead': 'DMAIC is a five-step improvement method: define, measure, analyze, improve and control. Each '
                     'step is examined in turn, first through the evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': None,
 'ratings': False,
 'sites': None,
 'subject': 'people',
 'template': 'template_dmaic',
 'title_prefix': 'DMAIC Analysis',
 'unit': {'field': 'process',
          'label': 'The process you are improving',
          'help': 'A DMAIC cycle improves one process. Name it in a few words, for example the campus meal card '
                  'service or the ward discharge process.',
          'example': 'the campus meal card service',
          'refuse': 'A DMAIC cycle improves one process. Name the process you are improving, for example the '
                    'campus meal card service or the ward discharge process.'},
 'voice': {'thesis_question': 'whether the evidence supports the improvement the decision depends on',
           'unit_noun': 'process',
           'block_plural': 'steps',
           'lens': 'the five steps of one improvement cycle, from defining the problem to the control that keeps '
                   'the result',
           'closing': 'identifies the step the improvement depends on and the step the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the process rather than the firm, because DMAIC improves one '
                          'defined process rather than an organisation in general.',
           'context_frame': 'The relevant process is the one named in the brief; the steps belong to that process '
                            'rather than to improvement work in general.',
           'interaction': 'Read together, the steps describe a cycle that has to be evidenced in order rather than '
                          'a menu of good practice: a root cause asserted without measurement is an opinion, not '
                          'an analysis.',
           'implication_frame': 'A decision about the process has to match the step the evidence supports, because '
                                'an improvement that reaches control without a measured baseline cannot be shown '
                                'to have worked.',
           'reference_heading': 'References'}}


GENERIC_STRATEGIES = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'low cost cost leadership cheapest',
             'fill': 'research',
             'key': 'low_cost',
             'label': 'Low-Cost',
             'probe': 'state the evidence for the low-cost strategy',
             'prompt': 'Aims to be the cheapest producer',
             'queries': ['low cost and cost leadership strategies in this industry']},
            {'category': None,
             'cues': 'differentiation unique features premium',
             'fill': 'research',
             'key': 'differentiation',
             'label': 'Differentiation',
             'probe': 'state the evidence for differentiation',
             'prompt': 'Focuses on unique product features customers value',
             'queries': ['differentiation and uniqueness strategies in this industry']},
            {'category': None,
             'cues': 'focused low cost narrow segment',
             'fill': 'research',
             'key': 'focus_low_cost',
             'label': 'Focused Low-Cost',
             'probe': 'state the evidence for focused low-cost',
             'prompt': 'Low cost within a narrow market segment',
             'queries': ['focused low-cost strategy in this industry']},
            {'category': None,
             'cues': 'focused differentiation unique value narrow',
             'fill': 'research',
             'key': 'focus_differentiation',
             'label': 'Focused Differentiation',
             'probe': 'state the evidence for focused differentiation',
             'prompt': 'Unique value within a narrow market segment',
             'queries': ['focused differentiation strategy in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'generic_strategies',
 'label': 'Generic Strategies',
 'notes': {'differentiation': {'analysis': 'Differentiation means the firm focuses on unique features customers value. '
                                           'The relevant question is whether the evidence shows this.',
                               'probe': 'state the evidence for differentiation',
                               'qualify': 'The evidence does not establish uniqueness, so the strategy is described '
                                          'rather than measured.',
                               'short': 'A firm that is unique only in ways customers do not value has no advantage.'},
           'focus_differentiation': {'analysis': 'Focused differentiation means the firm offers unique value within a '
                                                 'narrow market segment. The relevant question is whether the evidence '
                                                 'shows this.',
                                     'probe': 'state the evidence for focused differentiation',
                                     'qualify': 'The evidence does not establish the segment, so the strategy is '
                                                'described rather than measured.',
                                     'short': 'A strategy focused on a segment that is too small has no reach.'},
           'focus_low_cost': {'analysis': 'Focused low cost means the firm lowers cost within a narrow market segment. '
                                          'The relevant question is whether the evidence shows this.',
                              'probe': 'state the evidence for focused low-cost',
                              'qualify': 'The evidence does not establish the segment, so the strategy is described '
                                         'rather than measured.',
                              'short': 'A strategy focused on a segment that is too small has no reach.'},
           'low_cost': {'analysis': 'Low cost means the firm aims to be the cheapest producer in the industry. The '
                                    'relevant question is whether the evidence shows this.',
                        'probe': 'state the evidence for the low-cost strategy',
                        'qualify': 'The evidence does not establish cost advantage, so the strategy is described '
                                   'rather than measured.',
                        'short': 'A firm that is cheapest only on price has an advantage, not a strategy.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'Generic Strategies',
             'implications': 'Implications for the decision',
             'lead': 'Porter"s generic strategies classify a firm"s competitive range into four types. Each is '
                     'examined in turn, first through the evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'strategy',
 'template': 'template_generic_strategies',
 'title_prefix': 'Generic Strategy Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': "Porter's generic strategies are chosen against a market. Name the industry or market.",
          'example': 'smartphones, grocery retail, banking',
          'refuse': "Porter's generic strategies are chosen against a market. Name the industry or market."},
 'voice': {'thesis_question': 'whether the evidence supports the competitive range the decision depends on',
           'unit_noun': 'market',
           'block_plural': 'types',
           'lens': 'the four competitive types a firm can choose, and the trade-off each one makes',
           'closing': 'identifies the type the evidence supports and the trade-off the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the market rather than the firm, because a generic strategy is '
                          'a choice made against the structure of a market rather than a description of one '
                          'company.',
           'context_frame': 'The relevant market is the one named in the brief; the types describe how a firm can '
                            'position itself in that market rather than how one firm happens to operate.',
           'interaction': 'Read together, the types describe choices that cannot all be held at once: the evidence '
                          'has to show where the firm sits, because a firm that claims both cost leadership and '
                          'differentiation has chosen neither.',
           'implication_frame': 'A decision about the firm has to match the type the evidence supports, because a '
                                'strategy that straddles two types usually loses the advantage of both.',
           'reference_heading': 'References'}}


BCG = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'stars high growth high share invest',
             'fill': 'research',
             'key': 'stars',
             'label': 'Stars',
             'probe': 'state the evidence for stars',
             'prompt': 'High growth, high market share - invest to grow',
             'queries': ['stars and high-growth high-share businesses in this industry']},
            {'category': None,
             'cues': 'cash cows low growth high share harvest',
             'fill': 'research',
             'key': 'cash_cows',
             'label': 'Cash Cows',
             'probe': 'state the evidence for cash cows',
             'prompt': 'Low growth, high market share - harvest for cash',
             'queries': ['cash cows and low-growth high-share businesses in this industry']},
            {'category': None,
             'cues': 'question marks high growth low share invest divest',
             'fill': 'research',
             'key': 'question_marks',
             'label': 'Question Marks',
             'probe': 'state the evidence for question marks',
             'prompt': 'High growth, low market share - invest or divest',
             'queries': ['question marks and high-growth low-share businesses in this industry']},
            {'category': None,
             'cues': 'dogs low growth low share divest',
             'fill': 'research',
             'key': 'dogs',
             'label': 'Dogs',
             'probe': 'state the evidence for dogs',
             'prompt': 'Low growth, low market share - divest or harvest',
             'queries': ['dogs and low-growth low-share businesses in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'bcg',
 'label': 'BCG Growth-Share Matrix',
 'notes': {'cash_cows': {'analysis': 'Cash cows are low-growth, high-market-share businesses. The relevant question is '
                                     'whether the evidence shows them.',
                         'probe': 'state the evidence for cash cows',
                         'qualify': 'The evidence does not establish growth or share, so cash cows are described '
                                    'rather than measured.',
                         'short': 'A cash cow without evidence is a business that may not be one.'},
           'dogs': {'analysis': 'Dogs are low-growth, low-market-share businesses. The relevant question is whether '
                                'the evidence shows them.',
                    'probe': 'state the evidence for dogs',
                    'qualify': 'The evidence does not establish growth or share, so dogs are described rather than '
                               'measured.',
                    'short': 'A dog without evidence is a business that may not be one.'},
           'question_marks': {'analysis': 'Question marks are high-growth, low-market-share businesses. The relevant '
                                          'question is whether the evidence shows them.',
                              'probe': 'state the evidence for question marks',
                              'qualify': 'The evidence does not establish growth or share, so question marks are '
                                         'described rather than measured.',
                              'short': 'A question mark without evidence is a business that may not be one.'},
           'stars': {'analysis': 'Stars are high-growth, high-market-share businesses. The relevant question is '
                                 'whether the evidence shows them.',
                     'probe': 'state the evidence for stars',
                     'qualify': 'The evidence does not establish growth or share, so stars are described rather than '
                                'measured.',
                     'short': 'A star without evidence is a business that may not be one.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'BCG Growth-Share Matrix',
             'implications': 'Implications for the decision',
             'lead': 'The BCG matrix classifies a firm"s portfolio into four types: stars, cash cows, question marks '
                     'and dogs. Each is examined in turn, first through the evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'strategy',
 'template': 'template_bcg',
 'title_prefix': 'BCG Growth-Share Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': 'The BCG growth-share matrix positions a portfolio against a market. Name the industry or market.',
          'example': 'smartphones, grocery retail, banking',
          'refuse': 'The BCG growth-share matrix positions a portfolio against a market. Name the industry or market.'},
 'voice': {'thesis_question': 'whether the evidence supports the portfolio position the decision depends on',
           'unit_noun': 'portfolio',
           'block_plural': 'quadrants',
           'lens': 'the four quadrants a business unit is placed in by market growth and relative share',
           'closing': 'identifies the quadrant the evidence places the unit in and the quadrant the evidence '
                      'cannot settle',
           'intro_frame': 'The unit of analysis is the portfolio rather than the industry, because the '
                          'growth-share matrix sorts the units a firm holds against each other by growth and '
                          'share.',
           'context_frame': 'The relevant portfolio is the one named in the brief; the quadrants are positions '
                            'within that portfolio rather than categories of market in general.',
           'interaction': 'Read together, the quadrants describe where a unit stands rather than what to do about '
                          'it: a unit placed by a growth estimate the evidence cannot support has not been placed '
                          'at all.',
           'implication_frame': 'A decision about the portfolio has to match the quadrant the unit is in, because '
                                'cash generated in one quadrant has to be read against the demand the other '
                                'quadrants will make on it.',
           'reference_heading': 'References'}}


GE_MCKINSEY = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'high high invest grow',
             'fill': 'research',
             'key': 'high_high',
             'label': 'High/High',
             'probe': 'state the evidence for high/high',
             'prompt': 'High industry attractiveness, high business strength - invest/grow',
             'queries': ['high attractiveness high strength businesses in this industry']},
            {'category': None,
             'cues': 'high medium invest selectively',
             'fill': 'research',
             'key': 'high_medium',
             'label': 'High/Medium',
             'probe': 'state the evidence for high/medium',
             'prompt': 'High industry attractiveness, medium business strength - invest/selectively',
             'queries': ['high attractiveness medium strength businesses in this industry']},
            {'category': None,
             'cues': 'high low protect selectively',
             'fill': 'research',
             'key': 'high_low',
             'label': 'High/Low',
             'probe': 'state the evidence for high/low',
             'prompt': 'High industry attractiveness, low business strength - protect/selectively',
             'queries': ['high attractiveness low strength businesses in this industry']},
            {'category': None,
             'cues': 'medium high invest selectively',
             'fill': 'research',
             'key': 'medium_high',
             'label': 'Medium/High',
             'probe': 'state the evidence for medium/high',
             'prompt': 'Medium industry attractiveness, high business strength - invest/selectively',
             'queries': ['medium attractiveness high strength businesses in this industry']},
            {'category': None,
             'cues': 'medium medium selectivity earnings',
             'fill': 'research',
             'key': 'medium_medium',
             'label': 'Medium/Medium',
             'probe': 'state the evidence for medium/medium',
             'prompt': 'Medium industry attractiveness, medium business strength - selectivity/earnings',
             'queries': ['medium attractiveness medium strength businesses in this industry']},
            {'category': None,
             'cues': 'medium low harvest divest',
             'fill': 'research',
             'key': 'medium_low',
             'label': 'Medium/Low',
             'probe': 'state the evidence for medium/low',
             'prompt': 'Medium industry attractiveness, low business strength - harvest/divest',
             'queries': ['medium attractiveness low strength businesses in this industry']},
            {'category': None,
             'cues': 'low high protect earnings',
             'fill': 'research',
             'key': 'low_high',
             'label': 'Low/High',
             'probe': 'state the evidence for low/high',
             'prompt': 'Low industry attractiveness, high business strength - protect/earnings',
             'queries': ['low attractiveness high strength businesses in this industry']},
            {'category': None,
             'cues': 'low medium harvest divest',
             'fill': 'research',
             'key': 'low_medium',
             'label': 'Low/Medium',
             'probe': 'state the evidence for low/medium',
             'prompt': 'Low industry attractiveness, medium business strength - harvest/divest',
             'queries': ['low attractiveness medium strength businesses in this industry']},
            {'category': None,
             'cues': 'low low divest liquidate',
             'fill': 'research',
             'key': 'low_low',
             'label': 'Low/Low',
             'probe': 'state the evidence for low/low',
             'prompt': 'Low industry attractiveness, low business strength - divest/liquidate',
             'queries': ['low attractiveness low strength businesses in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'ge_mckinsey',
 'label': 'GE-McKinsey Matrix',
 'notes': {'high_high': {'analysis': 'This quadrant describes a business position. The relevant question is whether '
                                     'the evidence shows it.',
                         'probe': 'state the evidence for this quadrant',
                         'qualify': 'The evidence does not establish the position, so it is described rather than '
                                    'measured.',
                         'short': 'A quadrant without evidence is a business that may not be in it.'},
           'high_low': {'analysis': 'This quadrant describes a business position. The relevant question is whether the '
                                    'evidence shows it.',
                        'probe': 'state the evidence for this quadrant',
                        'qualify': 'The evidence does not establish the position, so it is described rather than '
                                   'measured.',
                        'short': 'A quadrant without evidence is a business that may not be in it.'},
           'high_medium': {'analysis': 'This quadrant describes a business position. The relevant question is whether '
                                       'the evidence shows it.',
                           'probe': 'state the evidence for this quadrant',
                           'qualify': 'The evidence does not establish the position, so it is described rather than '
                                      'measured.',
                           'short': 'A quadrant without evidence is a business that may not be in it.'},
           'low_high': {'analysis': 'This quadrant describes a business position. The relevant question is whether the '
                                    'evidence shows it.',
                        'probe': 'state the evidence for this quadrant',
                        'qualify': 'The evidence does not establish the position, so it is described rather than '
                                   'measured.',
                        'short': 'A quadrant without evidence is a business that may not be in it.'},
           'low_low': {'analysis': 'This quadrant describes a business position. The relevant question is whether the '
                                   'evidence shows it.',
                       'probe': 'state the evidence for this quadrant',
                       'qualify': 'The evidence does not establish the position, so it is described rather than '
                                  'measured.',
                       'short': 'A quadrant without evidence is a business that may not be in it.'},
           'low_medium': {'analysis': 'This quadrant describes a business position. The relevant question is whether '
                                      'the evidence shows it.',
                          'probe': 'state the evidence for this quadrant',
                          'qualify': 'The evidence does not establish the position, so it is described rather than '
                                     'measured.',
                          'short': 'A quadrant without evidence is a business that may not be in it.'},
           'medium_high': {'analysis': 'This quadrant describes a business position. The relevant question is whether '
                                       'the evidence shows it.',
                           'probe': 'state the evidence for this quadrant',
                           'qualify': 'The evidence does not establish the position, so it is described rather than '
                                      'measured.',
                           'short': 'A quadrant without evidence is a business that may not be in it.'},
           'medium_low': {'analysis': 'This quadrant describes a business position. The relevant question is whether '
                                      'the evidence shows it.',
                          'probe': 'state the evidence for this quadrant',
                          'qualify': 'The evidence does not establish the position, so it is described rather than '
                                     'measured.',
                          'short': 'A quadrant without evidence is a business that may not be in it.'},
           'medium_medium': {'analysis': 'This quadrant describes a business position. The relevant question is '
                                         'whether the evidence shows it.',
                             'probe': 'state the evidence for this quadrant',
                             'qualify': 'The evidence does not establish the position, so it is described rather than '
                                        'measured.',
                             'short': 'A quadrant without evidence is a business that may not be in it.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'GE-McKinsey Matrix',
             'implications': 'Implications for the decision',
             'lead': 'The GE-McKinsey matrix classifies a firm"s portfolio into nine cells across industry '
                     'attractiveness and business strength. Each cell is examined in turn, first through the evidence '
                     'and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'strategy',
 'template': 'template_ge_mckinsey',
 'title_prefix': 'GE-McKinsey Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': 'The GE-McKinsey matrix assesses a portfolio against industry attractiveness and business '
                  'strength. Name the industry or market.',
          'example': 'smartphones, grocery retail, banking',
          'refuse': 'The GE-McKinsey matrix assesses a portfolio against industry attractiveness and business '
                    'strength. Name the industry or market.'},
 'voice': {'thesis_question': 'whether the evidence supports the portfolio assessment the decision depends on',
           'unit_noun': 'portfolio',
           'block_plural': 'cells',
           'lens': 'the nine cells of industry attractiveness against business strength',
           'closing': 'identifies the cell the evidence places the unit in and the cell the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the portfolio rather than the industry, because the GE-McKinsey '
                          'matrix sorts the units a firm holds by two judgments made about each of them.',
           'context_frame': 'The relevant portfolio is the one named in the brief; the cells are positions within '
                            'that portfolio rather than categories of market in general.',
           'interaction': 'Read together, the cells record the two judgments that place each unit rather than a '
                          'conclusion that follows from them: the scoring and the weights are yours, and the '
                          'system derives no portfolio plan.',
           'implication_frame': 'A decision about the portfolio has to name the cells whose scores the evidence '
                                'supports, because a cell placed on a score the case cannot defend is an '
                                'assumption rather than an assessment.',
           'reference_heading': 'References'}}


MCKINSEY_7S = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'strategy plan compete',
             'fill': 'research',
             'key': 'strategy',
             'label': 'Strategy',
             'probe': 'state the evidence for strategy',
             'prompt': 'The plan for competing',
             'queries': ['strategy and competitive choices']},
            {'category': None,
             'cues': 'structure organization reporting',
             'fill': 'research',
             'key': 'structure',
             'label': 'Structure',
             'probe': 'state the evidence for structure',
             'prompt': 'How the firm is organized',
             'queries': ['organizational structure']},
            {'category': None,
             'cues': 'systems processes routines',
             'fill': 'research',
             'key': 'systems',
             'label': 'Systems',
             'probe': 'state the evidence for systems',
             'prompt': 'The processes and routines that run the firm',
             'queries': ['systems and processes']},
            {'category': None,
             'cues': 'shared values culture core',
             'fill': 'research',
             'key': 'shared_values',
             'label': 'Shared Values',
             'probe': 'state the evidence for shared values',
             'prompt': 'The core values and culture',
             'queries': ['shared values and culture']},
            {'category': None,
             'cues': 'style leadership decisions',
             'fill': 'research',
             'key': 'style',
             'label': 'Style',
             'probe': 'state the evidence for style',
             'prompt': 'The leadership style and how decisions are made',
             'queries': ['leadership style and decision making']},
            {'category': None,
             'cues': 'staff people skills development',
             'fill': 'research',
             'key': 'staff',
             'label': 'Staff',
             'probe': 'state the evidence for staff',
             'prompt': 'The people, their skills and how they are developed',
             'queries': ['staff and skills development']},
            {'category': None,
             'cues': 'skills capabilities distinctive',
             'fill': 'research',
             'key': 'skills',
             'label': 'Skills',
             'probe': 'state the evidence for skills',
             'prompt': 'The distinctive capabilities the firm possesses',
             'queries': ['distinctive skills and capabilities']}],
 'gate': {'require_geography': False, 'title_context': False, 'title_cue': False},
 'key': 'mckinsey_7s',
 'label': 'McKinsey 7S',
 'notes': {
           'shared_values': {
                             'analysis': 'Shared values are the beliefs the organisation treats as settled: what '
                                         'counts as good work, what is not negotiable and what its people believe the '
                                         'organisation is for. They decide which changes are read as improvements and '
                                         'which are read as violations. The relevant question is whether the evidence '
                                         'shows the change being accepted by those values or resisted by them.',
                             'probe': 'state the values the change has to live with and the evidence that they hold',
                             'qualify': 'The evidence does not establish what the people of the organisation believe, '
                                        'so alignment is described rather than judged.',
                             'short': 'A change that contradicts what the organisation believes is good work will be '
                                      'corrected quietly, without argument.'},
           'skills': {
                      'analysis': 'Skills are the capabilities the organisation actually has, as distinct from the '
                                  'ones the strategy requires. It is the element that most often exposes the gap a '
                                  'strategy has been written across. The relevant question is whether the evidence '
                                  'shows the capability the change needs in the hands of the people who will carry '
                                  'it.',
                      'probe': 'state the capability the change requires and the evidence of what the people can do',
                      'qualify': 'The evidence does not establish what the people can do, so alignment is described '
                                 'rather than judged.',
                      'short': 'A strategy that assumes a capability the organisation does not have will be '
                               'implemented by people learning it under pressure.'},
           'staff': {
                     'analysis': 'Staff is the make-up of the organisation: the people in it, the roles they fill and '
                                 'the way the organisation recruits, deploys and moves them. The relevant question is '
                                 'whether the evidence shows the people who will carry the change, and whether the '
                                 'change gives them a reason to stay.',
                     'probe': 'state who works here, in what roles, and what the change asks of them',
                     'qualify': 'The evidence does not establish who works here or on what terms, so alignment is '
                                'described rather than judged.',
                     'short': 'A change that depends on a group the organisation is losing will be carried by fewer '
                              'people than the plan assumes.'},
           'strategy': {
                        'analysis': 'Strategy is the set of choices the organisation has made about where to compete '
                                    'and how, and the first question is whether the evidence shows the change serving '
                                    'those choices rather than a different set. A change that is not tied to the '
                                    'choices already made has no test of whether it worked. The relevant question is '
                                    'whether the alignment is visible in the evidence.',
                        'probe': 'state the choices the change is meant to serve and the evidence for them',
                        'qualify': 'The evidence does not establish which choices the organisation has made, so '
                                   'alignment is described rather than judged.',
                        'short': 'A change that cannot be traced to a choice cannot be assessed against one.'},
           'structure': {
                         'analysis': 'Structure is the arrangement of authority, work and accountability that people '
                                     'work within. The relevant question is whether the evidence shows the structure '
                                     'carrying the strategy or working against it, because a well-conceived change '
                                     'implemented through a structure that does not support it will not take. The '
                                     'relevant question is therefore whether the structure supports the change.',
                         'probe': 'state how the work is organised and what that arrangement does to the change',
                         'qualify': 'The evidence does not establish how the work is organised, so alignment is '
                                    'described rather than judged.',
                         'short': 'A change routed through a structure that was not designed for it will be reshaped '
                                  'by the structure.'},
           'style': {
                     'analysis': 'Style is the leadership behaviour that sets the norms people work to: how decisions '
                                 'are made, how much is delegated and what is tolerated. It is the element least '
                                 'written down and most often decisive. The relevant question is whether the evidence '
                                 'shows the leadership behaviour the change depends on.',
                     'probe': 'state how leaders behave and what the change requires of them',
                     'qualify': 'The evidence does not establish how decisions are actually made here, so alignment '
                                'is described rather than judged.',
                     'short': 'A change that needs leaders to behave differently will be delivered by leaders who '
                              'behave as they always have.'},
           'systems': {
                       'analysis': 'Systems are the formal routines, measures, controls and information flows that '
                                   'tell people what to do and what counts as good work. They are what makes a '
                                   'practice repeatable rather than dependent on particular people. The relevant '
                                   'question is whether the evidence shows the systems that will carry the change.',
                       'probe': 'state the systems, measures and controls that will carry the change',
                       'qualify': 'The evidence does not establish what the systems are or what they measure, so '
                                  'alignment is described rather than judged.',
                       'short': 'A new practice that the systems do not measure is a practice nobody can be held to.'}
          },
 'outline': {'conclusion': 'Conclusion',
             'context': 'The organisation and the decision',
             'discussion': 'What the evidence shows',
             'framework': 'McKinsey 7S',
             'implications': 'Implications for the decision',
             'lead': 'The McKinsey 7S framework examines seven elements: strategy, structure, systems, shared values, '
                     'style, staff and skills. Each is examined in turn, first through the evidence and then through '
                     'what it implies.',
             'limitations': 'Limitations'},
 'providers': None,
 'ratings': False,
 'sites': None,
 'subject': 'people',
 'template': 'template_mckinsey_7s',
 'title_prefix': 'McKinsey 7S Analysis',
 'unit': {'field': 'process',
          'label': 'The organisation you are describing',
          'help': 'An alignment review describes one organisation or unit. Name it in a few words, for example the '
                  'campus catering team or the university estates office.',
          'example': 'the campus catering team',
          'refuse': 'An alignment review describes one organisation or unit. Name the organisation you are '
                    'describing, for example the campus catering team or the university estates office.'},
 'voice': {'thesis_question': 'whether the evidence supports the alignment the decision depends on',
           'unit_noun': 'organisation',
           'block_plural': 'elements',
           'lens': 'the hard, soft and shared elements that have to be aligned for a strategy to hold',
           'closing': 'identifies the element the alignment depends on and the element the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the organisation rather than the firm or the market, because '
                          'the 7-S model reads one organisation against itself: its strategy, structure, systems, '
                          'shared values, skills, style and staff.',
           'context_frame': 'The relevant organisation is the one named in the brief; the elements belong to that '
                            'organisation rather than to its sector in general.',
           'interaction': 'Read together, the elements describe an organisation whose parts are or are not '
                          'aligned, and a mismatch between a hard and a soft element is the usual reason a '
                          'strategy that was agreed does not travel.',
           'implication_frame': 'A decision about the organisation has to name the element that is out of step, '
                                'because a strategy that changes one element without the others leaves the '
                                'organisation working to its old design.',
           'reference_heading': 'References'}}


RACI = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'responsible do work accountable',
             'fill': 'research',
             'key': 'responsible',
             'label': 'Responsible',
             'probe': 'state the evidence for who is responsible',
             'prompt': 'Who does the work and is accountable for getting it done',
             'queries': ['who is responsible for tasks in this industry']},
            {'category': None,
             'cues': 'accountable owns outcome final say',
             'fill': 'research',
             'key': 'accountable',
             'label': 'Accountable',
             'probe': 'state the evidence for who is accountable',
             'prompt': 'Who owns the outcome and has the final say',
             'queries': ['who is accountable for outcomes in this industry']},
            {'category': None,
             'cues': 'consulted input before decision',
             'fill': 'research',
             'key': 'consulted',
             'label': 'Consulted',
             'probe': 'state the evidence for who is consulted',
             'prompt': 'Who is asked for input before the decision is made',
             'queries': ['who is consulted before decisions in this industry']},
            {'category': None,
             'cues': 'informed told after decision',
             'fill': 'research',
             'key': 'informed',
             'label': 'Informed',
             'probe': 'state the evidence for who is informed',
             'prompt': 'Who is told after the decision is made',
             'queries': ['who is informed after decisions in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'raci',
 'label': 'RACI',
 'notes': {'accountable': {'analysis': 'This RACI role describes who is involved in a task. The relevant question is '
                                       'whether the evidence shows it.',
                           'probe': 'state the evidence for this role',
                           'qualify': 'The evidence does not establish the role, so it is described rather than '
                                      'measured.',
                           'short': 'A role without evidence is an assignment without support.'},
           'consulted': {'analysis': 'This RACI role describes who is involved in a task. The relevant question is '
                                     'whether the evidence shows it.',
                         'probe': 'state the evidence for this role',
                         'qualify': 'The evidence does not establish the role, so it is described rather than '
                                    'measured.',
                         'short': 'A role without evidence is an assignment without support.'},
           'informed': {'analysis': 'This RACI role describes who is involved in a task. The relevant question is '
                                    'whether the evidence shows it.',
                        'probe': 'state the evidence for this role',
                        'qualify': 'The evidence does not establish the role, so it is described rather than measured.',
                        'short': 'A role without evidence is an assignment without support.'},
           'responsible': {'analysis': 'This RACI role describes who is involved in a task. The relevant question is '
                                       'whether the evidence shows it.',
                           'probe': 'state the evidence for this role',
                           'qualify': 'The evidence does not establish the role, so it is described rather than '
                                      'measured.',
                           'short': 'A role without evidence is an assignment without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'RACI',
             'implications': 'Implications for the decision',
             'lead': 'RACI assigns four roles to each task: responsible, accountable, consulted and informed. Each '
                     'role is examined in turn, first through the evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'project-management',
 'template': 'template_raci',
 'title_prefix': 'RACI Analysis',
 'unit': {'example': 'smartphones, grocery retail, banking',
          'field': 'industry',
          'help': 'RACI assigns four roles to each task. Name the industry or market.',
          'label': 'Industry or market',
          'refuse': 'RACI assigns four roles to each task. Name the industry or market.'},
 'voice': {'block_plural': 'roles',
           'closing': 'identifies the role with the strongest evidence and the one most unsupported',
           'context_frame': 'The relevant industry is the one named in the brief; the roles are assigned to the '
                            'tasks that need to get things done there.',
           'implication_frame': 'A role assignment has to be defensible: someone must own the work, someone must '
                                'answer for the outcome, and the evidence must show who should do what.',
           'interaction': 'Read together, the roles describe how work gets done in the market: the person who does '
                          'the work, the person who answers for it, the person whose advice is needed, and the '
                          'person who is kept in the loop.',
           'intro_frame': 'The unit of analysis is the industry, because RACI assigns roles to tasks in that '
                          'industry.',
           'lens': 'the four RACI roles: responsible, accountable, consulted, informed',
           'reference_heading': 'References',
           'thesis_question': 'whether the evidence supports the role assignment the decision relies on',
           'unit_noun': 'industry'}}


PORTERS_DIAMOND = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'factor conditions resources endowment',
             'fill': 'research',
             'key': 'factor_conditions',
             'label': 'Factor Conditions',
             'probe': 'state the evidence for factor conditions',
             'prompt': 'The nations endowment of natural, human, capital and infrastructure resources',
             'queries': ['factor conditions and resource endowment in this industry']},
            {'category': None,
             'cues': 'demand conditions domestic market',
             'fill': 'research',
             'key': 'demand_conditions',
             'label': 'Demand Conditions',
             'probe': 'state the evidence for demand conditions',
             'prompt': 'The nature of domestic demand and how it shapes competitive advantage',
             'queries': ['demand conditions and domestic market in this industry']},
            {'category': None,
             'cues': 'related industries supporting suppliers',
             'fill': 'research',
             'key': 'related_industries',
             'label': 'Related and Supporting Industries',
             'probe': 'state the evidence for related industries',
             'prompt': 'The presence of supplier and related industries that are internationally competitive',
             'queries': ['related and supporting industries in this industry']},
            {'category': None,
             'cues': 'firm strategy structure rivalry',
             'fill': 'research',
             'key': 'firm_strategy',
             'label': 'Firm Strategy, Structure and Rivalry',
             'probe': 'state the evidence for firm strategy',
             'prompt': 'How firms are created, organized and managed, and the nature of domestic rivalry',
             'queries': ['firm strategy and domestic rivalry in this industry']},
            {'category': None,
             'cues': 'government policy role',
             'fill': 'research',
             'key': 'government',
             'label': 'Government',
             'probe': 'state the evidence for government',
             'prompt': 'The role of government in shaping the diamond',
             'queries': ['government role and policy in this industry']},
            {'category': None,
             'cues': 'chance events random',
             'fill': 'research',
             'key': 'chance',
             'label': 'Chance',
             'probe': 'state the evidence for chance',
             'prompt': 'The role of chance events in shaping competitive advantage',
             'queries': ['chance events and their role in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'porters_diamond',
 'label': 'Porters Diamond',
 'notes': {'chance': {'analysis': 'This element describes a factor in the diamond. The relevant question is whether '
                                  'the evidence shows it.',
                      'probe': 'state the evidence for this element',
                      'qualify': 'The evidence does not establish this element, so it is described rather than '
                                 'measured.',
                      'short': 'An element without evidence is a claim without support.'},
           'demand_conditions': {'analysis': 'This element describes a factor in the diamond. The relevant question is '
                                             'whether the evidence shows it.',
                                 'probe': 'state the evidence for this element',
                                 'qualify': 'The evidence does not establish this element, so it is described rather '
                                            'than measured.',
                                 'short': 'An element without evidence is a claim without support.'},
           'factor_conditions': {'analysis': 'This element describes a factor in the diamond. The relevant question is '
                                             'whether the evidence shows it.',
                                 'probe': 'state the evidence for this element',
                                 'qualify': 'The evidence does not establish this element, so it is described rather '
                                            'than measured.',
                                 'short': 'An element without evidence is a claim without support.'},
           'firm_strategy': {'analysis': 'This element describes a factor in the diamond. The relevant question is '
                                         'whether the evidence shows it.',
                             'probe': 'state the evidence for this element',
                             'qualify': 'The evidence does not establish this element, so it is described rather than '
                                        'measured.',
                             'short': 'An element without evidence is a claim without support.'},
           'government': {'analysis': 'This element describes a factor in the diamond. The relevant question is '
                                      'whether the evidence shows it.',
                          'probe': 'state the evidence for this element',
                          'qualify': 'The evidence does not establish this element, so it is described rather than '
                                     'measured.',
                          'short': 'An element without evidence is a claim without support.'},
           'related_industries': {'analysis': 'This element describes a factor in the diamond. The relevant question '
                                              'is whether the evidence shows it.',
                                  'probe': 'state the evidence for this element',
                                  'qualify': 'The evidence does not establish this element, so it is described rather '
                                             'than measured.',
                                  'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'Porters Diamond',
             'implications': 'Implications for the decision',
             'lead': 'Porters diamond describes four determinants of national competitive advantage: factor '
                     'conditions, demand conditions, related industries and firm strategy. Each is examined in turn, '
                     'first through the evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'strategy',
 'template': 'template_porters_diamond',
 'title_prefix': 'Porter Diamond Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': "Porter's Diamond analyses national or industry competitiveness. Name the industry or market.",
          'example': 'smartphones, grocery retail, banking',
          'refuse': "Porter's Diamond analyses national or industry competitiveness. Name the industry or market."},
 'voice': {'thesis_question': 'whether the evidence supports the competitive position the decision depends on',
           'unit_noun': 'market',
           'block_plural': 'determinants',
           'lens': 'the determinants of national and industry competitiveness, from factor conditions to the role '
                   'of government and chance',
           'closing': 'identifies the determinant the position depends on and the determinant the evidence cannot '
                      'settle',
           'intro_frame': 'The unit of analysis is the market rather than the firm, because the Diamond explains '
                          'why an industry in a country is positioned as it is rather than how one company in it '
                          'performs.',
           'context_frame': 'The relevant market is the one named in the brief; the determinants belong to that '
                            'industry in its country rather than to one participant.',
           'interaction': 'Read together, the determinants describe the conditions an industry develops in rather '
                          'than the advantages a firm has won: an industry with good factor conditions does not '
                          'give the advantage to any one of its firms.',
           'implication_frame': 'A decision about the firm has to match the determinant the evidence supports, '
                                'because an advantage built on a factor the country is losing does not hold for '
                                'long.',
           'reference_heading': 'References'}}


BURKE_LITWIN = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'external environment forces',
             'fill': 'research',
             'key': 'external_environment',
             'label': 'External Environment',
             'probe': 'state the evidence for the external environment',
             'prompt': 'The external forces that shape the organisation',
             'queries': ['external environment and forces shaping the organisation']},
            {'category': None,
             'cues': 'mission strategy goals',
             'fill': 'research',
             'key': 'mission_strategy',
             'label': 'Mission and Strategy',
             'probe': 'state the evidence for mission and strategy',
             'prompt': 'What the organisation is trying to achieve and how',
             'queries': ['mission and strategy']},
            {'category': None,
             'cues': 'leadership style behaviour',
             'fill': 'research',
             'key': 'leadership',
             'label': 'Leadership',
             'probe': 'state the evidence for leadership',
             'prompt': 'The style and behaviour of those who lead',
             'queries': ['leadership style and behaviour']},
            {'category': None,
             'cues': 'culture values beliefs assumptions',
             'fill': 'research',
             'key': 'culture',
             'label': 'Culture',
             'probe': 'state the evidence for culture',
             'prompt': 'The shared values, beliefs and assumptions',
             'queries': ['culture and values']},
            {'category': None,
             'cues': 'structure organisation authority',
             'fill': 'research',
             'key': 'structure',
             'label': 'Structure',
             'probe': 'state the evidence for structure',
             'prompt': 'How work is organised and authority is distributed',
             'queries': ['organisational structure']},
            {'category': None,
             'cues': 'management practices behaviour systems',
             'fill': 'research',
             'key': 'management_practices',
             'label': 'Management Practices',
             'probe': 'state the evidence for management practices',
             'prompt': 'How managers actually behave and the systems they use',
             'queries': ['management practices']},
            {'category': None,
             'cues': 'systems policies procedures rewards',
             'fill': 'research',
             'key': 'systems',
             'label': 'Systems and Policies',
             'probe': 'state the evidence for systems',
             'prompt': 'The formal procedures, policies and reward systems',
             'queries': ['systems and policies']},
            {'category': None,
             'cues': 'work unit climate morale atmosphere',
             'fill': 'research',
             'key': 'work_unit_climate',
             'label': 'Work Unit Climate',
             'probe': 'state the evidence for work unit climate',
             'prompt': 'The atmosphere and morale within teams',
             'queries': ['work unit climate and morale']},
            {'category': None,
             'cues': 'task skills abilities motivation',
             'fill': 'research',
             'key': 'task_requirements',
             'label': 'Task and Individual Skills',
             'probe': 'state the evidence for task requirements',
             'prompt': 'The skills, abilities and motivation of individuals',
             'queries': ['task requirements and individual skills']},
            {'category': None,
             'cues': 'motivation drivers performance',
             'fill': 'research',
             'key': 'motivation',
             'label': 'Motivation',
             'probe': 'state the evidence for motivation',
             'prompt': 'What drives people to perform',
             'queries': ['motivation and drivers of performance']},
            {'category': None,
             'cues': 'individual needs values wants',
             'fill': 'research',
             'key': 'individual_values',
             'label': 'Individual Needs and Values',
             'probe': 'state the evidence for individual values',
             'prompt': 'What individuals want and value',
             'queries': ['individual needs and values']},
            {'category': None,
             'cues': 'performance results outcomes',
             'fill': 'research',
             'key': 'performance',
             'label': 'Individual and Organisational Performance',
             'probe': 'state the evidence for performance',
             'prompt': 'The results the organisation achieves',
             'queries': ['performance and results']}],
 'gate': {'require_geography': False, 'title_context': False, 'title_cue': False},
 'key': 'burke_litwin',
 'label': 'Burke-Litwin',
 'notes': {
           'culture': {
                       'analysis': 'Culture is the shared set of assumptions, values and norms that determine how '
                                   'members of the organisation think and act. It shapes what is considered normal '
                                   'and what is treated as deviation. The relevant question is whether the evidence '
                                   'shows the culture as it is practised rather than as it is described.',
                       'probe': 'state the norms that are actually followed and the evidence for them',
                       'qualify': 'The evidence does not establish what the culture is in practice, so the diagnosis '
                                  'is described rather than judged.',
                       'short': 'The stated culture and the practised culture are often two different things, and '
                                'only one of them produces results.'},
           'external_environment': {
                                    'analysis': 'The external environment is the set of pressures the organisation '
                                                'does not control: the demand it serves, the rules it must meet, the '
                                                'technology available to it and the expectations of those it answers '
                                                'to. It is where change usually begins. The relevant question is '
                                                'whether the evidence shows the pressures acting on this organisation '
                                                'now.',
                                    'probe': 'state the external pressures acting on this organisation and the '
                                             'evidence for them',
                                    'qualify': 'The evidence does not establish the pressures acting here, so the '
                                               'diagnosis is described rather than asserted.',
                                    'short': 'A change that answers a pressure the organisation does not face will '
                                             'not be sustained by the urgency it was given.'},
           'individual_values': {
                                 'analysis': 'Individual needs and values are what each person brings and needs: '
                                             'their own commitments, the reward they value and the balance they '
                                             'strike between work and the rest of it. The relevant question is '
                                             'whether the evidence shows how the change bears on what the people '
                                             'affected value.',
                                 'probe': 'state what the people affected value and what the change asks of them',
                                 'qualify': 'The evidence does not establish what the individuals involved value, so '
                                            'the diagnosis is described rather than judged.',
                                 'short': 'A change that asks for a sacrifice nobody agreed to will be resisted '
                                          'without argument.'},
           'leadership': {
                          'analysis': 'Leadership is the direction and climate set at the top of the organisation: '
                                      'the priorities it endorses, the standards it applies and the example it sets. '
                                      'In the model it is the connector between the external environment and the '
                                      'internal system, because a strategy reaches the rest of the organisation only '
                                      'through it. The relevant question is whether the evidence shows leadership '
                                      'providing the direction the change depends on.',
                          'probe': 'state what the leadership has prioritised and what it has modelled',
                          'qualify': 'The evidence does not establish what leadership has actually endorsed, so the '
                                     'diagnosis is described rather than judged.',
                          'short': 'A strategy that the leadership does not carry personally reaches the organisation '
                                   'as a document.'},
           'management_practices': {
                                    'analysis': 'Management practices are the routines by which managers plan, '
                                                'monitor, coach and evaluate the work of their teams. They are the '
                                                'mechanism through which a strategy becomes routine performance. The '
                                                'relevant question is whether the evidence shows the practices that '
                                                'will carry the change.',
                                    'probe': 'state how managers plan, monitor and evaluate the work of their teams',
                                    'qualify': 'The evidence does not establish how managers actually work here, so '
                                               'the diagnosis is described rather than judged.',
                                    'short': 'A strategy that reaches the work only through managers is only as '
                                             'strong as those managers\' practice.'},
           'mission_strategy': {
                                'analysis': 'Mission and strategy are the organisation\'s statement of what it exists '
                                            'to do and the choices it has made about how. In the model they sit '
                                            'between the environment and the internal parts, because they are where '
                                            'an external pressure is converted into a plan. The relevant question is '
                                            'whether the evidence shows a mission and strategy that answer the '
                                            'pressures identified.',
                                'probe': 'state what the organisation exists to do and the choices it has made',
                                'qualify': 'The evidence does not establish what the organisation has committed to, '
                                           'so the diagnosis is described rather than judged.',
                                'short': 'An organisation with a clear mission and no strategy has described the '
                                         'purpose without answering the pressure.'},
           'motivation': {
                          'analysis': 'Motivation is the willingness to apply effort beyond what the role requires. '
                                      'In the model it is where a performance gap is usually located. The relevant '
                                      'question is whether the evidence shows what the people affected see in the '
                                      'change.',
                          'probe': 'state what the people affected gain or lose from the change',
                          'qualify': 'The evidence does not establish what people are willing to give, so the '
                                     'diagnosis is described rather than judged.',
                          'short': 'People give more than they are asked for when they believe it is worth something '
                                   'to them.'},
           'performance': {
                           'analysis': 'Individual and organisational performance is the outcome the model is trying '
                                       'to explain: the results the organisation and its people produce. It is the '
                                       'point at which the diagnosis is tested, because a model that cannot account '
                                       'for the performance has not explained anything. The relevant question is '
                                       'whether the evidence shows the performance and how it is measured.',
                           'probe': 'state the performance and the measure it is read from',
                           'qualify': 'The evidence does not establish the performance or how it is measured, so the '
                                      'diagnosis is described rather than asserted.',
                           'short': 'Performance is the only part of the model that is not an explanation; it is what '
                                    'the explanation has to answer for.'},
           'structure': {
                         'analysis': 'Structure is the formal allocation of authority, roles and accountability. It '
                                     'determines who decides, who carries out a decision and who is held to it. The '
                                     'relevant question is whether the evidence shows the structure the strategy '
                                     'needs, or a structure that works against it.',
                         'probe': 'state who decides what and who carries it out',
                         'qualify': 'The evidence does not establish how authority is allocated here, so the '
                                    'diagnosis is described rather than judged.',
                         'short': 'Where authority sits and where the work sits are rarely the same place, and the '
                                  'gap is where change stalls.'},
           'systems': {
                       'analysis': 'Systems and policies are the formal structures of the organisation: the '
                                   'procedures, rules, measures and information flows through which work is '
                                   'controlled and coordinated. The relevant question is whether the evidence shows '
                                   'the systems that will carry the change into everyday work.',
                       'probe': 'state the procedures, rules and measures that govern the work',
                       'qualify': 'The evidence does not establish what the systems require, so the diagnosis is '
                                  'described rather than judged.',
                       'short': 'A change that the systems do not measure is a change nobody can be held to.'},
           'task_requirements': {
                                 'analysis': 'Task requirements are the demands the work makes of the individual: the '
                                             'skills, knowledge and effort the role needs and the standard it must '
                                             'meet. The relevant question is whether the evidence shows what the work '
                                             'now demands of the people doing it.',
                                 'probe': 'state what the work demands of the people doing it',
                                 'qualify': 'The evidence does not establish what the work demands here, so the '
                                            'diagnosis is described rather than judged.',
                                 'short': 'A change raises what the work demands of people without giving them the '
                                          'means to meet it.'},
           'work_unit_climate': {
                                 'analysis': 'Work unit climate is the atmosphere of a particular unit: the trust, '
                                             'the openness to raise problems and the sense of fairness within a '
                                             'group, as distinct from the culture of the organisation as a whole. The '
                                             'relevant question is whether the evidence shows a climate in which the '
                                             'change can be discussed, because a change cannot be absorbed by a group '
                                             'that will not say what is wrong.',
                                 'probe': 'state how people in this unit talk about problems and whether they are '
                                          'heard',
                                 'qualify': 'The evidence does not establish the climate of this unit, so the '
                                            'diagnosis is described rather than judged.',
                                 'short': 'A change that cannot be questioned in the team where it lands will be '
                                          'absorbed as compliance.'}
          },
 'outline': {'conclusion': 'Conclusion',
             'context': 'The organisation and the decision',
             'discussion': 'What the evidence shows',
             'framework': 'Burke-Litwin',
             'implications': 'Implications for the decision',
             'lead': 'The Burke-Litwin model links twelve organisational elements from the external environment down '
                     'to individual performance. Each is examined in turn, first through the evidence and then through '
                     'what it implies.',
             'limitations': 'Limitations'},
 'providers': None,
 'ratings': False,
 'sites': None,
 'subject': 'people',
 'template': 'template_burke_litwin',
 'title_prefix': 'Burke-Litwin Analysis',
 'unit': {'field': 'process',
          'label': 'The organisation you are describing',
          'help': 'A change review describes one organisation or unit. Name it in a few words, for example the '
                  'campus catering team or the university estates office.',
          'example': 'the campus catering team',
          'refuse': 'A change review describes one organisation or unit. Name the organisation you are describing, '
                    'for example the campus catering team or the university estates office.'},
 'voice': {'thesis_question': 'whether the evidence supports the change the decision depends on',
           'unit_noun': 'organisation',
           'block_plural': 'elements',
           'lens': 'the twelve elements that carry a change through one organisation, from external environment to '
                   'individual performance',
           'closing': 'identifies the element the change depends on and the element the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the organisation rather than the firm or the market, because '
                          'the Burke-Litwin model traces a change through the elements of one organisation in '
                          'sequence.',
           'context_frame': 'The relevant organisation is the one named in the brief; the elements belong to that '
                            'organisation rather than to change in its sector in general.',
           'interaction': 'Read together, the elements trace the path a change takes through the organisation '
                          'rather than a list of conditions that apply independently.',
           'implication_frame': 'A decision about the change has to match the element the organisation has '
                                'actually reached, because an intervention aimed at an element the change has not '
                                'yet reached cannot be relied on.',
           'reference_heading': 'References'}}


GALBRAITH_STAR = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'strategy goals aims',
             'fill': 'research',
             'key': 'strategy',
             'label': 'Strategy',
             'probe': 'state the evidence for strategy',
             'prompt': 'What the organisation is trying to achieve',
             'queries': ['strategy and goals']},
            {'category': None,
             'cues': 'structure organisation authority',
             'fill': 'research',
             'key': 'structure',
             'label': 'Structure',
             'probe': 'state the evidence for structure',
             'prompt': 'How work and authority are organised',
             'queries': ['structure and organisation']},
            {'category': None,
             'cues': 'processes decisions workflows',
             'fill': 'research',
             'key': 'processes',
             'label': 'Processes',
             'probe': 'state the evidence for processes',
             'prompt': 'How decisions are made and work flows',
             'queries': ['processes and decision making']},
            {'category': None,
             'cues': 'rewards pay incentives',
             'fill': 'research',
             'key': 'rewards',
             'label': 'Rewards',
             'probe': 'state the evidence for rewards',
             'prompt': 'What the organisation pays people for',
             'queries': ['rewards and incentives']},
            {'category': None,
             'cues': 'people skills mindsets capabilities',
             'fill': 'research',
             'key': 'people',
             'label': 'People',
             'probe': 'state the evidence for people',
             'prompt': 'The skills, mindsets and capabilities needed',
             'queries': ['people skills and capabilities']}],
 'gate': {'require_geography': False, 'title_context': False, 'title_cue': False},
 'key': 'galbraith_star',
 'label': 'Galbraith Star',
 'notes': {
           'people': {
                      'analysis': 'People is the capability the design rests on: the skills, roles, numbers and '
                                  'experience the organisation has and needs. The relevant question is whether the '
                                  'evidence shows the people who will make the design work.',
                      'probe': 'state the skills, roles and experience the design needs and what exists',
                      'qualify': 'The evidence does not establish what capability exists here, so alignment is '
                                 'described rather than judged.',
                      'short': 'A design that assumes a capability the organisation does not have will be reshaped by '
                               'the people who do.'},
           'processes': {
                         'analysis': 'Processes are the routines that turn the strategy into work: how work is done, '
                                     'handed on and controlled. The relevant question is whether the evidence shows '
                                     'the processes that will deliver the strategy rather than preserve the old one.',
                         'probe': 'state how the work is done, handed on and controlled',
                         'qualify': 'The evidence does not establish how the work actually flows, so alignment is '
                                    'described rather than judged.',
                         'short': 'Most strategies fail in the process layer, where the daily routine quietly routes '
                                  'around them.'},
           'rewards': {
                       'analysis': 'Rewards are the consequences the organisation attaches to behaviour: what is '
                                   'paid, recognised, measured and praised. They tell people what the organisation '
                                   'actually wants, which is often not what its strategy says. The relevant question '
                                   'is whether the evidence shows what the design rewards people for.',
                       'probe': 'state what people are paid, recognised and measured for',
                       'qualify': 'The evidence does not establish what people are rewarded for, so alignment is '
                                  'described rather than judged.',
                       'short': 'People follow the reward, and the reward is the strategy the organisation actually '
                                'has.'},
           'strategy': {
                        'analysis': 'Strategy is the direction the organisation has chosen, and the centre of the '
                                    'star: every other element is judged by whether it serves it. The relevant '
                                    'question is whether the evidence shows the choices the design has to serve.',
                        'probe': 'state the direction the organisation has chosen and the evidence for it',
                        'qualify': 'The evidence does not establish which choices the organisation has made, so '
                                   'alignment is described rather than judged.',
                        'short': 'An operating model designed around a strategy the organisation does not hold will '
                                 'pull it back to the strategy it has.'},
           'structure': {
                         'analysis': 'Structure is the arrangement of roles, reporting lines and decision rights. The '
                                     'relevant question is whether the evidence shows the structure carrying the '
                                     'decisions the strategy needs.',
                         'probe': 'state how roles, reporting lines and decisions are arranged',
                         'qualify': 'The evidence does not establish how authority is arranged here, so alignment is '
                                    'described rather than judged.',
                         'short': 'A design that leaves the decisions where they already sit will be hollowed out by '
                                  'the existing structure.'}
          },
 'outline': {'conclusion': 'Conclusion',
             'context': 'The organisation and the decision',
             'discussion': 'What the evidence shows',
             'framework': 'Galbraith Star',
             'implications': 'Implications for the decision',
             'lead': 'The Galbraith star model links five elements: strategy, structure, processes, rewards and '
                     'people. Each is examined in turn, first through the evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': None,
 'ratings': False,
 'sites': None,
 'subject': 'people',
 'template': 'template_galbraith_star',
 'title_prefix': 'Galbraith Star Analysis',
 'unit': {'field': 'process',
          'label': 'The organisation you are describing',
          'help': 'An operating-model review describes one organisation or unit. Name it in a few words, for '
                  'example the campus catering team or the university estates office.',
          'example': 'the campus catering team',
          'refuse': 'An operating-model review describes one organisation or unit. Name the organisation you are '
                    'describing, for example the campus catering team or the university estates office.'},
 'voice': {'thesis_question': 'whether the evidence supports the operating model the decision depends on',
           'unit_noun': 'organisation',
           'block_plural': 'elements',
           'lens': 'the five elements a star-shaped operating model is built from',
           'closing': 'identifies the element the design depends on and the element the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the organisation rather than the firm or the market, because '
                          'the star model designs one organisation and shows how its five elements hold each other '
                          'in place.',
           'context_frame': 'The relevant organisation is the one named in the brief; the elements belong to that '
                            'organisation rather than to its sector in general.',
           'interaction': 'Read together, the elements show how the design holds: the strategy sets what the '
                          'others are for, and people are the element such a design is usually weakest on.',
           'implication_frame': 'A decision about the organisation has to name the element that has to change with '
                                'the others, because a star does not hold if one point of it is moved on its own.',
           'reference_heading': 'References'}}


MINTZBERG = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'strategic apex leadership mission',
             'fill': 'research',
             'key': 'strategic_apex',
             'label': 'Strategic Apex',
             'probe': 'state the evidence for the strategic apex',
             'prompt': 'Those who define the mission and strategy',
             'queries': ['strategic apex and leadership']},
            {'category': None,
             'cues': 'middle line managers translate',
             'fill': 'research',
             'key': 'middle_line',
             'label': 'Middle Line',
             'probe': 'state the evidence for the middle line',
             'prompt': 'Those who translate strategy into action',
             'queries': ['middle line management']},
            {'category': None,
             'cues': 'operating core basic work',
             'fill': 'research',
             'key': 'operating_core',
             'label': 'Operating Core',
             'probe': 'state the evidence for the operating core',
             'prompt': 'Those who do the basic work of the organisation',
             'queries': ['operating core and basic work']},
            {'category': None,
             'cues': 'technostructure design control',
             'fill': 'research',
             'key': 'technostructure',
             'label': 'Technostructure',
             'probe': 'state the evidence for the technostructure',
             'prompt': 'Those who design and control the work',
             'queries': ['technostructure and work design']},
            {'category': None,
             'cues': 'support staff indirect support',
             'fill': 'research',
             'key': 'support_staff',
             'label': 'Support Staff',
             'probe': 'state the evidence for support staff',
             'prompt': 'Those who provide indirect support',
             'queries': ['support staff and indirect support']}],
 'gate': {'require_geography': False, 'title_context': False, 'title_cue': False},
 'key': 'mintzberg',
 'label': 'Mintzberg',
 'notes': {
           'middle_line': {
                           'analysis': 'The middle line is the chain of managers between the apex and the operating '
                                       'core, and it exists to interpret the top\'s direction for the units below it. '
                                       'Where that chain is long, the organisation coordinates through supervision; '
                                       'where it is short, it coordinates through standardisation. The relevant '
                                       'question is whether the evidence shows how many levels sit between the top '
                                       'and the work.',
                           'probe': 'state the levels between the top and the work and what each level decides',
                           'qualify': 'The evidence does not establish how many levels exist here, so the '
                                      'configuration is described rather than typed.',
                           'short': 'The length of the line between the top and the work is the clearest clue to how '
                                    'this organisation coordinates.'},
           'operating_core': {
                              'analysis': 'The operating core is the part of the organisation that carries out the '
                                          'basic work the organisation exists to do. Its specialisation is the '
                                          'strongest single clue to the configuration: a standardised, tightly '
                                          'coupled operation and a professional one are built on different knowledge. '
                                          'The relevant question is whether the evidence shows what the basic work is '
                                          'and how specialised it is.',
                              'probe': 'state what the basic work is and how specialised it is',
                              'qualify': 'The evidence does not establish what the basic work is here, so the '
                                         'configuration is described rather than typed.',
                              'short': 'The basic work and its specialisation tell you more about how this '
                                       'organisation is built than any stated strategy.'},
           'strategic_apex': {
                              'analysis': 'The strategic apex is the small group at the top of the organisation that '
                                          'holds the overall direction and the decisions that commit the organisation '
                                          'as a whole. Its size and composition are the clearest single clue to how '
                                          'an organisation is actually configured. The relevant question is whether '
                                          'the evidence shows who sits at the top and what they decide.',
                              'probe': 'state who sits at the top and what decisions are taken there',
                              'qualify': 'The evidence does not establish who holds the top decisions here, so the '
                                         'configuration is described rather than typed.',
                              'short': 'The size of the top tells you how much the organisation can decide at once, '
                                       'and how much it must escalate.'},
           'support_staff': {
                             'analysis': 'The support staff are the parts of the organisation that serve the others '
                                         'rather than carry out the basic work: finance, legal, estates, human '
                                         'resources and the rest. Where they are large, the organisation is a '
                                         'conglomerate of specialist units; where they are small, they are an '
                                         'overhead on a single operation. The relevant question is whether the '
                                         'evidence shows the support services and how large they are.',
                             'probe': 'state what support services exist and how many people work in them',
                             'qualify': 'The evidence does not establish what support exists here, so the '
                                        'configuration is described rather than typed.',
                             'short': 'The support services are where an organisation hides the cost of being an '
                                      'organisation.'},
           'technostructure': {
                               'analysis': 'The technostructure is the part of the organisation that does not do the '
                                           'basic work but shapes it: the systems, the methods, the standards and the '
                                           'analysis that tell the others how the work is to be done. Where it is '
                                           'strong, the organisation coordinates by standardisation rather than by '
                                           'supervision. The relevant question is whether the evidence shows the '
                                           'techniques that shape the work.',
                               'probe': 'state who shapes the work and the standards and methods they use',
                               'qualify': 'The evidence does not establish who shapes the work here, so the '
                                          'configuration is described rather than typed.',
                               'short': 'An organisation that has written down how the work is done coordinates '
                                        'itself; one that has not coordinates through managers.'}
          },
 'outline': {'conclusion': 'Conclusion',
             'context': 'The organisation and the decision',
             'discussion': 'What the evidence shows',
             'framework': 'Mintzberg',
             'implications': 'Implications for the decision',
             'lead': 'Mintzberg"s organisational configuration describes five parts: strategic apex, middle line, '
                     'operating core, technostructure and support staff. Each is examined in turn, first through the '
                     'evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': None,
 'ratings': False,
 'sites': None,
 'subject': 'people',
 'template': 'template_mintzberg',
 'title_prefix': 'Mintzberg Analysis',
 'unit': {'field': 'process',
          'label': 'The organisation you are describing',
          'help': 'A configuration review describes one organisation or unit. Name it in a few words, for example '
                  'the campus catering team or the university estates office.',
          'example': 'the campus catering team',
          'refuse': 'A configuration review describes one organisation or unit. Name the organisation you are '
                    'describing, for example the campus catering team or the university estates office.'},
 'voice': {'thesis_question': 'whether the evidence supports the configuration the decision depends on',
           'unit_noun': 'organisation',
           'block_plural': 'parts',
           'lens': 'the parts a configuration is made of and the coordination that holds them together',
           'closing': 'identifies the part the configuration depends on and the part the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the organisation rather than the firm or the market, because a '
                          'configuration describes how one organisation is put together rather than which shape it '
                          'should have.',
           'context_frame': 'The relevant organisation is the one named in the brief; the parts belong to that '
                            'organisation rather than to its sector in general.',
           'interaction': 'Read together, the parts show how the organisation is actually coordinated rather than '
                          'how it is supposed to be structured: a design that does not match the dominant part is '
                          'a source of the conflict it was meant to remove.',
           'implication_frame': 'A decision about the organisation has to name the part that does not fit, because '
                                'the parts of a configuration pull against each other when one of them is changed '
                                'alone.',
           'reference_heading': 'References'}}


LOGIC_MODEL = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'inputs resources conditions',
             'fill': 'research',
             'key': 'inputs',
             'label': 'Inputs',
             'probe': 'state the evidence for inputs',
             'prompt': 'The resources and conditions brought to the effort',
             'queries': ['inputs and resources for change']},
            {'category': None,
             'cues': 'activities actions interventions',
             'fill': 'research',
             'key': 'activities',
             'label': 'Activities',
             'probe': 'state the evidence for activities',
             'prompt': 'The actions and interventions carried out',
             'queries': ['activities and actions in this programme']},
            {'category': None,
             'cues': 'outputs products results',
             'fill': 'research',
             'key': 'outputs',
             'label': 'Outputs',
             'probe': 'state the evidence for outputs',
             'prompt': 'The direct products of the activities',
             'queries': ['outputs and results']},
            {'category': None,
             'cues': 'outcomes results impact',
             'fill': 'research',
             'key': 'outcomes',
             'label': 'Outcomes',
             'probe': 'state the evidence for outcomes',
             'prompt': 'The short, medium and long-term results achieved',
             'queries': ['outcomes and impact']},
            {'category': None,
             'cues': 'impact long term contribution legacy systems wellbeing sustainability',
             'fill': 'research',
             'key': 'impact',
             'label': 'Impact',
             'probe': 'state the long-term change contributed to and the time horizon claimed',
             'prompt': 'The long-term change the programme is meant to contribute to',
             'queries': ['impact and long term contribution of a programme']}],
 'gate': {'require_geography': False, 'title_context': False, 'title_cue': False},
 'key': 'logic_model',
 'label': 'Logic Model',
 'notes': {
           'activities': {
                          'analysis': 'Activities are the interventions the programme delivers. The relevant question '
                                      'is whether the evidence shows what is delivered, to whom and with what '
                                      'intensity, because intensity is what distinguishes one delivery from another.',
                          'probe': 'state what is delivered, to whom and at what intensity',
                          'qualify': 'The evidence does not establish what was delivered, so the model is described '
                                     'rather than assumed.',
                          'short': 'Two programmes can run the same activity and deliver very different things.'},
           'impact': {
                      'analysis': 'Impact is the long-term change the model is meant to contribute to, and the level '
                                  'at which the programme cannot claim sole responsibility. The relevant question is '
                                  'whether the evidence shows the contribution and the time horizon over which it is '
                                  'claimed.',
                      'probe': 'state the long-term change contributed to and the time horizon claimed',
                      'qualify': 'The evidence does not establish the contribution to the wider change, so impact is '
                                 'described rather than attributed.',
                      'short': 'Impact is a contribution claimed over years; a programme that claims it as an outcome '
                               'is claiming more than it can show.'},
           'inputs': {
                      'analysis': 'Inputs are the resources the programme commits: the people, the money, the time '
                                  'and the premises. The relevant question is whether the evidence shows what the '
                                  'programme commits and what it costs to commit it.',
                      'probe': 'state what the programme commits and what it costs',
                      'qualify': 'The evidence does not establish what the programme has committed, so the model is '
                                 'described rather than costed.',
                      'short': 'A model that begins with an input nobody has committed is a plan, not a logic.'},
           'outcomes': {
                        'analysis': 'Outcomes are the changes the outputs are intended to produce, and the point at '
                                    'which the model must say who will change, in what way, over what period and how '
                                    'that will be known. The relevant question is whether the evidence shows the '
                                    'outcome and the measure that reads it.',
                        'probe': 'state who will change in what way, over what period, and how that will be known',
                        'qualify': 'The evidence does not establish the change in behaviour or wellbeing, so the '
                                   'outcome is described rather than claimed.',
                        'short': 'An outcome without a time horizon is a hope, not a measure.'},
           'outputs': {
                       'analysis': 'Outputs are the direct products of the activities: what the programme can count '
                                   'as having delivered. The relevant question is whether the evidence shows the '
                                   'outputs and the measure that counts them, and whether that measure was agreed '
                                   'before delivery.',
                       'probe': 'state what the activities produced and the measure that counts it',
                       'qualify': 'The evidence does not establish what was produced, so the model is described '
                                  'rather than reported.',
                       'short': 'An output measured after the fact is a description; a measure agreed before delivery '
                                'is a commitment.'}
          },
 'outline': {'conclusion': 'Conclusion',
             'context': 'The programme and the decision',
             'discussion': 'What the evidence shows',
             'framework': 'Logic Model',
             'implications': 'Implications for the decision',
             'lead': 'A logic model links inputs, activities, outputs and outcomes into a chain of expected results. '
                     'Each link is examined in turn, first through the evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': None,
 'ratings': False,
 'sites': None,
 'subject': 'people',
 'template': 'template_logic_model',
 'title_prefix': 'Logic Model Analysis',
 'unit': {'field': 'process',
          'label': 'The programme you are describing',
          'help': 'A logic model describes one programme or intervention. Name it in a few words, for example the '
                  'campus mentoring programme or the community health outreach.',
          'example': 'the campus mentoring programme',
          'refuse': 'A logic model describes one programme or intervention. Name the programme you are describing, '
                    'for example the campus mentoring programme or the community health outreach.'},
 'voice': {'thesis_question': 'whether the evidence supports the logic the decision depends on',
           'unit_noun': 'programme',
           'block_plural': 'elements',
           'lens': 'the inputs, activities, outputs and outcomes that a programme is meant to produce',
           'closing': 'identifies the element the logic depends on and the element the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the programme rather than the sector, because a logic model '
                          'describes what one programme is meant to produce rather than what a field achieves in '
                          'general.',
           'context_frame': 'The relevant programme is the one named in the brief; the elements belong to that '
                            'programme rather than to programme design in general.',
           'interaction': 'Read together, the elements describe what the programme is built to deliver rather than '
                          'what it has delivered: an output that is counted is not yet the outcome it was meant to '
                          'produce.',
           'implication_frame': 'A decision about the programme has to name the element the case cannot show, '
                                'because a missing link between activities and outcomes leaves the claim of impact '
                                'unsupported.',
           'reference_heading': 'References'}}


STRATEGIC_POSITIONING = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'position competitive market',
             'fill': 'research',
             'key': 'position',
             'label': 'Position',
             'probe': 'state the evidence for position',
             'prompt': 'Where the firm sits relative to competitors and customers',
             'queries': ['competitive position in this industry']},
            {'category': None,
             'cues': 'differentiation distinct unique',
             'fill': 'research',
             'key': 'differentiation',
             'label': 'Differentiation',
             'probe': 'state the evidence for differentiation',
             'prompt': 'What makes the firm distinct from competitors',
             'queries': ['differentiation and distinctiveness in this industry']},
            {'category': None,
             'cues': 'value proposition customer value',
             'fill': 'research',
             'key': 'value_proposition',
             'label': 'Value Proposition',
             'probe': 'state the evidence for value proposition',
             'prompt': 'The value the firm delivers to customers',
             'queries': ['value proposition in this industry']},
            {'category': None,
             'cues': 'target segment customers serve',
             'fill': 'research',
             'key': 'target_segment',
             'label': 'Target Segment',
             'probe': 'state the evidence for target segment',
             'prompt': 'The customers the firm chooses to serve',
             'queries': ['target segment and customer focus in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'strategic_positioning',
 'label': 'Strategic Positioning',
 'notes': {'differentiation': {'analysis': 'This element describes a strategic position. The relevant question is '
                                           'whether the evidence shows it.',
                               'probe': 'state the evidence for this element',
                               'qualify': 'The evidence does not establish this element, so it is described rather '
                                          'than measured.',
                               'short': 'An element without evidence is a claim without support.'},
           'position': {'analysis': 'This element describes a strategic position. The relevant question is whether the '
                                    'evidence shows it.',
                        'probe': 'state the evidence for this element',
                        'qualify': 'The evidence does not establish this element, so it is described rather than '
                                   'measured.',
                        'short': 'An element without evidence is a claim without support.'},
           'target_segment': {'analysis': 'This element describes a strategic position. The relevant question is '
                                          'whether the evidence shows it.',
                              'probe': 'state the evidence for this element',
                              'qualify': 'The evidence does not establish this element, so it is described rather than '
                                         'measured.',
                              'short': 'An element without evidence is a claim without support.'},
           'value_proposition': {'analysis': 'This element describes a strategic position. The relevant question is '
                                             'whether the evidence shows it.',
                                 'probe': 'state the evidence for this element',
                                 'qualify': 'The evidence does not establish this element, so it is described rather '
                                            'than measured.',
                                 'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'Strategic Positioning',
             'implications': 'Implications for the decision',
             'lead': 'Strategic positioning describes where a firm sits relative to competitors and customers. Each '
                     'element is examined in turn, first through the evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'strategy',
 'template': 'template_strategic_positioning',
 'title_prefix': 'Strategic Positioning Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': 'Strategic positioning is claimed against a market. Name the industry or market.',
          'example': 'smartphones, grocery retail, banking',
          'refuse': 'Strategic positioning is claimed against a market. Name the industry or market.'},
 'voice': {'thesis_question': 'whether the evidence supports the position the decision depends on',
           'unit_noun': 'market',
           'block_plural': 'elements',
           'lens': 'the four parts of a positioning claim: the place claimed, the difference it rests on, the '
                   'value promised and the segment it is aimed at',
           'closing': 'identifies the element the position depends on and the element the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the market rather than the firm, because a position is a claim '
                          "about a place in a market rather than a description of the firm's assets.",
           'context_frame': 'The relevant market is the one named in the brief; the elements describe the position '
                            "claimed in that market rather than the firm's activity in general.",
           'interaction': 'Read together, the elements are one claim read from four sides rather than four '
                          'independent statements: a difference that no customer values, or a segment the '
                          'difference does not reach, leaves the position unclaimed.',
           'implication_frame': 'A decision about the market has to match the evidence for the difference and the '
                                'segment, because a position that is not valued by the segment it is aimed at is a '
                                'statement about the firm rather than about the market.',
           'reference_heading': 'References'}}




CHANGE_ORGANIZATION = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'change type scope',
             'fill': 'research',
             'key': 'change_type',
             'label': 'Change Type',
             'probe': 'state the evidence for the change type',
             'prompt': 'The kind of change being made and its scope',
             'queries': ['types of change and their scope in this industry']},
            {'category': None,
             'cues': 'readiness preparedness',
             'fill': 'research',
             'key': 'readiness',
             'label': 'Readiness',
             'probe': 'state the evidence for readiness',
             'prompt': 'Whether the organisation is ready for the change',
             'queries': ['readiness for change in this industry']},
            {'category': None,
             'cues': 'resistance pushback opposition',
             'fill': 'research',
             'key': 'resistance',
             'label': 'Resistance',
             'probe': 'state the evidence for resistance',
             'prompt': 'What pushes back against the change',
             'queries': ['resistance to change in this industry']},
            {'category': None,
             'cues': 'support enable sustain',
             'fill': 'research',
             'key': 'support',
             'label': 'Support',
             'probe': 'state the evidence for support',
             'prompt': 'What enables and sustains the change',
             'queries': ['support and enablers for change in this industry']}],
 'gate': {'require_geography': False, 'title_context': False, 'title_cue': False},
 'key': 'change_organization',
 'label': 'Change and Organization',
 'notes': {'change_type': {'analysis': 'This element describes an aspect of change. The relevant question is whether '
                                       'the evidence shows it.',
                           'probe': 'state the evidence for this element',
                           'qualify': 'The evidence does not establish this element, so it is described rather than '
                                      'measured.',
                           'short': 'An element without evidence is a claim without support.'},
           'readiness': {'analysis': 'This element describes an aspect of change. The relevant question is whether the '
                                     'evidence shows it.',
                         'probe': 'state the evidence for this element',
                         'qualify': 'The evidence does not establish this element, so it is described rather than '
                                    'measured.',
                         'short': 'An element without evidence is a claim without support.'},
           'resistance': {'analysis': 'This element describes an aspect of change. The relevant question is whether '
                                      'the evidence shows it.',
                          'probe': 'state the evidence for this element',
                          'qualify': 'The evidence does not establish this element, so it is described rather than '
                                     'measured.',
                          'short': 'An element without evidence is a claim without support.'},
           'support': {'analysis': 'This element describes an aspect of change. The relevant question is whether the '
                                   'evidence shows it.',
                       'probe': 'state the evidence for this element',
                       'qualify': 'The evidence does not establish this element, so it is described rather than '
                                  'measured.',
                       'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'Change and Organization',
             'implications': 'Implications for the decision',
             'lead': 'Change and organization describes four elements: change type, readiness, resistance and support. '
                     'Each is examined in turn, first through the evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': None,
 'ratings': False,
 'sites': None,
 'subject': 'change',
 'template': 'template_change_organization',
 'title_prefix': 'Change and Organization Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': 'A change and organisation review reads one programme of change in the industry or market the '
                  'organisation competes in. Name the industry or market, for example grocery retail or '
                  'healthcare.',
          'example': 'grocery retail, healthcare',
          'refuse': 'A change and organisation review is analysed for the industry or market the organisation '
                    'competes in. Name the industry or market (for example grocery retail or healthcare).'},
 'voice': {'thesis_question': 'whether the evidence supports the change and the organisation it depends on',
           'unit_noun': 'industry',
           'block_plural': 'elements',
           'lens': 'the four questions a change review asks: what kind of change it is, how ready the organisation '
                   'is, where it will resist and what support it needs',
           'closing': 'identifies the element the change depends on and the element the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the industry or market the organisation competes in rather than '
                          'the firm on its own, because the readiness, resistance and support a change meets are '
                          'measured in that market.',
           'context_frame': 'The relevant industry is the one named in the brief; the four elements belong to the '
                            'change being made in that market rather than to change work in general.',
           'interaction': 'Read together, the elements describe the change and the organisation receiving it '
                          'rather than a plan to be followed: the type of change has to be judged against the '
                          'resistance the evidence shows.',
           'implication_frame': 'A decision about the change has to match the type of change and the resistance it '
                                'meets, because the support that carries a small local change will not carry one '
                                'that alters roles or identity.',
           'reference_heading': 'References'}}


MARKETING_PLAN = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'segmentation market divide',
             'fill': 'research',
             'key': 'segmentation',
             'label': 'Segmentation',
             'probe': 'state the evidence for segmentation',
             'prompt': 'How the market is divided into segments',
             'queries': ['market segmentation in this industry']},
            {'category': None,
             'cues': 'targeting segments chosen',
             'fill': 'research',
             'key': 'targeting',
             'label': 'Targeting',
             'probe': 'state the evidence for targeting',
             'prompt': 'Which segments are chosen and why',
             'queries': ['targeting and segment selection in this industry']},
            {'category': None,
             'cues': 'positioning offer market',
             'fill': 'research',
             'key': 'positioning',
             'label': 'Positioning',
             'probe': 'state the evidence for positioning',
             'prompt': 'How the offer is positioned in the market',
             'queries': ['positioning and differentiation in this industry']},
            {'category': None,
             'cues': 'product offer features',
             'fill': 'research',
             'key': 'product',
             'label': 'Product',
             'probe': 'state the evidence for the product',
             'prompt': 'What the offer is and what it does',
             'queries': ['product and offer design in this industry']},
            {'category': None,
             'cues': 'price cost pricing',
             'fill': 'research',
             'key': 'price',
             'label': 'Price',
             'probe': 'state the evidence for price',
             'prompt': 'What the offer costs and why',
             'queries': ['pricing strategy in this industry']},
            {'category': None,
             'cues': 'place distribution channel',
             'fill': 'research',
             'key': 'place',
             'label': 'Place',
             'probe': 'state the evidence for place',
             'prompt': 'Where and how the offer is distributed',
             'queries': ['distribution and channels in this industry']},
            {'category': None,
             'cues': 'promotion communication marketing',
             'fill': 'research',
             'key': 'promotion',
             'label': 'Promotion',
             'probe': 'state the evidence for promotion',
             'prompt': 'How the offer is communicated',
             'queries': ['promotion and communication in this industry']},
            {'category': None,
             'cues': 'people staff service',
             'fill': 'research',
             'key': 'people',
             'label': 'People',
             'probe': 'state the evidence for people',
             'prompt': 'The people involved in delivering the offer',
             'queries': ['people and service delivery in this industry']},
            {'category': None,
             'cues': 'process delivery service',
             'fill': 'research',
             'key': 'process',
             'label': 'Process',
             'probe': 'state the evidence for process',
             'prompt': 'The processes that deliver the offer',
             'queries': ['processes and service delivery in this industry']},
            {'category': None,
             'cues': 'physical evidence tangible',
             'fill': 'research',
             'key': 'physical_evidence',
             'label': 'Physical Evidence',
             'probe': 'state the evidence for physical evidence',
             'prompt': 'The tangible elements of the offer',
             'queries': ['physical evidence and tangibles in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'marketing_plan',
 'label': 'Marketing Plan',
 'notes': {'people': {'analysis': 'This element describes an aspect of the marketing plan. The relevant question is '
                                  'whether the evidence shows it.',
                      'probe': 'state the evidence for this element',
                      'qualify': 'The evidence does not establish this element, so it is described rather than '
                                 'measured.',
                      'short': 'An element without evidence is a claim without support.'},
           'physical_evidence': {'analysis': 'This element describes an aspect of the marketing plan. The relevant '
                                             'question is whether the evidence shows it.',
                                 'probe': 'state the evidence for this element',
                                 'qualify': 'The evidence does not establish this element, so it is described rather '
                                            'than measured.',
                                 'short': 'An element without evidence is a claim without support.'},
           'place': {'analysis': 'This element describes an aspect of the marketing plan. The relevant question is '
                                 'whether the evidence shows it.',
                     'probe': 'state the evidence for this element',
                     'qualify': 'The evidence does not establish this element, so it is described rather than '
                                'measured.',
                     'short': 'An element without evidence is a claim without support.'},
           'positioning': {'analysis': 'This element describes an aspect of the marketing plan. The relevant question '
                                       'is whether the evidence shows it.',
                           'probe': 'state the evidence for this element',
                           'qualify': 'The evidence does not establish this element, so it is described rather than '
                                      'measured.',
                           'short': 'An element without evidence is a claim without support.'},
           'price': {'analysis': 'This element describes an aspect of the marketing plan. The relevant question is '
                                 'whether the evidence shows it.',
                     'probe': 'state the evidence for this element',
                     'qualify': 'The evidence does not establish this element, so it is described rather than '
                                'measured.',
                     'short': 'An element without evidence is a claim without support.'},
           'process': {'analysis': 'This element describes an aspect of the marketing plan. The relevant question is '
                                   'whether the evidence shows it.',
                       'probe': 'state the evidence for this element',
                       'qualify': 'The evidence does not establish this element, so it is described rather than '
                                  'measured.',
                       'short': 'An element without evidence is a claim without support.'},
           'product': {'analysis': 'This element describes an aspect of the marketing plan. The relevant question is '
                                   'whether the evidence shows it.',
                       'probe': 'state the evidence for this element',
                       'qualify': 'The evidence does not establish this element, so it is described rather than '
                                  'measured.',
                       'short': 'An element without evidence is a claim without support.'},
           'promotion': {'analysis': 'This element describes an aspect of the marketing plan. The relevant question is '
                                     'whether the evidence shows it.',
                         'probe': 'state the evidence for this element',
                         'qualify': 'The evidence does not establish this element, so it is described rather than '
                                    'measured.',
                         'short': 'An element without evidence is a claim without support.'},
           'segmentation': {'analysis': 'This element describes an aspect of the marketing plan. The relevant question '
                                        'is whether the evidence shows it.',
                            'probe': 'state the evidence for this element',
                            'qualify': 'The evidence does not establish this element, so it is described rather than '
                                       'measured.',
                            'short': 'An element without evidence is a claim without support.'},
           'targeting': {'analysis': 'This element describes an aspect of the marketing plan. The relevant question is '
                                     'whether the evidence shows it.',
                         'probe': 'state the evidence for this element',
                         'qualify': 'The evidence does not establish this element, so it is described rather than '
                                    'measured.',
                         'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'Marketing Plan',
             'implications': 'Implications for the decision',
             'lead': 'A marketing plan covers segmentation, targeting, positioning and the marketing mix. Each element '
                     'is examined in turn, first through the evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_marketing_plan',
 'title_prefix': 'Marketing Plan Analysis',
 'unit': {'example': 'smartphones, grocery retail, banking',
          'field': 'industry',
          'help': 'A marketing plan is set for a firm in a market. Name the industry or market.',
          'label': 'Industry or market',
          'refuse': 'A marketing plan is set for a firm in a market. Name the industry or market.'},
 'voice': {'block_plural': 'elements',
           'closing': 'identifies the element with the strongest evidence and the one most unsupported',
           'context_frame': 'The relevant industry is the one named in the brief; the elements describe the plan '
                            'for that market rather than the plan the firm would prefer.',
           'implication_frame': 'A decision about the plan has to match the evidence the market supports: the '
                                'segment chosen has to justify the position, and the mix has to deliver that '
                                'position at a price and through channels the market accepts.',
           'interaction': 'Read together, the elements describe one plan in which some evidence is present and '
                          'some is not, and an element without evidence carries no weight.',
           'intro_frame': 'The unit of analysis is the industry or market, because the plan is read against the '
                          'market it addresses rather than describing the activity of the firm.',
           'lens': 'the segmentation, targeting and positioning decisions and the marketing mix that delivers them',
           'reference_heading': 'References',
           'thesis_question': 'whether the evidence supports the marketing plan the decision relies on',
           'unit_noun': 'industry'}}


KANO = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'must be basic expectations',
             'fill': 'research',
             'key': 'must_be',
             'label': 'Must-Be',
             'probe': 'state the evidence for must-be qualities',
             'prompt': 'Basic expectations customers take for granted',
             'queries': ['must-be qualities and basic expectations in this industry']},
            {'category': None,
             'cues': 'performance more better',
             'fill': 'research',
             'key': 'performance',
             'label': 'Performance',
             'probe': 'state the evidence for performance qualities',
             'prompt': 'Qualities where more is better',
             'queries': ['performance qualities in this industry']},
            {'category': None,
             'cues': 'attractive delighters surprise',
             'fill': 'research',
             'key': 'attractive',
             'label': 'Attractive',
             'probe': 'state the evidence for attractive qualities',
             'prompt': 'Delighters that surprise and please customers',
             'queries': ['attractive and delighter qualities in this industry']},
            {'category': None,
             'cues': 'indifferent neutral dont care',
             'fill': 'research',
             'key': 'indifferent',
             'label': 'Indifferent',
             'probe': 'state the evidence for indifferent qualities',
             'prompt': 'Qualities customers do not care about',
             'queries': ['indifferent qualities in this industry']},
            {'category': None,
             'cues': 'reverse annoy dislike',
             'fill': 'research',
             'key': 'reverse',
             'label': 'Reverse',
             'probe': 'state the evidence for reverse qualities',
             'prompt': 'Qualities that annoy some customers',
             'queries': ['reverse qualities that annoy in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'kano',
 'label': 'Kano Model',
 'notes': {'attractive': {'analysis': 'This category describes a type of customer requirement. The relevant question '
                                      'is whether the evidence shows it.',
                          'probe': 'state the evidence for this category',
                          'qualify': 'The evidence does not establish this category, so it is described rather than '
                                     'measured.',
                          'short': 'A category without evidence is a claim without support.'},
           'indifferent': {'analysis': 'This category describes a type of customer requirement. The relevant question '
                                       'is whether the evidence shows it.',
                           'probe': 'state the evidence for this category',
                           'qualify': 'The evidence does not establish this category, so it is described rather than '
                                      'measured.',
                           'short': 'A category without evidence is a claim without support.'},
           'must_be': {'analysis': 'This category describes a type of customer requirement. The relevant question is '
                                   'whether the evidence shows it.',
                       'probe': 'state the evidence for this category',
                       'qualify': 'The evidence does not establish this category, so it is described rather than '
                                  'measured.',
                       'short': 'A category without evidence is a claim without support.'},
           'performance': {'analysis': 'This category describes a type of customer requirement. The relevant question '
                                       'is whether the evidence shows it.',
                           'probe': 'state the evidence for this category',
                           'qualify': 'The evidence does not establish this category, so it is described rather than '
                                      'measured.',
                           'short': 'A category without evidence is a claim without support.'},
           'reverse': {'analysis': 'This category describes a type of customer requirement. The relevant question is '
                                   'whether the evidence shows it.',
                       'probe': 'state the evidence for this category',
                       'qualify': 'The evidence does not establish this category, so it is described rather than '
                                  'measured.',
                       'short': 'A category without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'Kano Model',
             'implications': 'Implications for the decision',
             'lead': 'The Kano model classifies customer requirements into five categories: must-be, performance, '
                     'attractive, indifferent and reverse. Each is examined in turn, first through the evidence and '
                     'then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_kano',
 'title_prefix': 'Kano Model Analysis',
 'unit': {'example': 'smartphones, grocery retail, banking',
          'field': 'industry',
          'help': 'The Kano model classifies requirements for a firm in a market. Name the industry or market.',
          'label': 'Industry or market',
          'refuse': 'The Kano model classifies requirements for a firm in a market. Name the industry or market.'},
 'voice': {'block_plural': 'categories',
           'closing': 'identifies the category with the strongest evidence and the one most unsupported',
           'context_frame': 'The relevant industry is the one named in the brief; the categories are how customers '
                            'in that market judge the offer.',
           'implication_frame': 'A decision about the offer has to match the categories the evidence supports: a '
                                'must-be quality left unmet loses the customer, while an attractive quality is '
                                'where the offer can be judged better than rivals.',
           'interaction': 'Read together, the categories describe one set of requirements in which some evidence '
                          'is present and some is not, and a category without evidence carries no weight.',
           'intro_frame': 'The unit of analysis is the industry or market, because the categories describe how '
                          'customers in that market react to quality rather than what the firm intends to deliver.',
           'lens': 'the five quality categories, from must-be to reverse',
           'reference_heading': 'References',
           'thesis_question': 'whether the evidence supports the quality classification the decision relies on',
           'unit_noun': 'industry'}}


PAID_MEDIA_PLAN = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'objective goal aim',
             'fill': 'research',
             'key': 'objective',
             'label': 'Objective',
             'probe': 'state the evidence for the objective',
             'prompt': 'What the campaign aims to achieve',
             'queries': ['campaign objectives in this industry']},
            {'category': None,
             'cues': 'audience target segment',
             'fill': 'research',
             'key': 'audience',
             'label': 'Audience',
             'probe': 'state the evidence for the audience',
             'prompt': 'Who the campaign targets',
             'queries': ['target audience in this industry']},
            {'category': None,
             'cues': 'channels placements where',
             'fill': 'research',
             'key': 'channels_placements',
             'label': 'Channels & Placements',
             'probe': 'state the evidence for channels',
             'prompt': 'Where the campaign runs',
             'queries': ['channels and placements in this industry']},
            {'category': None,
             'cues': 'budget bid spend',
             'fill': 'research',
             'key': 'budget_bid',
             'label': 'Budget & Bid',
             'probe': 'state the evidence for budget',
             'prompt': 'How much is spent and how bids are set',
             'queries': ['budget and bidding in this industry']},
            {'category': None,
             'cues': 'creative variants test',
             'fill': 'research',
             'key': 'creative_variants',
             'label': 'Creative Variants',
             'probe': 'state the evidence for creative',
             'prompt': 'What creative is tested',
             'queries': ['creative variants and testing in this industry']},
            {'category': None,
             'cues': 'conversion definition action',
             'fill': 'research',
             'key': 'conversion_definition',
             'label': 'Conversion Definition',
             'probe': 'state the evidence for conversion',
             'prompt': 'What counts as a conversion',
             'queries': ['conversion definition in this industry']},
            {'category': None,
             'cues': 'measurement tracking metrics',
             'fill': 'research',
             'key': 'measurement',
             'label': 'Measurement',
             'probe': 'state the evidence for measurement',
             'prompt': 'How the campaign is measured',
             'queries': ['measurement and tracking in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'paid_media_plan',
 'label': 'Paid Media Plan',
 'notes': {'audience': {'analysis': 'This element describes an aspect of the media plan. The relevant question is '
                                    'whether the evidence shows it.',
                        'probe': 'state the evidence for this element',
                        'qualify': 'The evidence does not establish this element, so it is described rather than '
                                   'measured.',
                        'short': 'An element without evidence is a claim without support.'},
           'budget_bid': {'analysis': 'This element describes an aspect of the media plan. The relevant question is '
                                      'whether the evidence shows it.',
                          'probe': 'state the evidence for this element',
                          'qualify': 'The evidence does not establish this element, so it is described rather than '
                                     'measured.',
                          'short': 'An element without evidence is a claim without support.'},
           'channels_placements': {'analysis': 'This element describes an aspect of the media plan. The relevant '
                                               'question is whether the evidence shows it.',
                                   'probe': 'state the evidence for this element',
                                   'qualify': 'The evidence does not establish this element, so it is described rather '
                                              'than measured.',
                                   'short': 'An element without evidence is a claim without support.'},
           'conversion_definition': {'analysis': 'This element describes an aspect of the media plan. The relevant '
                                                 'question is whether the evidence shows it.',
                                     'probe': 'state the evidence for this element',
                                     'qualify': 'The evidence does not establish this element, so it is described '
                                                'rather than measured.',
                                     'short': 'An element without evidence is a claim without support.'},
           'creative_variants': {'analysis': 'This element describes an aspect of the media plan. The relevant '
                                             'question is whether the evidence shows it.',
                                 'probe': 'state the evidence for this element',
                                 'qualify': 'The evidence does not establish this element, so it is described rather '
                                            'than measured.',
                                 'short': 'An element without evidence is a claim without support.'},
           'measurement': {'analysis': 'This element describes an aspect of the media plan. The relevant question is '
                                       'whether the evidence shows it.',
                           'probe': 'state the evidence for this element',
                           'qualify': 'The evidence does not establish this element, so it is described rather than '
                                      'measured.',
                           'short': 'An element without evidence is a claim without support.'},
           'objective': {'analysis': 'This element describes an aspect of the media plan. The relevant question is '
                                     'whether the evidence shows it.',
                         'probe': 'state the evidence for this element',
                         'qualify': 'The evidence does not establish this element, so it is described rather than '
                                    'measured.',
                         'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'Paid Media Plan',
             'implications': 'Implications for the decision',
             'lead': 'A paid media plan covers objective, audience, channels, budget, creative, conversion and '
                     'measurement. Each is examined in turn, first through the evidence and then through what it '
                     'implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_paid_media_plan',
 'title_prefix': 'Paid Media Plan Analysis',
 'unit': {'example': 'smartphones, grocery retail, banking',
          'field': 'industry',
          'help': 'A paid media plan is set for a firm in a market. Name the industry or market.',
          'label': 'Industry or market',
          'refuse': 'A paid media plan is set for a firm in a market. Name the industry or market.'},
 'voice': {'block_plural': 'elements',
           'closing': 'identifies the element with the strongest evidence and the one most unsupported',
           'context_frame': 'The relevant industry is the one named in the brief; the elements describe the media '
                            'bought in that market rather than the media the firm would prefer.',
           'implication_frame': 'A decision about the plan has to match what the market can deliver: the audience '
                                'has to be reachable on the named channels, the budget has to carry the bid, and '
                                'the conversion definition has to match what the plan is judged on.',
           'interaction': 'Read together, the elements describe one plan in which some evidence is present and '
                          'some is not, and an element without evidence carries no weight.',
           'intro_frame': 'The unit of analysis is the industry or market, because the plan buys attention in '
                          'that market rather than describing the activity of the firm.',
           'lens': 'the objective, audience, channels, budget, creative, conversion definition and measurement the plan sets out',
           'reference_heading': 'References',
           'thesis_question': 'whether the evidence supports the media plan the decision relies on',
           'unit_noun': 'industry'}}


MEASUREMENT_PLAN = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'questions aims answer',
             'fill': 'research',
             'key': 'questions',
             'label': 'Questions',
             'probe': 'state the evidence for the questions',
             'prompt': 'What the measurement plan aims to answer',
             'queries': ['measurement questions in this industry']},
            {'category': None,
             'cues': 'metrics tracked KPIs',
             'fill': 'research',
             'key': 'metrics',
             'label': 'Metrics',
             'probe': 'state the evidence for the metrics',
             'prompt': 'The metrics that will be tracked',
             'queries': ['metrics and KPIs in this industry']},
            {'category': None,
             'cues': 'events dimensions capture tracking',
             'fill': 'research',
             'key': 'events_dimensions',
             'label': 'Events & Dimensions',
             'probe': 'state the evidence for events and dimensions',
             'prompt': 'The events and dimensions to capture',
             'queries': ['events and dimensions to track in this industry']},
            {'category': None,
             'cues': 'data quality accuracy',
             'fill': 'research',
             'key': 'data_quality',
             'label': 'Data Quality',
             'probe': 'state the evidence for data quality',
             'prompt': 'How data quality is ensured',
             'queries': ['data quality and accuracy in this industry']},
            {'category': None,
             'cues': 'governance ownership data',
             'fill': 'research',
             'key': 'governance',
             'label': 'Governance',
             'probe': 'state the evidence for governance',
             'prompt': 'Who owns the data and how it is governed',
             'queries': ['data governance in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'measurement_plan',
 'label': 'Measurement Plan',
 'notes': {'data_quality': {'analysis': 'This element describes an aspect of the measurement plan. The relevant '
                                        'question is whether the evidence shows it.',
                            'probe': 'state the evidence for this element',
                            'qualify': 'The evidence does not establish this element, so it is described rather than '
                                       'measured.',
                            'short': 'An element without evidence is a claim without support.'},
           'events_dimensions': {'analysis': 'This element describes an aspect of the measurement plan. The relevant '
                                             'question is whether the evidence shows it.',
                                 'probe': 'state the evidence for this element',
                                 'qualify': 'The evidence does not establish this element, so it is described rather '
                                            'than measured.',
                                 'short': 'An element without evidence is a claim without support.'},
           'governance': {'analysis': 'This element describes an aspect of the measurement plan. The relevant question '
                                      'is whether the evidence shows it.',
                          'probe': 'state the evidence for this element',
                          'qualify': 'The evidence does not establish this element, so it is described rather than '
                                     'measured.',
                          'short': 'An element without evidence is a claim without support.'},
           'metrics': {'analysis': 'This element describes an aspect of the measurement plan. The relevant question is '
                                   'whether the evidence shows it.',
                       'probe': 'state the evidence for this element',
                       'qualify': 'The evidence does not establish this element, so it is described rather than '
                                  'measured.',
                       'short': 'An element without evidence is a claim without support.'},
           'questions': {'analysis': 'This element describes an aspect of the measurement plan. The relevant question '
                                     'is whether the evidence shows it.',
                         'probe': 'state the evidence for this element',
                         'qualify': 'The evidence does not establish this element, so it is described rather than '
                                    'measured.',
                         'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'Measurement Plan',
             'implications': 'Implications for the decision',
             'lead': 'A measurement plan covers questions, metrics, events, data quality and governance. Each is '
                     'examined in turn, first through the evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_measurement_plan',
 'title_prefix': 'Measurement Plan Analysis',
 'unit': {'example': 'smartphones, grocery retail, banking',
          'field': 'industry',
          'help': 'A measurement plan is set for a firm in a market. Name the industry or market.',
          'label': 'Industry or market',
          'refuse': 'A measurement plan is set for a firm in a market. Name the industry or market.'},
 'voice': {'block_plural': 'elements',
           'closing': 'identifies the element with the strongest evidence and the one most unsupported',
           'context_frame': 'The relevant industry is the one named in the brief; the elements describe what is '
                            'measured in that market rather than what the firm finds convenient.',
           'implication_frame': 'A decision about the plan has to match what the market can actually measure: each '
                                'metric has to answer a stated question, rest on events that are captured, and be '
                                'owned by someone accountable for its quality.',
           'interaction': 'Read together, the elements describe one plan in which some evidence is present and '
                          'some is not, and an element without evidence carries no weight.',
           'intro_frame': 'The unit of analysis is the industry or market, because the plan measures outcomes in '
                          'that market rather than describing the activity of the firm.',
           'lens': 'the questions, metrics, events, data quality and governance the plan sets out',
           'reference_heading': 'References',
           'thesis_question': 'whether the evidence supports the measurement plan the decision relies on',
           'unit_noun': 'industry'}}


STP = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'segmentation market divide',
             'fill': 'research',
             'key': 'segmentation',
             'label': 'Segmentation',
             'probe': 'state the evidence for segmentation',
             'prompt': 'How the market is divided into segments',
             'queries': ['market segmentation in this industry']},
            {'category': None,
             'cues': 'targeting segments chosen',
             'fill': 'research',
             'key': 'targeting',
             'label': 'Targeting',
             'probe': 'state the evidence for targeting',
             'prompt': 'Which segments are chosen and why',
             'queries': ['targeting and segment selection in this industry']},
            {'category': None,
             'cues': 'positioning offer market',
             'fill': 'research',
             'key': 'positioning',
             'label': 'Positioning',
             'probe': 'state the evidence for positioning',
             'prompt': 'How the offer is positioned in the market',
             'queries': ['positioning and differentiation in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'stp',
 'label': 'STP',
 'notes': {'positioning': {'analysis': 'This element describes an aspect of stp. The relevant question is whether the '
                                       'evidence shows it.',
                           'probe': 'state the evidence for this element',
                           'qualify': 'The evidence does not establish this element, so it is described rather than '
                                      'measured.',
                           'short': 'An element without evidence is a claim without support.'},
           'segmentation': {'analysis': 'This element describes an aspect of stp. The relevant question is whether the '
                                        'evidence shows it.',
                            'probe': 'state the evidence for this element',
                            'qualify': 'The evidence does not establish this element, so it is described rather than '
                                       'measured.',
                            'short': 'An element without evidence is a claim without support.'},
           'targeting': {'analysis': 'This element describes an aspect of stp. The relevant question is whether the '
                                     'evidence shows it.',
                         'probe': 'state the evidence for this element',
                         'qualify': 'The evidence does not establish this element, so it is described rather than '
                                    'measured.',
                         'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'STP',
             'implications': 'Implications for the decision',
             'lead': 'STP examines its elements. Each is examined in turn, first through the evidence and then through '
                     'what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_stp',
 'title_prefix': 'STP Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': 'Segmentation, targeting and positioning are decided against a market. Name the industry or market.',
          'example': 'smartphones, grocery retail, banking',
          'refuse': 'Segmentation, targeting and positioning are decided against a market. Name the industry or '
                    'market.'},
 'voice': {'thesis_question': 'whether the evidence supports the segmentation and positioning the decision depends on',
           'unit_noun': 'market',
           'block_plural': 'elements',
           'lens': 'the three decisions that lead from dividing a market to claiming a place in it',
           'closing': 'identifies the decision the evidence supports and the decision the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the market rather than the firm, because segmentation divides a '
                          'market and positioning is a claim made inside it.',
           'context_frame': 'The relevant market is the one named in the brief; the elements describe how that '
                            "market was divided, chosen and entered rather than the firm's activities in general.",
           'interaction': 'Read together, the elements are a chain rather than three independent statements: a '
                          'target chosen without a segment the evidence supports is a preference, and a position '
                          'that does not fit the target it was chosen for will not hold.',
           'implication_frame': 'A decision about the market has to match the evidence for the segment and the '
                                'target, because a position built for a segment the firm has not chosen is a claim '
                                'without a customer.',
           'reference_heading': 'References'}}


AIDA = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'attention awareness capture',
             'fill': 'research',
             'key': 'attention',
             'label': 'Attention',
             'probe': 'state the evidence for attention',
             'prompt': 'How awareness is captured',
             'queries': ['capturing attention and awareness in this industry']},
            {'category': None,
             'cues': 'interest sustain engage',
             'fill': 'research',
             'key': 'interest',
             'label': 'Interest',
             'probe': 'state the evidence for interest',
             'prompt': 'How interest is sustained',
             'queries': ['sustaining interest in this industry']},
            {'category': None,
             'cues': 'desire create want',
             'fill': 'research',
             'key': 'desire',
             'label': 'Desire',
             'probe': 'state the evidence for desire',
             'prompt': 'How desire is created',
             'queries': ['creating desire in this industry']},
            {'category': None,
             'cues': 'action trigger convert',
             'fill': 'research',
             'key': 'action',
             'label': 'Action',
             'probe': 'state the evidence for action',
             'prompt': 'How action is triggered',
             'queries': ['triggering action in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'aida',
 'label': 'AIDA',
 'notes': {'action': {'analysis': 'This element describes an aspect of aida. The relevant question is whether the '
                                  'evidence shows it.',
                      'probe': 'state the evidence for this element',
                      'qualify': 'The evidence does not establish this element, so it is described rather than '
                                 'measured.',
                      'short': 'An element without evidence is a claim without support.'},
           'attention': {'analysis': 'This element describes an aspect of aida. The relevant question is whether the '
                                     'evidence shows it.',
                         'probe': 'state the evidence for this element',
                         'qualify': 'The evidence does not establish this element, so it is described rather than '
                                    'measured.',
                         'short': 'An element without evidence is a claim without support.'},
           'desire': {'analysis': 'This element describes an aspect of aida. The relevant question is whether the '
                                  'evidence shows it.',
                      'probe': 'state the evidence for this element',
                      'qualify': 'The evidence does not establish this element, so it is described rather than '
                                 'measured.',
                      'short': 'An element without evidence is a claim without support.'},
           'interest': {'analysis': 'This element describes an aspect of aida. The relevant question is whether the '
                                    'evidence shows it.',
                        'probe': 'state the evidence for this element',
                        'qualify': 'The evidence does not establish this element, so it is described rather than '
                                   'measured.',
                        'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'AIDA',
             'implications': 'Implications for the decision',
             'lead': 'AIDA examines its elements. Each is examined in turn, first through the evidence and then '
                     'through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_aida',
 'title_prefix': 'AIDA Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': 'AIDA describes how an audience in a market is reached. Name the industry or market.',
          'example': 'smartphones, grocery retail, banking',
          'refuse': 'AIDA describes how an audience in a market is reached. Name the industry or market.'},
 'voice': {'thesis_question': 'whether the evidence supports the journey the decision depends on',
           'unit_noun': 'market',
           'block_plural': 'stages',
           'lens': 'the four stages a communication journey passes through, from attention to action',
           'closing': 'identifies the stage the journey depends on and the stage the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the market rather than the firm, because AIDA describes how an '
                          'audience in a market moves rather than what the firm does.',
           'context_frame': 'The relevant market is the one named in the brief; the stages belong to the journey '
                            'in that market rather than to communication activity in general.',
           'interaction': 'Read together, the stages describe a simplified journey rather than a rule: the '
                          'evidence has to show where the audience actually moves, because few customers move '
                          'through the stages in a straight line.',
           'implication_frame': 'A decision about the campaign has to match the stage the evidence shows, because '
                                'spend aimed at a stage the audience has already passed does not bring it further '
                                'along.',
           'reference_heading': 'References'}}


CUSTOMER_JOURNEY = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'awareness learn discover',
             'fill': 'research',
             'key': 'awareness',
             'label': 'Awareness',
             'probe': 'state the evidence for awareness',
             'prompt': 'How customers first learn about the offer',
             'queries': ['customer awareness in this industry']},
            {'category': None,
             'cues': 'consideration evaluate compare',
             'fill': 'research',
             'key': 'consideration',
             'label': 'Consideration',
             'probe': 'state the evidence for consideration',
             'prompt': 'How customers evaluate the offer',
             'queries': ['customer consideration in this industry']},
            {'category': None,
             'cues': 'purchase buy convert',
             'fill': 'research',
             'key': 'purchase',
             'label': 'Purchase',
             'probe': 'state the evidence for purchase',
             'prompt': 'How customers buy the offer',
             'queries': ['customer purchase in this industry']},
            {'category': None,
             'cues': 'retention keep loyal',
             'fill': 'research',
             'key': 'retention',
             'label': 'Retention',
             'probe': 'state the evidence for retention',
             'prompt': 'How customers are kept after purchase',
             'queries': ['customer retention in this industry']},
            {'category': None,
             'cues': 'advocacy recommend refer',
             'fill': 'research',
             'key': 'advocacy',
             'label': 'Advocacy',
             'probe': 'state the evidence for advocacy',
             'prompt': 'How customers recommend the offer',
             'queries': ['customer advocacy in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'customer_journey',
 'label': 'Customer Journey',
 'notes': {'advocacy': {'analysis': 'This element describes an aspect of customer journey. The relevant question is '
                                    'whether the evidence shows it.',
                        'probe': 'state the evidence for this element',
                        'qualify': 'The evidence does not establish this element, so it is described rather than '
                                   'measured.',
                        'short': 'An element without evidence is a claim without support.'},
           'awareness': {'analysis': 'This element describes an aspect of customer journey. The relevant question is '
                                     'whether the evidence shows it.',
                         'probe': 'state the evidence for this element',
                         'qualify': 'The evidence does not establish this element, so it is described rather than '
                                    'measured.',
                         'short': 'An element without evidence is a claim without support.'},
           'consideration': {'analysis': 'This element describes an aspect of customer journey. The relevant question '
                                         'is whether the evidence shows it.',
                             'probe': 'state the evidence for this element',
                             'qualify': 'The evidence does not establish this element, so it is described rather than '
                                        'measured.',
                             'short': 'An element without evidence is a claim without support.'},
           'purchase': {'analysis': 'This element describes an aspect of customer journey. The relevant question is '
                                    'whether the evidence shows it.',
                        'probe': 'state the evidence for this element',
                        'qualify': 'The evidence does not establish this element, so it is described rather than '
                                   'measured.',
                        'short': 'An element without evidence is a claim without support.'},
           'retention': {'analysis': 'This element describes an aspect of customer journey. The relevant question is '
                                     'whether the evidence shows it.',
                         'probe': 'state the evidence for this element',
                         'qualify': 'The evidence does not establish this element, so it is described rather than '
                                    'measured.',
                         'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'Customer Journey',
             'implications': 'Implications for the decision',
             'lead': 'Customer Journey examines its elements. Each is examined in turn, first through the evidence and '
                     'then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_customer_journey',
 'title_prefix': 'Customer Journey Analysis',
 'unit': {'example': 'smartphones, grocery retail, banking',
          'field': 'industry',
          'help': 'The customer journey is read for a firm in a market. Name the industry or market.',
          'label': 'Industry or market',
          'refuse': 'The customer journey is read for a firm in a market. Name the industry or market.'},
 'voice': {'block_plural': 'stages',
           'closing': 'identifies the element with the strongest evidence and the one most unsupported',
           'context_frame': 'The relevant industry is the one named in the brief; the stages are behaviours of '
                            'customers in that market.',
           'implication_frame': 'A decision about the offer has to match the journey the evidence supports: what '
                                'draws customers in at awareness has to be carried through consideration and '
                                'purchase to retention and advocacy.',
           'interaction': 'Read together, the stages describe one journey in which some evidence is present and '
                          'some is not, and a stage without evidence carries no weight.',
           'intro_frame': 'The unit of analysis is the industry or market, because the journey describes how '
                          'customers behave in that market rather than inside the firm.',
           'lens': 'the five stages a customer passes through, from awareness to advocacy',
           'reference_heading': 'References',
           'thesis_question': 'whether the evidence supports the customer journey the decision relies on',
           'unit_noun': 'industry'}}


FUNNEL = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'awareness enter funnel',
             'fill': 'research',
             'key': 'awareness',
             'label': 'Awareness',
             'probe': 'state the evidence for awareness',
             'prompt': 'How prospects enter the funnel',
             'queries': ['funnel awareness in this industry']},
            {'category': None,
             'cues': 'interest capture engage',
             'fill': 'research',
             'key': 'interest',
             'label': 'Interest',
             'probe': 'state the evidence for interest',
             'prompt': 'How interest is captured',
             'queries': ['funnel interest in this industry']},
            {'category': None,
             'cues': 'consideration evaluate',
             'fill': 'research',
             'key': 'consideration',
             'label': 'Consideration',
             'probe': 'state the evidence for consideration',
             'prompt': 'How prospects evaluate',
             'queries': ['funnel consideration in this industry']},
            {'category': None,
             'cues': 'intent form decide',
             'fill': 'research',
             'key': 'intent',
             'label': 'Intent',
             'probe': 'state the evidence for intent',
             'prompt': 'How intent is formed',
             'queries': ['funnel intent in this industry']},
            {'category': None,
             'cues': 'evaluation decision final',
             'fill': 'research',
             'key': 'evaluation',
             'label': 'Evaluation',
             'probe': 'state the evidence for evaluation',
             'prompt': 'How the final decision is made',
             'queries': ['funnel evaluation in this industry']},
            {'category': None,
             'cues': 'purchase buy convert',
             'fill': 'research',
             'key': 'purchase',
             'label': 'Purchase',
             'probe': 'state the evidence for purchase',
             'prompt': 'How the purchase happens',
             'queries': ['funnel purchase in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'funnel',
 'label': 'Funnel',
 'notes': {'awareness': {'analysis': 'This element describes an aspect of funnel. The relevant question is whether the '
                                     'evidence shows it.',
                         'probe': 'state the evidence for this element',
                         'qualify': 'The evidence does not establish this element, so it is described rather than '
                                    'measured.',
                         'short': 'An element without evidence is a claim without support.'},
           'consideration': {'analysis': 'This element describes an aspect of funnel. The relevant question is whether '
                                         'the evidence shows it.',
                             'probe': 'state the evidence for this element',
                             'qualify': 'The evidence does not establish this element, so it is described rather than '
                                        'measured.',
                             'short': 'An element without evidence is a claim without support.'},
           'evaluation': {'analysis': 'This element describes an aspect of funnel. The relevant question is whether '
                                      'the evidence shows it.',
                          'probe': 'state the evidence for this element',
                          'qualify': 'The evidence does not establish this element, so it is described rather than '
                                     'measured.',
                          'short': 'An element without evidence is a claim without support.'},
           'intent': {'analysis': 'This element describes an aspect of funnel. The relevant question is whether the '
                                  'evidence shows it.',
                      'probe': 'state the evidence for this element',
                      'qualify': 'The evidence does not establish this element, so it is described rather than '
                                 'measured.',
                      'short': 'An element without evidence is a claim without support.'},
           'interest': {'analysis': 'This element describes an aspect of funnel. The relevant question is whether the '
                                    'evidence shows it.',
                        'probe': 'state the evidence for this element',
                        'qualify': 'The evidence does not establish this element, so it is described rather than '
                                   'measured.',
                        'short': 'An element without evidence is a claim without support.'},
           'purchase': {'analysis': 'This element describes an aspect of funnel. The relevant question is whether the '
                                    'evidence shows it.',
                        'probe': 'state the evidence for this element',
                        'qualify': 'The evidence does not establish this element, so it is described rather than '
                                   'measured.',
                        'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'Funnel',
             'implications': 'Implications for the decision',
             'lead': 'Funnel examines its elements. Each is examined in turn, first through the evidence and then '
                     'through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_funnel',
 'title_prefix': 'Funnel Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': 'A funnel is measured for a market or a defined audience. Name the industry or market.',
          'example': 'smartphones, grocery retail, banking',
          'refuse': 'A funnel is measured for a market or a defined audience. Name the industry or market.'},
 'voice': {'thesis_question': 'whether the evidence supports the conversion path the decision depends on',
           'unit_noun': 'market',
           'block_plural': 'stages',
           'lens': 'the stages a defined audience passes through, and the conversion between each one',
           'closing': 'identifies the stage the path depends on and the stage the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the market rather than the firm, because a funnel is a measured '
                          "path through a market rather than a description of the seller's activity.",
           'context_frame': 'The relevant market is the one named in the brief; the stages belong to the path that '
                            'audience takes rather than to the funnel the firm would like it to take.',
           'interaction': 'Read together, the stages describe where the audience is lost rather than where it '
                          'might be won: a stage with a large drop and no evidence about it is a leak the plan '
                          'cannot account for.',
           'implication_frame': 'A decision about the funnel has to name the stage with the largest evidenced '
                                'drop, because effort spent above that stage raises the number that leaves at it.',
           'reference_heading': 'References'}}


SERVQUAL = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'tangibles physical facilities',
             'fill': 'research',
             'key': 'tangibles',
             'label': 'Tangibles',
             'probe': 'state the evidence for tangibles',
             'prompt': 'Physical facilities, equipment and appearance',
             'queries': ['tangibles and physical facilities in this industry']},
            {'category': None,
             'cues': 'reliability dependable service',
             'fill': 'research',
             'key': 'reliability',
             'label': 'Reliability',
             'probe': 'state the evidence for reliability',
             'prompt': 'Ability to perform the promised service dependably',
             'queries': ['reliability in this industry']},
            {'category': None,
             'cues': 'responsiveness help prompt',
             'fill': 'research',
             'key': 'responsiveness',
             'label': 'Responsiveness',
             'probe': 'state the evidence for responsiveness',
             'prompt': 'Willingness to help customers and provide prompt service',
             'queries': ['responsiveness in this industry']},
            {'category': None,
             'cues': 'assurance knowledge courtesy trust',
             'fill': 'research',
             'key': 'assurance',
             'label': 'Assurance',
             'probe': 'state the evidence for assurance',
             'prompt': 'Knowledge and courtesy of employees and their ability to inspire trust',
             'queries': ['assurance and trust in this industry']},
            {'category': None,
             'cues': 'empathy caring attention',
             'fill': 'research',
             'key': 'empathy',
             'label': 'Empathy',
             'probe': 'state the evidence for empathy',
             'prompt': 'Caring, individualised attention the firm provides its customers',
             'queries': ['empathy and customer care in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'servqual',
 'label': 'SERVQUAL',
 'notes': {'assurance': {'analysis': 'This element describes an aspect of servqual. The relevant question is whether '
                                     'the evidence shows it.',
                         'probe': 'state the evidence for this element',
                         'qualify': 'The evidence does not establish this element, so it is described rather than '
                                    'measured.',
                         'short': 'An element without evidence is a claim without support.'},
           'empathy': {'analysis': 'This element describes an aspect of servqual. The relevant question is whether the '
                                   'evidence shows it.',
                       'probe': 'state the evidence for this element',
                       'qualify': 'The evidence does not establish this element, so it is described rather than '
                                  'measured.',
                       'short': 'An element without evidence is a claim without support.'},
           'reliability': {'analysis': 'This element describes an aspect of servqual. The relevant question is whether '
                                       'the evidence shows it.',
                           'probe': 'state the evidence for this element',
                           'qualify': 'The evidence does not establish this element, so it is described rather than '
                                      'measured.',
                           'short': 'An element without evidence is a claim without support.'},
           'responsiveness': {'analysis': 'This element describes an aspect of servqual. The relevant question is '
                                          'whether the evidence shows it.',
                              'probe': 'state the evidence for this element',
                              'qualify': 'The evidence does not establish this element, so it is described rather than '
                                         'measured.',
                              'short': 'An element without evidence is a claim without support.'},
           'tangibles': {'analysis': 'This element describes an aspect of servqual. The relevant question is whether '
                                     'the evidence shows it.',
                         'probe': 'state the evidence for this element',
                         'qualify': 'The evidence does not establish this element, so it is described rather than '
                                    'measured.',
                         'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'SERVQUAL',
             'implications': 'Implications for the decision',
             'lead': 'SERVQUAL examines its elements. Each is examined in turn, first through the evidence and then '
                     'through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_servqual',
 'title_prefix': 'SERVQUAL Analysis',
 'unit': {'example': 'smartphones, grocery retail, banking',
          'field': 'industry',
          'help': 'SERVQUAL reads service quality for a firm in a market. Name the industry or market.',
          'label': 'Industry or market',
          'refuse': 'SERVQUAL reads service quality for a firm in a market. Name the industry or market.'},
 'voice': {'block_plural': 'dimensions',
           'closing': 'identifies the element with the strongest evidence and the one most unsupported',
           'context_frame': 'The relevant industry is the one named in the brief; the dimensions are how customers '
                            'in that market judge the service.',
           'implication_frame': 'A decision about the service has to match the dimensions the evidence supports: '
                                'reliability is the floor a customer expects, and the remaining dimensions are '
                                'where the service can be judged better than rivals.',
           'interaction': 'Read together, the dimensions describe one service in which some evidence is present '
                          'and some is not, and a dimension without evidence carries no weight.',
           'intro_frame': 'The unit of analysis is the industry or market, because the dimensions describe how '
                          'customers in that market judge service rather than how the firm believes it performs.',
           'lens': 'the five service-quality dimensions, from tangibles to empathy',
           'reference_heading': 'References',
           'thesis_question': 'whether the evidence supports the servqual the decision relies on',
           'unit_noun': 'industry'}}


RFM = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'recency recent purchase',
             'fill': 'research',
             'key': 'recency',
             'label': 'Recency',
             'probe': 'state the evidence for recency',
             'prompt': 'How recently the customer purchased',
             'queries': ['recency and recent purchases in this industry']},
            {'category': None,
             'cues': 'frequency often repeat',
             'fill': 'research',
             'key': 'frequency',
             'label': 'Frequency',
             'probe': 'state the evidence for frequency',
             'prompt': 'How often the customer purchases',
             'queries': ['frequency and repeat purchases in this industry']},
            {'category': None,
             'cues': 'monetary spend value',
             'fill': 'research',
             'key': 'monetary',
             'label': 'Monetary',
             'probe': 'state the evidence for monetary',
             'prompt': 'How much the customer spends',
             'queries': ['monetary value and spending in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'rfm',
 'label': 'RFM',
 'notes': {'frequency': {'analysis': 'This element describes an aspect of rfm. The relevant question is whether the '
                                     'evidence shows it.',
                         'probe': 'state the evidence for this element',
                         'qualify': 'The evidence does not establish this element, so it is described rather than '
                                    'measured.',
                         'short': 'An element without evidence is a claim without support.'},
           'monetary': {'analysis': 'This element describes an aspect of rfm. The relevant question is whether the '
                                    'evidence shows it.',
                        'probe': 'state the evidence for this element',
                        'qualify': 'The evidence does not establish this element, so it is described rather than '
                                   'measured.',
                        'short': 'An element without evidence is a claim without support.'},
           'recency': {'analysis': 'This element describes an aspect of rfm. The relevant question is whether the '
                                   'evidence shows it.',
                       'probe': 'state the evidence for this element',
                       'qualify': 'The evidence does not establish this element, so it is described rather than '
                                  'measured.',
                       'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'RFM',
             'implications': 'Implications for the decision',
             'lead': 'RFM examines its elements. Each is examined in turn, first through the evidence and then through '
                     'what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_rfm',
 'title_prefix': 'RFM Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': 'RFM segmentation groups the customers of a market. Name the industry or market.',
          'example': 'smartphones, grocery retail, banking',
          'refuse': 'RFM segmentation groups the customers of a market. Name the industry or market.'},
 'voice': {'thesis_question': 'whether the evidence supports the segmentation the decision depends on',
           'unit_noun': 'market',
           'block_plural': 'dimensions',
           'lens': 'the three measures a customer is grouped by: recency, frequency and monetary value',
           'closing': 'identifies the dimension the segmentation depends on and the dimension the evidence cannot '
                      'settle',
           'intro_frame': 'The unit of analysis is the market rather than the firm, because RFM groups the '
                          "customers of a market by their own behaviour rather than describing the seller's "
                          'activity.',
           'context_frame': 'The relevant market is the one named in the brief; the dimensions describe the '
                            'customers in that market rather than the segments a firm would prefer.',
           'interaction': 'Read together, the dimensions describe how the customers were grouped rather than how '
                          'they behave: the window and the scoring method are yours, and a segment built on a '
                          'window the case does not defend is a grouping, not a finding.',
           'implication_frame': 'A decision about the segment has to match the evidence for the dimensions it was '
                                'built on, because a customer who is valuable only in a narrow window is a '
                                'different proposition from one who buys often.',
           'reference_heading': 'References'}}


TAM = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'perceived usefulness useful',
             'fill': 'research',
             'key': 'perceived_usefulness',
             'label': 'Perceived Usefulness',
             'probe': 'state the evidence for perceived usefulness',
             'prompt': 'How useful the technology is perceived to be',
             'queries': ['perceived usefulness in this industry']},
            {'category': None,
             'cues': 'perceived ease of use easy',
             'fill': 'research',
             'key': 'perceived_ease_of_use',
             'label': 'Perceived Ease of Use',
             'probe': 'state the evidence for perceived ease of use',
             'prompt': 'How easy the technology is perceived to be',
             'queries': ['perceived ease of use in this industry']},
            {'category': None,
             'cues': 'attitude towards using',
             'fill': 'research',
             'key': 'attitude',
             'label': 'Attitude',
             'probe': 'state the evidence for attitude',
             'prompt': 'The attitude towards using the technology',
             'queries': ['attitude towards technology in this industry']},
            {'category': None,
             'cues': 'behavioral intention use',
             'fill': 'research',
             'key': 'behavioral_intention',
             'label': 'Behavioral Intention',
             'probe': 'state the evidence for behavioral intention',
             'prompt': 'The intention to use the technology',
             'queries': ['behavioral intention to use in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'tam',
 'label': 'Technology Acceptance Model',
 'notes': {'attitude': {'analysis': 'This element describes an aspect of technology acceptance model. The relevant '
                                    'question is whether the evidence shows it.',
                        'probe': 'state the evidence for this element',
                        'qualify': 'The evidence does not establish this element, so it is described rather than '
                                   'measured.',
                        'short': 'An element without evidence is a claim without support.'},
           'behavioral_intention': {'analysis': 'This element describes an aspect of technology acceptance model. The '
                                                'relevant question is whether the evidence shows it.',
                                    'probe': 'state the evidence for this element',
                                    'qualify': 'The evidence does not establish this element, so it is described '
                                               'rather than measured.',
                                    'short': 'An element without evidence is a claim without support.'},
           'perceived_ease_of_use': {'analysis': 'This element describes an aspect of technology acceptance model. The '
                                                 'relevant question is whether the evidence shows it.',
                                     'probe': 'state the evidence for this element',
                                     'qualify': 'The evidence does not establish this element, so it is described '
                                                'rather than measured.',
                                     'short': 'An element without evidence is a claim without support.'},
           'perceived_usefulness': {'analysis': 'This element describes an aspect of technology acceptance model. The '
                                                'relevant question is whether the evidence shows it.',
                                    'probe': 'state the evidence for this element',
                                    'qualify': 'The evidence does not establish this element, so it is described '
                                               'rather than measured.',
                                    'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'Technology Acceptance Model',
             'implications': 'Implications for the decision',
             'lead': 'Technology Acceptance Model examines its elements. Each is examined in turn, first through the '
                     'evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_tam',
 'title_prefix': 'TAM Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': 'The Technology Acceptance Model is read against the users of a system in a market. Name the '
                  'industry or market.',
          'example': 'smartphones, grocery retail, banking',
          'refuse': 'The Technology Acceptance Model is read against the users of a system in a market. Name the '
                    'industry or market.'},
 'voice': {'thesis_question': 'whether the evidence supports the acceptance the decision depends on',
           'unit_noun': 'market',
           'block_plural': 'elements',
           'lens': 'the constructs that shape whether a user will adopt a system',
           'closing': 'identifies the element the acceptance depends on and the element the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the market rather than the firm, because the model explains why '
                          'the intended users of a system accept or resist it.',
           'context_frame': 'The relevant market is the one named in the brief; the elements describe the users of '
                            'the system in that market rather than the system itself.',
           'interaction': 'Read together, the elements describe a testable set of beliefs rather than a checklist '
                          'for every adoption problem: the constructs need a validated scale and a suitable study '
                          'design before they can carry a conclusion.',
           'implication_frame': 'A decision about the system has to match the element the evidence supports, '
                                'because training that improves ease of use will not change a user who does not '
                                'expect the system to be useful.',
           'reference_heading': 'References'}}


UTAUT = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'performance expectancy help',
             'fill': 'research',
             'key': 'performance_expectancy',
             'label': 'Performance Expectancy',
             'probe': 'state the evidence for performance expectancy',
             'prompt': 'How much the technology helps performance',
             'queries': ['performance expectancy in this industry']},
            {'category': None,
             'cues': 'effort expectancy easy use',
             'fill': 'research',
             'key': 'effort_expectancy',
             'label': 'Effort Expectancy',
             'probe': 'state the evidence for effort expectancy',
             'prompt': 'How easy the technology is to use',
             'queries': ['effort expectancy in this industry']},
            {'category': None,
             'cues': 'social influence others',
             'fill': 'research',
             'key': 'social_influence',
             'label': 'Social Influence',
             'probe': 'state the evidence for social influence',
             'prompt': 'How others influence adoption',
             'queries': ['social influence on adoption in this industry']},
            {'category': None,
             'cues': 'facilitating conditions resources support',
             'fill': 'research',
             'key': 'facilitating_conditions',
             'label': 'Facilitating Conditions',
             'probe': 'state the evidence for facilitating conditions',
             'prompt': 'The resources and support available',
             'queries': ['facilitating conditions in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'utaut',
 'label': 'UTAUT',
 'notes': {'effort_expectancy': {'analysis': 'This element describes an aspect of utaut. The relevant question is '
                                             'whether the evidence shows it.',
                                 'probe': 'state the evidence for this element',
                                 'qualify': 'The evidence does not establish this element, so it is described rather '
                                            'than measured.',
                                 'short': 'An element without evidence is a claim without support.'},
           'facilitating_conditions': {'analysis': 'This element describes an aspect of utaut. The relevant question '
                                                   'is whether the evidence shows it.',
                                       'probe': 'state the evidence for this element',
                                       'qualify': 'The evidence does not establish this element, so it is described '
                                                  'rather than measured.',
                                       'short': 'An element without evidence is a claim without support.'},
           'performance_expectancy': {'analysis': 'This element describes an aspect of utaut. The relevant question is '
                                                  'whether the evidence shows it.',
                                      'probe': 'state the evidence for this element',
                                      'qualify': 'The evidence does not establish this element, so it is described '
                                                 'rather than measured.',
                                      'short': 'An element without evidence is a claim without support.'},
           'social_influence': {'analysis': 'This element describes an aspect of utaut. The relevant question is '
                                            'whether the evidence shows it.',
                                'probe': 'state the evidence for this element',
                                'qualify': 'The evidence does not establish this element, so it is described rather '
                                           'than measured.',
                                'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'UTAUT',
             'implications': 'Implications for the decision',
             'lead': 'UTAUT examines its elements. Each is examined in turn, first through the evidence and then '
                     'through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_utaut',
 'title_prefix': 'UTAUT Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': 'UTAUT reads the users of a system in a market. Name the industry or market.',
          'example': 'smartphones, grocery retail, banking',
          'refuse': 'UTAUT reads the users of a system in a market. Name the industry or market.'},
 'voice': {'thesis_question': 'whether the evidence supports the adoption the decision depends on',
           'unit_noun': 'market',
           'block_plural': 'elements',
           'lens': 'the constructs that shape whether a user will use a system, and the conditions that make use '
                   'possible',
           'closing': 'identifies the element the adoption depends on and the element the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the market rather than the firm, because the model explains the '
                          'use of a system by the people who are meant to use it.',
           'context_frame': 'The relevant market is the one named in the brief; the elements describe the users of '
                            'the system in that market rather than the system itself.',
           'interaction': 'Read together, the elements describe a testable set of beliefs rather than a checklist '
                          'for every adoption problem: the constructs need a validated scale and a suitable '
                          'research design before they can carry a conclusion.',
           'implication_frame': 'A decision about the rollout has to match the element the evidence supports, '
                                'because a user who is willing but not able will not use the system however '
                                'persuaded they are.',
           'reference_heading': 'References'}}


BRAND_EQUITY = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'brand awareness know',
             'fill': 'research',
             'key': 'awareness',
             'label': 'Brand Awareness',
             'probe': 'state the evidence for brand awareness',
             'prompt': 'How well customers know the brand',
             'queries': ['brand awareness in this industry']},
            {'category': None,
             'cues': 'brand associations associate',
             'fill': 'research',
             'key': 'associations',
             'label': 'Brand Associations',
             'probe': 'state the evidence for brand associations',
             'prompt': 'What customers associate with the brand',
             'queries': ['brand associations in this industry']},
            {'category': None,
             'cues': 'perceived quality',
             'fill': 'research',
             'key': 'perceived_quality',
             'label': 'Perceived Quality',
             'probe': 'state the evidence for perceived quality',
             'prompt': 'How customers perceive the quality',
             'queries': ['perceived quality in this industry']},
            {'category': None,
             'cues': 'brand loyalty loyal',
             'fill': 'research',
             'key': 'loyalty',
             'label': 'Brand Loyalty',
             'probe': 'state the evidence for brand loyalty',
             'prompt': 'How loyal customers are to the brand',
             'queries': ['brand loyalty in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'brand_equity',
 'label': 'Brand Equity',
 'notes': {'associations': {'analysis': 'This element describes an aspect of brand equity. The relevant question is '
                                        'whether the evidence shows it.',
                            'probe': 'state the evidence for this element',
                            'qualify': 'The evidence does not establish this element, so it is described rather than '
                                       'measured.',
                            'short': 'An element without evidence is a claim without support.'},
           'awareness': {'analysis': 'This element describes an aspect of brand equity. The relevant question is '
                                     'whether the evidence shows it.',
                         'probe': 'state the evidence for this element',
                         'qualify': 'The evidence does not establish this element, so it is described rather than '
                                    'measured.',
                         'short': 'An element without evidence is a claim without support.'},
           'loyalty': {'analysis': 'This element describes an aspect of brand equity. The relevant question is whether '
                                   'the evidence shows it.',
                       'probe': 'state the evidence for this element',
                       'qualify': 'The evidence does not establish this element, so it is described rather than '
                                  'measured.',
                       'short': 'An element without evidence is a claim without support.'},
           'perceived_quality': {'analysis': 'This element describes an aspect of brand equity. The relevant question '
                                             'is whether the evidence shows it.',
                                 'probe': 'state the evidence for this element',
                                 'qualify': 'The evidence does not establish this element, so it is described rather '
                                            'than measured.',
                                 'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'Brand Equity',
             'implications': 'Implications for the decision',
             'lead': 'Brand Equity examines its elements. Each is examined in turn, first through the evidence and '
                     'then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_brand_equity',
 'title_prefix': 'Brand Equity Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': 'Brand equity is assessed in a market against the alternatives customers can choose. Name the '
                  'industry or market.',
          'example': 'smartphones, grocery retail, banking',
          'refuse': 'Brand equity is assessed in a market against the alternatives customers can choose. Name the '
                    'industry or market.'},
 'voice': {'thesis_question': 'whether the evidence supports the brand the decision depends on',
           'unit_noun': 'market',
           'block_plural': 'elements',
           'lens': 'the selected dimensions of brand equity, from what customers know to what they are loyal to',
           'closing': 'identifies the dimension the brand depends on and the dimension the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the market rather than the firm, because brand equity is what '
                          'customers hold in a market against the alternatives available to them.',
           'context_frame': 'The relevant market is the one named in the brief; the elements describe the brand in '
                            "that market rather than the firm's marketing activity.",
           'interaction': 'Read together, the elements describe the brand as customers hold it rather than as the '
                          'firm intends it: the measurement and the model chosen have to be named, because '
                          'different variants of brand equity do not describe the same thing.',
           'implication_frame': 'A decision about the brand has to match the dimension the evidence supports, '
                                'because awareness without association does not carry the price a loyalty argument '
                                'assumes.',
           'reference_heading': 'References'}}


DIGITAL_MIX = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'owned channels control',
             'fill': 'research',
             'key': 'owned',
             'label': 'Owned Channels',
             'probe': 'state the evidence for owned channels',
             'prompt': 'Channels the brand controls',
             'queries': ['owned channels in this industry']},
            {'category': None,
             'cues': 'earned channels PR word of mouth',
             'fill': 'research',
             'key': 'earned',
             'label': 'Earned Channels',
             'probe': 'state the evidence for earned channels',
             'prompt': 'Channels gained through PR and word of mouth',
             'queries': ['earned channels in this industry']},
            {'category': None,
             'cues': 'paid channels advertising',
             'fill': 'research',
             'key': 'paid',
             'label': 'Paid Channels',
             'probe': 'state the evidence for paid channels',
             'prompt': 'Channels paid for advertising',
             'queries': ['paid channels in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'digital_mix',
 'label': 'Digital Marketing Mix',
 'notes': {'earned': {'analysis': 'This element describes an aspect of digital marketing mix. The relevant question is '
                                  'whether the evidence shows it.',
                      'probe': 'state the evidence for this element',
                      'qualify': 'The evidence does not establish this element, so it is described rather than '
                                 'measured.',
                      'short': 'An element without evidence is a claim without support.'},
           'owned': {'analysis': 'This element describes an aspect of digital marketing mix. The relevant question is '
                                 'whether the evidence shows it.',
                     'probe': 'state the evidence for this element',
                     'qualify': 'The evidence does not establish this element, so it is described rather than '
                                'measured.',
                     'short': 'An element without evidence is a claim without support.'},
           'paid': {'analysis': 'This element describes an aspect of digital marketing mix. The relevant question is '
                                'whether the evidence shows it.',
                    'probe': 'state the evidence for this element',
                    'qualify': 'The evidence does not establish this element, so it is described rather than measured.',
                    'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'Digital Marketing Mix',
             'implications': 'Implications for the decision',
             'lead': 'Digital Marketing Mix examines its elements. Each is examined in turn, first through the '
                     'evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_digital_mix',
 'title_prefix': 'Digital Mix Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': 'The digital mix is allocated across the channels available in a market. Name the industry or '
                  'market.',
          'example': 'smartphones, grocery retail, banking',
          'refuse': 'The digital mix is allocated across the channels available in a market. Name the industry or '
                    'market.'},
 'voice': {'thesis_question': 'whether the evidence supports the channel mix the decision depends on',
           'unit_noun': 'market',
           'block_plural': 'channels',
           'lens': 'the three kinds of digital channel, and the role and budget each is given',
           'closing': 'identifies the channel the mix depends on and the channel the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the market rather than the firm, because the mix describes the '
                          "channels available to reach an audience in a market rather than the firm's whole "
                          'channel set.',
           'context_frame': 'The relevant market is the one named in the brief; the channels belong to the '
                            'audience in that market rather than to the firm in general.',
           'interaction': 'Read together, the channels describe where the audience can be reached rather than what '
                          'the firm should do: the objective for each channel is yours, and the system allocates '
                          'no budget and predicts no reach.',
           'implication_frame': 'A decision about the mix has to name the channel whose role the evidence '
                                'supports, because a paid channel funded to do the work of an earned one will be '
                                'measured by the wrong thing.',
           'reference_heading': 'References'}}


SEO_CONTENT = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'keywords search terms',
             'fill': 'research',
             'key': 'keywords',
             'label': 'Keywords',
             'probe': 'state the evidence for keywords',
             'prompt': 'The search terms targeted',
             'queries': ['keywords and search terms in this industry']},
            {'category': None,
             'cues': 'content created search',
             'fill': 'research',
             'key': 'content',
             'label': 'Content',
             'probe': 'state the evidence for content',
             'prompt': 'The content created for search',
             'queries': ['content for search in this industry']},
            {'category': None,
             'cues': 'technical SEO optimisation',
             'fill': 'research',
             'key': 'technical',
             'label': 'Technical SEO',
             'probe': 'state the evidence for technical SEO',
             'prompt': 'The technical optimisation of the site',
             'queries': ['technical SEO in this industry']},
            {'category': None,
             'cues': 'links link building',
             'fill': 'research',
             'key': 'links',
             'label': 'Links',
             'probe': 'state the evidence for links',
             'prompt': 'The link building strategy',
             'queries': ['link building in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'seo_content',
 'label': 'SEO and Content',
 'notes': {'content': {'analysis': 'This element describes an aspect of seo and content. The relevant question is '
                                   'whether the evidence shows it.',
                       'probe': 'state the evidence for this element',
                       'qualify': 'The evidence does not establish this element, so it is described rather than '
                                  'measured.',
                       'short': 'An element without evidence is a claim without support.'},
           'keywords': {'analysis': 'This element describes an aspect of seo and content. The relevant question is '
                                    'whether the evidence shows it.',
                        'probe': 'state the evidence for this element',
                        'qualify': 'The evidence does not establish this element, so it is described rather than '
                                   'measured.',
                        'short': 'An element without evidence is a claim without support.'},
           'links': {'analysis': 'This element describes an aspect of seo and content. The relevant question is '
                                 'whether the evidence shows it.',
                     'probe': 'state the evidence for this element',
                     'qualify': 'The evidence does not establish this element, so it is described rather than '
                                'measured.',
                     'short': 'An element without evidence is a claim without support.'},
           'technical': {'analysis': 'This element describes an aspect of seo and content. The relevant question is '
                                     'whether the evidence shows it.',
                         'probe': 'state the evidence for this element',
                         'qualify': 'The evidence does not establish this element, so it is described rather than '
                                    'measured.',
                         'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'SEO and Content',
             'implications': 'Implications for the decision',
             'lead': 'SEO and Content examines its elements. Each is examined in turn, first through the evidence and '
                     'then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_seo_content',
 'title_prefix': 'SEO and Content Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': 'An SEO and content plan is written for an audience found in a market. Name the industry or market.',
          'example': 'smartphones, grocery retail, banking',
          'refuse': 'An SEO and content plan is written for an audience found in a market. Name the industry or '
                    'market.'},
 'voice': {'thesis_question': 'whether the evidence supports the content plan the decision depends on',
           'unit_noun': 'market',
           'block_plural': 'elements',
           'lens': 'the four parts of a search and content plan: the questions targeted, the content, the '
                   'technical base and the links',
           'closing': 'identifies the element the plan depends on and the element the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the market rather than the firm, because a content plan is '
                          'written for the questions an audience in a market is asking.',
           'context_frame': 'The relevant market is the one named in the brief; the elements belong to the '
                            "audience in that market rather than to the firm's publishing activity in general.",
           'interaction': 'Read together, the elements describe the parts of one plan rather than a ranking to be '
                          'won: the search demand, the page inventory and the calendar are yours, and the system '
                          'predicts no traffic or position.',
           'implication_frame': 'A decision about the plan has to match the element the demand evidence supports, '
                                'because content written for a question the audience is not asking cannot be found '
                                'by it.',
           'reference_heading': 'References'}}


EMAIL_CRM = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'email list health',
             'fill': 'research',
             'key': 'list',
             'label': 'List',
             'probe': 'state the evidence for list health',
             'prompt': 'The email list and its health',
             'queries': ['email list health in this industry']},
            {'category': None,
             'cues': 'segments segmentation',
             'fill': 'research',
             'key': 'segments',
             'label': 'Segments',
             'probe': 'state the evidence for segments',
             'prompt': 'How the list is segmented',
             'queries': ['email segmentation in this industry']},
            {'category': None,
             'cues': 'campaigns email sent',
             'fill': 'research',
             'key': 'campaigns',
             'label': 'Campaigns',
             'probe': 'state the evidence for campaigns',
             'prompt': 'The email campaigns sent',
             'queries': ['email campaigns in this industry']},
            {'category': None,
             'cues': 'automation flows automated',
             'fill': 'research',
             'key': 'automation',
             'label': 'Automation',
             'probe': 'state the evidence for automation',
             'prompt': 'The automated email flows',
             'queries': ['email automation in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'email_crm',
 'label': 'Email CRM and Lifecycle',
 'notes': {'automation': {'analysis': 'This element describes an aspect of email crm and lifecycle. The relevant '
                                      'question is whether the evidence shows it.',
                          'probe': 'state the evidence for this element',
                          'qualify': 'The evidence does not establish this element, so it is described rather than '
                                     'measured.',
                          'short': 'An element without evidence is a claim without support.'},
           'campaigns': {'analysis': 'This element describes an aspect of email crm and lifecycle. The relevant '
                                     'question is whether the evidence shows it.',
                         'probe': 'state the evidence for this element',
                         'qualify': 'The evidence does not establish this element, so it is described rather than '
                                    'measured.',
                         'short': 'An element without evidence is a claim without support.'},
           'list': {'analysis': 'This element describes an aspect of email crm and lifecycle. The relevant question is '
                                'whether the evidence shows it.',
                    'probe': 'state the evidence for this element',
                    'qualify': 'The evidence does not establish this element, so it is described rather than measured.',
                    'short': 'An element without evidence is a claim without support.'},
           'segments': {'analysis': 'This element describes an aspect of email crm and lifecycle. The relevant '
                                    'question is whether the evidence shows it.',
                        'probe': 'state the evidence for this element',
                        'qualify': 'The evidence does not establish this element, so it is described rather than '
                                   'measured.',
                        'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'Email CRM and Lifecycle',
             'implications': 'Implications for the decision',
             'lead': 'Email CRM and Lifecycle examines its elements. Each is examined in turn, first through the '
                     'evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_email_crm',
 'title_prefix': 'Email CRM Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': "Email and CRM performance is read for a market's audience. Name the industry or market.",
          'example': 'smartphones, grocery retail, banking',
          'refuse': "Email and CRM performance is read for a market's audience. Name the industry or market."},
 'voice': {'thesis_question': 'whether the evidence supports the lifecycle programme the decision depends on',
           'unit_noun': 'market',
           'block_plural': 'elements',
           'lens': 'the four parts of a lifecycle programme: the list, the segments, the campaigns and the automation',
           'closing': 'identifies the element the programme depends on and the element the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the market rather than the firm, because a lifecycle programme '
                          "is run against a consented audience in a market rather than against the firm's own "
                          'records in general.',
           'context_frame': 'The relevant market is the one named in the brief; the elements belong to the '
                            'audience in that market rather than to lifecycle work in general.',
           'interaction': 'Read together, the elements describe how the programme is built rather than how it '
                          'performed: the consent record and the counts are yours, and the system derives no '
                          'revenue figure or engagement rate.',
           'implication_frame': 'A decision about the programme has to match the element the evidence supports, '
                                'because a segment built on a list the consent record cannot cover is a segment '
                                'the firm may not lawfully write to.',
           'reference_heading': 'References'}}


SOCIAL_MEDIA = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'platforms social used',
             'fill': 'research',
             'key': 'platforms',
             'label': 'Platforms',
             'probe': 'state the evidence for platforms',
             'prompt': 'Which social platforms are used',
             'queries': ['social platforms in this industry']},
            {'category': None,
             'cues': 'content posted social',
             'fill': 'research',
             'key': 'content',
             'label': 'Content',
             'probe': 'state the evidence for content',
             'prompt': 'The content posted on social media',
             'queries': ['social media content in this industry']},
            {'category': None,
             'cues': 'engagement audience interact',
             'fill': 'research',
             'key': 'engagement',
             'label': 'Engagement',
             'probe': 'state the evidence for engagement',
             'prompt': 'How audiences engage with the content',
             'queries': ['social engagement in this industry']},
            {'category': None,
             'cues': 'influencers partners',
             'fill': 'research',
             'key': 'influencers',
             'label': 'Influencers',
             'probe': 'state the evidence for influencers',
             'prompt': 'The influencers and partners used',
             'queries': ['influencers in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'social_media',
 'label': 'Social Media and Influencer',
 'notes': {'content': {'analysis': 'This element describes an aspect of social media and influencer. The relevant '
                                   'question is whether the evidence shows it.',
                       'probe': 'state the evidence for this element',
                       'qualify': 'The evidence does not establish this element, so it is described rather than '
                                  'measured.',
                       'short': 'An element without evidence is a claim without support.'},
           'engagement': {'analysis': 'This element describes an aspect of social media and influencer. The relevant '
                                      'question is whether the evidence shows it.',
                          'probe': 'state the evidence for this element',
                          'qualify': 'The evidence does not establish this element, so it is described rather than '
                                     'measured.',
                          'short': 'An element without evidence is a claim without support.'},
           'influencers': {'analysis': 'This element describes an aspect of social media and influencer. The relevant '
                                       'question is whether the evidence shows it.',
                           'probe': 'state the evidence for this element',
                           'qualify': 'The evidence does not establish this element, so it is described rather than '
                                      'measured.',
                           'short': 'An element without evidence is a claim without support.'},
           'platforms': {'analysis': 'This element describes an aspect of social media and influencer. The relevant '
                                     'question is whether the evidence shows it.',
                         'probe': 'state the evidence for this element',
                         'qualify': 'The evidence does not establish this element, so it is described rather than '
                                    'measured.',
                         'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'Social Media and Influencer',
             'implications': 'Implications for the decision',
             'lead': 'Social Media and Influencer examines its elements. Each is examined in turn, first through the '
                     'evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_social_media',
 'title_prefix': 'Social Media Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': 'A social and influencer plan is written for an audience in a market. Name the industry or market.',
          'example': 'smartphones, grocery retail, banking',
          'refuse': 'A social and influencer plan is written for an audience in a market. Name the industry or '
                    'market.'},
 'voice': {'thesis_question': 'whether the evidence supports the social plan the decision depends on',
           'unit_noun': 'market',
           'block_plural': 'elements',
           'lens': 'the four parts of a social and influencer plan, from the platforms to the metric each is '
                   'judged on',
           'closing': 'identifies the element the plan depends on and the element the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the market rather than the firm, because a social plan is '
                          "written for the audience a market's platforms carry rather than for the firm's own "
                          'staff.',
           'context_frame': 'The relevant market is the one named in the brief; the elements belong to the '
                            'audience in that market rather than to social activity in general.',
           'interaction': 'Read together, the elements describe the plan and the metric each part is judged on '
                          'rather than a verdict on the platform: reach, engagement and the terms agreed with a '
                          'creator are yours to state, and the system derives no performance figure.',
           'implication_frame': 'A decision about the plan has to match the metric the evidence supports, because '
                                'a platform judged on a metric it was never chosen for will keep failing the test '
                                'it was given.',
           'reference_heading': 'References'}}


ATTRIBUTION = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'touchpoints tracked',
             'fill': 'research',
             'key': 'touchpoints',
             'label': 'Touchpoints',
             'probe': 'state the evidence for touchpoints',
             'prompt': 'The customer touchpoints tracked',
             'queries': ['touchpoints tracked in this industry']},
            {'category': None,
             'cues': 'attribution model credit',
             'fill': 'research',
             'key': 'model',
             'label': 'Attribution Model',
             'probe': 'state the evidence for attribution model',
             'prompt': 'The model used to assign credit',
             'queries': ['attribution model in this industry']},
            {'category': None,
             'cues': 'credit assignment',
             'fill': 'research',
             'key': 'credit',
             'label': 'Credit Assignment',
             'probe': 'state the evidence for credit assignment',
             'prompt': 'How credit is assigned across touchpoints',
             'queries': ['credit assignment in this industry']},
            {'category': None,
             'cues': 'reporting attribution',
             'fill': 'research',
             'key': 'reporting',
             'label': 'Reporting',
             'probe': 'state the evidence for reporting',
             'prompt': 'How attribution is reported',
             'queries': ['attribution reporting in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'attribution',
 'label': 'Attribution and Campaign Measurement',
 'notes': {'credit': {'analysis': 'This element describes an aspect of attribution and campaign measurement. The '
                                  'relevant question is whether the evidence shows it.',
                      'probe': 'state the evidence for this element',
                      'qualify': 'The evidence does not establish this element, so it is described rather than '
                                 'measured.',
                      'short': 'An element without evidence is a claim without support.'},
           'model': {'analysis': 'This element describes an aspect of attribution and campaign measurement. The '
                                 'relevant question is whether the evidence shows it.',
                     'probe': 'state the evidence for this element',
                     'qualify': 'The evidence does not establish this element, so it is described rather than '
                                'measured.',
                     'short': 'An element without evidence is a claim without support.'},
           'reporting': {'analysis': 'This element describes an aspect of attribution and campaign measurement. The '
                                     'relevant question is whether the evidence shows it.',
                         'probe': 'state the evidence for this element',
                         'qualify': 'The evidence does not establish this element, so it is described rather than '
                                    'measured.',
                         'short': 'An element without evidence is a claim without support.'},
           'touchpoints': {'analysis': 'This element describes an aspect of attribution and campaign measurement. The '
                                       'relevant question is whether the evidence shows it.',
                           'probe': 'state the evidence for this element',
                           'qualify': 'The evidence does not establish this element, so it is described rather than '
                                      'measured.',
                           'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'Attribution and Campaign Measurement',
             'implications': 'Implications for the decision',
             'lead': 'Attribution and Campaign Measurement examines its elements. Each is examined in turn, first '
                     'through the evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_attribution',
 'title_prefix': 'Attribution Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': 'Campaign attribution is read for the campaigns running in a market. Name the industry or market.',
          'example': 'smartphones, grocery retail, banking',
          'refuse': 'Campaign attribution is read for the campaigns running in a market. Name the industry or market.'},
 'voice': {'thesis_question': 'whether the evidence supports the attribution the decision depends on',
           'unit_noun': 'market',
           'block_plural': 'elements',
           'lens': 'the four parts of a measurement frame: the touchpoints, the model, the credit given and the '
                   'reporting it feeds',
           'closing': 'identifies the part the attribution depends on and the part the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the market rather than the firm, because attribution compares '
                          'how credit is given across the campaigns running in a market rather than describing one '
                          "company's activity.",
           'context_frame': 'The relevant market is the one named in the brief; the elements belong to the '
                            'measurement frame applied to those campaigns rather than to marketing activity in '
                            'general.',
           'interaction': 'Read together, the elements record the rule that was applied rather than the effect the '
                          'campaign had: the touchpoint log, the conversion definition and the attribution rule '
                          'are yours, and no causal claim follows from a share that was assigned by rule.',
           'implication_frame': 'A decision about the budget has to match the rule the evidence supports, because '
                                'a credit share that changes with the model chosen will move the budget without '
                                'any change in what the campaign did.',
           'reference_heading': 'References'}}


CRO = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'hypothesis testing',
             'fill': 'research',
             'key': 'hypothesis',
             'label': 'Hypothesis',
             'probe': 'state the evidence for the hypothesis',
             'prompt': 'The hypothesis being tested',
             'queries': ['hypothesis testing in this industry']},
            {'category': None,
             'cues': 'variants testing',
             'fill': 'research',
             'key': 'variants',
             'label': 'Variants',
             'probe': 'state the evidence for variants',
             'prompt': 'The variants being tested',
             'queries': ['variants testing in this industry']},
            {'category': None,
             'cues': 'metrics tracking',
             'fill': 'research',
             'key': 'metrics',
             'label': 'Metrics',
             'probe': 'state the evidence for metrics',
             'prompt': 'The metrics being tracked',
             'queries': ['metrics tracking in this industry']},
            {'category': None,
             'cues': 'results test outcome',
             'fill': 'research',
             'key': 'results',
             'label': 'Results',
             'probe': 'state the evidence for results',
             'prompt': 'The results of the test',
             'queries': ['test results in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'cro',
 'label': 'Conversion Rate Optimisation',
 'notes': {'hypothesis': {'analysis': 'This element describes an aspect of conversion rate optimisation. The relevant '
                                      'question is whether the evidence shows it.',
                          'probe': 'state the evidence for this element',
                          'qualify': 'The evidence does not establish this element, so it is described rather than '
                                     'measured.',
                          'short': 'An element without evidence is a claim without support.'},
           'metrics': {'analysis': 'This element describes an aspect of conversion rate optimisation. The relevant '
                                   'question is whether the evidence shows it.',
                       'probe': 'state the evidence for this element',
                       'qualify': 'The evidence does not establish this element, so it is described rather than '
                                  'measured.',
                       'short': 'An element without evidence is a claim without support.'},
           'results': {'analysis': 'This element describes an aspect of conversion rate optimisation. The relevant '
                                   'question is whether the evidence shows it.',
                       'probe': 'state the evidence for this element',
                       'qualify': 'The evidence does not establish this element, so it is described rather than '
                                  'measured.',
                       'short': 'An element without evidence is a claim without support.'},
           'variants': {'analysis': 'This element describes an aspect of conversion rate optimisation. The relevant '
                                    'question is whether the evidence shows it.',
                        'probe': 'state the evidence for this element',
                        'qualify': 'The evidence does not establish this element, so it is described rather than '
                                   'measured.',
                        'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'Conversion Rate Optimisation',
             'implications': 'Implications for the decision',
             'lead': 'Conversion Rate Optimisation examines its elements. Each is examined in turn, first through the '
                     'evidence and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_cro',
 'title_prefix': 'CRO Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': 'A conversion test is run on a page or step reached in a market. Name the industry or market.',
          'example': 'smartphones, grocery retail, banking',
          'refuse': 'A conversion test is run on a page or step reached in a market. Name the industry or market.'},
 'voice': {'thesis_question': 'whether the evidence supports the test the decision depends on',
           'unit_noun': 'market',
           'block_plural': 'elements',
           'lens': 'the four parts of one conversion test: the hypothesis, the variants, the measures and the result',
           'closing': 'identifies the part the test depends on and the part the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the market rather than the firm, because a conversion test is '
                          "run on the traffic a market sends to a page rather than on the firm's own activity.",
           'context_frame': 'The relevant market is the one named in the brief; the elements belong to that test '
                            'rather than to conversion activity in general.',
           'interaction': 'Read together, the elements describe one test rather than a record of testing: the '
                          'baseline, the traffic split and the declared minimum effect are yours, and the system '
                          'computes no significance and recommends no variant.',
           'implication_frame': 'A decision about the page has to match the result the test actually supports, '
                                'because a variant that wins on a split the case cannot defend is a difference in '
                                'the sample rather than in the page.',
           'reference_heading': 'References'}}


MARKETING_AUTOMATION = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'triggers automated actions',
             'fill': 'research',
             'key': 'triggers',
             'label': 'Triggers',
             'probe': 'state the evidence for triggers',
             'prompt': 'What triggers automated actions',
             'queries': ['triggers for automation in this industry']},
            {'category': None,
             'cues': 'flows automated marketing',
             'fill': 'research',
             'key': 'flows',
             'label': 'Flows',
             'probe': 'state the evidence for flows',
             'prompt': 'The automated marketing flows',
             'queries': ['automated flows in this industry']},
            {'category': None,
             'cues': 'lead scoring',
             'fill': 'research',
             'key': 'scoring',
             'label': 'Lead Scoring',
             'probe': 'state the evidence for lead scoring',
             'prompt': 'How leads are scored',
             'queries': ['lead scoring in this industry']},
            {'category': None,
             'cues': 'nurture leads',
             'fill': 'research',
             'key': 'nurture',
             'label': 'Nurture',
             'probe': 'state the evidence for nurture',
             'prompt': 'How leads are nurtured',
             'queries': ['lead nurturing in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'marketing_automation',
 'label': 'Marketing Automation',
 'notes': {'flows': {'analysis': 'This element describes an aspect of marketing automation. The relevant question is '
                                 'whether the evidence shows it.',
                     'probe': 'state the evidence for this element',
                     'qualify': 'The evidence does not establish this element, so it is described rather than '
                                'measured.',
                     'short': 'An element without evidence is a claim without support.'},
           'nurture': {'analysis': 'This element describes an aspect of marketing automation. The relevant question is '
                                   'whether the evidence shows it.',
                       'probe': 'state the evidence for this element',
                       'qualify': 'The evidence does not establish this element, so it is described rather than '
                                  'measured.',
                       'short': 'An element without evidence is a claim without support.'},
           'scoring': {'analysis': 'This element describes an aspect of marketing automation. The relevant question is '
                                   'whether the evidence shows it.',
                       'probe': 'state the evidence for this element',
                       'qualify': 'The evidence does not establish this element, so it is described rather than '
                                  'measured.',
                       'short': 'An element without evidence is a claim without support.'},
           'triggers': {'analysis': 'This element describes an aspect of marketing automation. The relevant question '
                                    'is whether the evidence shows it.',
                        'probe': 'state the evidence for this element',
                        'qualify': 'The evidence does not establish this element, so it is described rather than '
                                   'measured.',
                        'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'Marketing Automation',
             'implications': 'Implications for the decision',
             'lead': 'Marketing Automation examines its elements. Each is examined in turn, first through the evidence '
                     'and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_marketing_automation',
 'title_prefix': 'Marketing Automation Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': 'Marketing automation rules are written for the leads moving through a market. Name the industry '
                  'or market.',
          'example': 'smartphones, grocery retail, banking',
          'refuse': 'Marketing automation rules are written for the leads moving through a market. Name the '
                    'industry or market.'},
 'voice': {'thesis_question': 'whether the evidence supports the automation the decision depends on',
           'unit_noun': 'market',
           'block_plural': 'elements',
           'lens': 'the four parts of an automation set: the triggers, the flows, the scoring and the nurture',
           'closing': 'identifies the element the automation depends on and the element the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the market rather than the firm, because the rules are written '
                          "for the leads moving through a market rather than for the firm's own records.",
           'context_frame': 'The relevant market is the one named in the brief; the elements belong to that lead '
                            'flow rather than to marketing systems in general.',
           'interaction': 'Read together, the elements describe the rules and the behaviour behind them rather '
                          'than a result: the stage definitions and the score are yours, and the system validates '
                          'no lead and derives no revenue.',
           'implication_frame': 'A decision about the automation has to name the element the evidence supports, '
                                'because a score that was never validated against sales outcomes will qualify the '
                                'wrong leads without anyone noticing.',
           'reference_heading': 'References'}}


STP_EVIDENCE = {'assumption': 'probe',
 'blocks': [{'category': None,
             'cues': 'segmentation evidence',
             'fill': 'research',
             'key': 'segmentation_evidence',
             'label': 'Segmentation Evidence',
             'probe': 'state the evidence for segmentation',
             'prompt': 'Evidence for the segmentation',
             'queries': ['segmentation evidence in this industry']},
            {'category': None,
             'cues': 'targeting evidence',
             'fill': 'research',
             'key': 'targeting_evidence',
             'label': 'Targeting Evidence',
             'probe': 'state the evidence for targeting',
             'prompt': 'Evidence for the targeting',
             'queries': ['targeting evidence in this industry']},
            {'category': None,
             'cues': 'positioning evidence',
             'fill': 'research',
             'key': 'positioning_evidence',
             'label': 'Positioning Evidence',
             'probe': 'state the evidence for positioning',
             'prompt': 'Evidence for the positioning',
             'queries': ['positioning evidence in this industry']}],
 'gate': {'require_geography': False, 'title_context': True, 'title_cue': True},
 'key': 'stp_evidence',
 'label': 'STP Evidence Check',
 'notes': {'positioning_evidence': {'analysis': 'This element describes an aspect of stp evidence check. The relevant '
                                                'question is whether the evidence shows it.',
                                    'probe': 'state the evidence for this element',
                                    'qualify': 'The evidence does not establish this element, so it is described '
                                               'rather than measured.',
                                    'short': 'An element without evidence is a claim without support.'},
           'segmentation_evidence': {'analysis': 'This element describes an aspect of stp evidence check. The relevant '
                                                 'question is whether the evidence shows it.',
                                     'probe': 'state the evidence for this element',
                                     'qualify': 'The evidence does not establish this element, so it is described '
                                                'rather than measured.',
                                     'short': 'An element without evidence is a claim without support.'},
           'targeting_evidence': {'analysis': 'This element describes an aspect of stp evidence check. The relevant '
                                              'question is whether the evidence shows it.',
                                  'probe': 'state the evidence for this element',
                                  'qualify': 'The evidence does not establish this element, so it is described rather '
                                             'than measured.',
                                  'short': 'An element without evidence is a claim without support.'}},
 'outline': {'conclusion': 'Conclusion',
             'context': 'The case and its industry',
             'discussion': 'What the evidence shows',
             'framework': 'STP Evidence Check',
             'implications': 'Implications for the decision',
             'lead': 'STP Evidence Check examines its elements. Each is examined in turn, first through the evidence '
                     'and then through what it implies.',
             'limitations': 'Limitations'},
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'ratings': False,
 'sites': 'industry',
 'subject': 'marketing',
 'template': 'template_stp_evidence',
 'title_prefix': 'STP Evidence Check Analysis',
 'unit': {'field': 'industry',
          'label': 'Industry or market',
          'help': 'The STP evidence check audits a claim made in a market. Name the industry or market.',
          'example': 'smartphones, grocery retail, banking',
          'refuse': 'The STP evidence check audits a claim made in a market. Name the industry or market.'},
 'voice': {'thesis_question': 'whether the evidence supports the segment, target and position the decision depends on',
           'unit_noun': 'market',
           'block_plural': 'elements',
           'lens': 'the three claims an STP decision makes, each read against the evidence behind it',
           'closing': 'identifies the claim the evidence supports and the claim the evidence cannot settle',
           'intro_frame': 'The unit of analysis is the market rather than the firm, because the check audits '
                          "claims made about a market rather than the firm's own activity.",
           'context_frame': 'The relevant market is the one named in the brief; the elements are the segmentation, '
                            'targeting and positioning claims made about that market.',
           'interaction': 'Read together, the elements are a quality layer on an STP decision rather than a repeat '
                          'of it: each claim is read against the research that supports it, and an unsupported '
                          'claim is named rather than quietly dropped.',
           'implication_frame': 'A decision about the market has to match the claim the research supports, because '
                                'a position chosen for a segment the evidence does not support cannot be tested '
                                'against the customers it was meant to win.',
           'reference_heading': 'References'}}


#: Blue Ocean ERRC ---------------------------------------------------------------

ERRC = {

    "template": "template_blue_ocean_errc",

    "key": "errc",

    "label": "Blue Ocean four actions (ERRC)",

    "title_prefix": "Blue Ocean ERRC Analysis",

    "subject": "management",

    "unit": {

        "field": "industry",

        "label": "Industry or market",

        "help": "The four actions are written against an industry. Name it.",

        "example": "smartphones, grocery retail, banking",

        "refuse": ("Blue Ocean's four actions are written against an industry. Name the industry or market."),

    },

    "ratings": False,

    "assumption": "probe",

    "sites": "industry",

    "providers": ["brave", "deepseek", "firecrawl"],

    "gate": {"title_cue": True, "title_context": True, "require_geography": False},

    "blocks": [

        {"key": "eliminate", "label": "Eliminate", "prompt": "Factors the industry competes on that should be eliminated",

         "fill": "research", "cues": "eliminate remove industry standard factor", "queries": ["factors eliminated in this industry"],

         "category": None, "probe": "state the factors you would eliminate, and the evidence"},

        {"key": "reduce", "label": "Reduce", "prompt": "Factors to reduce well below the industry standard",

         "fill": "research", "cues": "reduce below standard lower cost", "queries": ["factors reduced below standard in this industry"],

         "category": None, "probe": "state the factors you would reduce, and the evidence"},

        {"key": "raise", "label": "Raise", "prompt": "Factors to raise well above the industry standard",

         "fill": "research", "cues": "raise above standard higher value", "queries": ["factors raised above standard in this industry"],

         "category": None, "probe": "state the factors you would raise, and the evidence"},

        {"key": "create", "label": "Create", "prompt": "Factors the industry has never offered",

         "fill": "research", "cues": "create new never offered innovation", "queries": ["new factors created in this industry"],

         "category": None, "probe": "state the factors you would create, and the evidence"},

    ],

    "outline": {

        "framework": "Blue Ocean ERRC", "context": "The case and its industry",

        "discussion": "What the evidence shows",

        "implications": "Implications for the decision",

        "limitations": "Limitations", "conclusion": "Conclusion",

        "lead": ("The four actions - eliminate, reduce, raise, create - reshape the value curve of an offer "

                 "against an industry. Each action is treated in turn, first through the evidence and then through "

                 "what it implies."),

    },

    "voice": {

        "thesis_question": "whether the evidence supports the value curve the decision proposes",

        "unit_noun": "industry", "block_plural": "actions",

        "lens": "the factors an offer competes on, and how each is moved",

        "closing": "identifies the action the evidence supports most and the one it cannot settle",

        "intro_frame": ("The unit of analysis is the industry, because the four actions reshape the value curve "

                        "against the industry's standard."),

        "context_frame": ("The relevant industry is the one named in the brief; the actions are properties of the "

                          "offer in that industry."),

        "interaction": ("Read together, the actions describe an offer in which some factors are evidenced and "

                        "others are not, and a factor without evidence carries no weight."),

        "implication_frame": ("A value innovation has to answer the actions the evidence supports: what is "

                              "eliminated, reduced, raised and created."),

        "reference_heading": "References",

    },

    "notes": {

        block: {

            "analysis": ("This action moves one factor of the value curve against the industry standard. The "

                         "relevant question is whether the evidence shows the factor to be in the industry's "

                         "competing set."),

            "qualify": ("The evidence does not establish the value of the factor to buyers, so the action is "

                        "declared rather than measured."),

            "short": ("A factor moved without evidence is a wish about the value curve."),

            "probe": "state the factor and the evidence behind it",

        }

        for block in ("eliminate", "reduce", "raise", "create")

    },

}

#: Activity system fit -----------------------------------------------------------

ACTIVITY_SYSTEM = {

    "template": "template_activity_system_fit",

    "key": "activity_system",

    "label": "Strategic positioning and activity-system fit",

    "title_prefix": "Activity-System Analysis",

    "subject": "management",

    "unit": {

        "field": "industry",

        "label": "Industry or market",

        "help": "Activity systems are written against a market. Name it.",

        "example": "smartphones, grocery retail, banking",

        "refuse": ("Activity-system fit is written against a market. Name the industry or market."),

    },

    "ratings": False,

    "assumption": "probe",

    "sites": "industry",

    "providers": ["brave", "deepseek", "firecrawl"],

    "gate": {"title_cue": True, "title_context": True, "require_geography": False},

    "blocks": [

        {"key": "strategic_position", "label": "Strategic position", "prompt": "The choice the activity system supports",

         "fill": "research", "cues": "position strategy choice differentiation cost", "queries": ["strategic positioning in this industry"],

         "category": None, "probe": "state the position and the choice it rests on"},

        {"key": "activities", "label": "Activities", "prompt": "The main activities that deliver that position",

         "fill": "research", "cues": "activity process capability operation", "queries": ["activities that deliver a position in this industry"],

         "category": None, "probe": "state the activities and the evidence for each"},

        {"key": "reinforcing_choices", "label": "Reinforcing choices", "prompt": "How the activities reinforce one another",

         "fill": "research", "cues": "fit reinforce complement link reinforce", "queries": ["activity system fit and complementarity"],

         "category": None, "probe": "state the fit you claim, and the evidence"},

        {"key": "boundaries", "label": "What we will not do", "prompt": "Activities, segments or promises deliberately excluded",

         "fill": "research", "cues": "boundary boundaries trade-off tradeoffs exclusion exclude focus discipline not do", "queries": ["strategic trade-offs and exclusions in this industry"],

         "category": None, "probe": "state the exclusions and the reason for each"},

    ],

    "outline": {

        "framework": "Activity-system fit", "context": "The case and its market",

        "discussion": "What the evidence shows",

        "implications": "Implications for the decision",

        "limitations": "Limitations", "conclusion": "Conclusion",

        "lead": ("Activity-system fit examines the position a firm chooses and the activities that deliver it, "

                 "including the choices that reinforce one another and the ones deliberately excluded."),

    },

    "voice": {

        "thesis_question": "whether the activities the evidence supports deliver the position the decision proposes",

        "unit_noun": "market", "block_plural": "elements",

        "lens": "the position, the activities and the fit between them",

        "closing": "identifies the activity the evidence supports most and the element it cannot settle",

        "intro_frame": ("The unit of analysis is the market, because the activity system is a position taken "

                        "inside a market."),

        "context_frame": ("The relevant market is the one named in the brief; the elements are properties of the "

                          "position in that market."),

        "interaction": ("Read together, the elements describe a position in which some are evidenced and others "

                        "are not, and an element without evidence carries no weight."),

        "implication_frame": ("A position has to be delivered by the activities the evidence shows, and by the "

                              "trade-offs it accepts."),

        "reference_heading": "References",

    },

    "notes": {

        block: {

            "analysis": ("This element is part of the position and the activities that deliver it. The relevant "

                         "question is whether the evidence shows it to hold."),

            "qualify": ("The evidence does not establish that the element holds in practice, so it is described "

                        "rather than tested."),

            "short": ("An element without evidence is a claimed activity, not a verified one."),

            "probe": "state the element and the evidence behind it",

        }

        for block in ("strategic_position", "activities", "reinforcing_choices", "boundaries")

    },

}

#: Scenario planning -----------------------------------------------------------

SCENARIO = {

    "template": "template_scenario_planning",

    "key": "scenario",

    "label": "Scenario planning",

    "title_prefix": "Scenario Planning Analysis",

    "subject": "management",

    "unit": {

        "field": "industry",

        "label": "Industry or market",

        "help": "Scenarios are written against a market. Name it.",

        "example": "smartphones, grocery retail, banking",

        "refuse": ("Scenario planning is written against a market. Name the industry or market."),

    },

    "ratings": False,

    "assumption": "probe",

    "sites": "industry",

    "providers": ["brave", "deepseek", "firecrawl"],

    "gate": {"title_cue": True, "title_context": True, "require_geography": False},

    "blocks": [

        {"key": "drivers", "label": "Drivers", "prompt": "The forces that could move the market",

         "fill": "research", "cues": "driver force uncertainty trend variable", "queries": ["driving forces and uncertainty in this industry"],

         "category": None, "probe": "state the drivers and the evidence for each"},

        {"key": "scenarios", "label": "Scenarios", "prompt": "The scenarios built on those drivers",

         "fill": "research", "cues": "scenario future narrative story", "queries": ["scenarios for the future of this industry"],

         "category": None, "probe": "state the scenarios and the driver that distinguishes each"},

        {"key": "implications", "label": "Implications", "prompt": "What each scenario means for the decision",

         "fill": "research", "cues": "implication decision consequence response", "queries": ["implications of alternative futures for this industry"],

         "category": None, "probe": "state the implication of each scenario for the decision"},

        {"key": "signposts", "label": "Signposts", "prompt": "The early signals that say which scenario is arriving",

         "fill": "research", "cues": "signpost signal indicator early warning", "queries": ["early indicators of change in this industry"],

         "category": None, "probe": "state the signpost and how you would read it"},

    ],

    "outline": {

        "framework": "Scenario planning", "context": "The case and its market",

        "discussion": "What the evidence shows",

        "implications": "Implications for the decision",

        "limitations": "Limitations", "conclusion": "Conclusion",

        "lead": ("Scenario planning builds a small number of futures from the drivers that could move a market, "

                 "then records what each means for the decision and the signposts that say which is arriving."),

    },

    "voice": {

        "thesis_question": "whether the scenarios the evidence supports change the decision",

        "unit_noun": "market", "block_plural": "elements",

        "lens": "the drivers, the futures they build and the decisions they change",

        "closing": "identifies the driver the evidence supports most and the scenario it cannot settle",

        "intro_frame": ("The unit of analysis is the market, because scenarios are futures of a market rather than "

                        "of a firm."),

        "context_frame": ("The relevant market is the one named in the brief; the elements are properties of that "

                          "market's future."),

        "interaction": ("Read together, the elements describe a market in which some drivers are evidenced and "

                        "others are not, and a driver without evidence carries no weight."),

        "implication_frame": ("A decision has to survive more than one future, and the signposts must say which "

                              "future is arriving."),

        "reference_heading": "References",

    },

    "notes": {

        block: {

            "analysis": ("This element is part of the scenario set: a driver, a future, its implication or its "

                         "signpost. The relevant question is whether the evidence shows it to hold."),

            "qualify": ("The evidence does not establish the probability of any scenario, so each is described "

                        "rather than forecast."),

            "short": ("A scenario without a driver is a story; a driver without a signpost cannot be tracked."),

            "probe": "state the element and the evidence behind it",

        }

        for block in ("drivers", "scenarios", "implications", "signposts")

    },

}

#: Strategic group map -----------------------------------------------------------

STRATEGIC_GROUP = {

    "template": "template_strategic_group_map",

    "key": "strategic_group",

    "label": "Strategic group mapping",

    "title_prefix": "Strategic Group Mapping Analysis",

    "subject": "management",

    "unit": {

        "field": "industry",

        "label": "Industry or market",

        "help": "Strategic groups are written against a market. Name it.",

        "example": "smartphones, grocery retail, banking",

        "refuse": ("Strategic group mapping is written against a market. Name the industry or market."),

    },

    "ratings": False,

    "assumption": "probe",

    "sites": "industry",

    "providers": ["brave", "deepseek", "firecrawl"],

    "gate": {"title_cue": True, "title_context": True, "require_geography": False},

    "blocks": [

        {"key": "axes", "label": "Axes", "prompt": "The two axes you declare, and why",

         "fill": "research", "cues": "group groups strategic grouping axis dimension price scope geography competitor", "queries": ["strategic groups in this industry"],

         "category": None, "probe": "state the two axes and the rationale for each"},

        {"key": "competitors", "label": "Competitors", "prompt": "The competitors placed on the map",

         "fill": "research", "cues": "competitor firm rival brand", "queries": ["competitors and their positions in this industry"],

         "category": None, "probe": "state the competitors and where each sits"},

        {"key": "groups", "label": "Strategic groups", "prompt": "The groups you assign, and why",

         "fill": "research", "cues": "group cluster strategy position", "queries": ["strategic groups in this industry"],

         "category": None, "probe": "state the groups and the rationale for each"},

        {"key": "mobility", "label": "Mobility barriers", "prompt": "What keeps competitors in their group",

         "fill": "research", "cues": "mobility barrier entry cost scale", "queries": ["mobility barriers between strategic groups"],

         "category": None, "probe": "state the barriers and the evidence for each"},

    ],

    "outline": {

        "framework": "Strategic group mapping", "context": "The case and its market",

        "discussion": "What the evidence shows",

        "implications": "Implications for the decision",

        "limitations": "Limitations", "conclusion": "Conclusion",

        "lead": ("Strategic group mapping places competitors on two declared axes, assigns them to groups, and "

                 "records the mobility barriers between the groups."),

    },

    "voice": {

        "thesis_question": "whether the declared groups explain the positions the evidence shows",

        "unit_noun": "market", "block_plural": "elements",

        "lens": "the axes, the groups and the barriers between them",

        "closing": "identifies the group the evidence supports most and the element it cannot settle",

        "intro_frame": ("The unit of analysis is the market, because strategic groups are a property of a "

                        "market's competitive structure."),

        "context_frame": ("The relevant market is the one named in the brief; the elements are properties of "

                          "that market's competitive structure."),

        "interaction": ("Read together, the elements describe a market in which some positions are evidenced and "

                        "others are not, and a position without evidence carries no weight."),

        "implication_frame": ("A position has to be chosen with the groups and the barriers in view, and the "

                              "axes have to be the ones the evidence supports."),

        "reference_heading": "References",

    },

    "notes": {

        block: {

            "analysis": ("This element is part of the map: the axes, the competitors, the groups or the "

                         "barriers. The relevant question is whether the evidence shows it to hold."),

            "qualify": ("The axes and groups are declared rather than measured, so they are recorded rather than "

                        "tested."),

            "short": ("A map with undeclared axes is a picture of a judgement."),

            "probe": "state the element and the evidence behind it",

        }

        for block in ("axes", "competitors", "groups", "mobility")

    },

}

#: People & organisation -------------------------------------------------------
#:
#: The eight frameworks on the People shelf.  Each one reads a unit the student
#: names, researches every part of it, and says what the evidence cannot settle.
#: None of them designs a role, runs a training, chooses an intervention, scores
#: a person or predicts who will succeed.

#: The eight People & organisation profiles.
#:
#: These are spliced into `framework_profiles.py` by the build step that
#: installs this shelf, so that every profile in the product lives in one
#: module.  The rules these follow are the rules the other shelves follow:
#: one unit of analysis named by the student, one profile per framework, every
#: part researched rather than filled by the model, and a deterministic
#: background paragraph for the parts where no source was found.
#:
#: Nothing in these profiles designs a role, runs a training, chooses an
#: intervention, scores a person or predicts who will succeed.  Each one
#: records a decision and the evidence behind it, and says what it cannot
#: settle.

JOB_CHARACTERISTICS = {
    "template": "template_job_characteristics",
    "key": "job_characteristics",
    "label": "Job Characteristics Model",
    "title_prefix": "Job Characteristics Model Analysis",
    "subject": "people",
    "unit": {
        "field": "process",
        "label": "The role you are reviewing",
        "help": ("A job characteristics review examines one role. Name it in a few words, for example the kitchen "
                 "supervisor role or the counter service role."),
        "example": "the kitchen supervisor role",
        "refuse": ("A job characteristics review examines one role. Name the role you are reviewing, for example "
                   "the kitchen supervisor role or the counter service role."),
    },
    "ratings": False,
    "assumption": "probe",
    "sites": None,
    "providers": None,
    "gate": {"title_context": False, "require_geography": False, "title_cue": False},
    "blocks": [
        {"key": "skill_variety", "label": "Skill variety",
         "prompt": "The range of skills and knowledge the role draws on",
         "fill": "research",
         "cues": "skill skills knowledge training qualification multi-skilled versatile",
         "queries": ["job design skill variety and the breadth of skills a role requires"],
         "category": None,
         "probe": "state the skills and tasks the role actually calls for"},
        {"key": "task_identity", "label": "Task identity",
         "prompt": "Whether the role produces a whole, identifiable piece of work",
         "fill": "research",
         "cues": "task identity whole complete finished unit piece job",
         "queries": ["task identity whether a role produces a whole identifiable piece of work"],
         "category": None,
         "probe": "state whether the role produces a whole piece of work or only part of one"},
        {"key": "task_significance", "label": "Task significance",
         "prompt": "Whether the role's contribution is visible and consequential",
         "fill": "research",
         "cues": "task significance meaningful consequence impact purpose contribution effect",
         "queries": ["task significance and the visible contribution a role makes"],
         "category": None,
         "probe": "state who feels the effect of the role's work"},
        {"key": "autonomy", "label": "Autonomy",
         "prompt": "The discretion the person has over how the work is done",
         "fill": "research",
         "cues": "autonomy discretion control ownership latitude decide decision",
         "queries": ["autonomy and discretion in job design"],
         "category": None,
         "probe": "state which decisions the person makes without reference"},
        {"key": "feedback", "label": "Feedback",
         "prompt": "How the person finds out how well the work is going",
         "fill": "research",
         "cues": "feedback performance information review appraisal results know",
         "queries": ["feedback to workers and job performance information"],
         "category": None,
         "probe": "state how the person hears how the work is going"},
    ],
    "outline": {
        "framework": "Job Characteristics Model",
        "context": "The role and the decision",
        "discussion": "What the evidence shows",
        "implications": "Implications for the decision",
        "limitations": "Limitations",
        "conclusion": "Conclusion",
        "lead": ("A job characteristics analysis examines one role through five characteristics: the skill variety "
                 "it draws on, the task identity it offers, the significance of its contribution, the autonomy "
                 "it allows and the feedback it provides. Each characteristic is treated in turn, first through "
                 "the evidence accepted for the case and then through what that evidence implies for the "
                 "decision the review must serve."),
    },
    "voice": {
        "thesis_question": "whether the evidence supports the characteristics of the role the review depends on",
        "unit_noun": "role",
        "block_plural": "characteristics",
        "lens": "the five characteristics that make a role demanding or draining",
        "closing": ("identifies the characteristic the role depends on most and the characteristic the evidence "
                    "cannot settle"),
        "intro_frame": ("The unit of analysis is the role rather than the firm, because job design is a property "
                        "of the work a person does and not of the organisation's people policy in general."),
        "context_frame": ("The relevant role is the one named in the brief; the characteristics belong to that "
                          "role rather than to the organisation's people policy in general."),
        "interaction": ("Read together, the characteristics describe a role: some are evidenced and some are "
                        "not, and a characteristic without accepted evidence cannot be treated as present."),
        "implication_frame": ("A decision about a role has to satisfy the characteristics the review relies on: "
                              "the skill the work demands, the discretion the person needs and the information "
                              "the person gets."),
        "reference_heading": "References",
    },
    "notes": {
        "skill_variety": {
            "analysis": ("Skill variety is the breadth of knowledge, skill and ability a role draws on, and the "
                         "breadth of different tasks it asks the person to perform. Where the work is narrow, the "
                         "person develops the skills they use and little else, and the capability available to "
                         "the organisation is narrower than the work may require. Where the work is wide, the "
                         "person can cover more of the process and can be moved when priorities change. The "
                         "relevant question is whether the skill variety the role actually demands is the skill "
                         "variety the design provides."),
            "qualify": ("The evidence does not establish what the role requires in practice or how the skills "
                        "were acquired, so the demand for skill is described rather than measured."),
            "short": ("A role that asks for more skill than it offers is a role that hires for potential it "
                      "never develops."),
            "probe": "state the skills and tasks the role actually calls for",
        },
        "task_identity": {
            "analysis": ("Task identity is whether the role produces a whole, identifiable piece of work rather "
                         "than a fragment of it. Where the person completes a recognisable unit, the work carries "
                         "meaning and the result of an effort can be seen. Where the person completes only part "
                         "of a unit, the effort is separated from its purpose, and the result depends on what "
                         "other people do next. The relevant question is whether the role leaves the person with "
                         "a finished piece of work."),
            "qualify": ("The evidence does not establish how the work is divided between roles, so the boundary "
                        "of the task is described rather than confirmed."),
            "short": "A person who never finishes anything cannot see that the work mattered.",
            "probe": "state whether the role produces a whole piece of work or only part of one",
        },
        "task_significance": {
            "analysis": ("Task significance is whether the contribution the role makes is visible and "
                         "consequential. Where the role's effect reaches the customer, the colleague or the "
                         "public, the person can connect effort to result. Where the effect is hidden or "
                         "distant, the work can be done well without the person ever learning that it "
                         "mattered. The relevant question is whether the significance the role actually has is "
                         "visible to the person doing it."),
            "qualify": ("The evidence does not establish how the contribution of the role is perceived, so "
                        "significance is argued from the work rather than measured from it."),
            "short": "Work nobody can see the effect of is work people stop taking pride in.",
            "probe": "state who feels the effect of the role's work",
        },
        "autonomy": {
            "analysis": ("Autonomy is the discretion the person has over how the work is done: the scope of "
                         "decisions they may take, the order in which they act, and the judgement they exercise "
                         "without reference. Where the discretion is narrow, the person carries the "
                         "responsibility for a result they cannot shape, which is a common source of effort that "
                         "buys nothing. Where the discretion is real, the person can adapt the method to the "
                         "case in front of them. The relevant question is whether the autonomy the design grants "
                         "matches the responsibility the role carries."),
            "qualify": ("The evidence does not establish which decisions the person actually takes, so the scope "
                        "of discretion is described rather than confirmed."),
            "short": "Responsibility without discretion is effort the organisation pays for and does not use.",
            "probe": "state which decisions the person makes without reference",
        },
        "feedback": {
            "analysis": ("Feedback is how the person finds out how the work is going while the work is still "
                         "going on. Where the information arrives soon and concerns the work itself, the person "
                         "can adjust the next attempt. Where the information arrives late, or concerns the "
                         "person rather than the work, the learning arrives after the decisions that mattered "
                         "have been made. The relevant question is whether the feedback the role receives is "
                         "timely and about the work."),
            "qualify": ("The evidence does not establish how often the role receives feedback or what it "
                        "contains, so the arrangement is described rather than evaluated."),
            "short": "Feedback that arrives after the season has turned cannot change the season.",
            "probe": "state how the person hears how the work is going",
        },
    },
}

KIRKPATRICK = {
    "template": "template_kirkpatrick",
    "key": "kirkpatrick",
    "label": "Kirkpatrick Training Evaluation Model",
    "title_prefix": "Kirkpatrick Training Evaluation Analysis",
    "subject": "people",
    "unit": {
        "field": "process",
        "label": "The training you are evaluating",
        "help": ("A training evaluation reads one programme. Name it in a few words, for example the food "
                 "safety induction for kitchen staff or the manual handling course for warehouse staff."),
        "example": "the food safety induction for kitchen staff",
        "refuse": ("A training evaluation reads one programme. Name the training you are evaluating, for "
                   "example the food safety induction for kitchen staff or the manual handling course for "
                   "warehouse staff."),
    },
    "ratings": False,
    "assumption": "probe",
    "sites": None,
    "providers": None,
    "gate": {"title_context": False, "require_geography": False, "title_cue": False},
    "blocks": [
        {"key": "reaction", "label": "Reaction",
         "prompt": "What participants thought of the training and whether they valued it",
         "fill": "research",
         "cues": "reaction satisfaction happy useful feedback evaluation participants",
         "queries": ["evaluation of learner reaction and satisfaction with training"],
         "category": None,
         "probe": "state what participants said about the training and how they were asked"},
        {"key": "learning", "label": "Learning",
         "prompt": "What participants learned, and what they can show they learned it",
         "fill": "research",
         "cues": "learning knowledge skill test assessment recall baseline pass",
         "queries": ["assessment of learning outcomes after training"],
         "category": None,
         "probe": "state what participants can now show, and how it was shown"},
        {"key": "behavior", "label": "Behaviour",
         "prompt": "What participants did differently at work afterwards",
         "fill": "research",
         "cues": "behaviour behavior change application practice transfer supervisor observe",
         "queries": ["transfer of training to the workplace and supervisor observation"],
         "category": None,
         "probe": "state what participants did differently at work afterwards"},
        {"key": "results", "label": "Results",
         "prompt": "What the organisation gained from the training",
         "fill": "research",
         "cues": "results outcome impact benefit productivity quality turnover cost savings",
         "queries": ["organisational outcomes attributed to a training programme"],
         "category": None,
         "probe": "state what the organisation gained, and what else changed at the same time"},
    ],
    "outline": {
        "framework": "Kirkpatrick Training Evaluation",
        "context": "The training and the decision",
        "discussion": "What the evidence shows",
        "implications": "Implications for the decision",
        "limitations": "Limitations",
        "conclusion": "Conclusion",
        "lead": ("A training evaluation reads a programme at four levels: what participants thought, what they "
                 "learned, what they did differently at work, and what the organisation gained. Each level is "
                 "treated in turn, first through the evidence accepted for the case and then through what that "
                 "evidence implies for the decision the evaluation must serve."),
    },
    "voice": {
        "thesis_question": "whether the evidence reaches the level of result the decision depends on",
        "unit_noun": "training",
        "block_plural": "levels",
        "lens": "the four levels at which a training programme can be judged",
        "closing": "identifies the level the evidence reaches and the level the evidence cannot settle",
        "intro_frame": ("The unit of analysis is the training rather than the firm, because a training is judged "
                        "at four levels and each level answers a different question about the same programme."),
        "context_frame": ("The relevant training is the one named in the brief; the levels are properties of that "
                          "programme rather than of the organisation's training activity in general."),
        "interaction": ("Read together, the levels form a chain: a weaker level does not support a stronger "
                        "claim, and the chain is only as strong as its weakest evidenced link."),
        "implication_frame": ("A decision to run, change or stop the training has to rest on the level the "
                              "evidence actually reaches, and on what the organisation can do about the level "
                              "below it."),
        "reference_heading": "References",
    },
    "notes": {
        "reaction": {
            "analysis": ("Reaction is what participants thought of the training and whether they valued it. It is "
                         "the level of the evaluation the organisation can obtain cheaply and immediately, and it "
                         "is the level most often treated as evidence of success. It is evidence of acceptance, "
                         "not of learning, and the two are commonly confused. The relevant question is whether "
                         "what participants said is being read as a judgement on the training or only as a "
                         "measure of satisfaction."),
            "qualify": ("The evidence does not establish how participants were asked or how they answered, so "
                        "the reaction is described rather than measured."),
            "short": "A satisfied audience is not the same as a capable one, and only one of them is evidence.",
            "probe": "state what participants said about the training and how they were asked",
        },
        "learning": {
            "analysis": ("Learning is what participants took from the training, shown by what they can now do "
                         "or know. It is the first level at which the training can be said to have worked, and it "
                         "is the first level at which the organisation has to have designed the assessment rather "
                         "than assumed it. The relevant question is whether what participants can now do was "
                         "established in a way that would have shown the learning had not happened."),
            "qualify": ("The evidence does not establish the assessment used or the standard applied, so the "
                        "learning is described rather than established."),
            "short": "Learning that was never assessed is a claim the organisation has made about itself.",
            "probe": "state what participants can now show, and how it was shown",
        },
        "behavior": {
            "analysis": ("Behaviour is what participants did differently at work afterwards. Learning that does "
                         "not reach the workplace changes the person and not the organisation, and the gap "
                         "between the two is where most training effort is quietly lost. Transfer depends on the "
                         "conditions the participant meets back at work. The relevant question is whether the "
                         "work the participants returned to gave them the scope to use what they had learned."),
            "qualify": ("The evidence does not establish what participants did at work or how that was "
                        "observed, so the transfer is described rather than traced."),
            "short": "Training that stops at the course door has changed the invoice rather than the work.",
            "probe": "state what participants did differently at work afterwards",
        },
        "results": {
            "analysis": ("Results are what the organisation gained from the training: the change in the "
                         "service, the cost or the measure the organisation set out to move. This is the level "
                         "the decision is usually argued from, and it is the level most exposed to the problems "
                         "of attribution, because many things change at once and a single programme rarely "
                         "explains the change. The relevant question is whether the result can be attributed to "
                         "the training rather than to everything else that moved at the same time."),
            "qualify": ("The evidence does not establish what the result was or what else changed at the same "
                        "time, so the outcome is described rather than attributed."),
            "short": ("A result that cannot be separated from everything else that changed is not yet an "
                      "argument for the training."),
            "probe": "state what the organisation gained, and what else changed at the same time",
        },
    },
}

AMO = {
    "template": "template_amo",
    "key": "amo",
    "label": "AMO Framework",
    "title_prefix": "AMO Framework Analysis",
    "subject": "people",
    "unit": {
        "field": "process",
        "label": "The performance problem you are diagnosing",
        "help": ("An ability, motivation and opportunity diagnosis explains one performance problem. Name it "
                 "in a few words, for example slow service on the meal counter or the late reporting in the "
                 "ward office."),
        "example": "slow service on the meal counter",
        "refuse": ("An ability, motivation and opportunity diagnosis explains one performance problem. Name "
                   "the problem you are diagnosing, for example slow service on the meal counter or the late "
                   "reporting in the ward office."),
    },
    "ratings": False,
    "assumption": "probe",
    "sites": None,
    "providers": None,
    "gate": {"title_context": False, "require_geography": False, "title_cue": False},
    "blocks": [
        {"key": "ability", "label": "Ability",
         "prompt": "Whether the person has the skill and knowledge to do the work",
         "fill": "research",
         "cues": "ability skill knowledge competence training qualified experience capability",
         "queries": ["skill ability and competence required for the work"],
         "category": None,
         "probe": "state what the work demands and what the person can do"},
        {"key": "motivation", "label": "Motivation",
         "prompt": "Whether the person wants to do the work, and sees the reason to",
         "fill": "research",
         "cues": "motivation willing effort care morale incentive want commitment",
         "queries": ["motivation and effort in the workplace"],
         "category": None,
         "probe": "state what the person wants from the role and why the work is worth doing"},
        {"key": "opportunity", "label": "Opportunity",
         "prompt": "Whether the person is allowed and equipped to do the work",
         "fill": "research",
         "cues": "opportunity allowed permitted resources tools time authority blocked process",
         "queries": ["resources time and authority given to perform the work"],
         "category": None,
         "probe": "state what the person is allowed and equipped to do"},
    ],
    "outline": {
        "framework": "Ability, Motivation and Opportunity",
        "context": "The performance problem and the decision",
        "discussion": "What the evidence shows",
        "implications": "Implications for the decision",
        "limitations": "Limitations",
        "conclusion": "Conclusion",
        "lead": ("An ability, motivation and opportunity diagnosis explains a performance problem by asking "
                 "what is present and what is missing: whether the person has the skill, whether the person "
                 "wants to do the work, and whether the organisation has allowed and equipped the work to be "
                 "done. Each condition is treated in turn, first through the evidence accepted for the case "
                 "and then through what that evidence implies for the decision the diagnosis must serve."),
    },
    "voice": {
        "thesis_question": "whether the evidence shows which part of performance the case turns on",
        "unit_noun": "performance",
        "block_plural": "conditions",
        "lens": "the three conditions that have to hold together for performance to happen",
        "closing": ("identifies the condition the evidence points to and the condition the evidence cannot "
                    "settle"),
        "intro_frame": ("The unit of analysis is the performance problem rather than the firm, because the "
                        "framework asks a narrower question than most people management asks: what is present "
                        "and what is missing."),
        "context_frame": ("The relevant problem is the one named in the brief; the conditions belong to that "
                          "performance rather than to the organisation's people policy in general."),
        "interaction": ("Read together, the conditions are a diagnosis rather than a sequence: the evidence "
                        "points to one condition without clearing the others, and a diagnosis that clears only "
                        "one does not explain the result."),
        "implication_frame": ("A decision about a performance problem has to address the condition the "
                              "evidence points to, and cannot be made to work by demanding effort at a "
                              "condition the organisation has not supplied."),
        "reference_heading": "References",
    },
    "notes": {
        "ability": {
            "analysis": ("Ability is whether the person has the skill and knowledge to do the work. It is the "
                         "part of performance most often treated as settled, because the selection that "
                         "appointed the person was evidence of ability at the time of the appointment. Ability "
                         "is consumed by doing the work and can be eroded by work that is unfamiliar. The "
                         "relevant question is whether the skill the work now demands is the skill the person "
                         "was hired with."),
            "qualify": ("The evidence does not establish what the work demands of the person or what the "
                        "person can do in it, so the ability is described rather than assessed."),
            "short": ("Performance explained by ability cannot be fixed by motivation, and asking for effort "
                      "cannot supply a skill the work needs."),
            "probe": "state what the work demands and what the person can do",
        },
        "motivation": {
            "analysis": ("Motivation is whether the person wants to do the work and sees the reason to. It is "
                         "the part of performance that moves most easily and is measured least often, because it "
                         "is the part of the case the organisation cannot observe directly. Where the reason to "
                         "perform is unclear, effort is spent on the part of the job that is noticed rather "
                         "than on the part that matters. The relevant question is whether the person can see "
                         "what good performance in this role is for."),
            "qualify": ("The evidence does not establish what the person wants or what they believe the role "
                        "is for, so the motivation is described rather than inferred from performance."),
            "short": "Effort spent where it is noticed is not the same as effort spent where it is wanted.",
            "probe": "state what the person wants from the role and why the work is worth doing",
        },
        "opportunity": {
            "analysis": ("Opportunity is whether the person is allowed and equipped to do the work. It is the "
                         "part of performance that no amount of individual effort can supply: the authority, the "
                         "information, the time and the equipment that let the work be done at all. Where the "
                         "organisation asks for a performance it has not made possible, the result is a demand "
                         "the person cannot meet. The relevant question is whether the organisation has given "
                         "the person the means to do what it asks of them."),
            "qualify": ("The evidence does not establish what the person is permitted or equipped to do, so "
                        "the opportunity is described rather than confirmed."),
            "short": "An organisation that withholds the means cannot fairly blame the person for the result.",
            "probe": "state what the person is allowed and equipped to do",
        },
    },
}

TUCKMAN = {
    "template": "template_tuckman",
    "key": "tuckman",
    "label": "Tuckman's Team Development Stages",
    "title_prefix": "Team Development Stage Review",
    "subject": "people",
    "unit": {
        "field": "process",
        "label": "The team you are reviewing",
        "help": ("A team development review reads one team. Name it in a few words, for example the tray "
                 "assembly team or the counter service team."),
        "example": "the tray assembly team",
        "refuse": ("A team development review reads one team. Name the team you are reviewing, for example "
                   "the tray assembly team or the counter service team."),
    },
    "ratings": False,
    "assumption": "probe",
    "sites": None,
    "providers": None,
    "gate": {"title_context": False, "require_geography": False, "title_cue": False},
    "blocks": [
        {"key": "forming", "label": "Forming",
         "prompt": "The stage where the team is orienting itself to the task and to each other",
         "fill": "research",
         "cues": "forming new team orientation first meeting introduction unsure",
         "queries": ["early stage of team formation and orientation to a task"],
         "category": None,
         "probe": "state what the team was told at the outset and what it still does not know"},
        {"key": "storming", "label": "Storming",
         "prompt": "The stage where roles, boundaries and ways of working are contested",
         "fill": "research",
         "cues": "storming conflict argument disagreement friction role clash resistance",
         "queries": ["conflict within a newly formed team and the contest over roles"],
         "category": None,
         "probe": "state what the team is contesting and how it is being settled"},
        {"key": "norming", "label": "Norming",
         "prompt": "The stage where the team settles on how it will work together",
         "fill": "research",
         "cues": "norming agreement norms routine settle ways working together",
         "queries": ["team norms and the working agreements a team adopts"],
         "category": None,
         "probe": "state the working arrangements the team has settled"},
        {"key": "performing", "label": "Performing",
         "prompt": "The stage where the team works together on the task",
         "fill": "research",
         "cues": "performing effective working together delivering interdependent flow",
         "queries": ["team performance and interdependence in delivering a shared task"],
         "category": None,
         "probe": "state what the team delivered together and how the members' work combined"},
        {"key": "adjourning", "label": "Adjourning",
         "prompt": "The stage where the team closes down, or changes shape",
         "fill": "research",
         "cues": "adjourning ending break up disband member leaving change team closure",
         "queries": ["team dissolution and the ending of a team's work"],
         "category": None,
         "probe": "state why the team is ending and what has been arranged"},
    ],
    "outline": {
        "framework": "Tuckman Team Development",
        "context": "The team and the decision",
        "discussion": "What the evidence shows",
        "implications": "Implications for the decision",
        "limitations": "Limitations",
        "conclusion": "Conclusion",
        "lead": ("A team development review reads one team against the stages a group passes through: "
                 "orienting itself, contesting its arrangements, settling them, working together on the task, "
                 "and closing down. Each stage is treated in turn, first through the evidence accepted for the "
                 "case and then through what that evidence implies for the decision the review must serve."),
    },
    "voice": {
        "thesis_question": "whether the evidence places the team in the stage the review assumes",
        "unit_noun": "team",
        "block_plural": "stages",
        "lens": "the stages a team passes through as it forms, settles and closes",
        "closing": "identifies the stage the evidence supports and the stage the evidence cannot settle",
        "intro_frame": ("The unit of analysis is the team rather than the firm, because the stages describe "
                        "what is happening inside a group of people who work together rather than what is "
                        "happening in an organisation."),
        "context_frame": ("The relevant team is the one named in the brief; the stages belong to that team "
                          "rather than to the organisation's teams in general."),
        "interaction": ("Read together, the stages give a reading of the team's present condition rather "
                        "than a schedule it must follow, and a team may be held in one stage for longer than "
                        "the model expects."),
        "implication_frame": ("A decision about the team has to match the stage the evidence places it in: "
                              "support offered to a forming team and support offered to a team in conflict are "
                              "not the same intervention."),
        "reference_heading": "References",
    },
    "notes": {
        "forming": {
            "analysis": ("Forming is the stage in which a team is orienting itself: to the task, to the "
                         "people in it and to what is expected of it. Uncertainty is the defining condition of "
                         "this stage, and the effort it consumes is effort spent on questions that a settled "
                         "team does not ask. The relevant question is whether the team has been given the "
                         "orientation the task needs, or whether it is expected to work it out from nothing."),
            "qualify": ("The evidence does not establish how long the team has existed or what it was told at "
                        "the outset, so the stage is described rather than dated."),
            "short": "Time spent on questions the team was never given the answer to is time the task does not get.",
            "probe": "state what the team was told at the outset and what it still does not know",
        },
        "storming": {
            "analysis": ("Storming is the stage in which the team contests its roles, its boundaries and its "
                         "ways of working. The conflict is structural rather than personal: members are testing "
                         "what the arrangement allows them to claim, and where the arrangement is unstated the "
                         "contest runs until it is settled in practice rather than in principle. The relevant "
                         "question is whether the team has a stated way of settling the disagreement it is "
                         "having."),
            "qualify": ("The evidence does not establish what the disagreement is about or how it has been "
                        "handled, so the contest is described rather than judged."),
            "short": ("Conflict that nobody has been given the means to settle becomes the method by which the "
                      "team works."),
            "probe": "state what the team is contesting and how it is being settled",
        },
        "norming": {
            "analysis": ("Norming is the stage in which the team settles how it will work together: the "
                         "working arrangements it has adopted, the expectations it holds of each other and the "
                         "conventions it no longer discusses. The evidence of this stage is in what the team has "
                         "stopped raising, which makes it difficult to observe from outside and easy to miss. "
                         "The relevant question is whether the arrangements the team has settled are the ones "
                         "the work needs."),
            "qualify": ("The evidence does not establish what the team has agreed or how the agreements were "
                        "made, so the conventions are described rather than confirmed."),
            "short": "A convention the team has never stated still governs the work; it is simply unexamined.",
            "probe": "state the working arrangements the team has settled",
        },
        "performing": {
            "analysis": ("Performing is the stage in which the team works together on the task with the "
                         "members' attention on the work rather than on the arrangement. Interdependence is what "
                         "the stage requires: the members' contributions have to be made in a way another "
                         "member can use. The relevant question is whether the team is able to deliver the work "
                         "that depends on more than one member of it."),
            "qualify": ("The evidence does not establish what the team delivered or how the members' work "
                        "combined, so the performance is described rather than evaluated."),
            "short": "A team that has settled its arrangements has not yet shown that it can deliver together.",
            "probe": "state what the team delivered together and how the members' work combined",
        },
        "adjourning": {
            "analysis": ("Adjourning is the stage in which a team closes down or changes shape: its purpose "
                         "ends, its membership changes or its work is absorbed elsewhere. The stage is routinely "
                         "skipped in accounts of teams, and the costs of the ending are then carried by the "
                         "organisation without being named. The relevant question is whether the team is being "
                         "ended deliberately, with the knowledge and the arrangements that ending requires."),
            "qualify": ("The evidence does not establish why the team is ending or what has been arranged for "
                        "the members, so the closing is described rather than assessed."),
            "short": "A team that ends without ceremony carries its ending into everything that came after it.",
            "probe": "state why the team is ending and what has been arranged",
        },
    },
}

NINE_BOX = {
    "template": "template_nine_box",
    "key": "nine_box",
    "label": "Nine-Box Talent Grid",
    "title_prefix": "Nine-Box Talent Grid Review",
    "subject": "people",
    "unit": {
        "field": "process",
        "label": "The team you are reviewing",
        "help": ("A talent grid review places a group of people. Name the group in a few words, for example "
                 "the counter team or the ward nursing team."),
        "example": "the counter team",
        "refuse": ("A talent grid review places a group of people. Name the group you are reviewing, for "
                   "example the counter team or the ward nursing team."),
    },
    "ratings": False,
    "assumption": "probe",
    "sites": None,
    "providers": None,
    "gate": {"title_context": False, "require_geography": False, "title_cue": False},
    "blocks": [
        {"key": "performance_criteria", "label": "Performance criteria",
         "prompt": "How performance is judged, the criteria you use, and the evidence for each",
         "fill": "research",
         "cues": "performance criteria measure result quality rating target assessment",
         "queries": ["criteria used to assess performance and the evidence behind them"],
         "category": None,
         "probe": "state the criteria used to judge performance and the evidence for each"},
        {"key": "potential_criteria", "label": "Potential criteria",
         "prompt": "How potential is judged, the criteria you use, and the evidence for each",
         "fill": "research",
         "cues": "potential criteria ability readiness growth ambition capable future",
         "queries": ["criteria used to assess potential for a wider role"],
         "category": None,
         "probe": "state the criteria used to judge potential and the evidence for each"},
        {"key": "placements", "label": "Placements",
         "prompt": "Where each person you name sits in the nine boxes, and why",
         "fill": "research",
         "cues": "placement placed grid box performance potential team member staff",
         "queries": ["placing employees in a performance and potential grid"],
         "category": None,
         "probe": "state where each person named sits and the reason for it"},
        {"key": "development_actions", "label": "Development actions",
         "prompt": "What the placements require you to do for each group",
         "fill": "research",
         "cues": "development action plan rotation coaching stretch successor",
         "queries": ["development action planning from a talent review"],
         "category": None,
         "probe": "state the action each placement requires and who will arrange it"},
    ],
    "outline": {
        "framework": "Nine-Box Talent Grid",
        "context": "The team and the decision",
        "discussion": "What the evidence shows",
        "implications": "Implications for the decision",
        "limitations": "Limitations",
        "conclusion": "Conclusion",
        "lead": ("A talent grid review sets out four things: the criteria by which performance is judged, the "
                 "criteria by which potential is judged, where each person named is placed, and what those "
                 "placements require the organisation to do. Each part is treated in turn, first through the "
                 "evidence accepted for the case and then through what that evidence implies for the decision "
                 "the review must serve."),
    },
    "voice": {
        "thesis_question": "whether the evidence supports the judgements the grid rests on",
        "unit_noun": "team",
        "block_plural": "parts",
        "lens": "the criteria, the placements and the actions that turn a grid into a decision",
        "closing": ("identifies the part of the grid the decision depends on and the part the evidence cannot "
                    "settle"),
        "intro_frame": ("The unit of analysis is the group being reviewed rather than the firm, because a "
                        "talent grid is a set of judgements about named people and the criteria behind them."),
        "context_frame": ("The relevant group is the one named in the brief; the criteria and the placements "
                          "belong to that group rather than to the organisation's people in general."),
        "interaction": ("Read together, the parts form a chain of reasons: the criteria must be written down "
                        "before the placements can be defended, and the placements must be defended before the "
                        "actions can be justified."),
        "implication_frame": ("A decision about the group has to rest on criteria the organisation is willing "
                              "to publish, because a grid whose criteria are secret cannot be discussed by the "
                              "people it places."),
        "reference_heading": "References",
    },
    "notes": {
        "performance_criteria": {
            "analysis": ("Performance criteria are the measures by which performance is judged: what is "
                         "counted, what is compared and what counts as good. A grid built on unstated criteria "
                         "records the judgement of whoever placed the boxes rather than the performance of the "
                         "people in them, and the placement then looks like a finding. The relevant question is "
                         "whether the criteria that were used are written down, applied to everyone alike and "
                         "supported by evidence that is visible to the people judged."),
            "qualify": ("The evidence does not establish the criteria applied or how consistently they were "
                        "applied, so the judgement is described rather than audited."),
            "short": "A placement that cannot be traced to a written criterion is a record of opinion.",
            "probe": "state the criteria used to judge performance and the evidence for each",
        },
        "potential_criteria": {
            "analysis": ("Potential criteria are the measures by which potential is judged: the readiness, the "
                         "capacity and the appetite for a wider role that the evidence supports. Potential is "
                         "the harder of the two judgements because it concerns a person in a role they have not "
                         "yet held. The relevant question is whether the criteria used for potential are the "
                         "same as those used for performance, because where one set measures past output and "
                         "the other measures future capacity the two axes are not describing the same thing."),
            "qualify": ("The evidence does not establish what the criteria for potential measure, so the "
                        "judgement is described rather than tested."),
            "short": "Two axes that measure different things make a grid that cannot be read.",
            "probe": "state the criteria used to judge potential and the evidence for each",
        },
        "placements": {
            "analysis": ("Placements are where each person named sits in the grid, and the reason for it. The "
                         "placement is where the criteria are tested against a person rather than against a "
                         "job, and it is where the cost of a wrong judgement appears. The relevant question is "
                         "whether each placement is supported by the criteria stated and by the evidence behind "
                         "them."),
            "qualify": ("The evidence does not establish the basis of any individual placement, so the "
                        "placement is described rather than endorsed."),
            "short": "A placement the person could not see the reason for will be disputed rather than acted on.",
            "probe": "state where each person named sits and the reason for it",
        },
        "development_actions": {
            "analysis": ("Development actions are what the placements require: the movement, the assignment, "
                         "the support or the experience each group of people needs. A grid that produces no "
                         "action has documented a judgement without having decided anything, and the judgements "
                         "become stale. The relevant question is whether the action taken for each group is "
                         "matched to what the placement actually says."),
            "qualify": ("The evidence does not establish what action was arranged or what each person was "
                        "told, so the action is described rather than confirmed."),
            "short": "A grid with no action behind it records a ranking without making a decision.",
            "probe": "state the action each placement requires and who will arrange it",
        },
    },
}

KOTTER = {
    "template": "template_kotter",
    "key": "kotter",
    "label": "Kotter's Eight-Step Change Model",
    "title_prefix": "Kotter Eight-Step Change Review",
    "subject": "people",
    "unit": {
        "field": "process",
        "label": "The change you are planning",
        "help": ("A change review reads one programme of change. Name it in a few words, for example moving "
                 "the campus meal card to a contactless system or the restructuring of the ward rota."),
        "example": "moving the campus meal card to a contactless system",
        "refuse": ("A change review reads one programme of change. Name the change you are planning, for "
                   "example moving the campus meal card to a contactless system or the restructuring of the "
                   "ward rota."),
    },
    "ratings": False,
    "assumption": "probe",
    "sites": None,
    "providers": None,
    "gate": {"title_context": False, "require_geography": False, "title_cue": False},
    "blocks": [
        {"key": "urgency", "label": "Create urgency",
         "prompt": "The case for change, and the evidence that it cannot wait",
         "fill": "research",
         "cues": "urgency crisis deadline losing competitive complaint decline window",
         "queries": ["creating urgency for change and the case for acting now"],
         "category": None,
         "probe": "state what makes the change cannot wait and what is at stake"},
        {"key": "coalition", "label": "Form a powerful coalition",
         "prompt": "Who must lead the change, and why that group",
         "fill": "research",
         "cues": "coalition sponsor leadership team group authority power influential",
         "queries": ["leadership coalition guiding a change programme"],
         "category": None,
         "probe": "state who must lead the change and why that group"},
        {"key": "vision", "label": "Create a vision for change",
         "prompt": "What the organisation is aiming at once the change is made",
         "fill": "research",
         "cues": "vision future aim goal state strategy direction picture",
         "queries": ["vision and communication of a change vision"],
         "category": None,
         "probe": "state what the organisation is aiming at and how a person would recognise progress"},
        {"key": "communicate", "label": "Communicate the vision",
         "prompt": "How the vision reaches people, and what they are told",
         "fill": "research",
         "cues": "communicate communicates communicating communication message brief meeting conversation explain",
         "queries": ["communicating a change vision to employees"],
         "category": None,
         "probe": "state how the vision reaches people and what they are told"},
        {"key": "empower", "label": "Empower others to act",
         "prompt": "What removes the barriers that stop people acting",
         "fill": "research",
         "cues": "empower remove barrier obstacle delegate authority permission freedom",
         "queries": ["removing barriers to action and delegating authority during change"],
         "category": None,
         "probe": "state what stops people acting and who can remove it"},
        {"key": "wins", "label": "Plan for and create short-term wins",
         "prompt": "The early results that show the change is working",
         "fill": "research",
         "cues": "win early result milestone quick visible early success short-term",
         "queries": ["short term wins that build momentum in a change programme"],
         "category": None,
         "probe": "state the early result that shows the change is working and who will see it"},
        {"key": "consolidate", "label": "Consolidate gains and produce more change",
         "prompt": "How the early wins are used to go further",
         "fill": "research",
         "cues": "consolidate sustain momentum use gains further wave next change",
         "queries": ["consolidating gains and sustaining momentum in change"],
         "category": None,
         "probe": "state how the early wins are being used to go further"},
        {"key": "institutionalize", "label": "Institutionalize new approaches",
         "prompt": "What anchors the change in how the organisation works day to day",
         "fill": "research",
         "cues": "institutionalize anchor embed culture routine policy standard sustain",
         "queries": ["institutionalising change in routines policy and measures"],
         "category": None,
         "probe": "state what in the day-to-day working now carries the change"},
    ],
    "outline": {
        "framework": "Kotter Eight-Step Change Model",
        "context": "The change and the decision",
        "discussion": "What the evidence shows",
        "implications": "Implications for the decision",
        "limitations": "Limitations",
        "conclusion": "Conclusion",
        "lead": ("A change review reads a programme against the steps of a change sequence: making the case "
                 "urgent, forming a coalition, setting a vision, communicating it, removing the barriers, "
                 "producing an early result, consolidating that result and anchoring the change in the way the "
                 "organisation works. Each step is treated in turn, first through the evidence accepted for the "
                 "case and then through what that evidence implies for the decision the review must serve."),
    },
    "voice": {
        "thesis_question": "whether the evidence supports the change programme the decision depends on",
        "unit_noun": "change",
        "block_plural": "steps",
        "lens": "the steps a change programme moves through, in the order they depend on each other",
        "closing": "identifies the step the change depends on and the step the evidence cannot settle",
        "intro_frame": ("The unit of analysis is the change rather than the firm, because a change programme "
                        "is a sequence whose steps depend on each other rather than a set of independent "
                        "initiatives."),
        "context_frame": ("The relevant change is the one named in the brief; the steps belong to that "
                          "programme rather than to the organisation's change activity in general."),
        "interaction": ("Read together, the steps show where the programme stands rather than a programme "
                        "that must be followed, and a change may be stalled at a step without having failed at "
                        "it."),
        "implication_frame": ("A decision about the change has to match the step the programme has reached: "
                              "the support a programme needs at one step is not the support it needs at "
                              "another."),
        "reference_heading": "References",
    },
    "notes": {
        "urgency": {
            "analysis": ("Urgency is the case for change: why it cannot wait, and what happens if it does. "
                         "Change programmes fail here more often than at any later stage, because a change that "
                         "is urgent for one part of the organisation is not urgent for the parts it will "
                         "disturb. The relevant question is whether the case for change is made in terms the "
                         "people who must act on it already accept as real."),
            "qualify": ("The evidence does not establish what will be lost if the change is delayed, so the "
                        "case for change is described rather than sized."),
            "short": ("A change that only some of the organisation sees as urgent will meet resistance "
                      "exactly where it costs most."),
            "probe": "state what makes the change cannot wait and what is at stake",
        },
        "coalition": {
            "analysis": ("The coalition is the group that must lead the change, and the reason it is that "
                         "group rather than another. A change carried by one leader is a change that stops when "
                         "the leader does, and a change carried by a group that does not include those who "
                         "lose from it is a change that will be lost to them. The relevant question is whether "
                         "the coalition includes the authority to decide and the people whose agreement the "
                         "change depends on."),
            "qualify": ("The evidence does not establish who has agreed to lead the change, so the coalition "
                        "is described rather than confirmed."),
            "short": "A coalition of only the willing will carry only what the willing will accept.",
            "probe": "state who must lead the change and why that group",
        },
        "vision": {
            "analysis": ("The vision is where the organisation is aiming once the change is made, stated so "
                         "that people can tell whether it has been reached. A vision that lists programmes is "
                         "not a vision because it cannot be judged; the test is whether the work of the "
                         "organisation can be said to have moved towards it. The relevant question is whether "
                         "the stated aim is one that the people doing the work can recognise in their own "
                         "work."),
            "qualify": ("The evidence does not establish whether the aim has been understood by the people "
                        "doing the work, so the vision is described rather than tested."),
            "short": ("A vision that lists what will be built is a plan, and plans do not tell people which "
                      "of their work matters."),
            "probe": "state what the organisation is aiming at and how a person would recognise progress",
        },
        "communicate": {
            "analysis": ("Communicating the vision is how the aim reaches people: what is said, through "
                         "which channels, and how often the message can be expected to have been heard. "
                         "Communication is usually measured by what was sent rather than by what was "
                         "understood, and the two diverge most sharply in a change that alters what people are "
                         "asked to do. The relevant question is whether the people affected have been told in "
                         "terms they can apply to their own work."),
            "qualify": ("The evidence does not establish what was communicated or what was understood, so the "
                        "communication is described rather than evaluated."),
            "short": "A message that has been sent is not the same as a message that has been understood.",
            "probe": "state how the vision reaches people and what they are told",
        },
        "empower": {
            "analysis": ("Empowering others to act means removing what stops people acting: an approval "
                         "that will not be given, a rule that has not been changed, a decision that is still "
                         "reserved to a senior manager. Obstacles that stay in place make the change nominal, "
                         "and the organisation discovers this when the change has been announced and nothing "
                         "has moved. The relevant question is whether the barriers have been identified and who "
                         "is able to remove them."),
            "qualify": ("The evidence does not establish what barriers exist or who can remove them, so the "
                        "barriers are described rather than resolved."),
            "short": ("A change announced to a team that is still not allowed to act will produce compliance "
                      "and nothing else."),
            "probe": "state what stops people acting and who can remove it",
        },
        "wins": {
            "analysis": ("Short-term wins are the early results that show the change is working. They do more "
                         "than demonstrate progress: they buy the credibility that the later, harder stages of "
                         "a change depend on, and they build the support that carries it through the period "
                         "when the visible excitement has gone. The relevant question is whether the early "
                         "results are real and visible, rather than announced."),
            "qualify": ("The evidence does not establish what the early results were or how they were "
                        "verified, so the wins are described rather than confirmed."),
            "short": "A change without an early result spends its credibility before it has earned any.",
            "probe": "state the early result that shows the change is working and who will see it",
        },
        "consolidate": {
            "analysis": ("Consolidating gains means using the early wins to go further, because a change that "
                         "stops at the first success settles for what was easy. Consolidation is where the "
                         "momentum built in the early stages is converted into the next, harder stage of the "
                         "programme. The relevant question is whether the organisation has a second and third "
                         "wave of change planned, or whether the early win has become the finish line."),
            "qualify": ("The evidence does not establish what further change is planned, so the consolidation "
                        "is described rather than assessed."),
            "short": "The first success is where a change programme most often quietly ends.",
            "probe": "state how the early wins are being used to go further",
        },
        "institutionalize": {
            "analysis": ("Institutionalizing means anchoring the new way of working in how the organisation "
                         "operates day to day: the routines, the budgets, the measures and the standards that "
                         "will keep it in place after the programme ends. A change that rests on the attention "
                         "of a programme team is dependent on that team's existence. The relevant question is "
                         "whether the change has been written into the way the organisation works, or whether "
                         "it still depends on the people who introduced it."),
            "qualify": ("The evidence does not establish which routines, measures and standards have changed, "
                        "so the anchoring is described rather than confirmed."),
            "short": "A change that lives in a programme team dies with the programme team.",
            "probe": "state what in the day-to-day working now carries the change",
        },
    },
}

COMPETING_VALUES = {
    "template": "template_competing_values",
    "key": "competing_values",
    "label": "Competing Values Framework",
    "title_prefix": "Competing Values Framework Analysis",
    "subject": "people",
    "unit": {
        "field": "process",
        "label": "The organisation you are describing",
        "help": ("A culture review describes one organisation or unit. Name it in a few words, for example "
                 "the campus catering team or the university estates office."),
        "example": "the campus catering team",
        "refuse": ("A culture review describes one organisation or unit. Name the organisation you are "
                   "describing, for example the campus catering team or the university estates office."),
    },
    "ratings": False,
    "assumption": "probe",
    "sites": None,
    "providers": None,
    "gate": {"title_context": False, "require_geography": False, "title_cue": False},
    "blocks": [
        {"key": "clan", "label": "Clan culture",
         "prompt": "The orientation that puts people, commitment and development first",
         "fill": "research",
         "cues": "clan cohesion morale participation family commitment development team care",
         "queries": ["clan culture cohesion commitment and development in a team"],
         "category": None,
         "probe": "state what the orientation puts first and where it reaches"},
        {"key": "adhocracy", "label": "Adhocracy culture",
         "prompt": "The orientation that puts experimentation, innovation and outside challenge first",
         "fill": "research",
         "cues": "adhocracy innovation experimentation creativity growth external change flexible",
         "queries": ["adhocracy culture experimentation innovation and flexibility"],
         "category": None,
         "probe": "state what experimentation the work allows and who carries the risk"},
        {"key": "market", "label": "Market culture",
         "prompt": "The orientation that puts achievement, competition and the customer first",
         "fill": "research",
         "cues": "market competition achievement results share customer competitive external",
         "queries": ["market culture achievement competition and external comparison"],
         "category": None,
         "probe": "state what the organisation is measured against and who sets the measure"},
        {"key": "hierarchy", "label": "Hierarchy culture",
         "prompt": "The orientation that puts structure, control and predictability first",
         "fill": "research",
         "cues": "hierarchy structure control stability predictability process formal rules",
         "queries": ["hierarchy culture structure control and predictability"],
         "category": None,
         "probe": "state what the structure and rules control and where they stop"},
    ],
    "outline": {
        "framework": "Competing Values Framework",
        "context": "The organisation and the decision",
        "discussion": "What the evidence shows",
        "implications": "Implications for the decision",
        "limitations": "Limitations",
        "conclusion": "Conclusion",
        "lead": ("A competing values review describes an organisation against four orientations: the one "
                 "that puts people and development first, the one that puts experimentation first, the one "
                 "that puts achievement against external comparison first, and the one that puts structure and "
                 "control first. Each orientation is treated in turn, first through the evidence accepted for "
                 "the case and then through what that evidence implies for the decision the review must "
                 "serve."),
    },
    "voice": {
        "thesis_question": "whether the evidence supports the culture the decision depends on",
        "unit_noun": "organisation",
        "block_plural": "orientations",
        "lens": "the four orientations an organisation can be organised around",
        "closing": ("identifies the orientation the evidence supports and the orientation the evidence cannot "
                    "settle"),
        "intro_frame": ("The unit of analysis is the organisation rather than the firm or the market, because "
                        "a culture is a way of organising that can be held in one part of an organisation and "
                        "not in another."),
        "context_frame": ("The relevant organisation is the one named in the brief; the orientations belong to "
                          "that organisation rather than to its sector in general."),
        "interaction": ("Read together, the orientations are a diagnosis of competing demands rather than a "
                        "menu of options: the evidence has to show which demand the work actually makes, "
                        "because an organisation that tries to hold all four holds none of them well."),
        "implication_frame": ("A decision about the organisation has to match the demand the work makes, "
                              "because an organisation built for one orientation will read any other as a "
                              "failure to lead."),
        "reference_heading": "References",
    },
    "notes": {
        "clan": {
            "analysis": ("The clan orientation puts people, commitment and development first: cohesion, "
                         "participation, care for the members and the growth of their capacity. It works where "
                         "trust is the main asset and where the work needs people to act together without being "
                         "told what to do. The relevant question is whether the organisation's work actually "
                         "depends on that cohesion, rather than on the coordination of roles."),
            "qualify": ("The evidence does not establish how far the orientation reaches across the "
                        "organisation, so the culture is described rather than measured."),
            "short": "Cohesion is an asset where the work is shared and a cost where the work is not.",
            "probe": "state what the orientation puts first and where it reaches",
        },
        "adhocracy": {
            "analysis": ("The adhocracy orientation puts experimentation, innovation and outside challenge "
                         "first: flexibility, growth and the willingness to try something that has not been "
                         "tried. It works where the environment changes faster than a plan can be refreshed. "
                         "The relevant question is whether the organisation's work leaves the room to "
                         "experiment, and who bears the cost when an experiment fails."),
            "qualify": ("The evidence does not establish how much experimentation the work allows or how "
                        "failures are handled, so the orientation is described rather than judged."),
            "short": ("An organisation that asks for innovation and punishes the failed experiment will get "
                      "neither."),
            "probe": "state what experimentation the work allows and who carries the risk",
        },
        "market": {
            "analysis": ("The market orientation puts achievement, competition and the customer first: "
                         "results, share and the external standard against which the organisation is judged. It "
                         "works where the organisation is judged against a comparison it does not control. The "
                         "relevant question is whether the organisation is actually measured against such a "
                         "comparison, and whether the measures it is given are the ones that decide its "
                         "standing."),
            "qualify": ("The evidence does not establish which measures the organisation is judged by or how "
                        "they are set, so the orientation is described rather than confirmed."),
            "short": "A comparison the organisation cannot influence can still be the standard it is judged by.",
            "probe": "state what the organisation is measured against and who sets the measure",
        },
        "hierarchy": {
            "analysis": ("The hierarchy orientation puts structure, control and predictability first: "
                         "formal rules, defined authority and stability. It works where the work must be the "
                         "same every time and the cost of variation is high. The relevant question is whether "
                         "the work needs the stability, or whether the organisation is settling for the "
                         "stability it already has."),
            "qualify": ("The evidence does not establish what the rules cover or how often they are changed, so "
                        "the orientation is described rather than assessed."),
            "short": "Stability is a design when the work demands it and an avoidance when it does not.",
            "probe": "state what the structure and rules control and where they stop",
        },
    },
}

ORG_DESIGN = {
    "template": "template_org_design",
    "key": "org_design",
    "label": "Organisational Design Review",
    "title_prefix": "Organisational Design Review",
    "subject": "people",
    "unit": {
        "field": "process",
        "label": "The organisation you are redesigning",
        "help": ("A design review checks one organisation against the parts of a design. Name it in a few "
                 "words, for example the catering unit of the university or the estates office."),
        "example": "the catering unit of the university",
        "refuse": ("A design review checks one organisation against the parts of a design. Name the "
                   "organisation you are redesigning, for example the catering unit of the university or the "
                   "estates office."),
    },
    "ratings": False,
    "assumption": "probe",
    "sites": None,
    "providers": None,
    "gate": {"title_context": False, "require_geography": False, "title_cue": False},
    "blocks": [
        {"key": "strategy", "label": "Strategy",
         "prompt": "What the organisation is trying to achieve",
         "fill": "research",
         "cues": "strategy aim goal objective direction plan growth ambition priority",
         "queries": ["organisational strategy and the objectives a design must serve"],
         "category": None,
         "probe": "state what the organisation is trying to achieve"},
        {"key": "decision_rights", "label": "Decision rights",
         "prompt": "Who decides what, and who is accountable for it",
         "fill": "research",
         "cues": "decision rights authority accountable escalate approval decide responsibility",
         "queries": ["decision rights and accountability in an organisational design"],
         "category": None,
         "probe": "state who decides what and who is accountable"},
        {"key": "structure", "label": "Structure",
         "prompt": "How the roles and the work are grouped",
         "fill": "research",
         "cues": "structure grouping team department layer span reporting hierarchy organogram",
         "queries": ["organisational structure grouping teams and reporting lines"],
         "category": None,
         "probe": "state how the roles and the work are grouped"},
        {"key": "processes", "label": "Processes",
         "prompt": "How the work is actually done and governed",
         "fill": "research",
         "cues": "process workflow procedure governance control routine handoff interface",
         "queries": ["process design governance and handover between teams"],
         "category": None,
         "probe": "state how the work is done and how it is governed"},
        {"key": "people_capability", "label": "People and capability",
         "prompt": "The skills, roles and capacity the design needs",
         "fill": "research",
         "cues": "people capability skill role capacity number experience resourcing",
         "queries": ["organisational capability and resourcing requirements of a design"],
         "category": None,
         "probe": "state the skills, roles and capacity the design needs"},
        {"key": "incentives", "label": "Incentives",
         "prompt": "What the design rewards people for doing",
         "fill": "research",
         "cues": "incentive reward pay bonus measure target performance appraisal remuneration",
         "queries": ["incentives and reward design in an organisational structure"],
         "category": None,
         "probe": "state what the design rewards people for doing"},
    ],
    "outline": {
        "framework": "Organisational Design Review",
        "context": "The organisation and the decision",
        "discussion": "What the evidence shows",
        "implications": "Implications for the decision",
        "limitations": "Limitations",
        "conclusion": "Conclusion",
        "lead": ("A design review checks an organisation against six parts: the strategy the design must "
                 "serve, the decision rights that carry it, the structure that groups the work, the processes "
                 "that govern it, the capability it assumes and the incentives that make it real. Each part "
                 "is treated in turn, first through the evidence accepted for the case and then through what "
                 "that evidence implies for the decision the review must serve."),
    },
    "voice": {
        "thesis_question": "whether the design matches the strategy the decision depends on",
        "unit_noun": "organisation",
        "block_plural": "parts",
        "lens": "the parts of a design that have to fit one another",
        "closing": ("identifies the part of the design the decision turns on and the part the evidence cannot "
                    "settle"),
        "intro_frame": ("The unit of analysis is the organisation being redesigned rather than the firm, "
                        "because a design is a set of parts that have to be checked against one another rather "
                        "than a single choice."),
        "context_frame": ("The relevant organisation is the one named in the brief; the parts belong to that "
                          "organisation rather than to the sector's designs in general."),
        "interaction": ("Read together, the parts form a single argument: each part constrains the others, and "
                        "a design in which one part is unsupported by the rest will be sustained by habit "
                        "rather than by reason."),
        "implication_frame": ("A decision about the design has to settle the parts together, because changing "
                              "one part of a design without changing the others leaves the organisation "
                              "carrying two designs at once."),
        "reference_heading": "References",
    },
    "notes": {
        "strategy": {
            "analysis": ("Strategy is what the organisation is trying to achieve, and it is the constraint "
                         "every other part of a design has to answer to. A structure built for one strategy and "
                         "a set of incentives built for another will pull the organisation in different "
                         "directions, and the result is an organisation whose parts are each reasonable and "
                         "whose whole does not hold together. The relevant question is whether the design "
                         "matches the strategy the organisation has actually chosen."),
            "qualify": ("The evidence does not establish what the organisation has committed to, so the "
                        "strategy is described rather than confirmed."),
            "short": "A design that does not match the strategy will be outrun by it.",
            "probe": "state what the organisation is trying to achieve",
        },
        "decision_rights": {
            "analysis": ("Decision rights are who decides what and who is accountable for it. They are the "
                         "part of a design most often left implicit, and the result is that the decisions that "
                         "matter most are the ones nobody has been given the authority to take. The relevant "
                         "question is whether the rights needed to deliver the strategy are held where the "
                         "strategy is actually made."),
            "qualify": ("The evidence does not establish where authority formally sits, so the rights are "
                        "described rather than audited."),
            "short": "Decisions nobody has been given the authority to take are made late and badly.",
            "probe": "state who decides what and who is accountable",
        },
        "structure": {
            "analysis": ("Structure is how the roles and the work are grouped: into teams, layers and "
                         "functions. Grouping determines whose problem a problem is, and a structure that "
                         "groups work by accident rather than by purpose makes the coordination cost visible "
                         "as somebody's job. The relevant question is whether the grouping is the one the "
                         "strategy requires, or the one the organisation has inherited."),
            "qualify": ("The evidence does not establish what the grouping was intended to achieve, so the "
                        "structure is described rather than judged."),
            "short": "A grouping inherited from another strategy is a coordination cost nobody has chosen.",
            "probe": "state how the roles and the work are grouped",
        },
        "processes": {
            "analysis": ("Processes are how the work is actually done and governed: the sequence, the "
                         "handoffs and the rules that travel with the work across the structure. A design that "
                         "changes the structure without changing the processes leaves the old work in place "
                         "under the new boxes. The relevant question is whether the way the work is done has "
                         "been examined, and not only where the boxes now are."),
            "qualify": ("The evidence does not establish how the work is performed in practice, so the "
                        "processes are described rather than traced."),
            "short": "Moving the boxes while the work goes on as before changes the organisation on paper only.",
            "probe": "state how the work is done and how it is governed",
        },
        "people_capability": {
            "analysis": ("People and capability are the skills, the roles and the capacity the design needs, "
                         "and the gap between what the design requires and what the organisation holds. A "
                         "design that requires different work from the same people has assumed a resourcing "
                         "that has not been made. The relevant question is whether the capability the design "
                         "assumes exists, and what happens to the work if it does not."),
            "qualify": ("The evidence does not establish what the design requires of each role, so the "
                        "capability gap is described rather than sized."),
            "short": ("A design that asks for different work from the same people has assumed a resourcing it "
                      "has not made."),
            "probe": "state the skills, roles and capacity the design needs",
        },
        "incentives": {
            "analysis": ("Incentives are what the design rewards people for doing. They are the mechanism by "
                         "which a design is made real in practice, and where they point somewhere other than "
                         "the strategy they will be followed in preference to it. The relevant question is "
                         "whether what people are rewarded for in the design is what the strategy requires "
                         "them to do."),
            "qualify": ("The evidence does not establish what the design rewards in practice, so the incentives "
                        "are described rather than evaluated."),
            "short": "People will follow the incentive, and the incentive will not follow the diagram.",
            "probe": "state what the design rewards people for doing",
        },
    },
}

#: The eight profiles, in the order the People shelf lists them.
NINE_BOX, KOTTER, COMPETING_VALUES, ORG_DESIGN, ADKAR, LEWIN, THEORY_OF_CHANGE, PDSA, DMAIC, GENERIC_STRATEGIES, BCG, GE_MCKINSEY, MCKINSEY_7S, RACI, PORTERS_DIAMOND, BURKE_LITWIN, GALBRAITH_STAR, MINTZBERG, LOGIC_MODEL,


# ---- WO-3 profiles (inlined 2026-11-03) -------------------------------------
# These eight profiles were loaded at import time from a temporary file outside the
# repository by a bare `exec(open(...))`.  That made this module unimportable on any
# machine without that file, and nothing in the repository contained them.  They are
# now part of the module, exactly as the exec produced them (the last definition of
# each name in that file).

#: BMC (WO-3, inlined: it was loaded from an external temp file)
BMC = {'template': 'template_business_model_canvas',
 'key': 'bmc',
 'label': 'Business Model Canvas',
 'title_prefix': 'Business Model Canvas',
 'subject': 'strategy',
 'unit': {'field': 'unit',
          'label': 'Unit of analysis',
          'help': 'Name the single unit this worksheet covers.',
          'example': 'One project, one change programme, or one business model.',
          'refuse': 'A worksheet cannot be completed for a unit that has not been named.'},
 'ratings': False,
 'assumption': 'probe',
 'sites': 'organization',
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'gate': {'title_cue': True, 'title_context': True, 'require_geography': False},
 'blocks': [{'key': 'key_partners',
             'label': 'Key partners',
             'prompt': 'Who you depend on, and what each partner supplies',
             'fill': 'research',
             'cues': 'partner supplier alliance outsourcing vendor collaboration',
             'queries': ['strategic partnerships and supplier alliances in this industry', 'partner network and outsourcing in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'key_activities',
             'label': 'Key activities',
             'prompt': 'The few things the business must do well to deliver the value',
             'fill': 'research',
             'cues': 'activities operations production capability process',
             'queries': ['core business activities and operations in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'key_resources',
             'label': 'Key resources',
             'prompt': 'What it needs to do those activities: people, equipment, cash, licences',
             'fill': 'research',
             'cues': 'resources assets capability equipment funding licence',
             'queries': ['key resources and assets in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'value_propositions',
             'label': 'Value propositions',
             'prompt': "The value you promise each segment, in the customer's words",
             'fill': 'research',
             'cues': 'value proposition benefit offer differentiation customer',
             'queries': ['value proposition and customer benefit in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'customer_relationships',
             'label': 'Customer relationships',
             'prompt': 'How you win a customer, keep them and grow the relationship',
             'fill': 'research',
             'cues': 'relationship retention loyalty service community',
             'queries': ['customer relationship management and retention in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'channels',
             'label': 'Channels',
             'prompt': 'How the value reaches the customer, from first contact to delivery',
             'fill': 'research',
             'cues': 'channel distribution store online partner reach',
             'queries': ['distribution channels and channel reach in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'customer_segments',
             'label': 'Customer segments',
             'prompt': 'Who you serve, described by need and behaviour, not demographics alone',
             'fill': 'research',
             'cues': 'segment customer market niche targeting need',
             'queries': ['customer segments and target market in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'cost_structure',
             'label': 'Cost structure',
             'prompt': 'The main fixed and variable costs the model creates',
             'fill': 'research',
             'cues': 'cost fixed variable overhead structure margin',
             'queries': ['cost structure and cost drivers in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'revenue_streams',
             'label': 'Revenue streams',
             'prompt': 'How the business earns, and what the customer pays for',
             'fill': 'research',
             'cues': 'revenue pricing subscription margin income',
             'queries': ['revenue model and pricing in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'}],
 'outline': {'framework': 'Framework overview',
             'context': 'Context and unit',
             'discussion': 'Block-by-block evidence',
             'implications': 'Implications',
             'limitations': 'Limitations',
             'conclusion': 'Conclusion',
             'lead': 'A business model canvas lays out one business model on a single page: the key partners and key activities it depends on, the key resources it needs, the value propositions it offers, the customer relationships and channels it uses, the customer segments it serves, and its cost structure and revenue streams. Each block is treated in turn, first through the evidence accepted for the case and then through what that evidence implies for the decision.'},
 'voice': {'thesis_question': 'What does the evidence say about this framework for the named unit?',
           'unit_noun': 'unit',
           'block_plural': 'blocks',
           'lens': 'evidence audit',
           'closing': "The evidence is yours; the structure is the tool's.",
           'intro_frame': "This paper organises the evidence you supplied into the framework's blocks.",
           'context_frame': 'Context is limited to the unit named and the evidence supplied.',
           'interaction': 'Each block carries sourced items or a named gap.',
           'implication_frame': 'Implications are stated only where the evidence supports them.',
           'reference_heading': 'Sources'},
 'notes': {'key_partners': {'analysis': 'Key partners is a structural block awaiting evidence.',
                            'qualify': 'The evidence does not establish more than what is supplied.',
                            'short': 'Key partners awaits evidence.',
                            'probe': 'state the evidence for this block'},
           'key_activities': {'analysis': 'Key activities is a structural block awaiting evidence.',
                              'qualify': 'The evidence does not establish more than what is supplied.',
                              'short': 'Key activities awaits evidence.',
                              'probe': 'state the evidence for this block'},
           'key_resources': {'analysis': 'Key resources is a structural block awaiting evidence.',
                             'qualify': 'The evidence does not establish more than what is supplied.',
                             'short': 'Key resources awaits evidence.',
                             'probe': 'state the evidence for this block'},
           'value_propositions': {'analysis': 'Value propositions is a structural block awaiting evidence.',
                                  'qualify': 'The evidence does not establish more than what is supplied.',
                                  'short': 'Value propositions awaits evidence.',
                                  'probe': 'state the evidence for this block'},
           'customer_relationships': {'analysis': 'Customer relationships is a structural block awaiting '
                                                  'evidence.',
                                      'qualify': 'The evidence does not establish more than what is supplied.',
                                      'short': 'Customer relationships awaits evidence.',
                                      'probe': 'state the evidence for this block'},
           'channels': {'analysis': 'Channels is a structural block awaiting evidence.',
                        'qualify': 'The evidence does not establish more than what is supplied.',
                        'short': 'Channels awaits evidence.',
                        'probe': 'state the evidence for this block'},
           'customer_segments': {'analysis': 'Customer segments is a structural block awaiting evidence.',
                                 'qualify': 'The evidence does not establish more than what is supplied.',
                                 'short': 'Customer segments awaits evidence.',
                                 'probe': 'state the evidence for this block'},
           'cost_structure': {'analysis': 'Cost structure is a structural block awaiting evidence.',
                              'qualify': 'The evidence does not establish more than what is supplied.',
                              'short': 'Cost structure awaits evidence.',
                              'probe': 'state the evidence for this block'},
           'revenue_streams': {'analysis': 'Revenue streams is a structural block awaiting evidence.',
                               'qualify': 'The evidence does not establish more than what is supplied.',
                               'short': 'Revenue streams awaits evidence.',
                               'probe': 'state the evidence for this block'}}}

#: LEAN_CANVAS (WO-3, inlined: it was loaded from an external temp file)
LEAN_CANVAS = {'template': 'template_lean_canvas',
 'key': 'lean_canvas',
 'label': 'Lean Canvas',
 'title_prefix': 'Lean Canvas',
 'subject': 'strategy',
 'unit': {'field': 'unit',
          'label': 'Unit of analysis',
          'help': 'Name the single unit this worksheet covers.',
          'example': 'One project, one change programme, or one business model.',
          'refuse': 'A worksheet cannot be completed for a unit that has not been named.'},
 'ratings': False,
 'assumption': 'probe',
 'sites': 'organization',
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'gate': {'title_cue': True, 'title_context': True, 'require_geography': False},
 'blocks': [{'key': 'problem',
             'label': 'Problem',
             'prompt': 'The top problems you are solving',
             'fill': 'research',
             'cues': 'problem pain need complaint failure',
             'queries': ['customer problems and unmet needs in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'customer_segments',
             'label': 'Customer segments',
             'prompt': 'Who has those problems',
             'fill': 'research',
             'cues': 'segment customer market niche targeting need',
             'queries': ['customer segments and target market in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'unique_value_proposition',
             'label': 'Unique value proposition',
             'prompt': 'Why you are different and worth attention',
             'fill': 'research',
             'cues': 'unique value proposition difference message benefit',
             'queries': ['unique value proposition and differentiation in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'solution',
             'label': 'Solution',
             'prompt': 'The smallest thing that solves the problem',
             'fill': 'research',
             'cues': 'solution product feature prototype offering',
             'queries': ['product solution and features in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'channels',
             'label': 'Channels',
             'prompt': 'The route to customers',
             'fill': 'research',
             'cues': 'channel distribution store online partner reach',
             'queries': ['distribution channels and channel reach in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'revenue_streams',
             'label': 'Revenue streams',
             'prompt': 'How you earn',
             'fill': 'research',
             'cues': 'revenue pricing subscription margin income',
             'queries': ['revenue model and pricing in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'cost_structure',
             'label': 'Cost structure',
             'prompt': 'The main costs',
             'fill': 'research',
             'cues': 'cost fixed variable overhead structure margin',
             'queries': ['cost structure and cost drivers in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'key_metrics',
             'label': 'Key metrics',
             'prompt': 'The few numbers that show it is working',
             'fill': 'research',
             'cues': 'metric measure indicator performance track',
             'queries': ['key performance metrics and indicators in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'unfair_advantage',
             'label': 'Unfair advantage',
             'prompt': 'What cannot easily be copied',
             'fill': 'research',
             'cues': 'advantage barrier copy patent exclusive access',
             'queries': ['competitive advantage that is hard to copy in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'}],
 'outline': {'framework': 'Framework overview',
             'context': 'Context and unit',
             'discussion': 'Block-by-block evidence',
             'implications': 'Implications',
             'limitations': 'Limitations',
             'conclusion': 'Conclusion',
             'lead': 'A lean canvas tests one venture as a set of assumptions: the problem it solves, the customer segments that have it, its unique value proposition, the solution it proposes, the channels it reaches customers through, its revenue streams and cost structure, the key metrics that show it is working, and the unfair advantage a competitor cannot copy. Each block is treated in turn, first through the evidence accepted for the case and then through what that evidence implies for the decision.'},
 'voice': {'thesis_question': 'What does the evidence say about this framework for the named unit?',
           'unit_noun': 'unit',
           'block_plural': 'blocks',
           'lens': 'evidence audit',
           'closing': "The evidence is yours; the structure is the tool's.",
           'intro_frame': "This paper organises the evidence you supplied into the framework's blocks.",
           'context_frame': 'Context is limited to the unit named and the evidence supplied.',
           'interaction': 'Each block carries sourced items or a named gap.',
           'implication_frame': 'Implications are stated only where the evidence supports them.',
           'reference_heading': 'Sources'},
 'notes': {'problem': {'analysis': 'Problem is a structural block awaiting evidence.',
                       'qualify': 'The evidence does not establish more than what is supplied.',
                       'short': 'Problem awaits evidence.',
                       'probe': 'state the evidence for this block'},
           'customer_segments': {'analysis': 'Customer segments is a structural block awaiting evidence.',
                                 'qualify': 'The evidence does not establish more than what is supplied.',
                                 'short': 'Customer segments awaits evidence.',
                                 'probe': 'state the evidence for this block'},
           'unique_value_proposition': {'analysis': 'Unique value proposition is a structural block awaiting '
                                                    'evidence.',
                                        'qualify': 'The evidence does not establish more than what is '
                                                   'supplied.',
                                        'short': 'Unique value proposition awaits evidence.',
                                        'probe': 'state the evidence for this block'},
           'solution': {'analysis': 'Solution is a structural block awaiting evidence.',
                        'qualify': 'The evidence does not establish more than what is supplied.',
                        'short': 'Solution awaits evidence.',
                        'probe': 'state the evidence for this block'},
           'channels': {'analysis': 'Channels is a structural block awaiting evidence.',
                        'qualify': 'The evidence does not establish more than what is supplied.',
                        'short': 'Channels awaits evidence.',
                        'probe': 'state the evidence for this block'},
           'revenue_streams': {'analysis': 'Revenue streams is a structural block awaiting evidence.',
                               'qualify': 'The evidence does not establish more than what is supplied.',
                               'short': 'Revenue streams awaits evidence.',
                               'probe': 'state the evidence for this block'},
           'cost_structure': {'analysis': 'Cost structure is a structural block awaiting evidence.',
                              'qualify': 'The evidence does not establish more than what is supplied.',
                              'short': 'Cost structure awaits evidence.',
                              'probe': 'state the evidence for this block'},
           'key_metrics': {'analysis': 'Key metrics is a structural block awaiting evidence.',
                           'qualify': 'The evidence does not establish more than what is supplied.',
                           'short': 'Key metrics awaits evidence.',
                           'probe': 'state the evidence for this block'},
           'unfair_advantage': {'analysis': 'Unfair advantage is a structural block awaiting evidence.',
                                'qualify': 'The evidence does not establish more than what is supplied.',
                                'short': 'Unfair advantage awaits evidence.',
                                'probe': 'state the evidence for this block'}}}

#: VALUE_PROPOSITION_CANVAS (WO-3, inlined: it was loaded from an external temp file)
VALUE_PROPOSITION_CANVAS = {'template': 'template_value_proposition_canvas',
 'key': 'value_proposition_canvas',
 'label': 'Value Proposition Canvas',
 'title_prefix': 'Value Proposition Canvas',
 'subject': 'strategy',
 'unit': {'field': 'unit',
          'label': 'Unit of analysis',
          'help': 'Name the single unit this worksheet covers.',
          'example': 'One project, one change programme, or one business model.',
          'refuse': 'A worksheet cannot be completed for a unit that has not been named.'},
 'ratings': False,
 'assumption': 'probe',
 'sites': 'organization',
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'gate': {'title_cue': True, 'title_context': True, 'require_geography': False},
 'blocks': [{'key': 'customer_jobs',
             'label': 'Customer jobs',
             'prompt': 'What the customer is trying to get done',
             'fill': 'research',
             'cues': 'jobs tasks need outcome customer',
             'queries': ['customer jobs and tasks in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'customer_pains',
             'label': 'Pains',
             'prompt': 'What is costly, risky or annoying',
             'fill': 'research',
             'cues': 'pain risk cost annoyance obstacle',
             'queries': ['customer pains and risks in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'customer_gains',
             'label': 'Gains',
             'prompt': 'What the customer wants to gain',
             'fill': 'research',
             'cues': 'gain benefit outcome expectation satisfaction',
             'queries': ['customer gains and expected benefits in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'products_services',
             'label': 'Products and services',
             'prompt': 'What you offer',
             'fill': 'research',
             'cues': 'product service offering feature',
             'queries': ['products and services offered in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'pain_relievers',
             'label': 'Pain relievers',
             'prompt': 'How you remove a stated pain',
             'fill': 'research',
             'cues': 'reliever obstacle solution risk reduce',
             'queries': ['pain relievers and risk reduction in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'gain_creators',
             'label': 'Gain creators',
             'prompt': 'How you create a stated gain',
             'fill': 'research',
             'cues': 'creator benefit gain outcome increase',
             'queries': ['gain creators and benefit delivery in this industry'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'}],
 'outline': {'framework': 'Framework overview',
             'context': 'Context and unit',
             'discussion': 'Block-by-block evidence',
             'implications': 'Implications',
             'limitations': 'Limitations',
             'conclusion': 'Conclusion',
             'lead': 'A value proposition canvas fits one offer to one customer: the customer jobs the offer is hired for, the pains and gains those jobs bring, and the products and services, pain relievers and gain creators that answer them. Each block is treated in turn, first through the evidence accepted for the case and then through what that evidence implies for the decision.'},
 'voice': {'thesis_question': 'What does the evidence say about this framework for the named unit?',
           'unit_noun': 'unit',
           'block_plural': 'blocks',
           'lens': 'evidence audit',
           'closing': "The evidence is yours; the structure is the tool's.",
           'intro_frame': "This paper organises the evidence you supplied into the framework's blocks.",
           'context_frame': 'Context is limited to the unit named and the evidence supplied.',
           'interaction': 'Each block carries sourced items or a named gap.',
           'implication_frame': 'Implications are stated only where the evidence supports them.',
           'reference_heading': 'Sources'},
 'notes': {'customer_jobs': {'analysis': 'Customer jobs is a structural block awaiting evidence.',
                             'qualify': 'The evidence does not establish more than what is supplied.',
                             'short': 'Customer jobs awaits evidence.',
                             'probe': 'state the evidence for this block'},
           'customer_pains': {'analysis': 'Pains is a structural block awaiting evidence.',
                              'qualify': 'The evidence does not establish more than what is supplied.',
                              'short': 'Pains awaits evidence.',
                              'probe': 'state the evidence for this block'},
           'customer_gains': {'analysis': 'Gains is a structural block awaiting evidence.',
                              'qualify': 'The evidence does not establish more than what is supplied.',
                              'short': 'Gains awaits evidence.',
                              'probe': 'state the evidence for this block'},
           'products_services': {'analysis': 'Products and services is a structural block awaiting evidence.',
                                 'qualify': 'The evidence does not establish more than what is supplied.',
                                 'short': 'Products and services awaits evidence.',
                                 'probe': 'state the evidence for this block'},
           'pain_relievers': {'analysis': 'Pain relievers is a structural block awaiting evidence.',
                              'qualify': 'The evidence does not establish more than what is supplied.',
                              'short': 'Pain relievers awaits evidence.',
                              'probe': 'state the evidence for this block'},
           'gain_creators': {'analysis': 'Gain creators is a structural block awaiting evidence.',
                             'qualify': 'The evidence does not establish more than what is supplied.',
                             'short': 'Gain creators awaits evidence.',
                             'probe': 'state the evidence for this block'}}}

#: PROJECT_CHARTER (WO-3, inlined: it was loaded from an external temp file)
PROJECT_CHARTER = {'template': 'template_project_charter',
 'key': 'project_charter',
 'label': 'Project Charter',
 'title_prefix': 'Project Charter',
 'subject': 'project-management',
 'unit': {'field': 'unit',
          'label': 'Unit of analysis',
          'help': 'Name the single unit this worksheet covers.',
          'example': 'One project, one change programme, or one business model.',
          'refuse': 'A worksheet cannot be completed for a unit that has not been named.'},
 'ratings': False,
 'assumption': 'probe',
 'sites': 'organization',
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'gate': {'title_cue': True, 'title_context': True, 'require_geography': False},
 'blocks': [{'key': 'objective',
             'label': 'Objective',
             'prompt': 'The outcome the project exists to deliver, in one testable statement',
             'fill': 'research',
             'cues': ['objective', 'goal', 'purpose', 'outcome'],
             'queries': ['project objective and business case'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'scope_in',
             'label': 'In scope',
             'prompt': 'What the project will deliver and cover',
             'fill': 'research',
             'cues': ['scope', 'included', 'boundary', 'covered'],
             'queries': ['project scope statement inclusions'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'scope_out',
             'label': 'Out of scope',
             'prompt': 'What the project deliberately will not do',
             'fill': 'research',
             'cues': ['excluded', 'exclusion', 'boundary', 'not covered'],
             'queries': ['project scope exclusions'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'deliverables',
             'label': 'Deliverables',
             'prompt': 'The verifiable outputs you will hand over',
             'fill': 'research',
             'cues': ['deliverable', 'output', 'handover'],
             'queries': ['project deliverables and outputs'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'governance',
             'label': 'Sponsor and governance',
             'prompt': 'Who authorises the project, who decides, and how change is controlled',
             'fill': 'research',
             'cues': ['sponsor', 'governance', 'steering', 'authority'],
             'queries': ['project sponsor and governance authority'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'budget',
             'label': 'Budget and funding',
             'prompt': 'The declared budget, its source and the spending authority',
             'fill': 'research',
             'cues': ['budget', 'funding', 'capital', 'cost'],
             'queries': ['project budget and funding approval'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'milestones',
             'label': 'Milestones',
             'prompt': 'The dated checkpoints and decisions, including the end date',
             'fill': 'research',
             'cues': ['milestone', 'deadline', 'completion', 'gate'],
             'queries': ['project milestones and completion date'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'success_measures',
             'label': 'Success measures',
             'prompt': 'How completion and benefit will be judged, with baselines and targets',
             'fill': 'research',
             'cues': ['success', 'benefit', 'measure', 'criterion'],
             'queries': ['project success criteria and benefits'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'assumptions',
             'label': 'Assumptions',
             'prompt': 'What must hold for the plan to work, marked as assumptions',
             'fill': 'research',
             'cues': ['assumption', 'prerequisite', 'premise'],
             'queries': ['project assumptions and prerequisites'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'constraints',
             'label': 'Constraints and dependencies',
             'prompt': "Fixed dates, resources, contracts or dependencies outside the project's control",
             'fill': 'research',
             'cues': ['constraint', 'dependency', 'limitation'],
             'queries': ['project constraints and dependencies'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'}],
 'outline': {'framework': 'Framework overview',
             'context': 'Context and unit',
             'discussion': 'Block-by-block evidence',
             'implications': 'Implications',
             'limitations': 'Limitations',
             'conclusion': 'Conclusion',
             'lead': 'A project charter authorises one project: the objective it exists to deliver, the scope it covers and the scope it declines, the deliverables it hands over, the sponsor and governance that authorise it, the budget and funding behind it, the milestones it is committed to, the success measures it will be judged by, and the assumptions and constraints it carries. Each block is treated in turn, first through the evidence accepted for the case and then through what that evidence implies for the decision to proceed.'},
 'voice': {'thesis_question': 'What does the evidence say about this framework for the named unit?',
           'unit_noun': 'unit',
           'block_plural': 'blocks',
           'lens': 'evidence audit',
           'closing': "The evidence is yours; the structure is the tool's.",
           'intro_frame': "This paper organises the evidence you supplied into the framework's blocks.",
           'context_frame': 'Context is limited to the unit named and the evidence supplied.',
           'interaction': 'Each block carries sourced items or a named gap.',
           'implication_frame': 'Implications are stated only where the evidence supports them.',
           'reference_heading': 'Sources'},
 'notes': {'objective': {'analysis': 'Objective is a structural block awaiting evidence.',
                         'qualify': 'The evidence does not establish more than what is supplied.',
                         'short': 'Objective awaits evidence.',
                         'probe': 'state the evidence for this block'},
           'scope_in': {'analysis': 'In scope is a structural block awaiting evidence.',
                        'qualify': 'The evidence does not establish more than what is supplied.',
                        'short': 'In scope awaits evidence.',
                        'probe': 'state the evidence for this block'},
           'scope_out': {'analysis': 'Out of scope is a structural block awaiting evidence.',
                         'qualify': 'The evidence does not establish more than what is supplied.',
                         'short': 'Out of scope awaits evidence.',
                         'probe': 'state the evidence for this block'},
           'deliverables': {'analysis': 'Deliverables is a structural block awaiting evidence.',
                            'qualify': 'The evidence does not establish more than what is supplied.',
                            'short': 'Deliverables awaits evidence.',
                            'probe': 'state the evidence for this block'},
           'governance': {'analysis': 'Sponsor and governance is a structural block awaiting evidence.',
                          'qualify': 'The evidence does not establish more than what is supplied.',
                          'short': 'Sponsor and governance awaits evidence.',
                          'probe': 'state the evidence for this block'},
           'budget': {'analysis': 'Budget and funding is a structural block awaiting evidence.',
                      'qualify': 'The evidence does not establish more than what is supplied.',
                      'short': 'Budget and funding awaits evidence.',
                      'probe': 'state the evidence for this block'},
           'milestones': {'analysis': 'Milestones is a structural block awaiting evidence.',
                          'qualify': 'The evidence does not establish more than what is supplied.',
                          'short': 'Milestones awaits evidence.',
                          'probe': 'state the evidence for this block'},
           'success_measures': {'analysis': 'Success measures is a structural block awaiting evidence.',
                                'qualify': 'The evidence does not establish more than what is supplied.',
                                'short': 'Success measures awaits evidence.',
                                'probe': 'state the evidence for this block'},
           'assumptions': {'analysis': 'Assumptions is a structural block awaiting evidence.',
                           'qualify': 'The evidence does not establish more than what is supplied.',
                           'short': 'Assumptions awaits evidence.',
                           'probe': 'state the evidence for this block'},
           'constraints': {'analysis': 'Constraints and dependencies is a structural block awaiting evidence.',
                           'qualify': 'The evidence does not establish more than what is supplied.',
                           'short': 'Constraints and dependencies awaits evidence.',
                           'probe': 'state the evidence for this block'}}}

#: WBS (WO-3, inlined: it was loaded from an external temp file)
WBS = {'template': 'template_wbs',
 'key': 'wbs',
 'label': 'Work Breakdown Structure',
 'title_prefix': 'Work Breakdown Structure',
 'subject': 'project-management',
 'unit': {'field': 'unit',
          'label': 'Unit of analysis',
          'help': 'Name the single unit this worksheet covers.',
          'example': 'One project, one change programme, or one business model.',
          'refuse': 'A worksheet cannot be completed for a unit that has not been named.'},
 'ratings': False,
 'assumption': 'probe',
 'sites': 'organization',
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'gate': {'title_cue': True, 'title_context': True, 'require_geography': False},
 'blocks': [{'key': 'deliverables',
             'label': 'Level 1 deliverables',
             'prompt': 'The major deliverables the project must produce',
             'fill': 'research',
             'cues': ['deliverable', 'breakdown', 'decomposition'],
             'queries': ['work breakdown structure deliverables'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'work_packages',
             'label': 'Work packages',
             'prompt': 'The smallest pieces of work, each with an owner and a completion test',
             'fill': 'research',
             'cues': ['work package', 'activity', 'task'],
             'queries': ['work packages in a work breakdown structure'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'acceptance',
             'label': 'Acceptance criteria',
             'prompt': 'The test that shows a deliverable or work package is complete',
             'fill': 'research',
             'cues': ['acceptance', 'criterion', 'quality'],
             'queries': ['acceptance criteria and quality standards'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'exclusions',
             'label': 'Exclusions',
             'prompt': 'Work the WBS deliberately leaves out',
             'fill': 'research',
             'cues': ['exclusion', 'out of scope', 'boundary'],
             'queries': ['work breakdown structure exclusions'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'}],
 'outline': {'framework': 'Framework overview',
             'context': 'Context and unit',
             'discussion': 'Block-by-block evidence',
             'implications': 'Implications',
             'limitations': 'Limitations',
             'conclusion': 'Conclusion',
             'lead': 'A work breakdown structure decomposes one project into the level 1 deliverables it must hand over, the work packages beneath them, the acceptance criteria that show each one is complete, and the exclusions it deliberately leaves out. Each block is treated in turn, first through the evidence accepted for the case and then through what that evidence implies for the decision the breakdown has to support.'},
 'voice': {'thesis_question': 'What does the evidence say about this framework for the named unit?',
           'unit_noun': 'unit',
           'block_plural': 'blocks',
           'lens': 'evidence audit',
           'closing': "The evidence is yours; the structure is the tool's.",
           'intro_frame': "This paper organises the evidence you supplied into the framework's blocks.",
           'context_frame': 'Context is limited to the unit named and the evidence supplied.',
           'interaction': 'Each block carries sourced items or a named gap.',
           'implication_frame': 'Implications are stated only where the evidence supports them.',
           'reference_heading': 'Sources'},
 'notes': {'deliverables': {'analysis': 'Level 1 deliverables is a structural block awaiting evidence.',
                            'qualify': 'The evidence does not establish more than what is supplied.',
                            'short': 'Level 1 deliverables awaits evidence.',
                            'probe': 'state the evidence for this block'},
           'work_packages': {'analysis': 'Work packages is a structural block awaiting evidence.',
                             'qualify': 'The evidence does not establish more than what is supplied.',
                             'short': 'Work packages awaits evidence.',
                             'probe': 'state the evidence for this block'},
           'acceptance': {'analysis': 'Acceptance criteria is a structural block awaiting evidence.',
                          'qualify': 'The evidence does not establish more than what is supplied.',
                          'short': 'Acceptance criteria awaits evidence.',
                          'probe': 'state the evidence for this block'},
           'exclusions': {'analysis': 'Exclusions is a structural block awaiting evidence.',
                          'qualify': 'The evidence does not establish more than what is supplied.',
                          'short': 'Exclusions awaits evidence.',
                          'probe': 'state the evidence for this block'}}}

#: RISK_REGISTER (WO-3, inlined: it was loaded from an external temp file)
RISK_REGISTER = {'template': 'template_risk_register',
 'key': 'risk_register',
 'label': 'Risk Register',
 'title_prefix': 'Risk Register',
 'subject': 'project-management',
 'unit': {'field': 'unit',
          'label': 'Unit of analysis',
          'help': 'Name the single unit this worksheet covers.',
          'example': 'One project, one change programme, or one business model.',
          'refuse': 'A worksheet cannot be completed for a unit that has not been named.'},
 'ratings': False,
 'assumption': 'probe',
 'sites': 'organization',
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'gate': {'title_cue': True, 'title_context': True, 'require_geography': False},
 'blocks': [{'key': 'risk',
             'label': 'Risk',
             'prompt': 'Describe the risk',
             'fill': 'research',
             'cues': ['risk', 'threat', 'uncertainty', 'impact'],
             'queries': ['project risk register threats and impacts'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'response',
             'label': 'Response',
             'prompt': 'Describe the response',
             'fill': 'research',
             'cues': ['response', 'mitigation', 'contingency', 'owner'],
             'queries': ['risk response planning mitigation and contingency'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'}],
 'outline': {'framework': 'Framework overview',
             'context': 'Context and unit',
             'discussion': 'Block-by-block evidence',
             'implications': 'Implications',
             'limitations': 'Limitations',
             'conclusion': 'Conclusion',
             'lead': "A risk register records one project's risks and the response the project will take to each: what the risk is, what it would affect, and the response that carries it. Each block is treated in turn, first through the evidence accepted for the case and then through what that evidence implies for the decision to proceed."},
 'voice': {'thesis_question': 'What does the evidence say about this framework for the named unit?',
           'unit_noun': 'unit',
           'block_plural': 'blocks',
           'lens': 'evidence audit',
           'closing': "The evidence is yours; the structure is the tool's.",
           'intro_frame': "This paper organises the evidence you supplied into the framework's blocks.",
           'context_frame': 'Context is limited to the unit named and the evidence supplied.',
           'interaction': 'Each block carries sourced items or a named gap.',
           'implication_frame': 'Implications are stated only where the evidence supports them.',
           'reference_heading': 'Sources'},
 'notes': {'risk': {'analysis': 'Risk is a structural block awaiting evidence.',
                    'qualify': 'The evidence does not establish more than what is supplied.',
                    'short': 'Risk awaits evidence.',
                    'probe': 'state the evidence for this block'},
           'response': {'analysis': 'Response is a structural block awaiting evidence.',
                        'qualify': 'The evidence does not establish more than what is supplied.',
                        'short': 'Response awaits evidence.',
                        'probe': 'state the evidence for this block'}}}

#: STAKEHOLDER_PLAN (WO-3, inlined: it was loaded from an external temp file)
STAKEHOLDER_PLAN = {'template': 'template_stakeholder_plan',
 'key': 'stakeholder_plan',
 'label': 'Stakeholder Plan',
 'title_prefix': 'Stakeholder Plan',
 'subject': 'project-management',
 'unit': {'field': 'unit',
          'label': 'Unit of analysis',
          'help': 'Name the single unit this worksheet covers.',
          'example': 'One project, one change programme, or one business model.',
          'refuse': 'A worksheet cannot be completed for a unit that has not been named.'},
 'ratings': False,
 'assumption': 'probe',
 'sites': 'organization',
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'gate': {'title_cue': True, 'title_context': True, 'require_geography': False},
 'blocks': [{'key': 'stakeholders',
             'label': 'Stakeholders',
             'prompt': 'Who is affected by the project or can affect it',
             'fill': 'research',
             'cues': ['stakeholder', 'party', 'participant'],
             'queries': ['project stakeholder identification'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'interests',
             'label': 'Interests and concerns',
             'prompt': 'What each stakeholder wants, fears or needs from the project',
             'fill': 'research',
             'cues': ['interest', 'concern', 'expectation'],
             'queries': ['stakeholder interests and concerns'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'influence',
             'label': 'Influence and impact',
             'prompt': 'The influence and impact labels you assign, with the evidence for them',
             'fill': 'research',
             'cues': ['influence', 'power', 'impact'],
             'queries': ['stakeholder influence and impact'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'engagement',
             'label': 'Engagement approach',
             'prompt': 'How you will engage: inform, consult, involve or collaborate',
             'fill': 'research',
             'cues': ['engagement', 'involvement', 'consultation'],
             'queries': ['stakeholder engagement approach'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'messages',
             'label': 'Key messages',
             'prompt': 'What each stakeholder needs to hear, in plain terms',
             'fill': 'research',
             'cues': ['message', 'communication', 'information'],
             'queries': ['stakeholder communication messages'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'channels',
             'label': 'Channels',
             'prompt': 'The route the message takes: meeting, email, notice, report or one-to-one',
             'fill': 'research',
             'cues': ['channel', 'meeting', 'report'],
             'queries': ['communication channels and methods'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'frequency',
             'label': 'Timing and frequency',
             'prompt': 'When and how often the communication happens, tied to milestones',
             'fill': 'research',
             'cues': ['frequency', 'timing', 'interval'],
             'queries': ['communication frequency and timing'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'owners',
             'label': 'Communication owner',
             'prompt': 'Who is responsible for each message or channel',
             'fill': 'research',
             'cues': ['owner', 'responsible', 'lead'],
             'queries': ['communication owner and responsibility'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'risks',
             'label': 'Communication risks',
             'prompt': 'What could make the communication fail, and the response',
             'fill': 'research',
             'cues': ['miscommunication', 'resistance', 'communication risk'],
             'queries': ['communication risks and resistance'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'}],
 'outline': {'framework': 'Framework overview',
             'context': 'Context and unit',
             'discussion': 'Block-by-block evidence',
             'implications': 'Implications',
             'limitations': 'Limitations',
             'conclusion': 'Conclusion',
             'lead': 'A stakeholder plan names the stakeholders one project affects, their interests and concerns, the influence and impact each carries, the engagement approach the project will take, the key messages and channels it will use, how often it will communicate, who owns the communication, and the communication risks it carries. Each block is treated in turn, first through the evidence accepted for the case and then through what that evidence implies for the decision to proceed.'},
 'voice': {'thesis_question': 'What does the evidence say about this framework for the named unit?',
           'unit_noun': 'unit',
           'block_plural': 'blocks',
           'lens': 'evidence audit',
           'closing': "The evidence is yours; the structure is the tool's.",
           'intro_frame': "This paper organises the evidence you supplied into the framework's blocks.",
           'context_frame': 'Context is limited to the unit named and the evidence supplied.',
           'interaction': 'Each block carries sourced items or a named gap.',
           'implication_frame': 'Implications are stated only where the evidence supports them.',
           'reference_heading': 'Sources'},
 'notes': {'stakeholders': {'analysis': 'Stakeholders is a structural block awaiting evidence.',
                            'qualify': 'The evidence does not establish more than what is supplied.',
                            'short': 'Stakeholders awaits evidence.',
                            'probe': 'state the evidence for this block'},
           'interests': {'analysis': 'Interests and concerns is a structural block awaiting evidence.',
                         'qualify': 'The evidence does not establish more than what is supplied.',
                         'short': 'Interests and concerns awaits evidence.',
                         'probe': 'state the evidence for this block'},
           'influence': {'analysis': 'Influence and impact is a structural block awaiting evidence.',
                         'qualify': 'The evidence does not establish more than what is supplied.',
                         'short': 'Influence and impact awaits evidence.',
                         'probe': 'state the evidence for this block'},
           'engagement': {'analysis': 'Engagement approach is a structural block awaiting evidence.',
                          'qualify': 'The evidence does not establish more than what is supplied.',
                          'short': 'Engagement approach awaits evidence.',
                          'probe': 'state the evidence for this block'},
           'messages': {'analysis': 'Key messages is a structural block awaiting evidence.',
                        'qualify': 'The evidence does not establish more than what is supplied.',
                        'short': 'Key messages awaits evidence.',
                        'probe': 'state the evidence for this block'},
           'channels': {'analysis': 'Channels is a structural block awaiting evidence.',
                        'qualify': 'The evidence does not establish more than what is supplied.',
                        'short': 'Channels awaits evidence.',
                        'probe': 'state the evidence for this block'},
           'frequency': {'analysis': 'Timing and frequency is a structural block awaiting evidence.',
                         'qualify': 'The evidence does not establish more than what is supplied.',
                         'short': 'Timing and frequency awaits evidence.',
                         'probe': 'state the evidence for this block'},
           'owners': {'analysis': 'Communication owner is a structural block awaiting evidence.',
                      'qualify': 'The evidence does not establish more than what is supplied.',
                      'short': 'Communication owner awaits evidence.',
                      'probe': 'state the evidence for this block'},
           'risks': {'analysis': 'Communication risks is a structural block awaiting evidence.',
                     'qualify': 'The evidence does not establish more than what is supplied.',
                     'short': 'Communication risks awaits evidence.',
                     'probe': 'state the evidence for this block'}}}

#: LESSONS_LEARNED (WO-3, inlined: it was loaded from an external temp file)
LESSONS_LEARNED = {'template': 'template_lessons_learned',
 'key': 'lessons_learned',
 'label': 'Lessons Learned',
 'title_prefix': 'Lessons Learned',
 'subject': 'project-management',
 'unit': {'field': 'unit',
          'label': 'Unit of analysis',
          'help': 'Name the single unit this worksheet covers.',
          'example': 'One project, one change programme, or one business model.',
          'refuse': 'A worksheet cannot be completed for a unit that has not been named.'},
 'ratings': False,
 'assumption': 'probe',
 'sites': 'organization',
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'gate': {'title_cue': True, 'title_context': True, 'require_geography': False},
 'blocks': [{'key': 'went_well',
             'label': 'What went well',
             'prompt': 'Practices, decisions or behaviours that worked and should be repeated',
             'fill': 'research',
             'cues': ['went well', 'success', 'achievement'],
             'queries': ['lessons learned what went well'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'went_poorly',
             'label': 'What did not go well',
             'prompt': 'What failed, slipped or caused avoidable cost',
             'fill': 'research',
             'cues': ['went wrong', 'lessons learned', 'failure', 'problem', 'shortfall'],
             'queries': ['lessons learned what did not go well'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'causes',
             'label': 'Why it happened',
             'prompt': 'The cause you can evidence, not blame',
             'fill': 'research',
             'cues': ['cause', 'reason', 'why'],
             'queries': ['root cause of project problems'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'changes',
             'label': 'What to change next time',
             'prompt': 'The specific change the next project should make',
             'fill': 'research',
             'cues': ['change', 'recommend', 'next time'],
             'queries': ['recommended changes for the next project'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'actions',
             'label': 'Actions and owners',
             'prompt': 'Who will make the change, and by when',
             'fill': 'research',
             'cues': ['action', 'follow-up', 'implementation'],
             'queries': ['lesson learned actions and owners'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'share',
             'label': 'Who should see this',
             'prompt': 'The teams or roles that need the lesson',
             'fill': 'research',
             'cues': ['share', 'sharing', 'disseminate', 'knowledge', 'lessons learned', 'projects'],
             'queries': ['sharing lessons learned across projects'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'},
            {'key': 'evidence',
             'label': 'Evidence',
             'prompt': 'Records, incidents, change requests or data behind the lesson',
             'fill': 'research',
             'cues': ['record', 'incident', 'change log'],
             'queries': ['project records and incident evidence'],
             'category': 'worksheet',
             'probe': 'state the evidence for this block'}],
 'outline': {'framework': 'Framework overview',
             'context': 'Context and unit',
             'discussion': 'Block-by-block evidence',
             'implications': 'Implications',
             'limitations': 'Limitations',
             'conclusion': 'Conclusion',
             'lead': 'Lessons learned records what went well on one project and what did not, why each of them happened, what the next project should change, the actions and owners that carry those changes, who should see the record, and the evidence it stands on. Each block is treated in turn, first through the evidence accepted for the case and then through what that evidence implies for the next decision.'},
 'voice': {'thesis_question': 'What does the evidence say about this framework for the named unit?',
           'unit_noun': 'unit',
           'block_plural': 'blocks',
           'lens': 'evidence audit',
           'closing': "The evidence is yours; the structure is the tool's.",
           'intro_frame': "This paper organises the evidence you supplied into the framework's blocks.",
           'context_frame': 'Context is limited to the unit named and the evidence supplied.',
           'interaction': 'Each block carries sourced items or a named gap.',
           'implication_frame': 'Implications are stated only where the evidence supports them.',
           'reference_heading': 'Sources'},
 'notes': {'went_well': {'analysis': 'What went well is a structural block awaiting evidence.',
                         'qualify': 'The evidence does not establish more than what is supplied.',
                         'short': 'What went well awaits evidence.',
                         'probe': 'state the evidence for this block'},
           'went_poorly': {'analysis': 'What did not go well is a structural block awaiting evidence.',
                           'qualify': 'The evidence does not establish more than what is supplied.',
                           'short': 'What did not go well awaits evidence.',
                           'probe': 'state the evidence for this block'},
           'causes': {'analysis': 'Why it happened is a structural block awaiting evidence.',
                      'qualify': 'The evidence does not establish more than what is supplied.',
                      'short': 'Why it happened awaits evidence.',
                      'probe': 'state the evidence for this block'},
           'changes': {'analysis': 'What to change next time is a structural block awaiting evidence.',
                       'qualify': 'The evidence does not establish more than what is supplied.',
                       'short': 'What to change next time awaits evidence.',
                       'probe': 'state the evidence for this block'},
           'actions': {'analysis': 'Actions and owners is a structural block awaiting evidence.',
                       'qualify': 'The evidence does not establish more than what is supplied.',
                       'short': 'Actions and owners awaits evidence.',
                       'probe': 'state the evidence for this block'},
           'share': {'analysis': 'Who should see this is a structural block awaiting evidence.',
                     'qualify': 'The evidence does not establish more than what is supplied.',
                     'short': 'Who should see this awaits evidence.',
                     'probe': 'state the evidence for this block'},
           'evidence': {'analysis': 'Evidence is a structural block awaiting evidence.',
                        'qualify': 'The evidence does not establish more than what is supplied.',
                        'short': 'Evidence awaits evidence.',
                        'probe': 'state the evidence for this block'}}}


#: The Balanced Scorecard (PM-01) ---------------------------------------------
#: Four perspectives, each answered with an objective, a measure, a target and the
#: initiative behind it.  The grid is the declared-matrix template
#: (`template_balanced_scorecard`); this profile supplies the prose the paper is
#: written from, and the four perspectives are the paper's dimensions.  It computes
#: nothing: no weight, no score, no composite index.
BALANCED_SCORECARD = {'template': 'template_balanced_scorecard',
 'key': 'balanced_scorecard',
 'label': 'Balanced Scorecard',
 'title_prefix': 'Balanced Scorecard',
 'subject': 'project-management',
 'unit': {'field': 'unit',
          'label': 'Unit of analysis',
          'help': 'Name the project or business unit this scorecard steers.',
          'example': 'One project, one programme, or one operating unit.',
          'refuse': 'A scorecard cannot be completed for a unit that has not been named.'},
 'ratings': False,
 'assumption': 'probe',
 'sites': 'organization',
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'gate': {'title_cue': True, 'title_context': True, 'require_geography': False},
 'blocks': [{'key': 'financial',
             'label': 'Financial perspective',
             'prompt': 'The money objective, the measure, the target and the initiative behind it',
             'fill': 'research',
             'cues': ['financial', 'budget', 'cost', 'revenue', 'funding'],
             'queries': ['financial perspective objective measure target'],
             'category': 'worksheet',
             'probe': 'state the evidence for this perspective'},
            {'key': 'customer',
             'label': 'Customer perspective',
             'prompt': 'What the customer or beneficiary gets, measured and targeted',
             'fill': 'research',
             'cues': ['customer', 'client', 'service', 'satisfaction', 'beneficiary'],
             'queries': ['customer perspective objective measure target'],
             'category': 'worksheet',
             'probe': 'state the evidence for this perspective'},
            {'key': 'internal_process',
             'label': 'Internal process perspective',
             'prompt': 'The process that has to be excellent for the other perspectives to hold',
             'fill': 'research',
             'cues': ['process', 'operations', 'quality', 'cycle', 'delivery'],
             'queries': ['internal process perspective objective measure target'],
             'category': 'worksheet',
             'probe': 'state the evidence for this perspective'},
            {'key': 'organisational_capacity',
             'label': 'Organisational capacity perspective',
             'prompt': 'The skills, systems and culture the other three depend on',
             'fill': 'research',
             'cues': ['training', 'skills', 'capability', 'culture', 'system'],
             'queries': ['learning and growth perspective objective measure target'],
             'category': 'worksheet',
             'probe': 'state the evidence for this perspective'}],
 'outline': {'framework': 'Framework overview',
             'context': 'Context and unit',
             'discussion': 'Perspective by perspective',
             'implications': 'Implications',
             'limitations': 'Limitations',
             'conclusion': 'Conclusion',
             'lead': 'A balanced scorecard steers one unit through four perspectives at once: the '
                     'financial result, the customer who pays for it, the internal process that '
                     'delivers it and the organisational capacity the other three rest on. Each '
                     'perspective is treated in turn, first through the evidence accepted for the '
                     'case and then through what that evidence implies for the decision, with an '
                     'objective, a measure, a target and an initiative recorded for each.'},
 'voice': {'thesis_question': 'whether each perspective is carried by evidence and whether its '
                              'measure can actually be read',
           'unit_noun': 'unit',
           'block_plural': 'perspectives',
           'lens': 'the four perspectives and the measures behind them',
           'closing': 'separates the perspectives the evidence supports from the ones it leaves open',
           'intro_frame': 'The unit is the one named in the brief; every perspective is read '
                          'against it.',
           'context_frame': 'Context is limited to the unit named and the evidence supplied.',
           'interaction': 'Read together, the perspectives show whether the steering measures rest '
                          'on evidence or on intention.',
           'implication_frame': 'An objective without a measure, or a measure without an owner, is '
                                'named rather than assumed.',
           'reference_heading': 'References'},
 'notes': {'financial': {'analysis': 'This perspective states the money objective and the measure '
                                     'that shows it; a figure without a declared target is '
                                     'described, not judged.',
                         'qualify': 'The evidence does not establish the target or the initiative, '
                                    'so both stay yours to declare.',
                         'short': 'A financial measure without a target is a hope.',
                         'probe': 'state the evidence for this perspective'},
           'customer': {'analysis': 'This perspective states what the customer or beneficiary gets '
                                    'and how it is measured.',
                        'qualify': 'The evidence does not establish satisfaction, so the measure is '
                                   'described rather than computed.',
                        'short': 'A customer measure nobody collects is decoration.',
                        'probe': 'state the evidence for this perspective'},
           'internal_process': {'analysis': 'This perspective names the process that has to perform '
                                            'for the other perspectives to hold.',
                                'qualify': 'The evidence does not establish process capability, so '
                                           'the measure is described rather than computed.',
                                'short': 'A process objective without a measure cannot be steered.',
                                'probe': 'state the evidence for this perspective'},
           'organisational_capacity': {'analysis': 'This perspective covers the skills, systems and '
                                                   'culture the other three depend on.',
                                       'qualify': 'The evidence does not establish capability, so it '
                                                  'is described rather than measured.',
                                       'short': 'Capacity is the perspective most often assumed.',
                                       'probe': 'state the evidence for this perspective'}}}

#: The Strategy Map (PM-02), KPI Tree (PM-03) and OKRs (PM-04) ------------------
#: Three more matrix worksheets on the same declared-grid machinery as the
#: Scorecard.  Each records what the student declares and computes nothing: no
#: causal chain, no metric value, no attainment score.
STRATEGY_MAP = {'template': 'template_strategy_map',
 'key': 'strategy_map',
 'label': 'Strategy Map',
 'title_prefix': 'Strategy Map',
 'subject': 'project-management',
 'unit': {'field': 'unit',
          'label': 'Unit of analysis',
          'help': 'Name the project or business unit this map steers.',
          'example': 'One project, one programme, or one operating unit.',
          'refuse': 'A strategy map cannot be completed for a unit that has not been named.'},
 'ratings': False,
 'assumption': 'probe',
 'sites': 'organization',
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'gate': {'title_cue': True, 'title_context': True, 'require_geography': False},
 'blocks': [{'key': 'outcome', 'label': 'Outcome objectives',
             'prompt': 'The result the unit has to produce, and the objective that carries it',
             'fill': 'research', 'cues': ['outcome', 'result', 'benefit', 'value'],
             'queries': ['outcome objective measure strategy map'],
             'category': 'worksheet', 'probe': 'state the evidence for this layer'},
            {'key': 'customer', 'label': 'Customer objectives',
             'prompt': 'Who is served, and the objective that names what they get',
             'fill': 'research', 'cues': ['customer', 'client', 'service', 'beneficiary'],
             'queries': ['customer objective measure strategy map'],
             'category': 'worksheet', 'probe': 'state the evidence for this layer'},
            {'key': 'process', 'label': 'Process objectives',
             'prompt': 'The process that has to perform for the customer objective to hold',
             'fill': 'research', 'cues': ['process', 'operations', 'quality', 'cycle'],
             'queries': ['internal process objective measure strategy map'],
             'category': 'worksheet', 'probe': 'state the evidence for this layer'},
            {'key': 'capability', 'label': 'Capability objectives',
             'prompt': 'The skills, systems or culture the process depends on',
             'fill': 'research', 'cues': ['skills', 'training', 'capability', 'culture', 'system'],
             'queries': ['capability objective measure strategy map'],
             'category': 'worksheet', 'probe': 'state the evidence for this layer'}],
 'outline': {'framework': 'Framework overview', 'context': 'Context and unit',
             'discussion': 'Objective by objective', 'implications': 'Implications',
             'limitations': 'Limitations', 'conclusion': 'Conclusion',
             'lead': 'A strategy map connects the objectives of one unit into a chain of cause '
                     'and effect: the capability the team needs, the process that uses it, the '
                     'customer who feels it and the result that follows. Each objective is '
                     'treated in turn, first through the evidence accepted for the case and then '
                     'through what that evidence implies, and a link between two objectives exists '
                     'only where the student declares it.'},
 'voice': {'thesis_question': 'whether each declared link in the chain is carried by evidence',
           'unit_noun': 'unit', 'block_plural': 'objectives',
           'lens': 'the objectives and the links between them',
           'closing': 'separates the links the evidence supports from the ones it leaves open',
           'intro_frame': 'The unit is the one named in the brief; each objective is read against it.',
           'context_frame': 'Context is limited to the unit named and the evidence supplied.',
           'interaction': 'Read together, the objectives show whether the chain holds or breaks at '
                          'a declared link.',
           'implication_frame': 'A link nobody can evidence is named rather than assumed.',
           'reference_heading': 'References'},
 'notes': {'outcome': {'analysis': 'This layer states the result the unit has to produce.',
                       'qualify': 'The evidence does not establish the result, so it is described.',
                       'short': 'A result nobody measures cannot be steered.',
                       'probe': 'state the evidence for this layer'},
           'customer': {'analysis': 'This layer states who is served and what they get.',
                        'qualify': 'The evidence does not establish the benefit, so it is described.',
                        'short': 'A customer objective without a measure is an intention.',
                        'probe': 'state the evidence for this layer'},
           'process': {'analysis': 'This layer names the process that has to perform.',
                       'qualify': 'The evidence does not establish process capability, so it is '
                                  'described.',
                       'short': 'A process objective without a measure cannot be steered.',
                       'probe': 'state the evidence for this layer'},
           'capability': {'analysis': 'This layer names the capability the process depends on.',
                          'qualify': 'The evidence does not establish the capability, so it is '
                                     'described.',
                          'short': 'Capability is the layer most often assumed.',
                          'probe': 'state the evidence for this layer'}}}

KPI_TREE = {'template': 'template_kpi_tree',
 'key': 'kpi_tree',
 'label': 'KPI Tree',
 'title_prefix': 'KPI Tree',
 'subject': 'project-management',
 'unit': {'field': 'unit',
          'label': 'Unit of analysis',
          'help': 'Name the project or business unit this metric tree describes.',
          'example': 'One project, one programme, or one operating unit.',
          'refuse': 'A KPI tree cannot be completed for a unit that has not been named.'},
 'ratings': False,
 'assumption': 'probe',
 'sites': 'organization',
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'gate': {'title_cue': True, 'title_context': True, 'require_geography': False},
 'blocks': [{'key': 'outcome', 'label': 'Outcome metric',
             'prompt': 'The one number at the top of the tree that says the unit is working',
             'fill': 'research', 'cues': ['outcome', 'result', 'revenue', 'margin', 'service'],
             'queries': ['outcome metric definition source'],
             'category': 'worksheet', 'probe': 'state the evidence for this level'},
            {'key': 'drivers', 'label': 'Driver metrics',
             'prompt': 'The few numbers that move the outcome, and how they combine into it',
             'fill': 'research', 'cues': ['driver', 'volume', 'conversion', 'rate', 'utilisation'],
             'queries': ['driver metric definition decomposition'],
             'category': 'worksheet', 'probe': 'state the evidence for this level'},
            {'key': 'inputs', 'label': 'Input metrics',
             'prompt': 'The levers the team actually controls, and where each number comes from',
             'fill': 'research', 'cues': ['input', 'staff', 'hours', 'stock', 'capacity'],
             'queries': ['input metric operational lever measurement'],
             'category': 'worksheet', 'probe': 'state the evidence for this level'}],
 'outline': {'framework': 'Framework overview', 'context': 'Context and unit',
             'discussion': 'Level by level', 'implications': 'Implications',
             'limitations': 'Limitations', 'conclusion': 'Conclusion',
             'lead': 'A KPI tree takes one outcome metric and decomposes it into the drivers that '
                     'move it and the inputs a team can actually pull, so that every number on the '
                     'tree has a definition and a source. Each level is treated in turn, first '
                     'through the evidence accepted for the case and then through what that '
                     'evidence implies, and no value is calculated anywhere in the tree.'},
 'voice': {'thesis_question': 'whether every number on the tree is defined, sourced and owned',
           'unit_noun': 'unit', 'block_plural': 'levels',
           'lens': 'the outcome, its drivers and the inputs beneath them',
           'closing': 'separates the metrics that can be reported from the ones that cannot',
           'intro_frame': 'The unit is the one named in the brief; the tree describes it.',
           'context_frame': 'Context is limited to the unit named and the evidence supplied.',
           'interaction': 'Read together, the levels show whether the outcome can actually be moved '
                          'by the levers the team controls.',
           'implication_frame': 'A metric with no source is a name, not a measure.',
           'reference_heading': 'References'},
 'notes': {'outcome': {'analysis': 'This level names the number the unit is judged by.',
                       'qualify': 'The evidence does not establish the value, so the definition is '
                                  'described.',
                       'short': 'An outcome without a definition cannot be reported.',
                       'probe': 'state the evidence for this level'},
           'drivers': {'analysis': 'This level names the numbers that move the outcome.',
                       'qualify': 'The evidence does not establish the relationship, so the '
                                  'decomposition is described.',
                       'short': 'A driver with no formula is a guess.',
                       'probe': 'state the evidence for this level'},
           'inputs': {'analysis': 'This level names the levers the team controls.',
                      'qualify': 'The evidence does not establish the lever, so it is described.',
                      'short': 'An input nobody records cannot be managed.',
                      'probe': 'state the evidence for this level'}}}

OKRS = {'template': 'template_okrs',
 'key': 'okrs',
 'label': 'OKRs',
 'title_prefix': 'Objectives and Key Results',
 'subject': 'project-management',
 'unit': {'field': 'unit',
          'label': 'Unit of analysis',
          'help': 'Name the project or team these OKRs commit.',
          'example': 'One project, one team, or one operating unit.',
          'refuse': 'An OKR set cannot be completed for a unit that has not been named.'},
 'ratings': False,
 'assumption': 'probe',
 'sites': 'organization',
 'providers': ['brave', 'deepseek', 'firecrawl'],
 'gate': {'title_cue': True, 'title_context': True, 'require_geography': False},
 'blocks': [{'key': 'objectives', 'label': 'Objectives',
             'prompt': 'The qualitative commitment: what changes, for whom, by when',
             'fill': 'research', 'cues': ['objective', 'goal', 'aim', 'commitment'],
             'queries': ['objective statement commitment'],
             'category': 'worksheet', 'probe': 'state the evidence for this objective'},
            {'key': 'key_results', 'label': 'Key results',
             'prompt': 'The measurable results that show the objective moved, with a baseline and '
                       'a target',
             'fill': 'research', 'cues': ['key result', 'measure', 'baseline', 'target', 'metric'],
             'queries': ['key result baseline target measure'],
             'category': 'worksheet', 'probe': 'state the evidence for these results'},
            {'key': 'initiatives', 'label': 'Initiatives',
             'prompt': 'The work that will move each key result, and who owns it',
             'fill': 'research', 'cues': ['initiative', 'project', 'owner', 'work'],
             'queries': ['initiative owner work plan key result'],
             'category': 'worksheet', 'probe': 'state the evidence for these initiatives'}],
 'outline': {'framework': 'Framework overview', 'context': 'Context and unit',
             'discussion': 'Objective by objective', 'implications': 'Implications',
             'limitations': 'Limitations', 'conclusion': 'Conclusion',
             'lead': 'An OKR set commits one team to a small number of objectives and makes each of '
                     'them checkable with key results that carry a baseline, a target and a '
                     'source. Each objective is treated in turn, first through the evidence '
                     'accepted for the case and then through what that evidence implies, and no '
                     'attainment score is calculated.'},
 'voice': {'thesis_question': 'whether each key result can actually be checked at review',
           'unit_noun': 'unit', 'block_plural': 'objectives',
           'lens': 'the objectives and the key results that make them checkable',
           'closing': 'separates the key results that can be judged from the ones that cannot',
           'intro_frame': 'The unit is the one named in the brief; the OKRs commit it.',
           'context_frame': 'Context is limited to the unit named and the evidence supplied.',
           'interaction': 'Read together, the objectives and key results show whether the commitment '
                          'can be reviewed or only restated.',
           'implication_frame': 'A key result with no baseline cannot be judged, and is named.',
           'reference_heading': 'References'},
 'notes': {'objectives': {'analysis': 'This block states the qualitative commitment.',
                          'qualify': 'The evidence does not establish the commitment, so it is '
                                     'described.',
                          'short': 'An objective nobody recalls is not a commitment.',
                          'probe': 'state the evidence for this objective'},
           'key_results': {'analysis': 'This block states the measurable results.',
                           'qualify': 'The evidence does not establish the value, so the baseline '
                                      'and target stay yours to declare.',
                           'short': 'A key result without a baseline is a wish.',
                           'probe': 'state the evidence for these results'},
           'initiatives': {'analysis': 'This block names the work that moves the results.',
                           'qualify': 'The evidence does not establish ownership, so it is '
                                      'described.',
                           'short': 'An initiative with no owner does not happen.',
                           'probe': 'state the evidence for these initiatives'}}}

PROFILES = {profile["template"]: profile

            for profile in (FIVE_FORCES, PESTEL, VALUE_CHAIN, SWOT, ANSOFF, VRIO, ERRC, ACTIVITY_SYSTEM, SCENARIO, 
                            STRATEGIC_GROUP, SIPOC, VALUE_STREAM_MAP, TOC, A3, SCOR, 
                            FIVE_S, ROOT_CAUSE, FMEA, KRALJIC, SALES_AND_OPERATIONS, 
                            PDCA, JOB_CHARACTERISTICS, KIRKPATRICK, AMO, TUCKMAN, 
NINE_BOX, KOTTER, COMPETING_VALUES, ORG_DESIGN, ADKAR, LEWIN, THEORY_OF_CHANGE, PDSA, DMAIC, GENERIC_STRATEGIES, BCG, GE_MCKINSEY, MCKINSEY_7S, RACI, PORTERS_DIAMOND, BURKE_LITWIN, GALBRAITH_STAR, MINTZBERG, LOGIC_MODEL,
BMC, LEAN_CANVAS, VALUE_PROPOSITION_CANVAS, PROJECT_CHARTER, BALANCED_SCORECARD, STRATEGY_MAP, KPI_TREE, OKRS, WBS, RISK_REGISTER, STAKEHOLDER_PLAN, LESSONS_LEARNED,
STRATEGIC_POSITIONING, CHANGE_ORGANIZATION, MARKETING_PLAN, KANO, PAID_MEDIA_PLAN, MEASUREMENT_PLAN, STP, AIDA, CUSTOMER_JOURNEY, FUNNEL, SERVQUAL, RFM, TAM, UTAUT, BRAND_EQUITY, DIGITAL_MIX, SEO_CONTENT, EMAIL_CRM, SOCIAL_MEDIA, ATTRIBUTION, CRO, MARKETING_AUTOMATION, STP_EVIDENCE,)
}
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

    deterministic prose and its query phrase wherever a block is researched,

    because a half-filled profile would produce a generic paper with the

    framework's name on it.  A block's `fill` policy decides which of these it

    needs: a `research` block must carry queries, a `quote` block takes the

    student's own words and a `gap` block is stated only by the student.

    """

    profile = PROFILES.get(str(template or ""))
    # resolve by key as well
    if profile is None:
        for p in PROFILES.values():
            if p.get("key") == str(template):
                profile = p
                break

    if profile is None:

        raise KeyError(str(template or ""))

    missing = []

    for block in profile["blocks"]:

        if not block.get("cues"):

            missing.append("%s: cues" % block["key"])

        if block.get("fill", "research") not in FILL:

            missing.append("%s: fill must be one of %s" % (block["key"], list(FILL)))

        elif block.get("fill", "research") in ("research", "auto") and not block.get("queries"):

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

#: How a profile block may be completed.  See `fill_of`.

FILL = {"research": "research", "auto": "auto", "quote": "quote", "gap": "gap"}

def fill_of(block):

    """How one block may be completed.

    `research` is the default and behaves as the market frameworks always have:

    external evidence is retrieved for the block and a part without evidence is

    returned as a gap.  `auto` tries the same research first and then falls back

    to the student's own words in the brief, so a part the brief already states

    is never re-typed but a part only a source can settle is still searched.

    `quote` takes the student's own words only.  `gap` is stated only by the

    student: the pipeline supplies nothing and names what is missing.

    """

    return FILL.get(str(block.get("fill") or "research"), "research")

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

def advice_for(template, key):
    """The authoring help for one block: what a usable answer holds, and the question.

    Empty when no advice is authored for that block, so a new framework renders
    without a help panel rather than with a generic one.  This is teaching text,
    never evidence: it is shown beside the input and can never be placed in a block.
    """
    entry = (ADVICE.get(str(template or "")) or {}).get(str(key or "")) or {}
    return {"contains": [str(item) for item in entry.get("contains") or []],
            "ask": [str(item) for item in entry.get("ask") or []]}


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

        "subject": profile.get("subject") or "management",

        "unit": dict(profile["unit"]),

        "ratings": bool(profile["ratings"]),

        "assumption": profile["assumption"],

        "styles": ["apa", "harvard"],

        "lengths": [{"key": "short", "label": "Short (600-1,200 words)"},

                    {"key": "mid", "label": "Mid (1,200-2,500 words)"},

                    {"key": "long", "label": "Long (2,500-5,000 words)"}],

        "blocks": [{"key": block["key"], "label": block["label"],

                    "prompt": block.get("prompt") or "",

                    "advice": advice_for(template, block["key"]),

                    "fill": fill_of(block)} for block in profile["blocks"]],

        "fills": [{"key": "research", "label": "Research retrieves external evidence for this part."},

                  {"key": "auto", "label": "Researched where evidence exists, otherwise taken from your own words."},

                  {"key": "quote", "label": "Taken from your own words in the instruction, verbatim."},

                  {"key": "gap", "label": "Only you can state this part. It stays a named gap until you do."}],

    }



#: How to write one block, per block (authoring help, never content).
#:
#: `contains` is what a usable answer in that block holds; `ask` is the question
#: that unblocks a student staring at an empty cell.  Nothing here is evidence: an
#: entry is a prompt to the student's own thinking, it carries no fact, number or
#: source, and it can never be placed in a block as an item.  The page renders it
#: under the block; the model lane may rephrase `ask` into the student's own words,
#: which is why every returned string is validated before it is shown.
ADVICE = {
    'template_project_charter': {
        'objective': {'contains': ['one sentence naming the outcome and who benefits',
                                   'the change it makes or the decision it enables'],
                      'ask': ['What is different once this project is finished, and for whom?']},
        'scope_in': {'contains': ['what the project delivers and covers',
                                  'the boundary you will defend when scope creeps'],
                     'ask': ['What exactly sits inside the line you are drawing?']},
        'scope_out': {'contains': ['what the project deliberately will not do',
                                   'the request you expect and are already refusing'],
                      'ask': ['What will someone ask for that you have decided to leave out?']},
        'deliverables': {'contains': ['verifiable outputs, not activities',
                                      'who receives each one'],
                         'ask': ['What can be handed over and checked?']},
        'governance': {'contains': ['who sponsors the project and who decides',
                                    'how a change to scope or budget is approved'],
                       'ask': ['Who can stop this project, and who signs off a change?']},
        'budget': {'contains': ['the amount and where it comes from',
                                'who may spend it, and up to what'],
                   'ask': ['Where does the money come from, and who controls it?']},
        'milestones': {'contains': ['dated checkpoints that gate the next stage',
                                    'the completion date'],
                       'ask': ['Which dates decide whether this project continues?']},
        'success_measures': {'contains': ['a measure, a target and a time window',
                                          'who reads the measure'],
                             'ask': ['How will you know it worked, by when, and read by whom?']},
        'assumptions': {'contains': ['what you are treating as true without evidence',
                                     'what happens to the plan if it is not'],
                        'ask': ['What has to stay true for this plan to hold?']},
        'constraints': {'contains': ['the limits you cannot change',
                                     'the dependencies outside your control'],
                        'ask': ['What is fixed, and what are you waiting on?']},
    },
    'template_wbs': {
        'deliverables': {'contains': ['the top-level deliverables only, not tasks',
                                      'one line per deliverable'],
                         'ask': ['What are the few things this project hands over?']},
        'work_packages': {'contains': ['the work under each deliverable, small enough to own',
                                       'who owns each package'],
                          'ask': ['What work has to happen under each deliverable, and who owns it?']},
        'acceptance': {'contains': ['the test that shows the package is complete',
                                    'who accepts it'],
                       'ask': ['What test would you run, and who signs it off?']},
        'exclusions': {'contains': ['the work the breakdown leaves out',
                                    'why it is left out'],
                       'ask': ['What nearby work are you deliberately not doing?']},
    },
    'template_risk_register': {
        'risk': {'contains': ['the risk as a cause and its effect',
                              'what it would affect if it happened'],
                 'ask': ['What could happen, and what would it do to the project?']},
        'response': {'contains': ['the response, the trigger and the owner',
                                  'what is done now versus if it happens'],
                     'ask': ['Who acts, when do they act, and what do they do?']},
    },
    'template_raci': {
        'responsible': {'contains': ['who does the work, as a role rather than a name',
                                     'the task the role is attached to'],
                        'ask': ['Who actually does this work, role by role?']},
        'accountable': {'contains': ['the one role that answers for the outcome',
                                     'how a disagreement about it is settled'],
                        'ask': ['Who answers for the outcome if it fails?']},
        'consulted': {'contains': ['whose input is needed before the decision',
                                   'when in the process they are asked'],
                      'ask': ['Whose view must be heard before you decide?']},
        'informed': {'contains': ['who is told after the decision is made',
                                  'how and when they are told'],
                     'ask': ['Who must be told once the decision is made?']},
    },
    'template_balanced_scorecard': {
        'financial': {'contains': ['the money result, not the activity that produces it',
                                   'the measure, the target and who reads it'],
                      'ask': ['What money result must this project produce, and how will you know?']},
        'customer': {'contains': ['who is better off and what they get',
                                  'the measure they would actually feel'],
                     'ask': ['Who is better off when this works, and how would they notice?']},
        'internal_process': {'contains': ['the one process that has to perform',
                                          'the measure of that process, not of its staff'],
                             'ask': ['Which process has to be right for that to happen?']},
        'organisational_capacity': {'contains': ['the skills, systems or culture it depends on',
                                                 'the measure of that capacity'],
                                    'ask': ['What must the team be able to do that it cannot do yet?']},
    },
    'template_strategy_map': {
        'outcome': {'contains': ['the result the unit has to produce',
                                 'the objective that carries it'],
                    'ask': ['What result must this unit produce, and which objective carries it?']},
        'customer': {'contains': ['who is served and what they get',
                                  'the measure the customer would feel'],
                     'ask': ['Who is served, and what do they get that they do not get now?']},
        'process': {'contains': ['the process that has to perform',
                                 'what "performing" means in a number'],
                     'ask': ['Which process has to be excellent for that to happen?']},
        'capability': {'contains': ['the skill, system or habit the process depends on',
                                    'what the team can do afterwards that it cannot do now'],
                       'ask': ['What must the team be able to do that it cannot do yet?']},
    },
    'template_kpi_tree': {
        'outcome': {'contains': ['the one number the unit is judged by',
                                 'its exact definition, not just its name'],
                    'ask': ['What single number tells you this unit is working, and how is it '
                            'defined?']},
        'drivers': {'contains': ['the few numbers that move the outcome',
                                 'how they combine, written as a formula'],
                    'ask': ['Which numbers move that outcome, and how do they combine?']},
        'inputs': {'contains': ['the levers the team actually controls',
                                'where each number is recorded'],
                   'ask': ['What can the team change this week, and who records it?']},
    },
    'template_okrs': {
        'objectives': {'contains': ['what changes, for whom, by when',
                                    'a commitment someone owns'],
                       'ask': ['What will be true at the end of the period that is not true now?']},
        'key_results': {'contains': ['a number with a baseline and a target',
                                     'the source the number is read from'],
                        'ask': ['How will you show it moved, from what number to what number?']},
        'initiatives': {'contains': ['the work that moves each key result',
                                     'who owns it and when it lands'],
                        'ask': ['What work will move it, and who owns that work?']},
    },
    'template_stakeholder_plan': {
        'stakeholders': {'contains': ['named roles or groups, never "everyone"',
                                      'why each one is affected'],
                         'ask': ['Who is affected by this, and how?']},
        'interests': {'contains': ['what each one wants and what they fear',
                                   'what would make them resist'],
                      'ask': ['What does each stakeholder want, and what worries them?']},
        'influence': {'contains': ['how far each can help or block the project',
                                   'where that power comes from'],
                      'ask': ['Who can make this land, and who can stop it?']},
        'engagement': {'contains': ['the approach for each group: inform, consult or involve',
                                    'what you are asking of them'],
                       'ask': ['For each group, are you informing, consulting or involving them?']},
        'messages': {'contains': ['the one message each group needs first',
                                  'what you are deliberately not saying yet'],
                     'ask': ['What does each group need to hear first?']},
        'channels': {'contains': ['the channel and the form the message takes',
                                  'why that channel suits them'],
                     'ask': ['Where will they actually read it?']},
        'frequency': {'contains': ['how often for each group',
                                   'the event that forces an extra update'],
                      'ask': ['How often, and what event forces an update?']},
        'owners': {'contains': ['who sends each message',
                                'who covers when they are away'],
                   'ask': ['Who sends it, and who covers for them?']},
        'risks': {'contains': ['the communication failure you expect',
                               'what you will do if it appears'],
                  'ask': ['What could go wrong with the communication itself?']},
    },
    'template_lessons_learned': {
        'went_well': {'contains': ['what happened, with the instance it happened in',
                                   'why it worked'],
                      'ask': ['What went better than expected, and why?']},
        'went_poorly': {'contains': ['what happened, with the instance it happened in',
                                     'the effect it had'],
                        'ask': ['What went wrong, and what did it cost?']},
        'causes': {'contains': ['the cause you can act on',
                                'how you know that is the cause'],
                   'ask': ['Why did it happen, and how do you know?']},
        'changes': {'contains': ['a change the next project can actually make',
                                 'how it would have changed the outcome'],
                    'ask': ['What would you do differently next time?']},
        'actions': {'contains': ['a named action with the owner who carries it',
                                 'the date it is due'],
                    'ask': ['Who does what, and by when?']},
        'share': {'contains': ['who needs this lesson and why',
                               'where the record lives'],
                  'ask': ['Who should read this, and where will they find it?']},
        'evidence': {'contains': ['the record that supports the lesson',
                                  'where that record is kept'],
                     'ask': ['What record backs this lesson up?']},
    },
}


# ---------------------------------------------------------------------------
# The quote vocabulary (D-OPS-03)
# ---------------------------------------------------------------------------
# `cues` is the vocabulary a *retrieved source* is accepted on, and it needs the
# words a query uses.  It is the wrong vocabulary to decide whether a sentence of
# the student's own brief answers a part: every brief on an operations shelf says
# "change", "review", "cost", "quality" or "flow" somewhere, so a single shared
# token put "The manager reviews the change next term" into the PDCA cell asking
# what was standardised, and put "we must cut cost without losing quality" into
# the root-cause cell about inputs.  D-MGT-03 was the same defect on the
# management shelf, and the owner graded it BLOCKER: invented evidence is the one
# thing the product may not do.
#
# The fix is a declaration, not a heuristic: the Operations shelf's profiles say,
# per part, which words make a sentence *about that part*.  `completion.
# _quote_block` matches only these when they are declared.  An empty string means
# the part is never taken from the brief at all, because only a figure, a source
# or the student's own worksheet can answer it.
QUOTE_CUES = {
    "template_scor": {
        "plan": "forecast replenish schedule",
        "source": "supplier procurement purchasing vendor contract",
        "make": "production assembly manufacturing",
        "deliver": "deliver distribution transport logistics shipping",
        "return": "return reverse recall warranty credit",
        "enable": "governance compliance contract",
    },
    "template_sipoc": {
        "process": "step order prepare assemble pack serve collect take",
        "outputs": "output outputs parcel receipt hands produced passed",
        "customers": "customer client student guest passenger receives collects",
    },
    "template_value_stream_map": {
        "process_steps": "step order prepare assemble pack take collect deliver receive store",
        "cycle_and_lead_times": "cycle lead minutes seconds hours turnaround",
        "inventory_wip": "inventory stock wip batch backlog pile storage freezer shelf",
        "waits_delays": "wait waiting delay queue handoff bottleneck stalled",
    },
    "template_5s": {
        "sort": "sort removed unnecessary clutter unused broken excess discard",
        "set_in_order": "place location label mark arrangement layout",
        "shine": "clean cleaned inspect maintenance wash wipe spill",
        "standardize": "standard procedure checklist photograph posted",
        "sustain": "audit habit sustain discipline",
    },
    "template_a3": {
        "problem": "problem defect delay error complaint gap",
        "current_condition": "current currently present queue observed data",
        "target": "target goal reduce increase within",
        "causes": "cause root why because reason driver factor",
        "countermeasures": "countermeasure fix redesign separate combine simplify eliminate introduce",
        "plan": "owner responsible week month depends",
        "follow_up": "followup follow-up verify revisit audit",
    },
    "template_toc": {
        "identify": "constraint bottleneck throughput slowest starved",
        "exploit": "exploit uptime idle changeover losses",
        "subordinate": "subordinate pace release buffer drum rope",
        "elevate": "elevate invest outsource capex",
        "reassess": "reassess moved shifted inertia",
    },
    "template_root_cause": {
        "problem": "problem defect error delay complaint",
        "people": "staff training skill handover operator behaviour",
        "process": "process method procedure sequence workflow",
        "equipment": "equipment machine tool maintenance breakdown",
        "materials": "material input specification raw components",
        "measurement": "measurement metric calibration inspection gauge",
        "environment": "environment layout light heat noise space",
        "root_cause": "root cause confirmed verified proved",
    },
    "template_fmea": {
        "failure_modes": "failure mode wrong missing",
        "effects": "effect consequence impact",
        "causes": "cause reason because",
        "controls": "control prevention detection inspection",
        "actions": "action mitigate reduce redesign",
        "owners": "owner accountable assigned responsible",
    },
    "template_kraljic": {
        "criteria": "criteria threshold spend",
        "strategic": "strategic sole critical partnership",
        "leverage": "leverage tender competition",
        "bottleneck": "bottleneck scarce single",
        "non_critical": "routine catalogue noncritical non-critical",
    },
    "template_sop": {
        "demand_plan": "forecast volume",
        "supply_plan": "production capacity constraint",
        "inventory_plan": "inventory stock buffer safety",
        "capacity_plan": "capacity hours staffing",
        "financial_plan": "revenue margin profit budget",
        "decisions": "conflict reconcile trade",
    },
    "template_pdca": {
        "plan": "problem target hypothesis",
        "do": "trial pilot implemented ran",
        "check": "measured result compared",
        "act": "standardise standardised adopt abandon",
    },
}

for _template, _parts in QUOTE_CUES.items():
    _profile = PROFILES.get(_template)
    if _profile is None:
        continue
    for _block in _profile["blocks"]:
        if _block["key"] in _parts:
            _block["quote_cues"] = _parts[_block["key"]]


