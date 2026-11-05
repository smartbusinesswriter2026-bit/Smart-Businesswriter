"""Minimal JSON API + static shell (stdlib only; FastAPI can replace this later behind the same routes)."""
import base64, copy, json, os, re, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from decimal import Decimal
from .session import SessionManager
from urllib.parse import urlparse, parse_qs, quote
import uuid
from . import methods, registry, templates, assist, llm, literature, accounts, ingest, currency
from . import finance_methods  # registers additional computation methods into methods.LIBRARY
from .product import api as product_api, ops as product_ops, intake as product_intake, sources_file as product_sources, session_paper as product_session_paper, marketdata as product_marketdata, portfolios as product_portfolios, portfolio_docx as product_portfolio_docx, instruments as product_instruments
from .product import framework_profiles as product_profiles
product_api.attach_compute(lambda inputs: methods.breakeven(inputs))


def _plan_method(method_id, inputs):
    """Validate and run one frozen method for a business-plan block."""
    method = methods.LIBRARY[method_id]
    errors = methods.validate_inputs(method, inputs)
    if errors:
        raise ValueError("; ".join(errors))
    return method.impl(inputs)


product_api.attach_methods(_plan_method, methods.describe)
from .product import statements as product_statements, statements_council as product_statement_council
from . import statement_extract, statement_plan, schedule_math


def _statement_reader(text):
    """Read a statement instruction with the model council, or say plainly that none is configured."""
    if not product_statement_council.available():
        raise product_statement_council.CouncilError(
            "no model is configured (set BP_OPENGO_API_KEY), so only a trial balance can be read")
    return product_statement_council.read(text)


_statement_model_tier = 1


def _statement_models(tier=None):
    """A model for journal extraction, or None when none is configured.

    tier: 1=standard, 2=retry, 3=escalation. Controls which model is used.
    """
    global _statement_model_tier
    t = tier if tier is not None else _statement_model_tier
    models = llm.from_env()
    if models is not None:
        return models
    if os.environ.get("DEEPSEEK_API_KEY"):
        if t >= 2:
            try:
                return llm.Models(llm.DeepSeekProvider("deepseek-reasoner"),
                                  config=llm.LLMConfig(enabled=True, max_output_tokens=4096))
            except Exception:
                pass
        return llm.Models(llm.DeepSeekProvider("deepseek-chat"),
                          config=llm.LLMConfig(enabled=True, max_output_tokens=4096))
    return None


def set_statement_model_tier(tier):
    global _statement_model_tier
    _statement_model_tier = tier


def _statement_extract(text, period):
    """Structure a narrative into a grounded journal, or say plainly why no model is configured.

    The plan layer lives here, beside the core it compiles into, so the product package never
    imports it (`tests/test_product_boundary.py`).  The model is asked for language only; every
    derived figure is computed later by the adjustment DAG.
    """
    models = _statement_models()
    if models is None:
        raise product_statements.NoModel(
            "no model is configured, so only a trial balance can be read. "
            "Set DEEPSEEK_API_KEY (or BP_LLM_PROVIDER + BP_LLM_MODEL).")
    return statement_extract.extract(text, statement_plan.DEFAULT_CHART, models, consent=True,
                                     period=period, default_date=period["end"])


def _statement_build(plan):
    """Compile a journal into the full ledger, with the articulation gate."""
    plan = dict(plan)
    plan.setdefault("chart", statement_plan.DEFAULT_CHART)
    return statement_plan.build(plan)


# The statements tile reaches the core through these callables, so the product package never imports
# the frozen core (tests/test_product_boundary.py).  The reader is the model council; the tile's own
# parser runs first and is exact on a trial balance, whatever the reader says.
product_statements.attach_core(
    solve=lambda spec: methods.LIBRARY["management_accounts"].impl({"spec": spec}),
    diagnose=lambda rows, places: methods.LIBRARY["trial_balance_check"].impl(
        {"journal": None, "trial_balance": rows, "places": places}),
    ratio_analysis=lambda figures: methods.LIBRARY["ratio_analysis"].impl(figures),
    dupont=lambda inputs: methods.LIBRARY["dupont_analysis"].impl(inputs),
    reader=_statement_reader,
    extract=_statement_extract,
    build=_statement_build,
    set_tier=set_statement_model_tier,
    schedules=schedule_math.compute,
)
from .sandbox import SubprocessSandbox

ASSIST_RUNS = {}
M = SessionManager(assist_runs=ASSIST_RUNS)
MODELS = None            # llm.Models or None (model assistance off)
SANDBOX_ENABLED = True   # set by serve(); reported by /api/health
LITERATURE_SOURCES = {"crossref": literature.CrossrefSource(), "openalex": literature.OpenAlexSource()}
LITERATURE_AUTO = ("crossref", "openalex")   # declared priority order (B-064): Crossref first, OpenAlex fallback
LITERATURE_LABELS = {"crossref": "Crossref", "openalex": "OpenAlex", "auto": "Auto (Crossref, then OpenAlex)"}
LITERATURE_CALLS = 0
LITERATURE_CAP = 100     # per server run; the public APIs are free, but this stops a runaway loop
LITERATURE_LOG = os.environ.get("BP_RETRIEVAL_LOG") or "retrieval_log.jsonl"   # durable retrieval audit; "" disables it
LITERATURE_NOTICE = ("The title and DOI you enter are sent to the selected public bibliographic API (Crossref or OpenAlex) "
                     "to look the reference up. No case text is sent. A citation is marked verified only when the DOI resolves "
                     "and the title matches exactly. Every resolved retrieval is recorded in the local retrieval log (source, "
                     "UTC time, SHA-256 of the response bytes) so a citation can be re-checked later.")
WEB = os.path.join(os.path.dirname(__file__), "..", "..", "web")
MAXBODY = 100_000
INGEST_MAXBODY = 7_500_000   # base64 of the 5 MB ingestion limit, plus JSON overhead
PRESETS = {
    "npv": {"objective": "Should we invest in this project?", "method": "npv", "currency": "USD", "period": "annual",
           "inputs": {"rate": "0.10", "cashflows": ["-1000", "400", "400", "400"]}, "sensitivity": {"rate": ["0.05", "0.25"]}},
    "irr": {"objective": "What rate of return does the project earn?", "method": "irr", "period": "annual",
            "inputs": {"cashflows": ["-1000", "400", "400", "400", "400"]}},
    "dpayback": {"objective": "How long until the discounted cash flows repay the investment?", "method": "discounted_payback", "currency": "USD", "period": "annual",
                 "inputs": {"cashflows": ["-1000", "400", "400", "400", "400"], "rate": "0.10"}},
    "breakeven": {"objective": "How many units must we sell to break even?", "method": "breakeven", "period": "annual",
                  "inputs": {"fixed": "1000", "price": "20", "variable": "10"}},
    "marketsize": {"objective": "How big is the market we can actually serve and win?", "method": "market_sizing", "currency": "USD", "period": "annual",
                   "inputs": {"target_population": "20000", "annual_spend_per_customer": "3000", "serviceable_share": "0.25", "obtainable_share": "0.20"}},
    "startupcapital": {"objective": "How much capital must we raise to open the business?", "method": "startup_capital", "currency": "USD", "period": "annual",
                       "inputs": {"start_up_costs": "350000", "working_capital": "120000", "contingency_rate": "0.10",
                                  "owner_equity": "150000", "loan_amount": "200000"}},
    "cashrunway": {"objective": "How many months of cash do we have, and how much must we raise?", "method": "cash_runway", "currency": "USD", "period": "monthly",
                   "inputs": {"opening_cash": "300000", "monthly_net_cash_flow": "-40000", "monthly_growth": "0", "target_months": "9"}},
    "pricing": {"objective": "What price should we set under each pricing rule?", "method": "pricing_decision", "currency": "USD", "period": "annual",
                "inputs": {"unit_cost": "15", "fixed_cost": "45000", "expected_units": "6000", "markup_rate": "0.60",
                           "target_margin_rate": "0.375", "target_profit": "20000"}},
    "roi": {"objective": "What is the return on the money we invested?", "method": "return_on_investment", "currency": "USD", "period": "annual",
            "inputs": {"total_investment": "500000", "net_gain": "125000", "years": "3"}},
    "salesprojection": {"objective": "Project our sales, costs and profit for the next twelve months", "method": "sales_projection", "currency": "USD", "period": "monthly",
                        "inputs": {"start_units": "300", "price": "120", "unit_variable_cost": "55", "fixed_cost_per_period": "12000",
                                   "growth_rate": "0.05", "periods": "12"}},
    "captable": {"objective": "What share does the investor get in this round?", "method": "cap_table_round", "currency": "USD", "period": "point in time",
                 "inputs": {"pre_money_valuation": "4000000", "investment": "1000000", "founders_shares": "1000000", "option_pool_pct": "0.10"}},
    "funnel": {"objective": "Where do we lose customers between the first contact and the sale?", "method": "sales_funnel", "currency": "USD", "period": "monthly",
               "inputs": {"stages": [{"name": "store visits", "count": "10000"}, {"name": "inquiries", "count": "2500"}, {"name": "purchases", "count": "500"}],
                          "spend": "25000"}},
    "cohort": {"objective": "How well do we keep the customers we win each month?", "method": "cohort_retention", "currency": "USD", "period": "monthly",
               "inputs": {"cohort_sizes": ["200", "180", "150"],
                          "retained": [["200", "140", "110", "90"], ["180", "130", "100", "60"], ["150", "120", "95", "70"]]}},
    "demandcurve": {"objective": "What do our price and quantity observations imply about demand?", "method": "demand_curve", "currency": "USD", "period": "per observation",
                    "inputs": {"prices": ["20", "25", "30", "35", "40"], "quantities": ["400", "340", "280", "220", "160"]}},
    "purchaseintent": {"objective": "What share of the market intends to buy, and how many buyers is that?", "method": "purchase_intent", "currency": "USD", "period": "cross_section",
                       "inputs": {"definitely": "120", "probably": "80", "maybe": "150", "never": "50", "target_population": "20000", "price": "250"}},
    "campaign": {"objective": "Which campaign paid for itself after the cost of the sale?", "method": "campaign_efficiency", "currency": "USD", "period": "monthly",
                 "inputs": {"impressions": "250000", "clicks": "6000", "conversions": "220", "spend": "60000",
                            "revenue": "150000", "contribution_margin_rate": "0.45"}},
    "abtest": {"objective": "Did the new page really convert better than the old one?", "method": "ab_test_two_proportion", "period": "per observation",
               "inputs": {"visitors_a": "4000", "conversions_a": "320", "visitors_b": "4000", "conversions_b": "380",
                          "alpha": "0.05", "power": "0.8", "minimum_effect": "0.10"}},
    "attribution": {"objective": "How much credit does each channel get under different attribution rules?", "method": "attribution_split", "currency": "USD", "period": "monthly",
                    "inputs": {"channels": [{"name": "search", "first_click": "420", "last_click": "260", "linear": "320"},
                                            {"name": "social", "first_click": "180", "last_click": "310", "linear": "290"},
                                            {"name": "email", "first_click": "120", "last_click": "150", "linear": "110"}]}},
    "channelecon": {"objective": "Which acquisition channel is worth the money we spend on it?", "method": "channel_economics", "currency": "USD", "period": "monthly",
                    "inputs": {"channels": [{"name": "search", "spend": "60000", "new_customers": "400", "contribution_margin": "150", "churn_rate": "0.04"},
                                            {"name": "social", "spend": "35000", "new_customers": "180", "contribution_margin": "95", "churn_rate": "0.06"},
                                            {"name": "referral", "spend": "15000", "new_customers": "150", "contribution_margin": "150", "churn_rate": "0.03"}]}},
    "email": {"objective": "Is our email list growing and is it still engaged?", "method": "email_list_health", "currency": "USD", "period": "monthly",
              "inputs": {"list_start": "8000", "new_subscribers": "600", "unsubscribes": "90", "bounces": "40",
                         "sends": "7500", "opens": "2250", "clicks": "450", "revenue": "38000"}},
    "social": {"objective": "How far did our posts reach, and how engaged was the audience?", "method": "social_engagement", "currency": "USD", "period": "monthly",
               "inputs": {"impressions": "150000", "reach": "95000", "engagements": "5700", "followers_start": "18000",
                          "followers_gained": "900", "spend": "25000", "posts": "15"}},
    "web": {"objective": "Which traffic channel brings visits that turn into revenue?", "method": "web_analytics", "currency": "USD", "period": "monthly",
            "inputs": {"channels": [{"name": "organic search", "sessions": "42000", "conversions": "1350", "revenue": "680000"},
                                    {"name": "paid search", "sessions": "24000", "conversions": "960", "revenue": "430000"},
                                    {"name": "email", "sessions": "9000", "conversions": "540", "revenue": "260000"}],
                       "organic_impressions": "600000", "organic_clicks": "24000"}},
    "rfm": {"objective": "Which customer segments do we have, and how big is each?", "method": "rfm_scoring", "period": "point in time",
            "inputs": {"customers": [{"name": "C01", "recency_days": "3", "frequency": "9", "monetary": "15000"},
                                     {"name": "C02", "recency_days": "8", "frequency": "7", "monetary": "12000"},
                                     {"name": "C03", "recency_days": "15", "frequency": "6", "monetary": "9000"},
                                     {"name": "C04", "recency_days": "25", "frequency": "5", "monetary": "7000"},
                                     {"name": "C05", "recency_days": "40", "frequency": "4", "monetary": "5000"},
                                     {"name": "C06", "recency_days": "55", "frequency": "3", "monetary": "3500"},
                                     {"name": "C07", "recency_days": "70", "frequency": "2", "monetary": "2000"},
                                     {"name": "C08", "recency_days": "90", "frequency": "1", "monetary": "900"},
                                     {"name": "C09", "recency_days": "120", "frequency": "1", "monetary": "400"},
                                     {"name": "C10", "recency_days": "160", "frequency": "1", "monetary": "100"},
                                     {"name": "C11", "recency_days": "12", "frequency": "5", "monetary": "8000"},
                                     {"name": "C12", "recency_days": "200", "frequency": "2", "monetary": "1500"}]}},
    "mediaplan": {"objective": "What does this media plan buy in reach, frequency and rating points?", "method": "media_plan", "currency": "USD", "period": "monthly",
                  "inputs": {"population": "1000000",
                             "vehicles": [{"name": "TV prime time", "reach": "450000", "insertions": "8", "cost": "1200000"},
                                          {"name": "Radio drive time", "reach": "300000", "insertions": "12", "cost": "450000"},
                                          {"name": "Print weekly", "reach": "120000", "insertions": "4", "cost": "180000"}]}},
    "marketshare": {"objective": "What share of the market do we hold, and is it rising?", "method": "market_share", "currency": "USD", "period": "annual",
                    "inputs": {"firm_sales": "2400000", "market_sales": "12000000", "prior_firm_sales": "2100000",
                               "prior_market_sales": "11500000", "customers": "48000", "target_population": "400000",
                               "largest_competitor_sales": "3600000"}},
    "clv": {"objective": "What is a customer worth once churn and time are counted?", "method": "clv_model", "currency": "USD", "period": "monthly",
            "inputs": {"margin_per_period": "1500", "churn_rate": "0.04", "discount_rate": "0.10",
                       "horizon_periods": "24", "acquisition_cost": "9000"}},
    "custprofit": {"objective": "Which customer segments actually make money?", "method": "customer_profitability", "currency": "USD", "period": "annual",
                   "inputs": {"segments": [{"name": "Enterprise", "revenue": "5000000", "direct_cost": "3000000", "allocated_cost": "600000"},
                                           {"name": "SME", "revenue": "3000000", "direct_cost": "2100000", "allocated_cost": "400000"},
                                           {"name": "Retail", "revenue": "1200000", "direct_cost": "1500000", "allocated_cost": "100000"}],
                              "concentration_threshold": "0.8"}},
    "scv": {"objective": "Compute the material, labour and overhead variances for the period", "method": "standard_cost_variances", "currency": "USD", "period": "annual",
            "inputs": {"actual_units": "4800", "standard_material_per_unit": "2", "standard_material_price": "15",
                       "actual_material_quantity": "9800", "actual_material_price": "15.5",
                       "standard_hours_per_unit": "1.5", "standard_labour_rate": "40", "actual_hours": "7300", "actual_labour_rate": "41",
                       "standard_variable_overhead_rate": "10", "actual_variable_overhead": "70000",
                       "budgeted_fixed_overhead": "240000", "actual_fixed_overhead": "245000", "denominator_hours": "8000"}},
    "inventory": {"objective": "How much should we order, and when should we reorder?", "method": "inventory_policy", "currency": "USD", "period": "annual",
                  "inputs": {"annual_demand": "12000", "order_cost": "500", "holding_cost_per_unit": "30",
                             "lead_time_days": "10", "service_level": "0.95", "daily_demand_sd": "20"}},
    "queue": {"objective": "How long is the queue at the counter?", "method": "queue_analysis", "currency": "USD", "period": "per period",
              "inputs": {"arrival_rate": "18", "service_rate": "24"}},
    "capacity": {"objective": "Which step limits how much we can produce?", "method": "capacity_analysis", "currency": "USD", "period": "per period",
                 "inputs": {"resources": [{"name": "cutting", "available_hours": "8", "minutes_per_unit": "5"},
                                          {"name": "assembly", "available_hours": "8", "minutes_per_unit": "8"},
                                          {"name": "packing", "available_hours": "8", "minutes_per_unit": "3"}],
                            "demand": "50"}},
    "cpm": {"objective": "What is the critical path and when does the project finish?", "method": "cpm_schedule", "currency": "USD", "period": "days",
            "inputs": {"estimate": "single", "activities": [
                {"id": "A", "duration": "3", "predecessors": ""},
                {"id": "B", "duration": "4", "predecessors": "A"},
                {"id": "C", "duration": "2", "predecessors": "A"},
                {"id": "D", "duration": "5", "predecessors": "B,C"}]}},
    "leveling": {"objective": "Level the plan against the crew capacity", "method": "resource_leveling", "currency": "USD", "period": "days",
                 "inputs": {"resources": [{"name": "crew", "capacity": "2"}],
                            "activities": [{"id": "A", "duration": "2", "resource": "crew", "demand": "2", "predecessors": ""},
                                           {"id": "B", "duration": "2", "resource": "crew", "demand": "2", "predecessors": "A"},
                                           {"id": "C", "duration": "2", "resource": "crew", "demand": "1", "predecessors": "A"},
                                           {"id": "D", "duration": "1", "resource": "crew", "demand": "1", "predecessors": "B,C"}]}},
    "crashing": {"objective": "Crash the plan to the target duration", "method": "project_crashing", "currency": "USD", "period": "days",
                 "inputs": {"target_duration": "7", "activities": [
                     {"id": "A", "normal_duration": "5", "crash_duration": "3", "crash_cost": "100", "predecessors": ""},
                     {"id": "B", "normal_duration": "4", "crash_duration": "2", "crash_cost": "80", "predecessors": "A"},
                     {"id": "C", "normal_duration": "3", "crash_duration": "3", "crash_cost": "0", "predecessors": "A"}]}},
    "calendar": {"objective": "Schedule the plan over a working calendar", "method": "calendar_schedule", "currency": "USD", "period": "days",
                 "inputs": {"working_periods": "0,1,2,5,6,7,10,11,12", "activities": [
                     {"id": "A", "duration": "2", "predecessors": ""},
                     {"id": "B", "duration": "2", "predecessors": "A"},
                     {"id": "C", "duration": "1", "predecessors": "B"},
                     {"id": "D", "duration": "1", "predecessors": "A"}]}},
    "multiproject": {"objective": "Schedule two projects that share one crew", "method": "multi_project_schedule", "currency": "USD", "period": "days",
                     "inputs": {"resources": [{"name": "crew", "capacity": "2"}],
                                "projects": [
                                    {"name": "alpha", "priority": "1", "activities": [
                                        {"id": "A", "duration": "2", "resource": "crew", "demand": "2", "predecessors": ""},
                                        {"id": "B", "duration": "2", "resource": "crew", "demand": "2", "predecessors": "A"}]},
                                    {"name": "beta", "priority": "2", "activities": [
                                        {"id": "X", "duration": "2", "resource": "crew", "demand": "1", "predecessors": ""},
                                        {"id": "Y", "duration": "2", "resource": "crew", "demand": "1", "predecessors": "X"}]}]}},
    "schedrisk": {"objective": "How uncertain is the project duration?", "method": "schedule_risk", "currency": "USD", "period": "days",
                  "inputs": {"iterations": "1000", "seed": "42", "target_duration": "9",
                             "activities": [{"id": "A", "optimistic": "2", "most_likely": "3", "pessimistic": "5", "predecessors": ""},
                                            {"id": "B", "optimistic": "3", "most_likely": "4", "pessimistic": "6", "predecessors": "A"},
                                            {"id": "C", "optimistic": "1", "most_likely": "2", "pessimistic": "4", "predecessors": "A"}]}},
    "decisiontree": {"objective": "Which launch option should we choose?", "method": "decision_tree", "currency": "USD", "period": "point in time",
                     "inputs": {"tree": {"type": "decision", "alternatives": [
                         {"name": "Launch", "node": {"type": "chance", "branches": [
                             {"probability": "0.6", "node": {"type": "terminal", "value": "100000"}},
                             {"probability": "0.4", "node": {"type": "terminal", "value": "-20000"}}]}},
                         {"name": "Pilot", "node": {"type": "chance", "branches": [
                             {"probability": "0.7", "node": {"type": "terminal", "value": "40000"}},
                             {"probability": "0.3", "node": {"type": "terminal", "value": "5000"}}]}}]}}},
    "realoption": {"objective": "What is the option to invest in the project worth?", "method": "real_option", "currency": "USD", "period": "point in time",
                   "inputs": {"underlying_value": "100", "investment_cost": "100", "volatility": "0.30",
                              "risk_free_rate": "0.05", "steps": "5", "horizon_years": "1",
                              "option_type": "call", "exercise": "american"}},
    "mcda": {"objective": "Which supplier scores best on the declared criteria?", "method": "multi_criteria", "currency": "USD", "period": "point in time",
             "inputs": {"scale_max": "10", "criteria": [{"name": "cost", "weight": "0.6"}, {"name": "speed", "weight": "0.4"}],
                        "alternatives": [{"name": "A", "scores": {"cost": "9", "speed": "5"}},
                                         {"name": "B", "scores": {"cost": "6", "speed": "9"}},
                                         {"name": "C", "scores": {"cost": "7", "speed": "7"}}]}},
    "montecarlo": {"objective": "How uncertain is the project's net present value?", "method": "monte_carlo", "currency": "USD", "period": "point in time",
                   "inputs": {"model": "npv", "iterations": "2000", "seed": "7", "discount_rate": "0.10",
                              "cashflows": [{"name": "outlay", "period": "0", "distribution": "fixed", "value": "-1000"},
                                            {"name": "year_one", "period": "1", "distribution": "triangular", "low": "200", "mode": "400", "high": "600"},
                                            {"name": "year_two", "period": "2", "distribution": "triangular", "low": "200", "mode": "400", "high": "600"},
                                            {"name": "year_three", "period": "3", "distribution": "triangular", "low": "200", "mode": "400", "high": "600"}]}},
    "evm": {"objective": "Are we ahead or behind, and what will it cost?", "method": "earned_value", "currency": "USD", "period": "point in time",
            "inputs": {"planned_value": "100000", "earned_value": "90000", "actual_cost": "95000",
                       "budget_at_completion": "200000", "eac_method": "cpi"}},
    "oee": {"objective": "What is the overall equipment effectiveness of the line?", "method": "oee_analysis", "currency": "USD", "period": "per period",
            "inputs": {"planned_production_time": "480", "downtime": "40", "ideal_cycle_time": "0.5",
                       "total_units": "760", "good_units": "740"}},
    "spc": {"objective": "Is the process in control, and is it capable?", "method": "process_control", "currency": "USD", "period": "per observation",
            "inputs": {"values": ["10", "11", "9", "10", "12", "9", "10", "11"], "spec_lower": "7", "spec_upper": "13"}},
    "abc": {"objective": "What does each product really cost once activities are traced?", "method": "abc_costing", "currency": "USD", "period": "annual",
            "inputs": {"activities": [{"name": "Machining", "pool_cost": "120000"}, {"name": "Assembly", "pool_cost": "80000"}],
                       "products": [{"name": "Widget A", "units": "1000"}, {"name": "Widget B", "units": "2000"}],
                       "allocations": [{"activity": "Machining", "product": "Widget A", "driver_quantity": "600"},
                                       {"activity": "Machining", "product": "Widget B", "driver_quantity": "1400"},
                                       {"activity": "Assembly", "product": "Widget A", "driver_quantity": "400"},
                                       {"activity": "Assembly", "product": "Widget B", "driver_quantity": "1600"}]}},
    "salesvar": {"objective": "Why did revenue move against the budget?", "method": "sales_variances", "currency": "USD", "period": "annual",
                 "inputs": {"products": [{"name": "Product A", "budget_units": "1000", "budget_price": "50", "actual_units": "1100", "actual_price": "55"},
                                         {"name": "Product B", "budget_units": "2000", "budget_price": "30", "actual_units": "1800", "actual_price": "32"}]}},
    "linebalance": {"objective": "How many stations does the line need at this cycle time?", "method": "line_balancing", "currency": "USD", "period": "per period",
                    "inputs": {"cycle_time": "10", "rule": "longest_time", "tasks": [
                        {"id": "A", "time": "5", "predecessors": ""},
                        {"id": "B", "time": "3", "predecessors": "A"},
                        {"id": "C", "time": "4", "predecessors": "A"},
                        {"id": "D", "time": "2", "predecessors": "B"},
                        {"id": "E", "time": "3", "predecessors": "C"},
                        {"id": "F", "time": "4", "predecessors": "D,E"}]}},
    "tax": {"objective": "What is the tax charge on the declared income?", "method": "tax_declared", "currency": "USD", "period": "annual",
            "inputs": {"taxable_income": "1000000", "income_tax_rate": "0.25",
                       "vat_output_tax": "144000", "vat_input_tax": "84000",
                       "temporary_difference": "100000", "deferred_tax_rate": "0.25"}},
    "depreciation": {"objective": "What is the depreciation schedule for the equipment?", "method": "depreciation_schedule", "currency": "USD", "period": "annual",
                     "inputs": {"cost": "500000", "salvage": "50000", "life": "5", "method": "straight_line"}},
    "proforma": {"objective": "Project the income statement, cash flow and balance sheet", "method": "proforma_statements", "currency": "USD", "period": "annual",
                 "inputs": {"revenue": ["1200000", "1500000", "1800000"], "gross_margin_rate": "0.40",
                            "operating_costs": ["300000", "320000", "340000"],
                            "depreciation": ["90000", "90000", "90000"],
                            "interest": ["40000", "30000", "20000"],
                            "principal_repayment": ["100000", "100000", "100000"],
                            "capex": ["0", "0", "0"], "tax_rate": "0.25",
                            "receivable_days": "30", "inventory_days": "45", "payable_days": "30",
                            "opening_cash": "200000", "opening_fixed_assets": "450000",
                            "opening_receivables": "0", "opening_inventory": "0", "opening_payables": "0",
                            "opening_loan": "400000", "opening_equity": "250000"}},
    "frommarket": {"objective": "What revenue does our target market share imply?", "method": "sales_from_market", "currency": "USD", "period": "annual",
                   "inputs": {"market_size": "60000000", "target_share": "0.03", "price": "120"}},
    "sensitivity": {"objective": "What happens to profit if price or volume changes?", "method": "sensitivity_table", "currency": "USD", "period": "annual",
                    "inputs": {"base_price": "120", "base_units": "10000", "base_variable_cost": "55",
                               "base_fixed_cost": "300000",
                               "price_changes": ["-0.1", "0", "0.1"], "volume_changes": ["-0.2", "0", "0.2"]}},
    "descriptive": {"objective": "Describe the exam scores", "method": "descriptive_stats", "unit": "points",
                    "inputs": {"values": ["72", "85", "90", "68", "99", "77", "81"], "missing_codes": ["99"]}},
    "pearson": {"objective": "Is study time associated with exam score?", "method": "pearson",
                "inputs": {"x": ["1", "2", "3", "4", "5", "6", "7", "8"], "y": ["52", "55", "61", "58", "70", "72", "69", "80"], "missing_codes": []}},
    "ols": {"objective": "How are study hours and sleep associated with exam score?", "method": "ols",
            "inputs": {"y": ["52", "55", "61", "58", "70", "72", "69", "80", "66", "74"],
                       "predictors": {"study_hours": ["1", "2", "3", "4", "5", "6", "7", "8", "4", "6"], "sleep_hours": ["6", "7", "5", "8", "6", "7", "8", "6", "7", "7"]}, "missing_codes": []}},
    "welch": {"objective": "Do the two teaching methods differ in exam scores?", "method": "welch_t", "unit": "points",
              "inputs": {"groups": {"lecture": ["62", "70", "68", "75", "66", "71", "64", "73"], "workshop": ["72", "78", "74", "85", "80", "77", "69", "83", "79"]}, "missing_codes": []}},
    "anova": {"objective": "Do the three teaching formats differ in exam scores?", "method": "anova", "unit": "points",
              "inputs": {"groups": {"lecture": ["62", "70", "68", "75", "66", "71", "64", "73"], "workshop": ["72", "78", "74", "85", "80", "77", "69", "83", "79"], "online": ["60", "63", "58", "66", "61", "65", "60"]}, "missing_codes": []}},
    "chi_square": {"objective": "Is the outcome category associated with the treatment group?", "method": "chi_square",
                   "inputs": {"table": [[45, 30, 25], [20, 40, 40], [10, 20, 70]]}},
    "forecast": {"objective": "Forecast the next three periods", "method": "trend_forecast", "unit": "units",
                 "inputs": {"values": ["10", "12", "11", "14", "13", "16", "15", "18", "17", "20", "19", "22"], "missing_codes": [], "horizon": "3"}},
    "ratios": {"objective": "Compute the key ratios from our financial statements", "method": "ratio_analysis", "period": "annual",
               "inputs": {"current_assets": "5000", "current_liabilities": "2000", "cash": "800", "inventory": "1200", "receivables": "1500",
                          "payables": "900", "total_assets": "12000", "total_liabilities": "7000", "equity": "5000", "revenue": "20000",
                          "cost_of_sales": "12000", "operating_profit": "3000", "net_income": "1800", "interest_expense": "400"}},
    "paired": {"objective": "Did the scores change after the intervention?", "method": "paired_t", "unit": "points", "period": "cross_section",
               "inputs": {"pairs": {"before": ["10", "12", "11", "9", "13"], "after": ["12", "13", "12", "10", "14"]}}},
    "onesample": {"objective": "Is the mean different from the target?", "method": "one_sample_t", "unit": "points", "period": "cross_section",
                  "inputs": {"values": ["72", "85", "90", "68", "99", "77", "81"], "missing_codes": ["99"], "mu0": "75"}},
    "wacc": {"objective": "What is our weighted average cost of capital?", "method": "wacc", "period": "annual",
             "inputs": {"equity_value": "800000", "debt_value": "200000", "cost_of_equity": "0.12", "cost_of_debt_after_tax": "0.05"}},
    "dcf": {"objective": "Value the project from its free cash flows", "method": "dcf_valuation", "currency": "USD", "period": "annual",
            "inputs": {"cashflows": ["100000", "120000", "140000", "155000"], "discount_rate": "0.10", "terminal_growth": "0.02"}},
    "dcfmid": {"objective": "Value the project with mid-year cash flows", "method": "dcf_valuation", "currency": "USD", "period": "annual",
               "inputs": {"cashflows": ["100000", "120000", "140000", "155000"], "discount_rate": "0.10", "terminal_growth": "0.02", "timing": "mid"}},
    "equitybridge": {"objective": "What is the equity value after net debt and other claims?", "method": "equity_bridge", "currency": "USD", "period": "annual",
                     "inputs": {"enterprise_value": "1750939.14", "debt": "300000", "cash": "150000", "minority_interest": "20000",
                                "preferred_equity": "10000", "shares_outstanding": "100000"}},
    "currency": {"objective": "Convert a USD amount to EUR at a declared rate", "method": "currency_convert", "currency": "EUR", "period": "cross_section",
                 "inputs": {"amount": "1000", "from_currency": "USD", "to_currency": "EUR", "rate": "0.92", "rate_provenance": "user", "rate_date": "2026-10-20"}},
    "logit": {"objective": "What predicts the binary outcome?", "method": "logistic_regression", "period": "cross_section",
              "inputs": {"y": ["0", "0", "0", "1", "0", "1", "1", "1", "1", "1", "1", "1", "0", "1", "1", "0", "1", "0", "0", "1", "0", "0", "0", "1", "1", "0", "0", "1", "1", "0", "1", "1", "1", "1", "0", "1", "1", "1", "1", "0"], "predictors": {"size": ["-1.72", "-0.26", "-0.74", "-0.01", "0.2", "-0.72", "-0.74", "-0.28", "-0.8", "1.32", "0.48", "1.3", "-1.0", "-0.02", "0.62", "0.8", "3.11", "-0.84", "-0.01", "0.17", "-0.15", "0.42", "-0.17", "-0.96", "0.79", "-0.95", "-1.79", "-0.16", "0.26", "0.47", "2.23", "0.64", "0.92", "0.22", "0.89", "-0.08", "2.05", "1.76", "0.01", "0.15"], "group": ["0", "0", "0", "0", "1", "0", "0", "0", "1", "1", "1", "0", "0", "1", "1", "0", "1", "0", "0", "1", "0", "0", "1", "1", "0", "0", "0", "0", "1", "0", "0", "0", "0", "0", "1", "1", "1", "0", "1", "1"]}}},
    "alpha": {"objective": "Are the survey items internally consistent?", "method": "reliability_alpha", "unit": "points", "period": "cross_section",
              "inputs": {"items": {"one": ["4", "5", "3", "4", "5", "2", "4", "3"], "two": ["4", "4", "3", "5", "4", "3", "4", "2"], "three": ["3", "4", "2", "4", "5", "3", "4", "3"], "four": ["4", "5", "3", "4", "4", "2", "3", "3"]}}},
    "cba": {"objective": "Appraise the programme costs against its benefits", "method": "cost_benefit", "currency": "USD", "period": "annual",
            "inputs": {"costs": ["50000", "10000", "10000"], "benefits": ["20000", "30000", "40000"], "discount_rate": "0.05"}},
    "cea": {"objective": "Which option gives more effect per unit of cost?", "method": "cost_effectiveness", "currency": "USD", "period": "annual",
            "inputs": {"options": [{"name": "basic", "cost": "10000", "effect": "40"}, {"name": "intensive", "cost": "18000", "effect": "60"}]}},
    "sroi": {"objective": "What is the social return on the investment?", "method": "sroi", "currency": "USD", "period": "annual",
             "inputs": {"investment": "60000", "benefits": ["20000", "25000", "30000"], "discount_rate": "0.04"}},
    "unitecon": {"objective": "What does a customer cost and return?", "method": "unit_economics", "currency": "USD", "period": "annual",
                 "inputs": {"price": "49", "variable_cost": "12", "acquisition_cost": "80", "churn_rate": "0.04"}},
    "multibreakeven": {"objective": "How many units must the product mix sell to break even?", "method": "multi_product_breakeven", "currency": "USD", "period": "annual",
                       "inputs": {"fixed_costs": "100000",
                                  "products": [{"name": "Product A", "price": "50", "variable_cost": "30", "mix_units": "60"},
                                               {"name": "Product B", "price": "30", "variable_cost": "15", "mix_units": "40"}]}},
    "factorial": {"objective": "Do the two factors and their interaction matter?", "method": "two_way_anova", "unit": "points", "period": "cross_section",
                  "inputs": {"data": [{"response": "1", "factor_a": "low", "factor_b": "x"}, {"response": "3", "factor_a": "low", "factor_b": "x"}, {"response": "5", "factor_a": "low", "factor_b": "y"}, {"response": "7", "factor_a": "low", "factor_b": "y"}, {"response": "3", "factor_a": "high", "factor_b": "x"}, {"response": "5", "factor_a": "high", "factor_b": "x"}, {"response": "7", "factor_a": "high", "factor_b": "y"}, {"response": "9", "factor_a": "high", "factor_b": "y"}]}},
    "posthoc": {"objective": "Which groups differ from which?", "method": "posthoc_pairwise", "unit": "points", "period": "cross_section",
                "inputs": {"groups": {"a": ["10", "12", "11", "13"], "b": ["14", "15", "16", "14"], "c": ["18", "17", "19", "20"]}, "adjust": "holm", "alpha": "0.05"}},
    "multicomp": {"objective": "Correct a declared family of hypothesis tests", "method": "multiple_comparison", "period": "cross_section",
                  "inputs": {"p_values": ["0.01", "0.04", "0.03", "0.005"], "method": "holm", "alpha": "0.05"}},
    "power": {"objective": "Size a study to detect a stated effect", "method": "power_analysis", "unit": "points", "period": "cross_section",
              "inputs": {"design": "two_sample", "effect": "5", "n1": "30", "n2": "40", "sd1": "10", "sd2": "12", "alpha": "0.05", "tails": "two_sided", "target_power": "0.8"}},
    "missing": {"objective": "How much could the missing values move the mean?", "method": "missing_data_bounds", "unit": "points", "period": "cross_section",
                "inputs": {"values": ["10", "12", "", "14", "99", "16"], "missing_codes": ["99"], "mechanism": "unknown"}},
    "weighted": {"objective": "Summarize the survey scores with the design weights", "method": "weighted_summary", "unit": "points", "period": "cross_section",
                 "inputs": {"values": ["1", "2", "3", "4"], "weights": ["1", "1", "1", "3"], "weight_kind": "reliability"}},
    "accounts": {"objective": "Prepare the management accounts for the period", "method": "management_accounts", "currency": "USD",
                 "inputs": {"spec": {"period": {"start": "2026-01-01", "end": "2026-12-31"}, "currency": "USD", "framework": "IFRS", "places": 2,
                                     "chart": [{"code": "1000", "name": "Cash", "type": "asset", "line": "Cash", "section": "current", "role": "cash"},
                                               {"code": "1100", "name": "Trade receivables", "type": "asset", "line": "Trade receivables", "section": "current"},
                                               {"code": "1200", "name": "Inventory", "type": "asset", "line": "Inventory", "section": "current"},
                                               {"code": "1500", "name": "Equipment", "type": "asset", "line": "Property, plant and equipment", "section": "non_current"},
                                               {"code": "2000", "name": "Trade payables", "type": "liability", "line": "Trade payables", "section": "current"},
                                               {"code": "2100", "name": "Loan", "type": "liability", "line": "Borrowings", "section": "non_current"},
                                               {"code": "3000", "name": "Share capital", "type": "equity", "line": "Capital", "role": "capital"},
                                             {"code": "3100", "name": "Retained earnings", "type": "equity", "line": "Retained earnings", "role": "retained_earnings"},
                                               {"code": "4000", "name": "Sales", "type": "income", "line": "Revenue"},
                                               {"code": "5000", "name": "Cost of sales", "type": "expense", "line": "Cost of sales"},
                                               {"code": "6000", "name": "Operating expenses", "type": "expense", "line": "Operating expenses"}],
                                     "prior_closing": {}, "opening": [],
                                     "entries": [{"date": "2026-01-01", "description": "Shares issued", "lines": [{"account": "1000", "debit": "50000"}, {"account": "3000", "credit": "50000"}]},
                                                 {"date": "2026-12-31", "description": "Cash sales", "lines": [{"account": "1000", "debit": "120000"}, {"account": "4000", "credit": "120000"}]}],
                                     "schedules": []}}},
    "case": {"objective": "A regional bakery is losing customers to a new supermarket chain. Analyze the competition in our industry and compare strategic options.", "context": "Single owner, three shops"},
    "swot": templates.EXAMPLES["template_swot"], "five_forces": templates.EXAMPLES["template_five_forces"], "case_decision": templates.EXAMPLES["case_decision"],
    "unsupported": {"objective": "Value this startup", "method": "monte_carlo_valuation", "inputs": {"x": "1"}},
    "tbcheck": {"objective": "Check my trial balance against my journal", "method": "trial_balance_check",
                "currency": "USD", "period": "annual", "places": 2,
                "inputs": {
                    "journal": {"period": {"start": "2026-01-01", "end": "2026-03-31"}, "currency": "USD",
                                "framework": "IFRS", "places": 2,
                                "chart": [{"code": "1000", "name": "Cash", "type": "asset", "line": "Cash", "role": "cash"},
                                          {"code": "3000", "name": "Capital", "type": "equity", "line": "Capital", "role": "capital"},
                                          {"code": "3100", "name": "Retained earnings", "type": "equity", "line": "Retained earnings", "role": "retained_earnings"}],
                                "prior_closing": {"1000": "1000", "3000": "1000"},
                                "opening": [{"description": "opening", "lines": [{"account": "1000", "debit": "1000"}, {"account": "3000", "credit": "1000"}]}],
                                "entries": [{"date": "2026-02-01", "description": "capital introduced",
                                             "lines": [{"account": "1000", "debit": "500"}, {"account": "3000", "credit": "500"}]}],
                                "schedules": []},
                    "trial_balance": [{"code": "1000", "name": "Cash", "debit": "1500", "credit": "0"},
                                      {"code": "3000", "name": "Capital", "debit": "0", "credit": "1500"}],
                }},
    "tvm": {"objective": "What will my savings and regular deposits be worth?", "method": "time_value", "currency": "USD", "period": "annual",
            "inputs": {"present_value": "100000", "payment": "12000", "rate": "0.06", "periods": "5", "compounding": "quarterly", "timing": "end"}},
    "loan": {"objective": "What is the monthly payment on this loan?", "method": "loan_amortization", "currency": "USD", "period": "annual",
             "inputs": {"principal": "200000", "annual_rate": "0.09", "years": "5", "payments_per_year": "12"}},
    "bond": {"objective": "What is this bond worth and how sensitive is it to yield?", "method": "bond_analysis", "currency": "USD", "period": "annual",
             "inputs": {"face_value": "1000", "coupon_rate": "0.08", "years_to_maturity": "10", "yield_to_maturity": "0.06", "payments_per_year": "2"}},
    "capm": {"objective": "What cost of equity does CAPM imply?", "method": "capm", "period": "annual",
             "inputs": {"risk_free_rate": "0.04", "market_return": "0.10", "beta": "1.2", "debt_to_equity": "0.6", "tax_rate": "0.30"}},
    "dupont": {"objective": "Where does the return on equity come from?", "method": "dupont_analysis", "period": "annual",
               "inputs": {"revenue": "20000", "net_income": "1800", "total_assets": "12000", "equity": "5000", "cost_of_sales": "12000",
                          "ebit": "3000", "pretax_income": "2400", "tax_expense": "600",
                          "prior_revenue": "18000", "prior_net_income": "1500", "prior_total_assets": "11000", "prior_equity": "4700"}},
    "multiples": {"objective": "What value do comparable multiples imply?", "method": "multiples_valuation", "currency": "USD", "period": "annual",
                  "inputs": {"metric": "ebitda", "subject_value": "500000",
                             "comparables": [{"name": "Peer A", "multiple": "8"}, {"name": "Peer B", "multiple": "10"}, {"name": "Peer C", "multiple": "12"}],
                             "net_debt": "300000", "shares_outstanding": "100000"}},
    "workingcapital": {"objective": "How long is cash tied up in working capital?", "method": "working_capital", "currency": "USD", "period": "annual",
                       "inputs": {"revenue": "20000", "cost_of_sales": "12000", "inventory": "1200", "receivables": "1500", "payables": "900",
                                  "annual_demand": "5000", "order_cost": "50", "holding_cost_per_unit": "4", "discount_percent": "0.02",
                                  "credit_terms_days": "30", "discount_days": "10", "lead_time_days": "7", "safety_stock": "100"}},
    "portfolio": {"objective": "What return and risk does this two-asset portfolio have?", "method": "portfolio_analysis", "period": "period",
                  "inputs": {"returns_a": ["0.02", "0.03", "-0.01", "0.04", "0.01", "0.02"], "returns_b": ["0.01", "0.02", "0.00", "0.03", "0.02", "0.01"],
                             "weight_a": "0.6", "risk_free_rate": "0.02", "returns_market": ["0.01", "0.02", "-0.02", "0.03", "0.00", "0.02"]}},
    "projectmetrics": {"objective": "How does this project rank on PI, MIRR, payback and EAA?", "method": "project_metrics", "currency": "USD", "period": "annual",
                       "inputs": {"cashflows": ["-1000", "400", "400", "400", "400"], "rate": "0.10", "finance_rate": "0.08"}},
    "options": {"objective": "What is this option worth and what are its Greeks?", "method": "option_pricing", "currency": "USD", "period": "annual",
                "inputs": {"option_type": "call", "spot_price": "100", "strike_price": "100", "volatility": "0.25",
                           "risk_free_rate": "0.05", "time_to_maturity": "1", "steps": "200"}},
    "risk": {"objective": "How much could this portfolio lose at a stated confidence?", "method": "risk_metrics", "currency": "USD", "period": "period",
             "inputs": {"returns": ["0.01", "-0.02", "0.015", "0.00", "-0.03", "0.025", "0.01", "-0.01", "0.02", "-0.005"],
                        "confidence": "0.95", "portfolio_value": "1000000", "horizon_days": "1", "stress_return": "-0.05"}},
    "fx": {"objective": "What forward rate and expected spot do the parities imply?", "method": "fx_parity", "period": "annual",
           "inputs": {"spot_rate": "56", "domestic_rate": "0.05", "foreign_rate": "0.03", "domestic_inflation": "0.04",
                      "foreign_inflation": "0.02", "time_to_maturity": "1", "forward_rate": "57",
                      "exposure_amount": "100000", "hedge_forward": "57", "expected_spot": "57.5"}},
    "leverage": {"objective": "What do leverage, EPS and the Altman Z-score look like?", "method": "leverage_analysis", "currency": "USD", "period": "annual",
                 "inputs": {"ebit": "500000", "interest_expense": "100000", "tax_rate": "0.30", "debt": "800000", "equity": "1200000",
                            "shares_outstanding": "100000", "working_capital": "300000", "retained_earnings": "400000", "total_assets": "2000000",
                            "total_liabilities": "800000", "sales": "3000000", "market_value_equity": "1800000",
                            "alternative_interest_expense": "200000", "alternative_shares_outstanding": "60000"}},
    "scenario": {"objective": "How much does the decision swing with the discount rate?", "method": "scenario_analysis", "currency": "USD", "period": "annual",
                 "inputs": {"cashflows": ["-1000", "400", "400", "400", "400"], "discount_rate": "0.10", "rate_low": "0.05", "rate_high": "0.20"}},
    "equilibrium": {"objective": "Where do demand and supply meet?", "method": "demand_supply_equilibrium", "currency": "USD", "period": "annual",
                    "inputs": {"demand_intercept": "100", "demand_slope": "2", "supply_intercept": "20", "supply_slope": "2"}},
    "elasticity": {"objective": "How responsive is quantity to a price change?", "method": "elasticity", "currency": "USD", "period": "annual",
                   "inputs": {"quantity_1": "100", "price_1": "10", "quantity_2": "140", "price_2": "8"}},
    "taxincidence": {"objective": "Who bears a per-unit tax?", "method": "tax_incidence", "currency": "USD", "period": "annual",
                     "inputs": {"demand_intercept": "100", "demand_slope": "2", "supply_intercept": "20", "supply_slope": "2", "tax_per_unit": "6"}},
    "pricecontrol": {"objective": "What does a price ceiling or floor do?", "method": "price_control", "currency": "USD", "period": "annual",
                     "inputs": {"demand_intercept": "100", "demand_slope": "2", "supply_intercept": "20", "supply_slope": "2",
                                "control_price": "15", "control_type": "ceiling"}},
    "concentration": {"objective": "How concentrated is this market?", "method": "market_concentration", "currency": "USD", "period": "annual",
                      "inputs": {"firm_revenues": ["40", "25", "15", "10", "10"]}},
    "costcurves": {"objective": "What do average and marginal cost look like at this output?", "method": "cost_curves", "currency": "USD", "period": "annual",
                   "inputs": {"fixed_cost": "1000", "linear_cost": "10", "quadratic_cost": "0.5", "quantity": "20", "price": "40"}},
    "profitmax": {"objective": "What output and price maximise profit?", "method": "profit_maximization", "currency": "USD", "period": "annual",
                  "inputs": {"demand_intercept": "100", "demand_slope": "2", "fixed_cost": "100", "linear_cost": "10", "quadratic_cost": "0.5"}},
    "marketpower": {"objective": "How much market power does this price imply?", "method": "market_power", "currency": "USD", "period": "annual",
                    "inputs": {"price": "50", "marginal_cost": "20"}},
    "nationalincome": {"objective": "What is GDP by the expenditure approach?", "method": "national_income", "currency": "USD", "period": "annual",
                       "inputs": {"consumption": "600", "investment": "150", "government_spending": "200", "exports": "120", "imports": "170",
                                  "net_factor_income": "20", "depreciation": "50", "population": "100", "gdp_deflator": "120"}},
    "growth": {"objective": "What compound growth rate does this series imply?", "method": "growth_rate", "currency": "USD", "period": "annual",
               "inputs": {"start_value": "100", "end_value": "200", "periods": "10"}},
    "inflation": {"objective": "What is the inflation rate and the real interest rate?", "method": "inflation_cpi", "currency": "USD", "period": "annual",
                  "inputs": {"cpi_start": "100", "cpi_end": "105", "nominal_interest_rate": "0.08", "wage_start": "100", "wage_end": "104"}},
    "unemployment": {"objective": "What are the unemployment and participation rates?", "method": "unemployment_rate", "period": "annual",
                     "inputs": {"labour_force": "1000", "employed": "920", "working_age_population": "1500"}},
    "moneymultiplier": {"objective": "How much money does this base support?", "method": "money_multiplier", "currency": "USD", "period": "annual",
                        "inputs": {"monetary_base": "100", "reserve_ratio": "0.10", "currency_drain_ratio": "0.05"}},
    "fiscal": {"objective": "What output change does this fiscal package imply?", "method": "fiscal_multiplier", "currency": "USD", "period": "annual",
               "inputs": {"mpc": "0.8", "tax_rate": "0.25", "government_spending_change": "100", "tax_change": "0"}},
    "budgetdebt": {"objective": "What are the budget balance and the debt ratio?", "method": "budget_debt", "currency": "USD", "period": "annual",
                   "inputs": {"government_revenue": "500", "government_spending": "520", "interest_payments": "30", "debt_stock": "1000",
                              "nominal_gdp": "2000", "nominal_growth_rate": "0.05", "inflation_rate": "0.02"}},
    "externality": {"objective": "What is the Pigouvian tax and the deadweight loss?", "method": "externality_pigouvian", "currency": "USD", "period": "annual",
                    "inputs": {"demand_intercept": "100", "demand_slope": "2", "supply_intercept": "20", "supply_slope": "2", "marginal_external_cost": "4"}},
    "publicgood": {"objective": "What is the efficient provision of the public good?", "method": "public_good", "currency": "USD", "period": "annual",
                   "inputs": {"mb1_intercept": "100", "mb1_slope": "2", "mb2_intercept": "80", "mb2_slope": "3", "mc_intercept": "20", "mc_slope": "1"}},
    "socialwelfare": {"objective": "Compare utilitarian, Rawlsian and Nash welfare", "method": "social_welfare", "currency": "USD", "period": "annual",
                      "inputs": {"incomes": ["10", "20", "30", "40"], "welfare_function": "utilitarian"}},
    "gini": {"objective": "How unequal are these incomes?", "method": "gini_coefficient", "currency": "USD", "period": "annual",
             "inputs": {"incomes": ["10", "20", "30", "40"]}},
    "poverty": {"objective": "What are the poverty headcount and gap?", "method": "poverty_measures", "currency": "USD", "period": "annual",
                "inputs": {"incomes": ["10", "20", "30", "40"], "poverty_line": "25"}},
    "taxprogressivity": {"objective": "Is this tax progressive?", "method": "tax_progressivity", "currency": "USD", "period": "annual",
                         "inputs": {"incomes": ["10", "20", "30", "40"], "taxes": ["1", "3", "6", "10"]}},
    "optimalpollution": {"objective": "What is the optimal pollution level?", "method": "optimal_pollution", "currency": "USD", "period": "annual",
                         "inputs": {"marginal_damage_intercept": "10", "marginal_damage_slope": "2", "marginal_abatement_intercept": "100", "marginal_abatement_slope": "3"}},
    "okun": {"objective": "What does the output gap imply for unemployment?", "method": "output_gap_okun", "period": "annual",
             "inputs": {"actual_gdp": "1050", "potential_gdp": "1000", "current_unemployment_rate": "0.06", "okun_coefficient": "0.5"}},
    "comparative": {"objective": "Which country has comparative advantage in which good?", "method": "comparative_advantage", "period": "annual",
                    "inputs": {"countries": [{"name": "A", "good_1_hours": "2", "good_2_hours": "1"},
                                             {"name": "B", "good_1_hours": "5", "good_2_hours": "3"}]}},
    "tariff": {"objective": "What does a tariff cost the small country?", "method": "tariff_welfare", "currency": "USD", "period": "annual",
               "inputs": {"demand_intercept": "100", "demand_slope": "2", "supply_intercept": "20", "supply_slope": "2",
                          "world_price": "10", "tariff_per_unit": "5"}},
    "ppp": {"objective": "Is the exchange rate at purchasing-power parity?", "method": "exchange_rate_ppp", "period": "annual",
            "inputs": {"price_domestic": "5000", "price_foreign": "100", "nominal_rate": "55",
                       "domestic_inflation": "0.04", "foreign_inflation": "0.02"}},
    "irp": {"objective": "What forward rate does interest parity imply?", "method": "interest_rate_parity", "period": "annual",
            "inputs": {"spot_rate": "50", "domestic_rate": "0.06", "foreign_rate": "0.04", "time_to_maturity": "1",
                       "forward_rate": "51", "domestic_inflation": "0.04", "foreign_inflation": "0.02"}},
    "bop": {"objective": "Does the balance of payments close?", "method": "balance_of_payments", "currency": "USD", "period": "annual",
            "inputs": {"current_account": "-50", "capital_account": "0", "financial_account": "50", "gdp": "1000"}},
    "hdi": {"objective": "What is the Human Development Index?", "method": "hdi", "period": "annual",
            "inputs": {"life_expectancy": "70", "expected_years_schooling": "12", "mean_years_schooling": "8", "gni_per_capita": "5000"}},
    "expectedutility": {"objective": "What is the certainty equivalent of this gamble?", "method": "expected_utility", "currency": "USD", "period": "annual",
                        "inputs": {"outcomes": ["50", "150"], "probabilities": ["0.5", "0.5"], "utility_function": "crra", "risk_aversion": "2"}},
    "prospect": {"objective": "How does prospect theory value this gamble?", "method": "prospect_theory", "currency": "USD", "period": "annual",
                 "inputs": {"reference_point": "100", "outcomes": ["150", "50"], "probabilities": ["0.5", "0.5"]}},
    "labour": {"objective": "What are the real wage and the wage share?", "method": "labour_market", "currency": "USD", "period": "annual",
               "inputs": {"nominal_wage": "100", "cpi": "105", "labour_productivity": "120", "vacancies": "10", "unemployed": "50"}},
    "pricediscrimination": {"objective": "What prices does third-degree discrimination set?", "method": "price_discrimination", "currency": "USD", "period": "annual",
                            "inputs": {"demand_intercept_1": "100", "demand_slope_1": "2", "demand_intercept_2": "80", "demand_slope_2": "1", "marginal_cost": "10"}},
    "cournot": {"objective": "What is the Cournot duopoly outcome?", "method": "cournot_duopoly", "currency": "USD", "period": "annual",
                "inputs": {"demand_intercept": "100", "demand_slope": "2", "marginal_cost_1": "10", "marginal_cost_2": "20"}},
    "did": {"objective": "What is the difference-in-differences estimate?", "method": "difference_in_differences", "currency": "USD", "period": "annual",
            "inputs": {"treated_pre": "50", "treated_post": "70", "control_pre": "40", "control_post": "45"}},
    "nash": {"objective": "Where are the Nash equilibria in this game?", "method": "nash_equilibrium", "period": "annual",
             "inputs": {"row_payoffs": ["3", "0", "5", "1"], "column_payoffs": ["3", "5", "0", "1"]}},
    "panel": {"objective": "What is the within-entity effect?", "method": "panel_regression", "period": "annual",
              "inputs": {"data": [
                  {"entity": "A", "period": "1", "y": "2", "x": "1"}, {"entity": "A", "period": "2", "y": "4", "x": "2"}, {"entity": "A", "period": "3", "y": "6", "x": "3"},
                  {"entity": "B", "period": "1", "y": "5", "x": "2"}, {"entity": "B", "period": "2", "y": "7", "x": "3"}, {"entity": "B", "period": "3", "y": "9", "x": "4"},
                  {"entity": "C", "period": "1", "y": "1", "x": "1"}, {"entity": "C", "period": "2", "y": "5", "x": "3"}, {"entity": "C", "period": "3", "y": "9", "x": "5"}]}},
    "iv": {"objective": "What does the instrument imply for the effect?", "method": "instrumental_variables", "period": "annual",
           "inputs": {"y": ["3", "5", "7", "6", "8", "10", "11", "13"],
                      "x": ["2", "4", "5", "4", "5", "7", "8", "9"],
                      "z": ["1", "2", "3", "4", "5", "6", "7", "8"]}},
    "rdd": {"objective": "Is there a jump at the cutoff?", "method": "regression_discontinuity", "period": "annual",
            "inputs": {"data": [{"running": "-3", "outcome": "0"}, {"running": "-2", "outcome": "1"}, {"running": "-1", "outcome": "2"},
                                {"running": "1", "outcome": "10"}, {"running": "2", "outcome": "11"}, {"running": "3", "outcome": "12"}],
                       "cutoff": "0", "bandwidth": "2.5"}},
    "probit": {"objective": "What predicts the binary outcome?", "method": "probit", "period": "annual",
               "inputs": {"y": ["0", "1", "0", "1", "0", "1", "0", "1", "1", "0"],
                          "x": ["-2", "-1.5", "-1", "-0.5", "0", "0.5", "1", "1.5", "2", "2.5"]}},
    "trendanalysis": {"objective": "How has the business performed across these years?", "method": "trend_analysis", "currency": "USD", "period": "annual",
                      "inputs": {"years": ["2022", "2023", "2024", "2025"], "revenue": ["1000", "1100", "1210", "1331"],
                                 "cost_of_sales": ["600", "650", "710", "760"], "operating_expenses": ["200", "220", "240", "260"],
                                 "net_income": ["120", "140", "160", "190"], "total_assets": ["2000", "2100", "2250", "2400"],
                                 "equity": ["900", "980", "1080", "1200"]}},
    "portfolioperf": {"objective": "What return did the portfolio earn over these periods?", "method": "portfolio_performance", "currency": "USD", "period": "period",
                    "inputs": {"periods": [{"label": "week 1", "start_nav": "10000", "end_nav": "10250", "flow": "0"}, {"label": "week 2", "start_nav": "10250", "end_nav": "10100", "flow": "0"}]}},
    "portfolioval": {"objective": "What is this portfolio worth today?", "method": "portfolio_valuation", "currency": "USD", "period": "point in time",
                     "inputs": {"holdings": [{"symbol": "AAPL", "shares": "10", "price": "200"},
                                                {"symbol": "MSFT", "shares": "5", "price": "400"}], "cash": "1000"}},

}

# The accounts preset must be the documented example spec; the earlier inline chart
# drifted from `accounts.EXAMPLE_SPEC` and broke the statement modules that build on it.
PRESETS["accounts"]["inputs"]["spec"] = copy.deepcopy(accounts.EXAMPLE_SPEC)

def _template_payload(template_id):
    """A template description plus the completion profile, when it has one."""
    payload = templates.describe(template_id)
    extra = product_profiles.describe_extra(template_id)
    if extra:
        payload["completion"] = extra
    return payload


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json", filename=None):
        b = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b)))
        if filename:
            # A document download carries its own name, so the browser saves
            # "PESTEL and Break-even ... .docx" instead of the id it fetched. The
            # plain name is kept ASCII for old clients; the encoded one is exact.
            name = re.sub("[\\r\\n\"\\\\]", " ", str(filename)).strip() or "download"
            plain = re.sub(r"[^ -~]", "", name).strip() or "download"
            self.send_header("Content-Disposition",
                             'attachment; filename="%s"; filename*=UTF-8\'\'%s'
                             % (plain, quote(name)))
        self.send_header("X-Content-Type-Options", "nosniff")
        # Every response is computed fresh from the checkout on disk. A cached copy is
        # therefore always wrong after a change, and worse, it looks current. The build
        # pill only helps once the page has actually reloaded, so refuse to cache at all.
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.end_headers(); self.wfile.write(b)
        started = getattr(self, "_started", None)
        if started is not None:
            product_ops.log_request(self.command, self.path, code,
                                    (time.monotonic() - started) * 1000.0)   # method/path/status/ms only: no body
    def _body(self, maxb=None):
        n = int(self.headers.get("Content-Length") or 0)
        if n > (maxb or MAXBODY): raise ValueError("body too large")
        return json.loads(self.rfile.read(n) or b"{}", parse_float=Decimal)
    def _asset(self, name):
        """Serve one file from `web/assets` (the logo and the tab icons).

        The name is resolved and checked to stay inside `web/assets`, so a
        traversal attempt cannot read anything else on this machine.
        """
        root = os.path.realpath(os.path.join(WEB, "assets"))
        target = os.path.realpath(os.path.join(root, name))
        if target != root and not target.startswith(root + os.sep):
            return self._send(404, {"error": "no such asset"})
        kinds = {"png": "image/png", "svg": "image/svg+xml", "ico": "image/x-icon"}
        kind = kinds.get(target.rsplit(".", 1)[-1].lower(), "application/octet-stream")
        try:
            with open(target, "rb") as f: return self._send(200, f.read(), kind)
        except OSError:
            return self._send(404, {"error": "no such asset"})
    def do_GET(self):
        self._started = time.monotonic()
        try:
            if self.path == "/api/health":
                return self._send(200, product_ops.health({"sandbox": "on" if SANDBOX_ENABLED else "off (development)",
                                                          "model_assistance": bool(MODELS)}))
            if urlparse(self.path).path == "/":
                with open(os.path.join(WEB, "index.html"), "rb") as f: return self._send(200, f.read(), "text/html; charset=utf-8")
            if self.path == "/account.html":
                with open(os.path.join(WEB, "account.html"), "rb") as f: return self._send(200, f.read(), "text/html; charset=utf-8")
            if self.path == "/pricing.html":
                # Pricing is a dialog in the workbench, not a page of its own. The old URL stays
                # alive as a hop so a bookmark or a typed address still lands on the plans.
                return self._send(200, b'<!doctype html><meta charset="utf-8"><title>Pricing - Smart BusinessWriter</title>'
                                       b'<meta http-equiv="refresh" content="0;url=/?pricing=1">'
                                       b'<p style="font-family:system-ui;padding:24px">Opening the pricing dialog. '
                                       b'<a href="/?pricing=1">Continue</a></p>',
                                  "text/html; charset=utf-8")
            if self.path.startswith("/assets/"):
                return self._asset(self.path[len("/assets/"):].split("?")[0])
            if self.path == "/api/presets": return self._send(200, PRESETS)
            if self.path == "/api/intake" or self.path.startswith("/api/intake?"):
                return self._send(200, {"files": product_intake.list_files()})
            text_url = urlparse(self.path)
            im = re.fullmatch(r"/api/intake/([0-9a-f]{12})/text", text_url.path)
            if im:
                qs = parse_qs(text_url.query)
                try: return self._send(200, product_intake.extracted_text(im[1], (qs.get("limit") or [4000])[0]))
                except product_intake.IntakeNotFound as e: return self._send(404, {"error": str(e)})
                except product_intake.IntakeError as e: return self._send(422, {"error": str(e)})
            im = re.fullmatch(r"/api/intake/([0-9a-f]{12})/sources", text_url.path)
            if im:
                try:
                    return self._send(200, product_intake.declared_sources(im[1]))
                except product_intake.IntakeNotFound as e: return self._send(404, {"error": str(e)})
                except product_intake.IntakeError as e: return self._send(422, {"error": str(e)})
            im = re.fullmatch(r"/api/intake/([0-9a-f]{12})", self.path)
            if im:
                try: return self._send(200, product_intake.load(im[1]))
                except product_intake.IntakeNotFound as e: return self._send(404, {"error": str(e)})
                except product_intake.IntakeError as e: return self._send(422, {"error": str(e)})
            if self.path.startswith(product_api.BILLING_ROUTE):
                return self._send(*product_api.handle("GET", self.path))
            if self.path.startswith(product_api.CASE_ROUTE):
                result = product_api.handle("GET", self.path)
                if len(result) == 4:
                    code, payload, ctype, filename = result
                    return self._send(code, payload, ctype, filename=filename)
                return self._send(*result)
            if self.path.startswith("/api/portfolios"): return self._portfolios("GET")
            u = urlparse(self.path); qs = parse_qs(u.query)
            if u.path == "/api/market/fx":
                try: return self._send(200, product_marketdata.fx_rate((qs.get("base") or [""])[0], (qs.get("quote") or [""])[0], (qs.get("date") or [None])[0]))
                except product_marketdata.MarketDataError as e: return self._send(422, {"error": str(e)})
            if u.path == "/api/market/status":
                return self._send(200, product_marketdata.status())
            if u.path == "/api/market/riskfree":
                try: return self._send(200, product_marketdata.riskfree_rate((qs.get("maturity") or ["10Y"])[0]))
                except product_marketdata.MarketDataError as e: return self._send(422, {"error": str(e)})
            if u.path == "/api/market/quote":
                try: return self._send(200, product_marketdata.equity_quote((qs.get("symbol") or [""])[0]))
                except product_marketdata.MarketDataError as e: return self._send(422, {"error": str(e)})
            if u.path == "/api/market/fundamentals":
                try: return self._send(200, product_marketdata.sec_fundamentals((qs.get("symbol") or [""])[0]))
                except product_marketdata.MarketDataError as e: return self._send(422, {"error": str(e)})
            if u.path == "/api/market/filings":
                try:
                    return self._send(200, product_marketdata.sec_filings(
                        (qs.get("ticker") or [""])[0], (qs.get("form") or ["10-K"])[0],
                        (qs.get("count") or ["5"])[0]))
                except product_marketdata.MarketDataError as e: return self._send(422, {"error": str(e)})
            if u.path == "/api/market/macro":
                try:
                    return self._send(200, product_marketdata.worldbank_indicator(
                        (qs.get("country") or [""])[0], (qs.get("indicator") or ["gdp_growth"])[0],
                        (qs.get("years") or ["5"])[0]))
                except product_marketdata.MarketDataError as e: return self._send(422, {"error": str(e)})
            if u.path == "/api/frameworks":
                q = (qs.get("q") or [""])[0]; ty = (qs.get("type") or [None])[0]
                if ty and ty not in registry.TYPE_LABEL: return self._send(400, {"error": "type must be F, M, Q or T"})
                return self._send(200, {"registry": {"version": registry.load()["registry_version"], "hash": registry.load()["hash"]}, "results": registry.search(q, ty, min(int((qs.get("limit") or [10])[0]), 25))})
            fm = re.fullmatch(r"/api/frameworks/([A-Za-z0-9\-]+)", u.path)
            if fm: return self._send(200, registry.brief(registry.get(fm[1])))
            if u.path == "/api/assist/config":
                if not MODELS: return self._send(200, {"enabled": False, "reason": "No model provider is configured on this server. Set BP_LLM_PROVIDER and BP_LLM_MODEL (and the provider's API key) and restart."})
                c = MODELS.config; return self._send(200, {"enabled": c.enabled, "provider": MODELS.builder.name, "builder_model": MODELS.builder.model, "reviewer_model": MODELS.reviewer.model, "same_model": MODELS.same_model,
                                                          "limits": {"max_calls_total": c.max_calls_total, "calls_used": MODELS.calls, "max_input_chars": c.max_input_chars}, "privacy_notice": c.privacy_notice, "prompt_version": assist.PROMPT_VERSION})
            if u.path == "/api/currencies":
                return self._send(200, {"currencies": currency.catalog(), "note": "ISO 4217 codes and their minor units (decimal places). No exchange rates are provided: a conversion needs a declared rate (B-069)."})
            if u.path == "/api/literature/sources":
                names = ["auto"] + [k for k in LITERATURE_AUTO if k in LITERATURE_SOURCES] + [k for k in LITERATURE_SOURCES if k not in LITERATURE_AUTO]
                return self._send(200, {"sources": [{"name": n, "label": LITERATURE_LABELS.get(n, n)} for n in names], "notice": LITERATURE_NOTICE,
                                        "citation_styles": list(literature.CITATION_STYLES), "citation_notices": dict(literature.CITATION_NOTICES),
                                        "priority": [k for k in LITERATURE_AUTO if k in LITERATURE_SOURCES] or list(LITERATURE_SOURCES), "log_enabled": bool(LITERATURE_LOG)})
            if u.path == "/api/literature/drift":
                if not LITERATURE_LOG: return self._send(200, {"enabled": False, "checked": 0, "result": [], "notice": "The retrieval log is disabled on this server."})
                try: n = max(1, min(int((qs.get("limit") or [10])[0]), 25))
                except ValueError: return self._send(400, {"error": "limit must be an integer"})
                srcs = [LITERATURE_SOURCES[k] for k in LITERATURE_AUTO if k in LITERATURE_SOURCES] or list(LITERATURE_SOURCES.values())
                try: rep = literature.drift_check(LITERATURE_LOG, n, srcs)
                except literature.SourceError as e: return self._send(502, {"error": str(e)})
                return self._send(200, rep)
            if u.path == "/api/literature/log":
                if not LITERATURE_LOG: return self._send(200, {"enabled": False, "entries": [], "notice": "The retrieval log is disabled on this server."})
                try: n = max(1, min(int((qs.get("limit") or [20])[0]), 100))
                except ValueError: return self._send(400, {"error": "limit must be an integer"})
                try: entries = literature.read_log(LITERATURE_LOG, n)
                except literature.SourceError as e: return self._send(502, {"error": str(e)})
                return self._send(200, {"enabled": True, "format": literature.LOG_FORMAT, "entries": entries,
                                        "notice": "Local append-only retrieval log: source, UTC time, response SHA-256. Entries are not evidence that the metadata is correct."})
            if u.path == "/api/templates": return self._send(200, [_template_payload(k) for k in templates.TEMPLATES])
            tm = re.fullmatch(r"/api/templates/(\w+)", u.path)
            if tm:
                if tm[1] not in templates.TEMPLATES: return self._send(404, {"error": "unknown template"})
                return self._send(200, _template_payload(tm[1]))
            if self.path == "/api/methods": return self._send(200, methods.list_methods())
            m = re.fullmatch(r"/api/sessions/(\w+)", self.path)
            if m: return self._send(200, M.get(m[1]).to_dict())
            self._send(404, {"error": "not found"})
        except KeyError as e: self._send(404, {"error": "unknown session" if "registry" not in str(e) else str(e).strip("'\"")})
    def do_POST(self):
        self._started = time.monotonic()
        try:
            if self.path.startswith(product_api.BILLING_ROUTE):
                return self._send(*product_api.handle("POST", self.path, self._body()))
            if self.path.startswith(product_api.CASE_ROUTE):
                n = int(self.headers.get("Content-Length") or 0)
                if n > MAXBODY: raise ValueError("body too large")
                return self._send(*product_api.handle("POST", self.path, json.loads(self.rfile.read(n) or b"{}")))
            if self.path.startswith("/api/portfolios"): return self._portfolios("POST")
            if self.path == "/api/sessions": return self._send(201, M.create(self._body()).to_dict())
            pm = re.fullmatch(r"/api/sessions/(\w+)/paper", self.path)
            if pm: return self._session_paper(pm[1], self._body())
            if self.path == "/api/assist": return self._assist(self._body())
            if self.path == "/api/intake": return self._intake_upload(self._body(INGEST_MAXBODY))
            im = re.fullmatch(r"/api/intake/([0-9a-f]{12})/ingest", self.path)
            if im: return self._intake_ingest(im[1], self._body())
            im = re.fullmatch(r"/api/intake/([0-9a-f]{12})/extract", self.path)
            if im:
                self._body()
                try: return self._send(200, product_intake.extract(im[1]))
                except product_intake.IntakeNotFound as e: return self._send(404, {"error": str(e)})
                except product_intake.IntakeError as e: return self._send(422, {"error": str(e)})
            im = re.fullmatch(r"/api/intake/([0-9a-f]{12})/sources", self.path)
            if im:
                # Read a stored .bib/.ris as the student's own source list (B-182): cited,
                # never evidence.  Nothing is resolved or fetched.
                self._body()
                return self._intake_sources(im[1])
            im = re.fullmatch(r"/api/intake/([0-9a-f]{12})/brief", self.path)
            if im:
                # Use a stored attachment as the paper's instruction.  The text comes back
                # unverified and nothing is started: the page puts it in the brief box and
                # the student decides.
                self._body()
                try: return self._send(200, product_intake.use_as_brief(im[1]))
                except product_intake.IntakeNotFound as e: return self._send(404, {"error": str(e)})
                except product_intake.IntakeError as e: return self._send(422, {"error": str(e)})
            im = re.fullmatch(r"/api/intake/([0-9a-f]{12})/rubric", self.path)
            if im:
                # Read a stored attachment as the paper's marking guide.  Nothing is
                # started: the page holds the parsed rubric, shows the student what was
                # read from it, and follows it only once they confirm.
                self._body()
                try: return self._send(200, product_intake.use_as_rubric(im[1]))
                except product_intake.IntakeNotFound as e: return self._send(404, {"error": str(e)})
                except product_intake.IntakeError as e: return self._send(422, {"error": str(e)})
            im = re.fullmatch(r"/api/intake/([0-9a-f]{12})/map", self.path)
            if im:
                # Propose a method's inputs from a stored table.  Nothing runs: the page
                # fills the form with these values and the student presses the button.
                b = self._body()
                if not isinstance(b, dict) or not b.get("method") or not isinstance(b.get("columns"), dict):
                    return self._send(422, {"error": "map needs {method, columns}"})
                try: return self._send(200, product_intake.mapped_request(im[1], b["method"], b["columns"]))
                except product_intake.IntakeNotFound as e: return self._send(404, {"error": str(e)})
                except product_intake.IntakeError as e: return self._send(422, {"error": str(e)})
            if self.path == "/api/ingest": return self._ingest(self._body(INGEST_MAXBODY))
            if self.path == "/api/literature/verify": return self._literature(self._body())
            m = re.fullmatch(r"/api/sessions/(\w+)/(confirm|reject)", self.path)
            if m:
                body = self._body(); s = M.get(m[1])
                if not isinstance(body, dict): raise ValueError("body must be an object")
                s.confirm(m[2] == "confirm", body.get("frameworks")); return self._send(200, s.to_dict())
            self._send(404, {"error": "not found"})
        except KeyError: self._send(404, {"error": "unknown session"})
        except (ValueError, TypeError) as e: self._send(400, {"error": str(e)})
    def do_DELETE(self):
        self._started = time.monotonic()
        try:
            im = re.fullmatch(r"/api/intake/([0-9a-f]{12})", self.path)
            if im:
                try:
                    product_intake.delete(im[1]); return self._send(200, {"deleted": im[1]})
                except product_intake.IntakeNotFound as e: return self._send(404, {"error": str(e)})
                except product_intake.IntakeError as e: return self._send(422, {"error": str(e)})
            if self.path.startswith(product_api.CASE_ROUTE): return self._send(*product_api.handle("DELETE", self.path))
            if self.path.startswith("/api/portfolios"): return self._portfolios("DELETE")
            self._send(404, {"error": "not found"})
        except (ValueError, TypeError) as e: self._send(400, {"error": str(e)})
    def _portfolios(self, verb):
        """Portfolio Lab storage routes; the snapshot route calls the frozen method library."""
        path = urlparse(self.path).path
        parts = [part for part in path.split("/") if part]
        body = self._body() if verb in ("POST", "PATCH") else None
        try:
            if len(parts) == 3 and parts[1] == "portfolios" and parts[2] == "instruments":
                if verb != "GET":
                    return self._send(405, {"error": "method %s is not allowed on the instrument list" % verb})
                return self._send(200, product_instruments.bundle())
            if len(parts) == 2 and parts[1] == "portfolios":
                if verb == "GET": return self._send(200, {"portfolios": product_portfolios.summaries()})
                if verb == "POST":
                    if not isinstance(body, dict): raise ValueError("body must be an object")
                    doc = product_portfolios.create(body.get("name"), body.get("base_currency", "USD"),
                                                    body.get("benchmark", ""), body.get("mode", "paper"),
                                                    objective=body.get("objective", ""),
                                                    roster=body.get("roster", ""))
                    return self._send(201, doc)
            if len(parts) < 3 or parts[1] != "portfolios": return self._send(404, {"error": "not found"})
            portfolio_id = parts[2]
            if len(parts) == 3:
                if verb == "GET": return self._send(200, product_portfolios.load(portfolio_id))
                if verb == "PATCH": return self._send(200, product_portfolios.update(portfolio_id, body or {}))
                if verb == "DELETE":
                    product_portfolios.delete(portfolio_id)
                    return self._send(200, {"deleted": portfolio_id})
            action = parts[3]
            if action == "holdings" and verb == "POST" and len(parts) == 5 and parts[4] == "import":
                if not isinstance(body, dict): raise ValueError("body must be an object")
                rows = product_portfolios.import_holdings(portfolio_id, body.get("text"))
                return self._send(200, {"holdings": rows})
            if action == "prices" and verb == "POST" and len(parts) == 5 and parts[4] == "import":
                if not isinstance(body, dict): raise ValueError("body must be an object")
                document = product_portfolios.import_prices(portfolio_id, body.get("text"),
                                                             body.get("date"), body.get("source", "user"))
                return self._send(200, document)
            if action == "holdings" and verb == "POST":
                if not isinstance(body, dict): raise ValueError("body must be an object")
                rows = product_portfolios.add_holding(portfolio_id, body.get("symbol"), body.get("shares"),
                                                       body.get("cost_basis", "0"),
                                                       body.get("rationale", ""))
                return self._send(200, {"holdings": rows})
            if action == "holdings" and verb == "DELETE" and len(parts) == 5:
                rows = product_portfolios.remove_holding(portfolio_id, parts[4])
                return self._send(200, {"holdings": rows})
            if action == "prices" and verb == "POST" and len(parts) == 5 and parts[4] == "fetch":
                if not isinstance(body, dict): raise ValueError("body must be an object")
                return self._portfolio_price_fetch(portfolio_id, body)
            if action == "prices" and verb == "POST":
                if not isinstance(body, dict): raise ValueError("body must be an object")
                document = product_portfolios.set_price(portfolio_id, body.get("symbol"), body.get("date"),
                                                        body.get("price"), body.get("source", "user"))
                return self._send(200, document)
            if action == "snapshots" and verb == "GET":
                return self._send(200, product_portfolios.load(portfolio_id)["snapshots"])
            if action == "journal" and verb == "GET" and len(parts) == 4:
                return self._send(200, {"journal": product_portfolios.journal(portfolio_id)})
            if action == "journal" and verb == "POST" and len(parts) == 4:
                if not isinstance(body, dict): raise ValueError("body must be an object")
                entry = product_portfolios.save_journal(portfolio_id, body.get("date"), body.get("note", ""),
                                                        body.get("flow", "0"), body.get("benchmark", ""))
                return self._send(200, entry)
            if action == "journal" and verb == "DELETE" and len(parts) == 5:
                product_portfolios.remove_journal(portfolio_id, parts[4])
                return self._send(200, {"deleted": parts[4]})
            if action == "performance" and verb == "GET" and len(parts) == 4:
                return self._send(200, self._performance_payload(portfolio_id))
            if action == "snapshot" and verb == "GET" and len(parts) == 5:
                return self._send(200, product_portfolios.snapshot(portfolio_id, parts[4]))
            if action == "snapshot" and verb == "POST":
                return self._portfolio_snapshot(portfolio_id, body or {})
            if action == "export" and verb == "POST":
                return self._portfolio_export(portfolio_id, body or {})
            return self._send(404, {"error": "not found"})
        except product_portfolios.PortfolioNotFound as error:
            return self._send(404, {"error": str(error)})
        except (product_portfolios.PortfolioError, ValueError, TypeError) as error:
            return self._send(422, {"error": str(error)})

    def _performance_payload(self, portfolio_id):
        """Chain the stored snapshots through the frozen performance method.

        The flow and benchmark level recorded on a date belong to the period that
        ends on that date. A benchmark is used only when every period carries both
        levels; otherwise the return is reported without one and the gap is named.
        """
        bundle = product_portfolios.load(portfolio_id)
        snapshots = bundle["snapshots"]
        if len(snapshots) < 2:
            raise ValueError("at least two dated snapshots are required for a return")
        entries = {entry["date"]: entry for entry in bundle.get("journal", [])}
        loaded = [product_portfolios.snapshot(portfolio_id, row["date"]) for row in snapshots]
        periods, starts, ends = [], [], []
        benchmark_complete = True
        for previous, current in zip(loaded, loaded[1:]):
            entry = entries.get(current["date"], {})
            periods.append({"label": current["date"],
                            "start_nav": previous["outputs"].get("nav", ""),
                            "end_nav": current["outputs"].get("nav", ""),
                            "flow": str(entry.get("flow", "0") or "0")})
            b_start = str(entries.get(previous["date"], {}).get("benchmark", "") or "")
            b_end = str(entry.get("benchmark", "") or "")
            if b_start and b_end:
                starts.append(b_start); ends.append(b_end)
            else:
                benchmark_complete = False
        inputs = {"periods": periods}
        if benchmark_complete and starts:
            inputs["benchmark_start"] = starts
            inputs["benchmark_end"] = ends
        method = methods.LIBRARY["portfolio_performance"]
        issues = methods.validate_inputs(method, inputs) + method.profile(inputs)
        if issues:
            raise ValueError("; ".join(issues))
        results = method.tests(inputs, method.impl)
        failed = [name for name, ok in results if not ok]
        if failed:
            raise ValueError("the performance checks failed: " + ", ".join(failed))
        outputs = method.impl(inputs)
        appendix = outputs.pop("_appendix", {})
        outputs.pop("_checks", None)
        return {"outputs": {key: str(value) for key, value in outputs.items()},
                "periods": appendix.get("periods", []),
                "conventions": appendix.get("conventions", ""),
                "benchmark_used": "benchmark_return" in outputs,
                "benchmark_complete": benchmark_complete,
                "checks": [{"name": name, "ok": bool(ok)} for name, ok in results]}

    def _portfolio_price_fetch(self, portfolio_id, body):
        """Fetch a quote per holding from the configured free equity source.

        The key lives in the server's environment, never in the page. Every quote
        is stored with its source and its real trading day; a symbol that fails is
        named rather than filled, and a date with a saved snapshot is refused before
        anything is fetched.
        """
        bundle = product_portfolios.load(portfolio_id)
        holdings = bundle["holdings"]
        if not holdings:
            raise ValueError("add at least one holding before fetching prices")
        day = str(body.get("date") or "").strip()
        if not day:
            raise ValueError("a price date is required (YYYY-MM-DD)")
        if day in {row.get("date") for row in bundle["snapshots"]}:
            raise ValueError("the snapshot for %s is already saved; its prices are immutable" % day)
        status = product_marketdata.status()
        if not status["sources"].get("equity"):
            raise ValueError("equity quotes need an Alpha Vantage key: set BP_ALPHAVANTAGE_KEY and restart the server")
        stored, failed, quota = {}, [], None
        for row in holdings:
            symbol = row["symbol"]
            try:
                quote = product_marketdata.equity_quote(symbol)
                product_portfolios.set_price(portfolio_id, symbol, day, quote["value"],
                                             source=quote.get("source", "Alpha Vantage"),
                                             as_of=quote.get("as_of", ""))
                stored[symbol] = {"price": str(quote["value"]), "as_of": quote.get("as_of", ""),
                                  "source": quote.get("source", "")}
            except product_marketdata.MarketDataQuota as error:
                quota = str(error)
                failed.append({"symbol": symbol, "error": str(error)})
            except (product_marketdata.MarketDataError, ValueError, TypeError) as error:
                failed.append({"symbol": symbol, "error": str(error)})
        if not stored and quota:
            return self._send(429, {"error": "the free equity source's daily limit is reached; "
                                             "enter prices manually or paste them, or retry tomorrow",
                                    "quota": True, "failed": failed})
        if not stored and failed:
            raise ValueError("; ".join("%s: %s" % (row["symbol"], row["error"]) for row in failed))
        return self._send(200, {"prices": stored, "failed": failed, "quota": bool(quota), "date": day})

    def _portfolio_snapshot(self, portfolio_id, body):
        bundle = product_portfolios.load(portfolio_id)
        holdings = bundle["holdings"]
        if not holdings:
            return self._send(422, {"error": "add at least one holding before the snapshot"})
        day = str(body.get("date") or "").strip()
        if not day:
            return self._send(422, {"error": "a snapshot date is required (YYYY-MM-DD)"})
        supplied = body.get("prices") or {}
        if isinstance(supplied, dict):
            for symbol, point in supplied.items():
                value = point.get("price") if isinstance(point, dict) else point
                source = point.get("source", "user") if isinstance(point, dict) else "user"
                product_portfolios.set_price(portfolio_id, symbol, day, value, source)
        try:
            prices = product_portfolios.prices(portfolio_id, day)["prices"]
        except product_portfolios.PortfolioNotFound:
            prices = {}
        missing = [row["symbol"] for row in holdings if row["symbol"] not in prices]
        if missing:
            return self._send(422, {"error": "missing prices for " + ", ".join(missing), "missing": missing})
        inputs = {"holdings": [{"symbol": row["symbol"], "shares": str(row["shares"]),
                                "price": str(prices[row["symbol"]]["price"])} for row in holdings],
                  "cash": str(body.get("cash", "0") or "0")}
        method = methods.LIBRARY["portfolio_valuation"]
        issues = methods.validate_inputs(method, inputs) + method.profile(inputs)
        if issues:
            return self._send(422, {"error": "; ".join(issues)})
        results = method.tests(inputs, method.impl)
        failed = [name for name, ok in results if not ok]
        if failed:
            return self._send(422, {"error": "the valuation checks failed: " + ", ".join(failed)})
        outputs = method.impl(inputs)
        appendix = outputs.pop("_appendix", {})
        outputs.pop("_checks", None)
        snapshot = {
            "date": day, "inputs": inputs,
            "outputs": {key: str(value) for key, value in outputs.items()},
            "positions": appendix.get("positions", []),
            "conventions": appendix.get("conventions", ""),
            "prices": {symbol: {"price": str(point["price"]), "source": point.get("source", ""),
                                "as_of": point.get("as_of", day)}
                       for symbol, point in prices.items() if symbol in {row["symbol"] for row in holdings}},
            "checks": [{"name": name, "ok": bool(ok)} for name, ok in results],
            "method": "portfolio_valuation", "version": method.version,
        }
        return self._send(201, product_portfolios.save_snapshot(portfolio_id, snapshot))

    def _portfolio_export(self, portfolio_id, body):
        bundle = product_portfolios.load(portfolio_id)
        snapshots = bundle["snapshots"]
        if not snapshots:
            return self._send(422, {"error": "create a snapshot before exporting"})
        date = str(body.get("date") or max(row["date"] for row in snapshots))
        snapshot = product_portfolios.snapshot(portfolio_id, date)
        performance = None
        if bundle["portfolio"].get("mode") == "fund" and len(snapshots) >= 2:
            try:
                performance = self._performance_payload(portfolio_id)
            except ValueError:
                performance = None
        data, filename = product_portfolio_docx.render(bundle["portfolio"], snapshot,
                                                       holdings=bundle.get("holdings", []),
                                                       performance=performance,
                                                       journal=bundle.get("journal", []))
        return self._send(200, {"filename": filename, "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                "data": base64.b64encode(data).decode("ascii")})

    def _assist(self, b):
        if not isinstance(b, dict): raise ValueError("body must be an object")
        if not MODELS or not MODELS.config.enabled: return self._send(503, {"error": "model assistance is not configured on this server"})
        task, consent = b.get("task"), b.get("consent") is True
        try:
            if task == "facts": res = assist.extract_facts(MODELS, b.get("case_text"), consent, b.get("pii_acknowledged") is True)
            elif task == "alternatives": res = assist.propose_alternatives(MODELS, b.get("facts"), b.get("objective"), consent)
            elif task == "critique":
                if not isinstance(b.get("facts"), list) or not isinstance(b.get("alternatives"), list): raise assist.AssistError("facts and alternatives are required")
                if not all(isinstance(x, dict) and isinstance(x.get("id"), str) and isinstance(x.get("text", x.get("name", "")), str) for x in b["facts"] + b["alternatives"]): raise assist.AssistError("each fact and alternative needs an id")
                res = assist.critique(models=MODELS, facts=b["facts"], alternatives=b["alternatives"], consent=consent)
            else: raise ValueError("task must be facts, alternatives or critique")
        except llm.ConsentRequired as e: return self._send(400, {"error": str(e)})
        except llm.BudgetExceeded as e: return self._send(429, {"error": str(e)})
        except llm.ProviderError as e: return self._send(502, {"error": str(e)})
        except assist.AssistError as e: return self._send(422, {"error": str(e), "rejected": e.rejected})
        rid = uuid.uuid4().hex[:12]; run = {**res["run"], "run_id": rid, "accepted_by_code": len(res.get("proposals", res.get("items", []))), "rejected_by_code": len(res["rejected"])}
        ASSIST_RUNS[rid] = run; res["run"] = run; return self._send(200, res)
    def _literature(self, b):
        global LITERATURE_CALLS
        if not isinstance(b, dict): raise ValueError("body must be an object")
        title, doi, name = b.get("title"), b.get("doi"), b.get("source") or "auto"
        if not isinstance(title, str) or not title.strip(): raise ValueError("title is required")
        if not isinstance(name, str) or (name != "auto" and name not in LITERATURE_SOURCES):
            raise ValueError("source must be 'auto' or one of: " + ", ".join(sorted(LITERATURE_SOURCES)))
        style = b.get("cite")
        if style is not None and (not isinstance(style, str) or style not in literature.CITATION_STYLES):
            raise ValueError("cite must be one of: " + ", ".join(literature.CITATION_STYLES))
        if LITERATURE_CALLS >= LITERATURE_CAP: return self._send(429, {"error": "literature verification call cap reached for this server run"})
        LITERATURE_CALLS += 1
        try:
            if name == "auto":
                srcs = [LITERATURE_SOURCES[k] for k in LITERATURE_AUTO if k in LITERATURE_SOURCES] or list(LITERATURE_SOURCES.values())
                ref = literature.verify_reference(title, doi, sources=srcs, log=LITERATURE_LOG or None)
            else:
                ref = literature.verify_reference(title, doi, LITERATURE_SOURCES[name], log=LITERATURE_LOG or None)
        except literature.SourceError as e:
            return self._send(502, {"error": str(e)})
        body = {"reference": {"title": ref.title, "doi": ref.doi, "authors": list(ref.authors), "year": ref.year,
                              "container": ref.container, "volume": ref.volume, "issue": ref.issue, "pages": ref.pages,
                              "reference_type": ref.reference_type, "resolved_title": ref.resolved_title, "status": ref.status, "source": ref.source,
                              "retrieved_at": ref.retrieved_at, "response_hash": ref.response_hash},
                "notice": LITERATURE_NOTICE}
        if style: body["citation"] = literature.format_citation(ref, style)
        return self._send(200, body)
    def log_message(self, *a): pass

    def _ingest(self, b):
        try:
            table = ingest.decode_request(b)
            body = {"table": table}
            if isinstance(b, dict) and b.get("map") is not None:
                mp = b["map"]
                if not isinstance(mp, dict) or "method" not in mp or "columns" not in mp: raise ingest.IngestError("map needs {method, columns}")
                body["mapped_request"] = ingest.to_method_inputs(table, mp["method"], mp["columns"])
        except ingest.IngestError as e: return self._send(422, {"error": str(e)})
        return self._send(200, body)

    def _intake_upload(self, b):
        """Store one attached file; read it only when the frozen ingest module can."""
        if not isinstance(b, dict): raise ValueError("body must be an object")
        encoded = b.get("content_base64")
        if not isinstance(encoded, str) or not encoded.strip(): raise ValueError("content_base64 is required")
        try: raw = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError): raise ValueError("content_base64 is not valid base64")
        merged = b.get("merged", "refuse")
        if merged not in ingest.MERGED_POLICIES:
            return self._send(422, {"error": "merged must be one of: " + ", ".join(ingest.MERGED_POLICIES)})
        record = product_intake.save(b.get("filename"), raw, b.get("content_type"), b.get("role"))
        if record["kind"] != "structured": return self._send(201, record)
        try:
            table = ingest.read_table(record["filename"], raw, sheet=b.get("sheet"), merged=merged)
        except ingest.IngestError as e:
            return self._send(201, product_intake.fail(record["id"], str(e)))
        return self._send(201, product_intake.attach_table(record["id"], table))

    def _session_paper(self, session_id, b):
        """The delivered computation as a downloadable paper: the same record, as Word or Excel.

        It adds no sentence the screen does not show.  The declared sources are the student's own
        citations (B-182): their own section, headed "not evidence", never merged into the
        references of retrieved evidence.
        """
        if not isinstance(b, dict): raise ValueError("body must be an object")
        delivery = (M.get(session_id).to_dict() or {}).get("delivery") or {}
        if delivery.get("status") != "delivered":
            return self._send(409, {"error": "the paper is written only after the result is delivered; "
                                             "confirm the specification first"})
        fmt = str(b.get("format") or "docx").lower()
        if fmt not in ("docx", "xlsx"):
            return self._send(422, {"error": "format must be docx or xlsx"})
        declared = []
        for file_id in b.get("source_files") or []:
            try:
                declared.extend(product_intake.declared_sources(file_id)["citations"])
            except (product_intake.IntakeError, ValueError) as error:
                declared.append("A declared source list could not be read: " + str(error)[:120])
        title = str(b.get("title") or "") or None
        if fmt == "xlsx":
            return self._send(200,
                              product_session_paper.xlsx_bytes(delivery, declared, title, session_id),
                              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                              product_session_paper.filename(delivery, "xlsx", title))
        return self._send(200, product_session_paper.docx_bytes(delivery, declared, title),
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                          product_session_paper.filename(delivery, "docx", title))

    def _intake_sources(self, file_id):
        """Read a stored .bib/.ris as the student's own source list (B-182).

        The entries are the student's citations: nothing here resolves a DOI, fetches a
        page or claims the source exists.  An entry that cannot be read is returned as a
        named problem, and a file with no source reader is refused with the reason.
        """
        try:
            record = product_intake.load(file_id)
            filename, raw = product_intake.payload(file_id)
        except product_intake.IntakeNotFound as e:
            return self._send(404, {"error": str(e)})
        except product_intake.IntakeError as e:
            return self._send(422, {"error": str(e)})
        if record.get("kind") != "sources":
            return self._send(422, {"error": "attach a .bib or .ris source list; %s has no source reader"
                                    % (record.get("ext") or "this file")})
        try:
            table = product_sources.parse(filename, raw)
        except product_sources.SourcesError as e:
            product_intake.fail(file_id, str(e))
            return self._send(422, {"error": str(e)})
        return self._send(200, product_intake.attach_sources(file_id, table))

    def _intake_ingest(self, file_id, b):
        """Read a stored structured file again, with sheet/merged options."""
        if not isinstance(b, dict): raise ValueError("body must be an object")
        merged = b.get("merged", "refuse")
        if merged not in ingest.MERGED_POLICIES:
            return self._send(422, {"error": "merged must be one of: " + ", ".join(ingest.MERGED_POLICIES)})
        try:
            record = product_intake.load(file_id)
            filename, raw = product_intake.payload(file_id)
        except product_intake.IntakeNotFound as e:
            return self._send(404, {"error": str(e)})
        except product_intake.IntakeError as e:
            return self._send(422, {"error": str(e)})
        if record["kind"] != "structured":
            return self._send(422, {"error": "no reader is implemented for this file type; it is stored only"})
        try:
            table = ingest.read_table(filename, raw, sheet=b.get("sheet"), merged=merged)
        except ingest.IngestError as e:
            product_intake.fail(file_id, str(e))
            return self._send(422, {"error": str(e)})
        return self._send(200, product_intake.attach_table(file_id, table))

def _load_local_keys(path=None):
    """Load local provider keys into the environment at server startup.

    The file is gitignored (``state/market_keys.json``). An environment variable
    that is already set wins, so a shell export or CI key is never overwritten.
    A missing or malformed file is ignored: the server still starts.
    """
    from pathlib import Path
    candidate = path or os.environ.get("BP_MARKET_KEYS_FILE") or (
        Path(__file__).resolve().parents[2] / "state" / "market_keys.json")
    try:
        data = json.loads(Path(candidate).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    mapping = {
        "alpha_vantage": "BP_ALPHAVANTAGE_KEY",
        "massive": "BP_MASSIVE_KEY",
        "qveris": "BP_QVERIS_KEY",
        "qveris_tool_id": "BP_QVERIS_TOOL_ID",
        "qveris_symbol_param": "BP_QVERIS_SYMBOL_PARAM",
        "qveris_price_path": "BP_QVERIS_PRICE_PATH",
        "qveris_asof_path": "BP_QVERIS_ASOF_PATH",
    }
    loaded = {}
    for key, env in mapping.items():
        value = str(data.get(key) or "").strip()
        if value and not os.environ.get(env):
            os.environ[env] = value
            loaded[env] = True
    return loaded


def serve(port=8000, host="127.0.0.1", sandbox=True, models=None):
    global M, MODELS, SANDBOX_ENABLED
    M = SessionManager(SubprocessSandbox() if sandbox else None, ASSIST_RUNS); MODELS = models if models is not None else llm.from_env()
    SANDBOX_ENABLED = bool(sandbox)
    print(f"Workbench on http://{host}:{port} (sandbox {'ON' if sandbox else 'OFF: development only'}; model assistance {'ON: ' + MODELS.builder.name + ' ' + MODELS.builder.model if MODELS else 'OFF'}; literature ON: {', '.join(LITERATURE_SOURCES)})")
    print("Health: /api/health | cases: /api/cases | request log: " + (str(product_ops.request_log_path()) if product_ops.request_log_path() else "disabled"))
    class _Reusable(ThreadingHTTPServer):
        allow_reuse_address = True
    try:
        _Reusable((host, port), H).serve_forever()
    except OSError as e:
        print(f"server: cannot bind {host}:{port}: {e}")
        raise

if __name__ == "__main__":
    _load_local_keys()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    serve(int(args[0]) if args else 8000, sandbox="--no-sandbox" not in sys.argv)
