"""WO-2b: the worksheet definitions for the 32 registered profiles.

Every entry gives the four things `bp.templates` needs for a canvas template:

- ``blocks``    the block labels and prompts (only for the nine templates that
                had none; the other twenty-three already carry blocks that
                match their profile exactly).
- ``meta``      the name, the short name, the catalogue id, and the intended
                and unsupported uses, in the house voice.
- ``prefixes``  a short readable id prefix per block, so a student can link
                two items by an id they can read.
- ``example``   a worked request on the synthetic campus-meal-service case
                that every file already uses.

The examples carry no digits, so the rendered narrative stays free of numbers
the student never supplied.
"""

TEMPLATES = {
    # ---------------------------------------------------------------- change
    "template_adkar": {
        "catalogue_id": "CHG-02",
        "blocks": {
            "awareness": ("Awareness", "Why the change is needed and why now"),
            "desire": ("Desire", "Why change matters and what people gain"),
            "knowledge": ("Knowledge", "What people need to know and how they are taught"),
            "ability": ("Ability", "What people must do differently"),
            "reinforcement": ("Reinforcement", "What makes the change stick"),
        },
        "meta": {
            "name": "ADKAR readiness review with an evidence audit",
            "short": "ADKAR review",
            "intended_use": "Read the evidence behind each of the five ADKAR elements for one change programme, and audit the elements that have no evidence behind them.",
            "unsupported_use": "Scoring readiness, diagnosing individual employees, or deciding what a person thinks; the elements describe the change and the evidence is yours.",
            "extra_help": "The five elements are the ones ADKAR names. An element with no evidence is named and left empty; the worksheet computes no readiness index.",
        },
        "prefixes": {"awareness": "AW", "desire": "DE", "knowledge": "KN", "ability": "AB", "reinforcement": "RE"},
        "example": {
            "objective": "Read the readiness evidence for the move to a contactless meal card",
            "blocks": {
                "awareness": [{"text": "The change is announced in the same email that closes the old card", "provenance": "synthetic"}],
                "desire": [{"text": "Counter staff have asked for the change because the old card is slow to load", "provenance": "synthetic"}],
                "knowledge": [{"text": "Nobody has written the steps for loading a new balance", "provenance": "assumption"}],
                "ability": [{"text": "Training for the new card is a single session at the counter", "provenance": "synthetic"}],
            },
        },
    },
    "template_lewin": {
        "catalogue_id": "CHG-03",
        "blocks": {
            "unfreeze": ("Unfreeze", "Prepare the organisation for change by undermining the existing status quo"),
            "change": ("Change", "Move the organisation to a new state through the steps the change requires"),
            "refreeze": ("Refreeze", "Anchor the new state in daily routines so the change sticks"),
        },
        "meta": {
            "name": "Lewin's three-stage change review with an evidence audit",
            "short": "Lewin review",
            "intended_use": "Read the evidence for the three stages of one change programme and audit the stage the evidence cannot settle.",
            "unsupported_use": "Claiming a change has succeeded, skipping a stage, or deciding how an organisation should feel; the stages are a lens and the evidence is yours.",
            "extra_help": "The three stages are the ones Lewin names. A stage with no evidence is named and left empty; the worksheet advances no programme and derives no verdict.",
        },
        "prefixes": {"unfreeze": "UN", "change": "CH", "refreeze": "RF"},
        "example": {
            "objective": "Read where the contactless meal card change stands",
            "blocks": {
                "unfreeze": [{"text": "The old card is kept live for one more term, so nothing has been given up yet", "provenance": "synthetic"}],
                "change": [{"text": "The new card is loaded at the counter and staff take payment on a second device", "provenance": "synthetic"}],
                "refreeze": [{"text": "The new card is still a temporary arrangement at the counter", "provenance": "assumption"}],
            },
        },
    },
    "template_mckinsey_7s": {
        "catalogue_id": "CHG-04",
        "blocks": {
            "strategy": ("Strategy", "What the organisation is trying to achieve and how"),
            "structure": ("Structure", "How the work is organised and authority is distributed"),
            "systems": ("Systems", "The formal procedures and systems the work runs on"),
            "shared_values": ("Shared Values", "The beliefs the organisation holds in common"),
            "style": ("Style", "The leadership behaviour that shapes the work"),
            "staff": ("Staff", "The people, numbers and skills the work needs"),
            "skills": ("Skills", "The capability the organisation has and lacks"),
        },
        "meta": {
            "name": "McKinsey 7-S alignment review with an evidence audit",
            "short": "7-S review",
            "intended_use": "Read the evidence across the seven elements of one organisation and record where the elements do not fit each other.",
            "unsupported_use": "Scoring alignment, ranking the elements, or redesigning the organisation; the review names the mismatch and the redesign is yours to propose.",
            "extra_help": "The seven elements are the ones the model names. No single score is authoritative, so the worksheet computes none.",
        },
        "prefixes": {"strategy": "SG", "structure": "SC", "systems": "SY", "shared_values": "VA",
                     "style": "ST", "staff": "SF", "skills": "SK"},
        "example": {
            "objective": "Check the fit of the seven elements for the campus catering service",
            "blocks": {
                "strategy": [{"text": "The service aims to be the fastest student-priced hot meal on campus", "provenance": "synthetic"}],
                "structure": [{"text": "One kitchen line and one counter, with the counter team reporting to the estate office", "provenance": "synthetic"}],
                "systems": [{"text": "Ordering is by phone, and no record is kept of what was ordered", "provenance": "assumption"}],
                "shared_values": [{"text": "The team treats the queue as the problem to be hidden rather than removed", "provenance": "synthetic"}],
                "skills": [{"text": "Two of the four counter staff have run the kitchen before", "provenance": "synthetic"}],
            },
        },
    },
    "template_burke_litwin": {
        "catalogue_id": "CHG-05",
        "blocks": {
            "external_environment": ("External Environment", "The external forces that shape the organisation"),
            "mission_strategy": ("Mission and Strategy", "What the organisation is trying to achieve and how"),
            "leadership": ("Leadership", "The style and behaviour of those who lead"),
            "culture": ("Culture", "The shared values, beliefs and assumptions"),
            "structure": ("Structure", "How work is organised and authority is distributed"),
            "management_practices": ("Management Practices", "How managers actually behave and the systems they use"),
            "systems": ("Systems and Policies", "The formal procedures, policies and reward systems"),
            "work_unit_climate": ("Work Unit Climate", "The atmosphere and morale within teams"),
            "task_requirements": ("Task and Individual Skills", "The skills, abilities and motivation of individuals"),
            "motivation": ("Motivation", "What drives people to perform"),
            "individual_values": ("Individual Needs and Values", "What individuals want and value"),
            "performance": ("Individual and Organisational Performance", "The results the organisation achieves"),
        },
        "meta": {
            "name": "Burke-Litwin organisational change review with an evidence audit",
            "short": "Burke-Litwin review",
            "intended_use": "Trace one change through the twelve elements of one organisation and audit the element the evidence cannot settle.",
            "unsupported_use": "Claiming a causal link between the elements, diagnosing the organisation, or prescribing the change; the elements are traced and the cause is yours to argue.",
            "extra_help": "The twelve elements are the ones the model names. An element with no evidence is named and left empty; the worksheet derives no causal claim.",
        },
        "prefixes": {"external_environment": "EE", "mission_strategy": "MS", "leadership": "LD", "culture": "CU",
                     "structure": "SC", "management_practices": "MP", "systems": "SY", "work_unit_climate": "WC",
                     "task_requirements": "TR", "motivation": "MO", "individual_values": "IV", "performance": "PF"},
        "example": {
            "objective": "Trace the catering reorganisation through the organisation it affects",
            "blocks": {
                "external_environment": [{"text": "The university is moving food concessions to a single supplier next year", "provenance": "synthetic"}],
                "mission_strategy": [{"text": "The canteen intends to keep its own cooking team", "provenance": "synthetic"}],
                "leadership": [{"text": "The canteen manager sets the rota and approves all leave personally", "provenance": "synthetic"}],
                "culture": [{"text": "The team has always been told the menu is fixed and cannot be argued with", "provenance": "synthetic"}],
                "structure": [{"text": "Cooking and counter service sit in two separate line-management structures", "provenance": "synthetic"}],
                "management_practices": [{"text": "The kitchen and the counter do not hold a shared daily meeting", "provenance": "assumption"}],
            },
        },
    },
    "template_galbraith_star": {
        "catalogue_id": "CHG-06",
        "blocks": {
            "strategy": ("Strategy", "What the organisation is trying to achieve"),
            "structure": ("Structure", "How the work is organised and who decides what"),
            "processes": ("Processes", "How the work is actually done and handed over"),
            "rewards": ("Rewards", "What the organisation rewards people for doing"),
            "people": ("People", "The roles, capability and capacity the design needs"),
        },
        "meta": {
            "name": "Galbraith star operating model review with an evidence audit",
            "short": "star model review",
            "intended_use": "Read the evidence across the five elements of one operating model and audit the element that does not hold the others up.",
            "unsupported_use": "Reorganising the organisation, choosing the shape of the model, or scoring how well the points of the star fit; the elements are read and the redesign is yours.",
            "extra_help": "The five elements are the ones the model names. An element with no evidence is named and left empty; the worksheet computes no fit score.",
        },
        "prefixes": {"strategy": "ST", "structure": "SC", "processes": "PR", "rewards": "RW", "people": "PE"},
        "example": {
            "objective": "Read the operating model of the campus catering service",
            "blocks": {
                "strategy": [{"text": "The service aims to be the fastest student-priced hot meal on campus", "provenance": "synthetic"}],
                "structure": [{"text": "One kitchen line and one counter, with the counter team reporting to the estate office", "provenance": "synthetic"}],
                "processes": [{"text": "Orders are taken by phone and cooked to order at the counter", "provenance": "synthetic"}],
                "rewards": [{"text": "Staff are rewarded for meals sold rather than for queue time", "provenance": "assumption"}],
                "people": [{"text": "The counter team is three part-time students and one supervisor", "provenance": "synthetic"}],
            },
        },
    },
    "template_theory_of_change": {
        "catalogue_id": "CHG-07",
        "blocks": {
            "inputs": ("Inputs", "The resources and conditions brought to the change effort"),
            "activities": ("Activities", "The actions and interventions the change will carry out"),
            "outputs": ("Outputs", "The direct products of the activities, in expected quantity"),
            "outcomes": ("Outcomes", "The short, medium and long-term results the change aims to achieve"),
        },
        "meta": {
            "name": "Theory of change with an evidence audit",
            "short": "theory of change",
            "intended_use": "Lay the causal links from inputs through activities and outputs to outcomes for one programme, and audit the links that rest on assumptions.",
            "unsupported_use": "Claiming the causal pathway holds, proving impact, or filling a missing link; the links are hypotheses to test and the evidence is yours.",
            "extra_help": "Each link is a hypothesis. An assumption is flagged and left as it is; the worksheet derives no impact estimate.",
        },
        "prefixes": {"inputs": "IN", "activities": "AC", "outputs": "OU", "outcomes": "OC"},
        "example": {
            "objective": "Set out the causal pathway for the campus mentoring programme",
            "blocks": {
                "inputs": [{"text": "Two trained mentors and a room booked for one afternoon a week", "provenance": "synthetic"}],
                "activities": [{"text": "Each mentor sees a small group of first-year students for an hour", "provenance": "synthetic"}],
                "outputs": [{"text": "A record of the sessions held and the students who attended", "provenance": "synthetic"}],
                "outcomes": [{"text": "Students report that they know where to ask for help", "provenance": "assumption"}],
            },
        },
    },
    "template_logic_model": {
        "catalogue_id": "CHG-08",
        "blocks": {
            "inputs": ("Inputs", "The resources and conditions brought to the change effort"),
            "activities": ("Activities", "The actions and interventions the change will carry out"),
            "outputs": ("Outputs", "The direct products of the activities, in expected quantity"),
            "outcomes": ("Outcomes", "The short, medium and long-term results the change aims to achieve"),
        },
        "meta": {
            "name": "Logic model with an evidence audit",
            "short": "logic model",
            "intended_use": "Lay the inputs, activities, outputs and outcomes of one programme beside each other and audit the element the evidence cannot settle.",
            "unsupported_use": "Measuring the outcomes, proving the programme worked, or filling an empty element; the worksheet distinguishes what is counted from what is achieved.",
            "extra_help": "Activities are what the programme does and outputs are what it produces directly; outcomes are the changes it aims to cause. The worksheet keeps them apart and computes no indicator.",
        },
        "prefixes": {"inputs": "IN", "activities": "AC", "outputs": "OU", "outcomes": "OC"},
        "example": {
            "objective": "Lay out the logic of the campus mentoring programme",
            "blocks": {
                "inputs": [{"text": "Two trained mentors and a room booked for one afternoon a week", "provenance": "synthetic"}],
                "activities": [{"text": "Each mentor sees a small group of first-year students for an hour", "provenance": "synthetic"}],
                "outputs": [{"text": "A session record is kept for each group", "provenance": "synthetic"}],
                "outcomes": [{"text": "No measure of student retention has been agreed yet", "provenance": "assumption"}],
            },
        },
    },
    "template_pdsa": {
        "catalogue_id": "CHG-09",
        "blocks": {
            "plan": ("Plan", "What change is planned and what will be measured"),
            "do": ("Do", "What was carried out and on what scale"),
            "study": ("Study", "What the results show and what was learned"),
            "act": ("Act", "What is adopted, adapted or abandoned as a result"),
        },
        "meta": {
            "name": "PDSA improvement cycle with an evidence audit",
            "short": "PDSA cycle",
            "intended_use": "Record one cycle of a small test of change, from the plan and the prediction to what was studied and what was adopted.",
            "unsupported_use": "Claiming the cycle succeeded, generalising from one cycle, or choosing what to adopt next; the worksheet records the cycle and the decision is yours.",
            "extra_help": "The four steps are the ones PDSA names. A step with no evidence is named and left empty; the worksheet computes no significance and derives no verdict.",
        },
        "prefixes": {"plan": "PL", "do": "DO", "study": "SY", "act": "AC"},
        "example": {
            "objective": "Record the first cycle of the contactless meal card trial",
            "blocks": {
                "plan": [{"text": "Test a pre-order shelf for ten minutes at the counter, and record the wait at the counter", "provenance": "synthetic"}],
                "do": [{"text": "The shelf was run at the counter on four days", "provenance": "synthetic"}],
                "study": [{"text": "Wait times were noted on a sheet but the count was never totalled", "provenance": "assumption"}],
            },
        },
    },
    "template_dmaic": {
        "catalogue_id": "CHG-10",
        "blocks": {
            "define": ("Define", "The problem, the scope and the goal of the improvement"),
            "measure": ("Measure", "The baseline, the current performance and the data collected"),
            "analyze": ("Analyze", "The root causes and the evidence behind them"),
            "improve": ("Improve", "The changes tested and the results they produced"),
            "control": ("Control", "How the improvement is held in place going forward"),
        },
        "meta": {
            "name": "DMAIC improvement cycle with an evidence audit",
            "short": "DMAIC cycle",
            "intended_use": "Walk one process improvement through the five steps of DMAIC and audit the step the evidence cannot settle.",
            "unsupported_use": "Asserting a root cause without measurement, scoring the improvement, or certifying that the process is now controlled; the steps are recorded and the judgement is yours.",
            "extra_help": "The five steps are the ones DMAIC names. A step with no evidence is named and left empty; the worksheet derives no cause and computes no capability figure.",
        },
        "prefixes": {"define": "DE", "measure": "ME", "analyze": "AN", "improve": "IM", "control": "CO"},
        "example": {
            "objective": "Walk the campus meal card service through a DMAIC cycle",
            "blocks": {
                "define": [{"text": "Students give up on lunch when the queue at the counter is long", "provenance": "synthetic"}],
                "measure": [{"text": "The wait at the counter was timed on a sheet for one week", "provenance": "synthetic"}],
                "analyze": [{"text": "Most of the wait comes from meals cooked to order rather than from serving", "provenance": "assumption"}],
                "improve": [{"text": "Two meals are cooked in advance and held for the rush", "provenance": "synthetic"}],
                "control": [{"text": "Nothing is in place to hold the change once the test ends", "provenance": "assumption"}],
            },
        },
    },
    "template_mintzberg": {
        "catalogue_id": "CHG-13",
        "blocks": {
            "strategic_apex": ("Strategic Apex", "The top of the hierarchy, where direction is set"),
            "middle_line": ("Middle Line", "The managers between the apex and the operating core"),
            "operating_core": ("Operating Core", "The people who do the operational work"),
            "technostructure": ("Technostructure", "The specialists who standardise the work"),
            "support_staff": ("Support Staff", "The people who support the others rather than doing the core work"),
        },
        "meta": {
            "name": "Mintzberg configuration review with an evidence audit",
            "short": "configuration review",
            "intended_use": "Read how one organisation is actually put together, part by part, and audit the part the evidence cannot settle.",
            "unsupported_use": "Assigning a configuration type, redesigning the organisation, or deciding which shape it should have; the parts are read and the diagnosis is yours.",
            "extra_help": "The five parts are the ones the model names. A part with no evidence is named and left empty; the worksheet assigns no type and computes no fit.",
        },
        "prefixes": {"strategic_apex": "SA", "middle_line": "ML", "operating_core": "OC",
                     "technostructure": "TS", "support_staff": "SS"},
        "example": {
            "objective": "Read how the campus catering service is actually put together",
            "blocks": {
                "strategic_apex": [{"text": "The estate office decides the concession and sets the rent", "provenance": "synthetic"}],
                "middle_line": [{"text": "The canteen manager sits between the estate office and the kitchen", "provenance": "synthetic"}],
                "operating_core": [{"text": "The kitchen and the counter teams cook and serve", "provenance": "synthetic"}],
                "technostructure": [{"text": "Nobody writes the food-handling procedure the kitchen follows", "provenance": "assumption"}],
            },
        },
    },
    "template_change_organization": {
        "catalogue_id": "CHG-15",
        "blocks": {
            "change_type": ("Change Type", "What kind of change it is and what it reaches"),
            "readiness": ("Readiness", "How ready the organisation is to carry it"),
            "resistance": ("Resistance", "Where the change is likely to be resisted and why"),
            "support": ("Support", "The support the change needs to hold"),
        },
        "meta": {
            "name": "Change and organisation review with an evidence audit",
            "short": "change and organisation review",
            "intended_use": "Read one programme of change against the organisation that has to carry it, and audit the element the evidence cannot settle.",
            "unsupported_use": "Predicting whether the change will succeed, diagnosing individual attitudes, or prescribing the intervention; the four elements are read and the plan is yours.",
            "extra_help": "The four elements are the ones the review names. An element with no evidence is named and left empty; the worksheet computes no readiness score.",
        },
        "prefixes": {"change_type": "CT", "readiness": "RD", "resistance": "RS", "support": "SU"},
        "example": {
            "objective": "Read the organisation behind the contactless meal card change",
            "blocks": {
                "change_type": [{"text": "The change alters how students pay, not how the kitchen works", "provenance": "synthetic"}],
                "readiness": [{"text": "Counter staff asked for the change after the old card became unreliable", "provenance": "synthetic"}],
                "resistance": [{"text": "Students who pay in cash at the counter have not been considered", "provenance": "assumption"}],
                "support": [{"text": "A short session is planned for counter staff", "provenance": "synthetic"}],
            },
        },
    },
    # -------------------------------------------------------------- strategy
    "template_generic_strategies": {
        "catalogue_id": "STR-02",
        "blocks": {
            "low_cost": ("Low-Cost", "Aims to be the cheapest producer"),
            "differentiation": ("Differentiation", "Focuses on unique product features customers value"),
            "focus_low_cost": ("Focused Low-Cost", "Low cost within a narrow market segment"),
            "focus_differentiation": ("Focused Differentiation", "Unique value within a narrow market segment"),
        },
        "meta": {
            "name": "Porter's generic strategies with an evidence audit",
            "short": "generic strategies",
            "intended_use": "Read the evidence for where a firm sits against cost leadership and differentiation, and audit the choice the evidence cannot settle.",
            "unsupported_use": "Choosing a strategy for the firm, scoring the trade-off, or claiming the firm can hold both; the types are a lens and the choice is yours.",
            "extra_help": "The four types are the ones the model names. A type with no evidence is named and left empty; the worksheet computes no trade-off score.",
        },
        "prefixes": {"low_cost": "LC", "differentiation": "DF", "focus_low_cost": "FL", "focus_differentiation": "FD"},
        "example": {
            "objective": "Read the competitive range of the campus meal service",
            "blocks": {
                "low_cost": [{"text": "Ingredients are bought at the wholesale market and cooked in one batch", "provenance": "synthetic"}],
                "differentiation": [{"text": "Meals are cooked to order from a menu that changes each week", "provenance": "synthetic"}],
                "focus_low_cost": [{"text": "The service is positioned as the cheapest hot meal for students on campus", "provenance": "synthetic"}],
            },
        },
    },
    "template_porters_diamond": {
        "catalogue_id": "STR-05",
        "blocks": {
            "factor_conditions": ("Factor Conditions", "The inputs and skills the location gives the industry"),
            "demand_conditions": ("Demand Conditions", "The home demand the industry serves"),
            "related_industries": ("Related Industries", "The nearby suppliers, buyers and supporting industries"),
            "firm_strategy": ("Firm Strategy and Rivalry", "How firms in the industry choose and how they compete"),
            "government": ("Government", "The role policy, trade and regulation play"),
            "chance": ("Chance", "The events outside the industry's control"),
        },
        "meta": {
            "name": "Porter's Diamond with an evidence audit",
            "short": "Porter's Diamond",
            "intended_use": "Read the conditions that shape one industry in its country and audit the determinant the evidence cannot settle.",
            "unsupported_use": "Attributing an advantage to a country, predicting a national outcome, or deciding where to locate; the determinants are read and the conclusion is yours.",
            "extra_help": "The determinants are the ones the model names. A determinant with no evidence is named and left empty; the worksheet derives no competitive verdict.",
        },
        "prefixes": {"factor_conditions": "FC", "demand_conditions": "DC", "related_industries": "RI",
                     "firm_strategy": "FS", "government": "GV", "chance": "CH"},
        "example": {
            "objective": "Read the conditions shaping the campus food industry",
            "blocks": {
                "factor_conditions": [{"text": "Vegetables are bought from a market a few hours from campus", "provenance": "synthetic"}],
                "demand_conditions": [{"text": "Most students eat on campus between classes", "provenance": "synthetic"}],
                "related_industries": [{"text": "A printing shop on the same street supplies menus and flyers", "provenance": "synthetic"}],
                "firm_strategy": [{"text": "Two counters compete on price and one competes on variety", "provenance": "synthetic"}],
            },
        },
    },
    "template_bcg": {
        "catalogue_id": "STR-10",
        "blocks": {
            "stars": ("Stars", "High growth, high market share - invest to grow"),
            "cash_cows": ("Cash Cows", "Low growth, high market share - harvest for cash"),
            "question_marks": ("Question Marks", "High growth, low market share - invest or divest"),
            "dogs": ("Dogs", "Low growth, low market share - divest or harvest"),
        },
        "meta": {
            "name": "BCG growth-share matrix with an evidence audit",
            "short": "BCG matrix",
            "intended_use": "Read the evidence that places each business unit in a quadrant, and audit the placement the growth or share estimate cannot support.",
            "unsupported_use": "Deciding what to invest in or divest, ranking the units, or computing a portfolio plan; the quadrants record a placement and the decision is yours.",
            "extra_help": "The quadrants are the ones the matrix names. A quadrant with no evidence is named and left empty; the worksheet computes no growth rate and no share.",
        },
        "prefixes": {"stars": "ST", "cash_cows": "CC", "question_marks": "QM", "dogs": "DG"},
        "example": {
            "objective": "Place the campus food lines on the growth-share matrix",
            "blocks": {
                "stars": [{"text": "The hot meal line grows with the student population and holds the largest share of campus meals", "provenance": "synthetic"}],
                "cash_cows": [{"text": "The drinks counter has a high share of campus spending and no growth", "provenance": "synthetic"}],
                "question_marks": [{"text": "Breakfast packs are growing but hold a small share", "provenance": "assumption"}],
            },
        },
    },
    "template_ge_mckinsey": {
        "catalogue_id": "STR-11",
        "blocks": {
            "high_high": ("High/High", "High industry attractiveness, high business strength - invest/grow"),
            "high_medium": ("High/Medium", "High industry attractiveness, medium business strength - invest/selectively"),
            "high_low": ("High/Low", "High industry attractiveness, low business strength - protect/selectively"),
            "medium_high": ("Medium/High", "Medium industry attractiveness, high business strength - invest/selectively"),
            "medium_medium": ("Medium/Medium", "Medium industry attractiveness, medium business strength - selectivity/earnings"),
            "medium_low": ("Medium/Low", "Medium industry attractiveness, low business strength - harvest/divest"),
            "low_high": ("Low/High", "Low industry attractiveness, high business strength - protect/earnings"),
            "low_medium": ("Low/Medium", "Low industry attractiveness, medium business strength - harvest/divest"),
            "low_low": ("Low/Low", "Low industry attractiveness, low business strength - divest/liquidate"),
        },
        "meta": {
            "name": "GE-McKinsey portfolio matrix with an evidence audit",
            "short": "GE-McKinsey matrix",
            "intended_use": "Read the scores and weights that place each business unit in a cell, and audit the cell the evidence cannot support.",
            "unsupported_use": "Fixing the criteria or the weights, deriving a portfolio plan, or recommending an allocation; the worksheet records your judgments and derives no plan.",
            "extra_help": "The nine cells are the ones the matrix names. A cell with no evidence is named and left empty; the worksheet computes no score and applies no weighting.",
        },
        "prefixes": {"high_high": "HH", "high_medium": "HM", "high_low": "HL", "medium_high": "MH",
                     "medium_medium": "MM", "medium_low": "ML", "low_high": "LH", "low_medium": "LM", "low_low": "LL"},
        "example": {
            "objective": "Place the campus food lines on the GE-McKinsey matrix",
            "blocks": {
                "high_high": [{"text": "The hot meal line sits in a growing segment and holds the strongest position", "provenance": "synthetic"}],
                "medium_medium": [{"text": "The drinks counter sits in a slow segment with a middling position", "provenance": "assumption"}],
            },
        },
    },
    "template_strategic_positioning": {
        "catalogue_id": "STR-19",
        "blocks": {
            "position": ("Position", "The place you want to occupy in the market"),
            "differentiation": ("Differentiation", "The difference the position rests on"),
            "value_proposition": ("Value Proposition", "The value you promise the segment"),
            "target_segment": ("Target Segment", "The segment the position is aimed at"),
        },
        "meta": {
            "name": "Strategic positioning with an evidence audit",
            "short": "strategic positioning",
            "intended_use": "Read one positioning claim from its four sides and audit the side the evidence cannot settle.",
            "unsupported_use": "Choosing the segment or the position, scoring the fit, or deciding whether the claim holds; the claim is read and the choice is yours.",
            "extra_help": "The four elements are the ones the review names. An element with no evidence is named and left empty; the worksheet derives no verdict on the position.",
        },
        "prefixes": {"position": "PO", "differentiation": "DF", "value_proposition": "VP", "target_segment": "TS"},
        "example": {
            "objective": "Read the positioning claim of the campus meal service",
            "blocks": {
                "position": [{"text": "The fastest student-priced hot meal on campus", "provenance": "synthetic"}],
                "differentiation": [{"text": "Meals are ready within ten minutes because they are cooked in advance", "provenance": "synthetic"}],
                "value_proposition": [{"text": "A hot meal you can eat between classes without leaving the gate", "provenance": "synthetic"}],
                "target_segment": [{"text": "Students with a short break between classes", "provenance": "synthetic"}],
            },
        },
    },
    "template_strategy_4": {
        "catalogue_id": "STR-20",
        "blocks": {
            "perspective": ("Perspective", "The beliefs about the world the strategy rests on"),
            "position": ("Position", "The place the strategy claims in the market"),
            "plan": ("Plan", "The coordinated choices that deliver the position"),
            "pattern": ("Pattern", "The behaviour the plan has to produce in practice"),
        },
        "meta": {
            "name": "Strategy framework with an evidence audit",
            "short": "strategy framework",
            "intended_use": "Read one strategy from its perspective, position, plan and pattern, and audit the element the evidence cannot settle.",
            "unsupported_use": "Writing the strategy, choosing the position, or scoring how coherent it is; the elements are read and the strategy is yours.",
            "extra_help": "The four elements are the ones the framework names. An element with no evidence is named and left empty; the worksheet derives no coherence score.",
        },
        "prefixes": {"perspective": "PE", "position": "PO", "plan": "PL", "pattern": "PA"},
        "example": {
            "objective": "Read the strategy of the campus meal service",
            "blocks": {
                "perspective": [{"text": "Students will pay more for a meal they can eat without waiting in a queue", "provenance": "assumption"}],
                "position": [{"text": "The fastest student-priced hot meal on campus", "provenance": "synthetic"}],
                "plan": [{"text": "Cook in advance, sell at one counter beside the gate and keep the menu fixed", "provenance": "synthetic"}],
                "pattern": [{"text": "The kitchen, the counter and the supplier all work to the same fixed menu", "provenance": "synthetic"}],
            },
        },
    },
    # ------------------------------------------------------------- marketing
    "template_stp": {
        "catalogue_id": "MKT-01",
        "blocks": {
            "segmentation": ("Segmentation", "How the market is divided"),
            "targeting": ("Targeting", "Which segments you choose and why"),
            "positioning": ("Positioning", "The place you want to occupy in the customer's mind"),
        },
        "meta": {
            "name": "Segmentation, targeting and positioning with an evidence audit",
            "short": "STP",
            "intended_use": "Lay the segmentation, the target choice and the positioning claim side by side for one market and audit the decision the evidence cannot settle.",
            "unsupported_use": "Choosing a segment for you, inventing customers or competitors, or scoring the fit; the three decisions are yours and the evidence is what you supply.",
            "extra_help": "The three elements are the ones STP names. An element with no evidence is named and left empty; the worksheet computes no market size and derives no position.",
        },
        "prefixes": {"segmentation": "SG", "targeting": "TG", "positioning": "PO"},
        "example": {
            "objective": "Lay out the STP decisions for the campus meal market",
            "blocks": {
                "segmentation": [{"text": "Students are divided by the length of the break between their classes", "provenance": "synthetic"}],
                "targeting": [{"text": "First- and second-year students with a short midday break", "provenance": "synthetic"}],
                "positioning": [{"text": "The fastest student-priced hot meal beside the gate", "provenance": "synthetic"}],
            },
        },
    },
    "template_stp_evidence": {
        "catalogue_id": "MKT-12",
        "blocks": {
            "segmentation_evidence": ("Segmentation Evidence", "Evidence for the segmentation"),
            "targeting_evidence": ("Targeting Evidence", "Evidence for the targeting"),
            "positioning_evidence": ("Positioning Evidence", "Evidence for the positioning"),
        },
        "meta": {
            "name": "STP evidence-to-action check with an evidence audit",
            "short": "STP evidence check",
            "intended_use": "Audit each STP claim against the research behind it and name the claim that rests on nothing.",
            "unsupported_use": "Filling a gap with general background, scoring the evidence, or dropping a claim for you; the check names what is missing and the action is yours.",
            "extra_help": "This is a quality layer on an STP decision, not a second STP. Each claim is read against the research that supports it; the worksheet derives no option.",
        },
        "prefixes": {"segmentation_evidence": "SE", "targeting_evidence": "TE", "positioning_evidence": "PE"},
        "example": {
            "objective": "Audit the evidence behind the STP decisions for the campus meal market",
            "blocks": {
                "segmentation_evidence": [{"text": "Break lengths were taken from the published timetable", "provenance": "synthetic"}],
                "targeting_evidence": [{"text": "The chosen segment has not been surveyed for how often it eats on campus", "provenance": "assumption"}],
                "positioning_evidence": [{"text": "A count of the wait at the two counters was kept for a week", "provenance": "synthetic"}],
            },
        },
    },
    "template_aida": {
        "catalogue_id": "MKT-03",
        "blocks": {
            "attention": ("Attention", "How the audience first notices the offer"),
            "interest": ("Interest", "What keeps the audience reading"),
            "desire": ("Desire", "What makes the audience want the offer"),
            "action": ("Action", "What the audience is asked to do"),
        },
        "meta": {
            "name": "AIDA journey with an evidence audit",
            "short": "AIDA journey",
            "intended_use": "Read the evidence at each stage of one communication journey and audit the stage the evidence cannot settle.",
            "unsupported_use": "Treating the journey as a rule, filling a stage, or deciding what to spend next; the stages are a simplified lens and the evidence is yours.",
            "extra_help": "The four stages are the ones AIDA names. A stage with no evidence is named and left empty; the worksheet computes no conversion rate.",
        },
        "prefixes": {"attention": "AT", "interest": "IN", "desire": "DE", "action": "AC"},
        "example": {
            "objective": "Read the communication journey for the campus meal service",
            "blocks": {
                "attention": [{"text": "A poster in the corridor where class groups wait", "provenance": "synthetic"}],
                "interest": [{"text": "The opening offer was posted in the class chat of the subject with the longest queue", "provenance": "synthetic"}],
                "desire": [{"text": "The price of the first meal card is lower than the walk-up price", "provenance": "synthetic"}],
                "action": [{"text": "The meal card can be bought at the counter without a queue", "provenance": "synthetic"}],
            },
        },
    },
    "template_funnel": {
        "catalogue_id": "MKT-05",
        "blocks": {
            "awareness": ("Awareness", "How customers first learn about the offer"),
            "interest": ("Interest", "How customers evaluate the offer"),
            "consideration": ("Consideration", "What customers weigh before they buy"),
            "intent": ("Intent", "What makes a customer ready to buy"),
            "evaluation": ("Evaluation", "How customers judge the offer against the alternatives"),
            "purchase": ("Purchase", "How customers buy the offer"),
        },
        "meta": {
            "name": "Marketing funnel with an evidence audit",
            "short": "marketing funnel",
            "intended_use": "Read the stage definitions and the evidence at each stage of one funnel, and audit the stage with the largest unexplained drop.",
            "unsupported_use": "Setting the stage definitions for you, inventing conversion rates, or recommending where to spend; the stages and the rates are yours.",
            "extra_help": "The stages are the ones the funnel names. A stage with no evidence is named and left empty; the worksheet computes no conversion rate and derives no leak.",
        },
        "prefixes": {"awareness": "AW", "interest": "IN", "consideration": "CO", "intent": "IT",
                     "evaluation": "EV", "purchase": "PU"},
        "example": {
            "objective": "Read the funnel for the campus meal service",
            "blocks": {
                "awareness": [{"text": "Posters in the corridor and a mention in the class chat", "provenance": "synthetic"}],
                "interest": [{"text": "A sample plate is shown at the counter during the first week", "provenance": "synthetic"}],
                "consideration": [{"text": "The menu is posted at the counter and on the class page", "provenance": "synthetic"}],
                "purchase": [{"text": "Most students pay cash at the counter rather than buying a meal card", "provenance": "assumption"}],
            },
        },
    },
    "template_rfm": {
        "catalogue_id": "MKT-08",
        "blocks": {
            "recency": ("Recency", "How recently the customer bought"),
            "frequency": ("Frequency", "How often the customer buys"),
            "monetary": ("Monetary", "How much the customer spends"),
        },
        "meta": {
            "name": "RFM segmentation with an evidence audit",
            "short": "RFM segmentation",
            "intended_use": "Read the window, the scoring method and the evidence behind each RFM dimension for one customer list.",
            "unsupported_use": "Setting the window or the scoring bands, inventing customer data, or deriving lifetime value; the grouping is yours and the worksheet computes no segment.",
            "extra_help": "The three dimensions are the ones RFM names. A dimension with no evidence is named and left empty; the worksheet scores nothing and derives no segment.",
        },
        "prefixes": {"recency": "RE", "frequency": "FR", "monetary": "MO"},
        "example": {
            "objective": "Read the RFM grouping of the campus meal customers",
            "blocks": {
                "recency": [{"text": "Recency is measured from the last meal card top-up in the register", "provenance": "synthetic"}],
                "frequency": [{"text": "Frequency is the number of meals bought in the term", "provenance": "synthetic"}],
                "monetary": [{"text": "The window is a term, and students who left are not in the list", "provenance": "assumption"}],
            },
        },
    },
    "template_tam": {
        "catalogue_id": "MKT-09",
        "blocks": {
            "perceived_usefulness": ("Perceived Usefulness", "What the user expects the system to help them do"),
            "perceived_ease_of_use": ("Perceived Ease of Use", "How easy the user expects the system to be"),
            "attitude": ("Attitude", "How the user feels about using the system"),
            "behavioral_intention": ("Behavioural Intention", "How far the user intends to use the system"),
        },
        "meta": {
            "name": "Technology Acceptance Model with an evidence audit",
            "short": "acceptance model",
            "intended_use": "Read the evidence behind the constructs of one acceptance model for the users of a system, and audit the construct the evidence cannot settle.",
            "unsupported_use": "Administering a survey, treating the constructs as a checklist for any adoption problem, or claiming the model predicts use; the evidence is yours.",
            "extra_help": "The constructs are the ones the model names. A construct with no evidence is named and left empty; the worksheet computes no scale and derives no intention.",
        },
        "prefixes": {"perceived_usefulness": "PU", "perceived_ease_of_use": "PE", "attitude": "AT",
                     "behavioral_intention": "BI"},
        "example": {
            "objective": "Read the acceptance evidence for the meal card ordering system",
            "blocks": {
                "perceived_usefulness": [{"text": "Students were asked whether pre-ordering saves their break", "provenance": "synthetic"}],
                "perceived_ease_of_use": [{"text": "No question asked whether ordering by phone is easy", "provenance": "assumption"}],
                "attitude": [{"text": "The survey closed before the attitude questions were asked", "provenance": "assumption"}],
            },
        },
    },
    "template_utaut": {
        "catalogue_id": "MKT-10",
        "blocks": {
            "performance_expectancy": ("Performance Expectancy", "What the user expects the system to make easier"),
            "effort_expectancy": ("Effort Expectancy", "How easy the user expects the system to be to use"),
            "social_influence": ("Social Influence", "What the user thinks others expect them to do"),
            "facilitating_conditions": ("Facilitating Conditions", "What makes use possible in practice"),
        },
        "meta": {
            "name": "UTAUT with an evidence audit",
            "short": "UTAUT",
            "intended_use": "Read the evidence behind the constructs of one adoption model for the users of a system, and audit the construct the evidence cannot settle.",
            "unsupported_use": "Administering a survey, treating the constructs as a checklist for any adoption problem, or claiming the model predicts use; the evidence is yours.",
            "extra_help": "The constructs are the ones the model names. A construct with no evidence is named and left empty; the worksheet computes no scale and derives no intention.",
        },
        "prefixes": {"performance_expectancy": "PE", "effort_expectancy": "EE", "social_influence": "SI",
                     "facilitating_conditions": "FC"},
        "example": {
            "objective": "Read the adoption evidence for the meal card ordering system",
            "blocks": {
                "performance_expectancy": [{"text": "Students were asked whether pre-ordering saves their break", "provenance": "synthetic"}],
                "effort_expectancy": [{"text": "No question asked whether ordering by phone is easy", "provenance": "assumption"}],
                "facilitating_conditions": [{"text": "The counter has one phone that staff cannot leave unattended", "provenance": "synthetic"}],
            },
        },
    },
    "template_brand_equity": {
        "catalogue_id": "MKT-11",
        "blocks": {
            "awareness": ("Awareness", "What customers know about the brand"),
            "associations": ("Associations", "What customers attach to the brand"),
            "perceived_quality": ("Perceived Quality", "How customers judge the brand's performance"),
            "loyalty": ("Loyalty", "What keeps customers with the brand"),
        },
        "meta": {
            "name": "Brand equity assessment with an evidence audit",
            "short": "brand equity",
            "intended_use": "Read the evidence behind the selected dimensions of one brand and audit the dimension the evidence cannot settle.",
            "unsupported_use": "Mixing variants of brand equity, inventing customer research, or scoring the brand; the measurement and the model are yours to name.",
            "extra_help": "The dimensions are the ones the selected model names. A dimension with no evidence is named and left empty; the worksheet computes no index.",
        },
        "prefixes": {"awareness": "AW", "associations": "AS", "perceived_quality": "PQ", "loyalty": "LY"},
        "example": {
            "objective": "Read the brand equity of the campus meal service",
            "blocks": {
                "awareness": [{"text": "A short survey asked students whether they had heard of the counter", "provenance": "synthetic"}],
                "associations": [{"text": "The same survey asked what students associate the counter with", "provenance": "synthetic"}],
                "perceived_quality": [{"text": "Perceived quality was not asked in the survey", "provenance": "assumption"}],
            },
        },
    },
    "template_digital_mix": {
        "catalogue_id": "MKT-13",
        "blocks": {
            "owned": ("Owned", "The channels you control"),
            "earned": ("Earned", "The channels others create for you"),
            "paid": ("Paid", "The channels you pay for"),
        },
        "meta": {
            "name": "Digital marketing mix with an evidence audit",
            "short": "digital mix",
            "intended_use": "Record the role, the objective and the evidence for each kind of digital channel in one market, and audit the channel the evidence cannot settle.",
            "unsupported_use": "Allocating a budget, predicting reach, or choosing which channel to use; the roles and the amounts are yours and the worksheet allocates nothing.",
            "extra_help": "The three kinds of channel are the ones the mix names. A channel with no evidence is named and left empty; the worksheet computes no spend and derives no reach.",
        },
        "prefixes": {"owned": "OW", "earned": "EA", "paid": "PD"},
        "example": {
            "objective": "Record the digital channel mix for the campus meal service",
            "blocks": {
                "owned": [{"text": "The class group and the counter page, both posted by the counter team", "provenance": "synthetic"}],
                "earned": [{"text": "A student food blog mentioned the counter once", "provenance": "synthetic"}],
                "paid": [{"text": "No paid channel has been used", "provenance": "assumption"}],
            },
        },
    },
    "template_seo_content": {
        "catalogue_id": "MKT-14",
        "blocks": {
            "keywords": ("Keywords", "The questions and terms the audience searches for"),
            "content": ("Content", "The page or post that answers the question"),
            "technical": ("Technical", "The state of the page that carries the answer"),
            "links": ("Links", "The other pages that point at it"),
        },
        "meta": {
            "name": "SEO and content plan with an evidence audit",
            "short": "SEO and content plan",
            "intended_use": "Read the search demand, the page, the technical base and the links for one content plan, and audit the part the evidence cannot settle.",
            "unsupported_use": "Predicting traffic or a ranking, choosing the keywords for you, or writing the content; the demand and the pages are yours and the worksheet forecasts nothing.",
            "extra_help": "The four parts are the ones the plan names. A part with no evidence is named and left empty; the worksheet computes no search volume and derives no position.",
        },
        "prefixes": {"keywords": "KW", "content": "CN", "technical": "TC", "links": "LK"},
        "example": {
            "objective": "Record the search and content plan for the campus meal service",
            "blocks": {
                "keywords": [{"text": "Students search for cheap meals near campus during a short break", "provenance": "synthetic"}],
                "content": [{"text": "A page listing the meal times and the fixed price", "provenance": "synthetic"}],
                "technical": [{"text": "The page loads slowly on a phone", "provenance": "assumption"}],
            },
        },
    },
    "template_email_crm": {
        "catalogue_id": "MKT-16",
        "blocks": {
            "list": ("List", "How the list grew and how consent was recorded"),
            "segments": ("Segments", "How the list is divided"),
            "campaigns": ("Campaigns", "What was sent and when"),
            "automation": ("Automation", "What the system sends on its own"),
        },
        "meta": {
            "name": "Email, CRM and lifecycle marketing with an evidence audit",
            "short": "email and CRM plan",
            "intended_use": "Record the list, the segments, the campaigns and the automation for one lifecycle programme, and audit the element the evidence cannot settle.",
            "unsupported_use": "Computing open or click rates, inventing consent, or claiming revenue from a send; the records are yours and the worksheet derives no figure.",
            "extra_help": "The four elements are the ones the programme names. An element with no evidence is named and left empty; the worksheet counts nothing and derives no engagement rate.",
        },
        "prefixes": {"list": "LI", "segments": "SG", "campaigns": "CA", "automation": "AU"},
        "example": {
            "objective": "Record the lifecycle programme for the campus meal service",
            "blocks": {
                "list": [{"text": "Students sign up at the counter and the list is kept in a spreadsheet", "provenance": "synthetic"}],
                "segments": [{"text": "Students are split by whether they have bought a meal card", "provenance": "synthetic"}],
                "campaigns": [{"text": "A welcome email goes out when a student signs up", "provenance": "synthetic"}],
                "automation": [{"text": "Nothing is sent automatically and no reminder is set", "provenance": "assumption"}],
            },
        },
    },
    "template_social_media": {
        "catalogue_id": "MKT-17",
        "blocks": {
            "platforms": ("Platforms", "Where the audience is reached"),
            "content": ("Content", "What is posted and how often"),
            "engagement": ("Engagement", "How the audience responds and what is measured"),
            "influencers": ("Influencers", "Who is paid or partnered with, on what terms"),
        },
        "meta": {
            "name": "Social media and influencer marketing with an evidence audit",
            "short": "social and influencer plan",
            "intended_use": "Record the platforms, the content, the engagement measures and the creator terms for one plan, and audit the part the evidence cannot settle.",
            "unsupported_use": "Computing engagement rates, inventing creator terms, or recommending a platform; the plan and the terms are yours and the worksheet derives no figure.",
            "extra_help": "The four parts are the ones the plan names. A part with no evidence is named and left empty; the worksheet computes no reach and derives no rate.",
        },
        "prefixes": {"platforms": "PF", "content": "CN", "engagement": "EN", "influencers": "IN"},
        "example": {
            "objective": "Record the social and influencer plan for the campus meal service",
            "blocks": {
                "platforms": [{"text": "The counter posts in the campus student group", "provenance": "synthetic"}],
                "content": [{"text": "A daily post of the day's menu", "provenance": "synthetic"}],
                "engagement": [{"text": "Reach is read by eye from the group and is not recorded", "provenance": "assumption"}],
                "influencers": [{"text": "One student creator posts once in return for a free meal card", "provenance": "synthetic"}],
            },
        },
    },
    "template_attribution": {
        "catalogue_id": "MKT-19",
        "blocks": {
            "touchpoints": ("Touchpoints", "The points at which a customer meets the campaign"),
            "model": ("Model", "The rule that decides which touchpoint gets the credit"),
            "credit": ("Credit", "The share each touchpoint was given"),
            "reporting": ("Reporting", "Where the credit is used and what it is compared against"),
        },
        "meta": {
            "name": "Attribution and campaign measurement with an evidence audit",
            "short": "attribution",
            "intended_use": "Record the touchpoints, the attribution rule and the credit it gives for one campaign, and audit the part the evidence cannot settle.",
            "unsupported_use": "Claiming what the campaign caused, choosing the model for you, or deriving a budget split; the rule is yours and no causal claim follows from it.",
            "extra_help": "The four parts are the ones the measurement frame names. A part with no evidence is named and left empty; the worksheet computes no share and derives no effect.",
        },
        "prefixes": {"touchpoints": "TP", "model": "MD", "credit": "CR", "reporting": "RP"},
        "example": {
            "objective": "Record how credit is given for the campus meal campaign",
            "blocks": {
                "touchpoints": [{"text": "The corridor poster, the class chat and the counter are the three recorded touchpoints", "provenance": "synthetic"}],
                "model": [{"text": "The last recorded touchpoint before a meal card is bought gets the credit", "provenance": "synthetic"}],
                "credit": [{"text": "The counter is credited for most of the new meal cards", "provenance": "assumption"}],
            },
        },
    },
    "template_cro": {
        "catalogue_id": "MKT-20",
        "blocks": {
            "hypothesis": ("Hypothesis", "What you believe will change and why"),
            "variants": ("Variants", "The versions of the page or step that are compared"),
            "metrics": ("Metrics", "What is counted and over what window"),
            "results": ("Results", "What the test produced"),
        },
        "meta": {
            "name": "Conversion-rate optimisation with an evidence audit",
            "short": "conversion test",
            "intended_use": "Record the hypothesis, the variants, the measures and the result of one conversion test, and audit the part the evidence cannot settle.",
            "unsupported_use": "Computing significance, recommending a winning variant, or reading a causal effect from a split; the test is yours and the worksheet derives no verdict.",
            "extra_help": "The four parts are the ones the test names. A part with no evidence is named and left empty; the worksheet computes no test and derives no winner.",
        },
        "prefixes": {"hypothesis": "HY", "variants": "VA", "metrics": "ME", "results": "RS"},
        "example": {
            "objective": "Record the first conversion test on the campus meal page",
            "blocks": {
                "hypothesis": [{"text": "Putting the price before the menu will raise the number of meal cards bought", "provenance": "synthetic"}],
                "variants": [{"text": "The menu first and the price first are the two versions", "provenance": "synthetic"}],
                "metrics": [{"text": "Meal cards bought per visitor over one week", "provenance": "synthetic"}],
                "results": [{"text": "The test has not run yet", "provenance": "assumption"}],
            },
        },
    },
    "template_marketing_automation": {
        "catalogue_id": "MKT-21",
        "blocks": {
            "triggers": ("Triggers", "The events that start a rule"),
            "flows": ("Flows", "The steps a lead moves through"),
            "scoring": ("Scoring", "The score that qualifies a lead"),
            "nurture": ("Nurture", "What the lead receives while it is being worked"),
        },
        "meta": {
            "name": "Marketing automation and lead scoring with an evidence audit",
            "short": "marketing automation",
            "intended_use": "Record the triggers, the flows, the score and the nurture for one automation set, and audit the element the evidence cannot settle.",
            "unsupported_use": "Validating a score, inventing lead data, or deriving revenue from a flow; the rules are yours and the worksheet derives no figure.",
            "extra_help": "The four elements are the ones the automation set names. An element with no evidence is named and left empty; the worksheet scores nothing and derives no revenue.",
        },
        "prefixes": {"triggers": "TR", "flows": "FL", "scoring": "SC", "nurture": "NU"},
        "example": {
            "objective": "Record the automation behind the campus meal enquiry",
            "blocks": {
                "triggers": [{"text": "A form on the counter page starts the sequence", "provenance": "synthetic"}],
                "flows": [{"text": "Enquiry, sample offered, meal card sold", "provenance": "synthetic"}],
                "scoring": [{"text": "The score counts form visits and has never been checked against sales", "provenance": "assumption"}],
                "nurture": [{"text": "One email a week for a month, then the contact is left alone", "provenance": "synthetic"}],
            },
        },
    },
}
