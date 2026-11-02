"""Minimal JSON API + static shell (stdlib only; FastAPI can replace this later behind the same routes)."""
import base64, json, os, re, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from decimal import Decimal
from .session import SessionManager
from urllib.parse import urlparse, parse_qs
import uuid
from . import methods, registry, templates, assist, llm, literature, accounts, ingest, currency
from .product import api as product_api, ops as product_ops, intake as product_intake, marketdata as product_marketdata
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
    "marketsize": {"objective": "How big is the market we can actually serve and win?", "method": "market_sizing", "currency": "PHP", "period": "annual",
                   "inputs": {"target_population": "20000", "annual_spend_per_customer": "3000", "serviceable_share": "0.25", "obtainable_share": "0.20"}},
    "startupcapital": {"objective": "How much capital must we raise to open the business?", "method": "startup_capital", "currency": "PHP", "period": "annual",
                       "inputs": {"start_up_costs": "350000", "working_capital": "120000", "contingency_rate": "0.10",
                                  "owner_equity": "150000", "loan_amount": "200000"}},
    "cashrunway": {"objective": "How many months of cash do we have, and how much must we raise?", "method": "cash_runway", "currency": "PHP", "period": "monthly",
                   "inputs": {"opening_cash": "300000", "monthly_net_cash_flow": "-40000", "monthly_growth": "0", "target_months": "9"}},
    "pricing": {"objective": "What price should we set under each pricing rule?", "method": "pricing_decision", "currency": "PHP", "period": "annual",
                "inputs": {"unit_cost": "15", "fixed_cost": "45000", "expected_units": "6000", "markup_rate": "0.60",
                           "target_margin_rate": "0.375", "target_profit": "20000"}},
    "roi": {"objective": "What is the return on the money we invested?", "method": "return_on_investment", "currency": "PHP", "period": "annual",
            "inputs": {"total_investment": "500000", "net_gain": "125000", "years": "3"}},
    "salesprojection": {"objective": "Project our sales, costs and profit for the next twelve months", "method": "sales_projection", "currency": "PHP", "period": "monthly",
                        "inputs": {"start_units": "300", "price": "120", "unit_variable_cost": "55", "fixed_cost_per_period": "12000",
                                   "growth_rate": "0.05", "periods": "12"}},
    "captable": {"objective": "What share does the investor get in this round?", "method": "cap_table_round", "currency": "PHP", "period": "point in time",
                 "inputs": {"pre_money_valuation": "4000000", "investment": "1000000", "founders_shares": "1000000", "option_pool_pct": "0.10"}},
    "funnel": {"objective": "Where do we lose customers between the first contact and the sale?", "method": "sales_funnel", "currency": "PHP", "period": "monthly",
               "inputs": {"stages": [{"name": "store visits", "count": "10000"}, {"name": "inquiries", "count": "2500"}, {"name": "purchases", "count": "500"}],
                          "spend": "25000"}},
    "cohort": {"objective": "How well do we keep the customers we win each month?", "method": "cohort_retention", "currency": "PHP", "period": "monthly",
               "inputs": {"cohort_sizes": ["200", "180", "150"],
                          "retained": [["200", "140", "110", "90"], ["180", "130", "100", "60"], ["150", "120", "95", "70"]]}},
    "demandcurve": {"objective": "What do our price and quantity observations imply about demand?", "method": "demand_curve", "currency": "PHP", "period": "per observation",
                    "inputs": {"prices": ["20", "25", "30", "35", "40"], "quantities": ["400", "340", "280", "220", "160"]}},
    "purchaseintent": {"objective": "What share of the market intends to buy, and how many buyers is that?", "method": "purchase_intent", "currency": "PHP", "period": "cross_section",
                       "inputs": {"definitely": "120", "probably": "80", "maybe": "150", "never": "50", "target_population": "20000", "price": "250"}},
    "campaign": {"objective": "Which campaign paid for itself after the cost of the sale?", "method": "campaign_efficiency", "currency": "PHP", "period": "monthly",
                 "inputs": {"impressions": "250000", "clicks": "6000", "conversions": "220", "spend": "60000",
                            "revenue": "150000", "contribution_margin_rate": "0.45"}},
    "abtest": {"objective": "Did the new page really convert better than the old one?", "method": "ab_test_two_proportion", "period": "per observation",
               "inputs": {"visitors_a": "4000", "conversions_a": "320", "visitors_b": "4000", "conversions_b": "380",
                          "alpha": "0.05", "power": "0.8", "minimum_effect": "0.10"}},
    "attribution": {"objective": "How much credit does each channel get under different attribution rules?", "method": "attribution_split", "currency": "PHP", "period": "monthly",
                    "inputs": {"channels": [{"name": "search", "first_click": "420", "last_click": "260", "linear": "320"},
                                            {"name": "social", "first_click": "180", "last_click": "310", "linear": "290"},
                                            {"name": "email", "first_click": "120", "last_click": "150", "linear": "110"}]}},
    "channelecon": {"objective": "Which acquisition channel is worth the money we spend on it?", "method": "channel_economics", "currency": "PHP", "period": "monthly",
                    "inputs": {"channels": [{"name": "search", "spend": "60000", "new_customers": "400", "contribution_margin": "150", "churn_rate": "0.04"},
                                            {"name": "social", "spend": "35000", "new_customers": "180", "contribution_margin": "95", "churn_rate": "0.06"},
                                            {"name": "referral", "spend": "15000", "new_customers": "150", "contribution_margin": "150", "churn_rate": "0.03"}]}},
    "email": {"objective": "Is our email list growing and is it still engaged?", "method": "email_list_health", "currency": "PHP", "period": "monthly",
              "inputs": {"list_start": "8000", "new_subscribers": "600", "unsubscribes": "90", "bounces": "40",
                         "sends": "7500", "opens": "2250", "clicks": "450", "revenue": "38000"}},
    "social": {"objective": "How far did our posts reach, and how engaged was the audience?", "method": "social_engagement", "currency": "PHP", "period": "monthly",
               "inputs": {"impressions": "150000", "reach": "95000", "engagements": "5700", "followers_start": "18000",
                          "followers_gained": "900", "spend": "25000", "posts": "15"}},
    "web": {"objective": "Which traffic channel brings visits that turn into revenue?", "method": "web_analytics", "currency": "PHP", "period": "monthly",
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
    "mediaplan": {"objective": "What does this media plan buy in reach, frequency and rating points?", "method": "media_plan", "currency": "PHP", "period": "monthly",
                  "inputs": {"population": "1000000",
                             "vehicles": [{"name": "TV prime time", "reach": "450000", "insertions": "8", "cost": "1200000"},
                                          {"name": "Radio drive time", "reach": "300000", "insertions": "12", "cost": "450000"},
                                          {"name": "Print weekly", "reach": "120000", "insertions": "4", "cost": "180000"}]}},
    "marketshare": {"objective": "What share of the market do we hold, and is it rising?", "method": "market_share", "currency": "PHP", "period": "annual",
                    "inputs": {"firm_sales": "2400000", "market_sales": "12000000", "prior_firm_sales": "2100000",
                               "prior_market_sales": "11500000", "customers": "48000", "target_population": "400000",
                               "largest_competitor_sales": "3600000"}},
    "clv": {"objective": "What is a customer worth once churn and time are counted?", "method": "clv_model", "currency": "PHP", "period": "monthly",
            "inputs": {"margin_per_period": "1500", "churn_rate": "0.04", "discount_rate": "0.10",
                       "horizon_periods": "24", "acquisition_cost": "9000"}},
    "custprofit": {"objective": "Which customer segments actually make money?", "method": "customer_profitability", "currency": "PHP", "period": "annual",
                   "inputs": {"segments": [{"name": "Enterprise", "revenue": "5000000", "direct_cost": "3000000", "allocated_cost": "600000"},
                                           {"name": "SME", "revenue": "3000000", "direct_cost": "2100000", "allocated_cost": "400000"},
                                           {"name": "Retail", "revenue": "1200000", "direct_cost": "1500000", "allocated_cost": "100000"}],
                              "concentration_threshold": "0.8"}},
    "scv": {"objective": "Compute the material, labour and overhead variances for the period", "method": "standard_cost_variances", "currency": "PHP", "period": "annual",
            "inputs": {"actual_units": "4800", "standard_material_per_unit": "2", "standard_material_price": "15",
                       "actual_material_quantity": "9800", "actual_material_price": "15.5",
                       "standard_hours_per_unit": "1.5", "standard_labour_rate": "40", "actual_hours": "7300", "actual_labour_rate": "41",
                       "standard_variable_overhead_rate": "10", "actual_variable_overhead": "70000",
                       "budgeted_fixed_overhead": "240000", "actual_fixed_overhead": "245000", "denominator_hours": "8000"}},
    "inventory": {"objective": "How much should we order, and when should we reorder?", "method": "inventory_policy", "currency": "PHP", "period": "annual",
                  "inputs": {"annual_demand": "12000", "order_cost": "500", "holding_cost_per_unit": "30",
                             "lead_time_days": "10", "service_level": "0.95", "daily_demand_sd": "20"}},
    "queue": {"objective": "How long is the queue at the counter?", "method": "queue_analysis", "currency": "PHP", "period": "per period",
              "inputs": {"arrival_rate": "18", "service_rate": "24"}},
    "capacity": {"objective": "Which step limits how much we can produce?", "method": "capacity_analysis", "currency": "PHP", "period": "per period",
                 "inputs": {"resources": [{"name": "cutting", "available_hours": "8", "minutes_per_unit": "5"},
                                          {"name": "assembly", "available_hours": "8", "minutes_per_unit": "8"},
                                          {"name": "packing", "available_hours": "8", "minutes_per_unit": "3"}],
                            "demand": "50"}},
    "cpm": {"objective": "What is the critical path and when does the project finish?", "method": "cpm_schedule", "currency": "PHP", "period": "days",
            "inputs": {"estimate": "single", "activities": [
                {"id": "A", "duration": "3", "predecessors": ""},
                {"id": "B", "duration": "4", "predecessors": "A"},
                {"id": "C", "duration": "2", "predecessors": "A"},
                {"id": "D", "duration": "5", "predecessors": "B,C"}]}},
    "evm": {"objective": "Are we ahead or behind, and what will it cost?", "method": "earned_value", "currency": "PHP", "period": "point in time",
            "inputs": {"planned_value": "100000", "earned_value": "90000", "actual_cost": "95000",
                       "budget_at_completion": "200000", "eac_method": "cpi"}},
    "oee": {"objective": "What is the overall equipment effectiveness of the line?", "method": "oee_analysis", "currency": "PHP", "period": "per period",
            "inputs": {"planned_production_time": "480", "downtime": "40", "ideal_cycle_time": "0.5",
                       "total_units": "760", "good_units": "740"}},
    "spc": {"objective": "Is the process in control, and is it capable?", "method": "process_control", "currency": "PHP", "period": "per observation",
            "inputs": {"values": ["10", "11", "9", "10", "12", "9", "10", "11"], "spec_lower": "7", "spec_upper": "13"}},
    "abc": {"objective": "What does each product really cost once activities are traced?", "method": "abc_costing", "currency": "PHP", "period": "annual",
            "inputs": {"activities": [{"name": "setup", "pool_cost": "50000"}, {"name": "inspection", "pool_cost": "30000"}],
                       "products": [{"name": "X", "units": "1000"}, {"name": "Y", "units": "500"}],
                       "allocations": [{"activity": "setup", "product": "X", "driver_quantity": "40"},
                                       {"activity": "setup", "product": "Y", "driver_quantity": "60"},
                                       {"activity": "inspection", "product": "X", "driver_quantity": "20"},
                                       {"activity": "inspection", "product": "Y", "driver_quantity": "10"}]}},
    "salesvar": {"objective": "Why did revenue move against the budget?", "method": "sales_variances", "currency": "PHP", "period": "annual",
                 "inputs": {"products": [
                     {"name": "X", "budget_units": "100", "budget_price": "10", "actual_units": "120", "actual_price": "11"},
                     {"name": "Y", "budget_units": "100", "budget_price": "20", "actual_units": "80", "actual_price": "18"}]}},
    "linebalance": {"objective": "How many stations does the line need at this cycle time?", "method": "line_balancing", "currency": "PHP", "period": "per period",
                    "inputs": {"cycle_time": "10", "rule": "longest_time", "tasks": [
                        {"id": "A", "time": "5", "predecessors": ""},
                        {"id": "B", "time": "3", "predecessors": "A"},
                        {"id": "C", "time": "4", "predecessors": "A"},
                        {"id": "D", "time": "2", "predecessors": "B"},
                        {"id": "E", "time": "3", "predecessors": "C"},
                        {"id": "F", "time": "4", "predecessors": "D,E"}]}},
    "tax": {"objective": "What is the tax charge on the declared income?", "method": "tax_declared", "currency": "PHP", "period": "annual",
            "inputs": {"taxable_income": "1000000", "income_tax_rate": "0.25",
                       "vat_output_tax": "144000", "vat_input_tax": "84000",
                       "temporary_difference": "100000", "deferred_tax_rate": "0.25"}},
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
                       "inputs": {"fixed_costs": "6000", "products": [{"name": "coffee", "price": "5", "variable_cost": "2", "mix_units": "3"}, {"name": "cake", "price": "6", "variable_cost": "3", "mix_units": "1"}]}},
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
                 "inputs": {"spec": accounts.EXAMPLE_SPEC}},
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
    "equilibrium": {"objective": "Where do demand and supply meet?", "method": "demand_supply_equilibrium", "currency": "PHP", "period": "annual",
                    "inputs": {"demand_intercept": "100", "demand_slope": "2", "supply_intercept": "20", "supply_slope": "2"}},
    "elasticity": {"objective": "How responsive is quantity to a price change?", "method": "elasticity", "currency": "PHP", "period": "annual",
                   "inputs": {"quantity_1": "100", "price_1": "10", "quantity_2": "140", "price_2": "8"}},
    "taxincidence": {"objective": "Who bears a per-unit tax?", "method": "tax_incidence", "currency": "PHP", "period": "annual",
                     "inputs": {"demand_intercept": "100", "demand_slope": "2", "supply_intercept": "20", "supply_slope": "2", "tax_per_unit": "6"}},
    "pricecontrol": {"objective": "What does a price ceiling or floor do?", "method": "price_control", "currency": "PHP", "period": "annual",
                     "inputs": {"demand_intercept": "100", "demand_slope": "2", "supply_intercept": "20", "supply_slope": "2",
                                "control_price": "15", "control_type": "ceiling"}},
    "concentration": {"objective": "How concentrated is this market?", "method": "market_concentration", "currency": "PHP", "period": "annual",
                      "inputs": {"firm_revenues": ["40", "25", "15", "10", "10"]}},
    "costcurves": {"objective": "What do average and marginal cost look like at this output?", "method": "cost_curves", "currency": "PHP", "period": "annual",
                   "inputs": {"fixed_cost": "1000", "linear_cost": "10", "quadratic_cost": "0.5", "quantity": "20", "price": "40"}},
    "profitmax": {"objective": "What output and price maximise profit?", "method": "profit_maximization", "currency": "PHP", "period": "annual",
                  "inputs": {"demand_intercept": "100", "demand_slope": "2", "fixed_cost": "100", "linear_cost": "10", "quadratic_cost": "0.5"}},
    "marketpower": {"objective": "How much market power does this price imply?", "method": "market_power", "currency": "PHP", "period": "annual",
                    "inputs": {"price": "50", "marginal_cost": "20"}},
    "nationalincome": {"objective": "What is GDP by the expenditure approach?", "method": "national_income", "currency": "PHP", "period": "annual",
                       "inputs": {"consumption": "600", "investment": "150", "government_spending": "200", "exports": "120", "imports": "170",
                                  "net_factor_income": "20", "depreciation": "50", "population": "100", "gdp_deflator": "120"}},
    "growth": {"objective": "What compound growth rate does this series imply?", "method": "growth_rate", "currency": "PHP", "period": "annual",
               "inputs": {"start_value": "100", "end_value": "200", "periods": "10"}},
    "inflation": {"objective": "What is the inflation rate and the real interest rate?", "method": "inflation_cpi", "currency": "PHP", "period": "annual",
                  "inputs": {"cpi_start": "100", "cpi_end": "105", "nominal_interest_rate": "0.08", "wage_start": "100", "wage_end": "104"}},
    "unemployment": {"objective": "What are the unemployment and participation rates?", "method": "unemployment_rate", "period": "annual",
                     "inputs": {"labour_force": "1000", "employed": "920", "working_age_population": "1500"}},
    "moneymultiplier": {"objective": "How much money does this base support?", "method": "money_multiplier", "currency": "PHP", "period": "annual",
                        "inputs": {"monetary_base": "100", "reserve_ratio": "0.10", "currency_drain_ratio": "0.05"}},
    "fiscal": {"objective": "What output change does this fiscal package imply?", "method": "fiscal_multiplier", "currency": "PHP", "period": "annual",
               "inputs": {"mpc": "0.8", "tax_rate": "0.25", "government_spending_change": "100", "tax_change": "0"}},
    "budgetdebt": {"objective": "What are the budget balance and the debt ratio?", "method": "budget_debt", "currency": "PHP", "period": "annual",
                   "inputs": {"government_revenue": "500", "government_spending": "520", "interest_payments": "30", "debt_stock": "1000",
                              "nominal_gdp": "2000", "nominal_growth_rate": "0.05", "inflation_rate": "0.02"}},
    "externality": {"objective": "What is the Pigouvian tax and the deadweight loss?", "method": "externality_pigouvian", "currency": "PHP", "period": "annual",
                    "inputs": {"demand_intercept": "100", "demand_slope": "2", "supply_intercept": "20", "supply_slope": "2", "marginal_external_cost": "4"}},
    "publicgood": {"objective": "What is the efficient provision of the public good?", "method": "public_good", "currency": "PHP", "period": "annual",
                   "inputs": {"mb1_intercept": "100", "mb1_slope": "2", "mb2_intercept": "80", "mb2_slope": "3", "mc_intercept": "20", "mc_slope": "1"}},
    "socialwelfare": {"objective": "Compare utilitarian, Rawlsian and Nash welfare", "method": "social_welfare", "currency": "PHP", "period": "annual",
                      "inputs": {"incomes": ["10", "20", "30", "40"], "welfare_function": "utilitarian"}},
    "gini": {"objective": "How unequal are these incomes?", "method": "gini_coefficient", "currency": "PHP", "period": "annual",
             "inputs": {"incomes": ["10", "20", "30", "40"]}},
    "poverty": {"objective": "What are the poverty headcount and gap?", "method": "poverty_measures", "currency": "PHP", "period": "annual",
                "inputs": {"incomes": ["10", "20", "30", "40"], "poverty_line": "25"}},
    "taxprogressivity": {"objective": "Is this tax progressive?", "method": "tax_progressivity", "currency": "PHP", "period": "annual",
                         "inputs": {"incomes": ["10", "20", "30", "40"], "taxes": ["1", "3", "6", "10"]}},
    "optimalpollution": {"objective": "What is the optimal pollution level?", "method": "optimal_pollution", "currency": "PHP", "period": "annual",
                         "inputs": {"marginal_damage_intercept": "10", "marginal_damage_slope": "2", "marginal_abatement_intercept": "100", "marginal_abatement_slope": "3"}},
    "okun": {"objective": "What does the output gap imply for unemployment?", "method": "output_gap_okun", "period": "annual",
             "inputs": {"actual_gdp": "1050", "potential_gdp": "1000", "current_unemployment_rate": "0.06", "okun_coefficient": "0.5"}},
    "comparative": {"objective": "Which country has comparative advantage in which good?", "method": "comparative_advantage", "period": "annual",
                    "inputs": {"countries": [{"name": "A", "good_1_hours": "2", "good_2_hours": "1"},
                                             {"name": "B", "good_1_hours": "5", "good_2_hours": "3"}]}},
    "tariff": {"objective": "What does a tariff cost the small country?", "method": "tariff_welfare", "currency": "PHP", "period": "annual",
               "inputs": {"demand_intercept": "100", "demand_slope": "2", "supply_intercept": "20", "supply_slope": "2",
                          "world_price": "10", "tariff_per_unit": "5"}},
    "ppp": {"objective": "Is the exchange rate at purchasing-power parity?", "method": "exchange_rate_ppp", "period": "annual",
            "inputs": {"price_domestic": "5000", "price_foreign": "100", "nominal_rate": "55",
                       "domestic_inflation": "0.04", "foreign_inflation": "0.02"}},
    "irp": {"objective": "What forward rate does interest parity imply?", "method": "interest_rate_parity", "period": "annual",
            "inputs": {"spot_rate": "50", "domestic_rate": "0.06", "foreign_rate": "0.04", "time_to_maturity": "1",
                       "forward_rate": "51", "domestic_inflation": "0.04", "foreign_inflation": "0.02"}},
    "bop": {"objective": "Does the balance of payments close?", "method": "balance_of_payments", "currency": "PHP", "period": "annual",
            "inputs": {"current_account": "-50", "capital_account": "0", "financial_account": "50", "gdp": "1000"}},
    "hdi": {"objective": "What is the Human Development Index?", "method": "hdi", "period": "annual",
            "inputs": {"life_expectancy": "70", "expected_years_schooling": "12", "mean_years_schooling": "8", "gni_per_capita": "5000"}},
    "expectedutility": {"objective": "What is the certainty equivalent of this gamble?", "method": "expected_utility", "currency": "PHP", "period": "annual",
                        "inputs": {"outcomes": ["50", "150"], "probabilities": ["0.5", "0.5"], "utility_function": "crra", "risk_aversion": "2"}},
    "prospect": {"objective": "How does prospect theory value this gamble?", "method": "prospect_theory", "currency": "PHP", "period": "annual",
                 "inputs": {"reference_point": "100", "outcomes": ["150", "50"], "probabilities": ["0.5", "0.5"]}},
    "labour": {"objective": "What are the real wage and the wage share?", "method": "labour_market", "currency": "PHP", "period": "annual",
               "inputs": {"nominal_wage": "100", "cpi": "105", "labour_productivity": "120", "vacancies": "10", "unemployment_rate": "0.05"}},
    "pricediscrimination": {"objective": "What prices does third-degree discrimination set?", "method": "price_discrimination", "currency": "PHP", "period": "annual",
                            "inputs": {"demand_intercept_1": "100", "demand_slope_1": "2", "demand_intercept_2": "80", "demand_slope_2": "1", "marginal_cost": "10"}},
    "cournot": {"objective": "What is the Cournot duopoly outcome?", "method": "cournot_duopoly", "currency": "PHP", "period": "annual",
                "inputs": {"demand_intercept": "100", "demand_slope": "2", "marginal_cost_1": "10", "marginal_cost_2": "20"}},
    "did": {"objective": "What is the difference-in-differences estimate?", "method": "difference_in_differences", "currency": "PHP", "period": "annual",
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
}

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b)))
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
    def do_GET(self):
        self._started = time.monotonic()
        try:
            if self.path == "/api/health":
                return self._send(200, product_ops.health({"sandbox": "on" if SANDBOX_ENABLED else "off (development)",
                                                          "model_assistance": bool(MODELS)}))
            if self.path == "/": 
                with open(os.path.join(WEB, "index.html"), "rb") as f: return self._send(200, f.read(), "text/html; charset=utf-8")
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
            im = re.fullmatch(r"/api/intake/([0-9a-f]{12})", self.path)
            if im:
                try: return self._send(200, product_intake.load(im[1]))
                except product_intake.IntakeNotFound as e: return self._send(404, {"error": str(e)})
                except product_intake.IntakeError as e: return self._send(422, {"error": str(e)})
            if self.path.startswith(product_api.CASE_ROUTE): return self._send(*product_api.handle("GET", self.path))
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
            if u.path == "/api/templates": return self._send(200, [templates.describe(k) for k in templates.TEMPLATES])
            tm = re.fullmatch(r"/api/templates/(\w+)", u.path)
            if tm:
                if tm[1] not in templates.TEMPLATES: return self._send(404, {"error": "unknown template"})
                return self._send(200, templates.describe(tm[1]))
            if self.path == "/api/methods": return self._send(200, methods.list_methods())
            m = re.fullmatch(r"/api/sessions/(\w+)", self.path)
            if m: return self._send(200, M.get(m[1]).to_dict())
            self._send(404, {"error": "not found"})
        except KeyError as e: self._send(404, {"error": "unknown session" if "registry" not in str(e) else str(e).strip("'\"")})
    def do_POST(self):
        self._started = time.monotonic()
        try:
            if self.path.startswith(product_api.CASE_ROUTE):
                n = int(self.headers.get("Content-Length") or 0)
                if n > MAXBODY: raise ValueError("body too large")
                return self._send(*product_api.handle("POST", self.path, json.loads(self.rfile.read(n) or b"{}")))
            if self.path == "/api/sessions": return self._send(201, M.create(self._body()).to_dict())
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
            self._send(404, {"error": "not found"})
        except (ValueError, TypeError) as e: self._send(400, {"error": str(e)})
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
        record = product_intake.save(b.get("filename"), raw, b.get("content_type"))
        if record["kind"] != "structured": return self._send(201, record)
        try:
            table = ingest.read_table(record["filename"], raw, sheet=b.get("sheet"), merged=merged)
        except ingest.IngestError as e:
            return self._send(201, product_intake.fail(record["id"], str(e)))
        return self._send(201, product_intake.attach_table(record["id"], table))

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

def serve(port=8000, host="127.0.0.1", sandbox=True, models=None):
    global M, MODELS, SANDBOX_ENABLED
    M = SessionManager(SubprocessSandbox() if sandbox else None, ASSIST_RUNS); MODELS = models if models is not None else llm.from_env()
    SANDBOX_ENABLED = bool(sandbox)
    print(f"Workbench on http://{host}:{port} (sandbox {'ON' if sandbox else 'OFF: development only'}; model assistance {'ON: ' + MODELS.builder.name + ' ' + MODELS.builder.model if MODELS else 'OFF'}; literature ON: {', '.join(LITERATURE_SOURCES)})")
    print("Health: /api/health | cases: /api/cases | request log: " + (str(product_ops.request_log_path()) if product_ops.request_log_path() else "disabled"))
    ThreadingHTTPServer((host, port), H).serve_forever()

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    serve(int(args[0]) if args else 8000, sandbox="--no-sandbox" not in sys.argv)
