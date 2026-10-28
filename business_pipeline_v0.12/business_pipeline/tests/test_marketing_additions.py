"""Digital marketing additions (B-113): goldens, refusals, presets and shelf wiring.

Each test is written from a student's point of view: does the method give the figure a
textbook would give, does it refuse an input it cannot honestly handle, and does the
Marketing & customers page actually offer it with notes and a glossary?
"""

import sys
import os
import unittest
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import methods, server  # noqa: E402
from bp.methods import DataError, LIBRARY  # noqa: E402
from bp.orchestrator import Pipeline  # noqa: E402
from bp.product import subjects  # noqa: E402

NEW = ["campaign_efficiency", "ab_test_two_proportion", "attribution_split", "channel_economics",
       "email_list_health", "social_engagement", "web_analytics", "rfm_scoring", "media_plan"]

INPUTS = {
    "campaign_efficiency": {"impressions": "250000", "clicks": "6000", "conversions": "220",
                            "spend": "60000", "revenue": "150000", "contribution_margin_rate": "0.45"},
    "ab_test_two_proportion": {"visitors_a": "4000", "conversions_a": "320",
                               "visitors_b": "4000", "conversions_b": "380",
                               "alpha": "0.05", "power": "0.8", "minimum_effect": "0.10"},
    "attribution_split": {"channels": [{"name": "search", "first_click": "420", "last_click": "260", "linear": "320"},
                                       {"name": "social", "first_click": "180", "last_click": "310", "linear": "290"},
                                       {"name": "email", "first_click": "120", "last_click": "150", "linear": "110"}]},
    "channel_economics": {"channels": [{"name": "search", "spend": "60000", "new_customers": "400",
                                        "contribution_margin": "150", "churn_rate": "0.04"},
                                       {"name": "social", "spend": "35000", "new_customers": "180",
                                        "contribution_margin": "95", "churn_rate": "0.06"},
                                       {"name": "referral", "spend": "15000", "new_customers": "150",
                                        "contribution_margin": "150", "churn_rate": "0.03"}]},
    "email_list_health": {"list_start": "8000", "new_subscribers": "600", "unsubscribes": "90",
                          "bounces": "40", "sends": "7500", "opens": "2250", "clicks": "450",
                          "revenue": "38000"},
    "social_engagement": {"impressions": "150000", "reach": "95000", "engagements": "5700",
                          "followers_start": "18000", "followers_gained": "900", "spend": "25000",
                          "posts": "15"},
    "web_analytics": {"channels": [{"name": "organic search", "sessions": "42000", "conversions": "1350", "revenue": "680000"},
                                   {"name": "paid search", "sessions": "24000", "conversions": "960", "revenue": "430000"},
                                   {"name": "email", "sessions": "9000", "conversions": "540", "revenue": "260000"}],
                      "organic_impressions": "600000", "organic_clicks": "24000"},
    "rfm_scoring": {"customers": [
        {"name": "C1", "recency_days": "3", "frequency": "10", "monetary": "20000"},
        {"name": "C2", "recency_days": "8", "frequency": "9", "monetary": "18000"},
        {"name": "C3", "recency_days": "15", "frequency": "8", "monetary": "16000"},
        {"name": "C4", "recency_days": "25", "frequency": "7", "monetary": "14000"},
        {"name": "C5", "recency_days": "40", "frequency": "6", "monetary": "12000"},
        {"name": "C6", "recency_days": "55", "frequency": "5", "monetary": "10000"},
        {"name": "C7", "recency_days": "70", "frequency": "4", "monetary": "8000"},
        {"name": "C8", "recency_days": "90", "frequency": "3", "monetary": "6000"},
        {"name": "C9", "recency_days": "120", "frequency": "2", "monetary": "4000"},
        {"name": "C10", "recency_days": "160", "frequency": "1", "monetary": "2000"}]},
    "media_plan": {"population": "1000000", "vehicles": [
        {"name": "TV prime time", "reach": "450000", "insertions": "8", "cost": "1200000"},
        {"name": "Radio drive time", "reach": "300000", "insertions": "12", "cost": "450000"},
        {"name": "Print weekly", "reach": "120000", "insertions": "4", "cost": "180000"}]},
}

PRESETS = ["campaign", "abtest", "attribution", "channelecon", "email", "social", "web", "rfm", "mediaplan"]


class DigitalGoldens(unittest.TestCase):
    """Textbook figures, computed here independently of the method's float second route."""

    def near(self, got, want, places=6):
        self.assertAlmostEqual(float(got), want, places=places)

    def test_campaign_efficiency_matches_the_media_formulas(self):
        out = LIBRARY["campaign_efficiency"].impl(INPUTS["campaign_efficiency"])
        self.near(out["ctr"], 0.024, 12)
        self.near(out["cpc"], 10, 12)
        self.near(out["cpm"], 240, 10)
        self.near(out["conversion_rate"], 220 / 6000, 12)
        self.near(out["cpa"], 60000 / 220, 10)
        self.near(out["roas"], 2.5, 12)
        self.near(out["acos"], 0.4, 12)
        self.near(out["break_even_roas"], 1 / 0.45, 10)
        self.near(out["profit_after_media"], 7500, 8)

    def test_campaign_efficiency_omits_the_return_when_no_revenue_is_declared(self):
        out = LIBRARY["campaign_efficiency"].impl({**INPUTS["campaign_efficiency"], "revenue": "0"})
        self.assertNotIn("acos", out)
        self.assertEqual(out["roas"], D(0))

    def test_ab_test_two_proportion_matches_the_pooled_z_test(self):
        out = LIBRARY["ab_test_two_proportion"].impl(INPUTS["ab_test_two_proportion"])
        self.near(out["rate_a"], 0.08, 12)
        self.near(out["rate_b"], 0.095, 12)
        self.near(out["absolute_lift"], 0.015, 12)
        self.near(out["relative_lift"], 0.1875, 12)
        self.near(out["pooled_rate"], 0.0875, 12)
        pooled, na = 0.0875, 4000
        se = (pooled * (1 - pooled) * (1 / na + 1 / na)) ** 0.5
        self.near(out["z"], 0.015 / se, 8)
        self.assertLess(out["p_value"], D("0.05"))
        self.assertLess(out["ci_low"], out["absolute_lift"])
        self.assertGreater(out["ci_high"], out["absolute_lift"])
        self.assertGreater(out["required_per_arm"], D(18000))
        self.assertLess(out["required_per_arm"], D(19500))

    def test_ab_test_sample_size_falls_as_the_effect_grows(self):
        small = LIBRARY["ab_test_two_proportion"].impl(INPUTS["ab_test_two_proportion"])
        large = LIBRARY["ab_test_two_proportion"].impl({**INPUTS["ab_test_two_proportion"], "minimum_effect": "0.20"})
        self.assertLess(large["required_per_arm"], small["required_per_arm"])

    def test_attribution_shares_and_the_largest_spread(self):
        out = LIBRARY["attribution_split"].impl(INPUTS["attribution_split"])
        self.near(out["first_share_1"], 420 / 720, 12)
        self.near(out["last_share_2"], 310 / 720, 12)
        self.near(out["linear_share_3"], 110 / 720, 12)
        self.near(out["max_spread"], 420 / 720 - 260 / 720, 12)
        for model in ("first", "last", "linear"):
            total = sum((out["%s_share_%d" % (model, i)] for i in (1, 2, 3)), D(0))
            self.assertAlmostEqual(float(total), 1.0, places=12)

    def test_channel_economics_acquisition_payback_and_value(self):
        out = LIBRARY["channel_economics"].impl(INPUTS["channel_economics"])
        self.near(out["blended_cac"], 110000 / 730, 9)
        self.near(out["cac_1"], 150, 12)
        self.near(out["payback_1"], 1, 12)
        self.near(out["ltv_1"], 3750, 10)
        self.near(out["ltv_cac_1"], 25, 10)
        self.near(out["cac_2"], 35000 / 180, 9)
        self.near(out["spend_share_1"], 60000 / 110000, 12)

    def test_email_list_health_growth_and_engagement(self):
        out = LIBRARY["email_list_health"].impl(INPUTS["email_list_health"])
        self.assertEqual(out["list_end"], D(8470))
        self.near(out["growth_rate"], 470 / 8000, 12)
        self.near(out["churn_rate"], 130 / 8000, 12)
        self.near(out["open_rate"], 0.30, 12)
        self.near(out["click_rate"], 0.06, 12)
        self.near(out["click_to_open"], 0.20, 12)
        self.near(out["revenue_per_subscriber"], 38000 / 8470, 9)

    def test_social_engagement_rate_and_growth(self):
        out = LIBRARY["social_engagement"].impl(INPUTS["social_engagement"])
        self.near(out["engagement_rate"], 0.06, 12)
        self.near(out["frequency"], 150000 / 95000, 10)
        self.near(out["cpm"], 25000 / 150000 * 1000, 9)
        self.near(out["cost_per_engagement"], 25000 / 5700, 9)
        self.near(out["follower_growth"], 900 / 18000, 12)
        self.near(out["engagement_per_post"], 380, 10)

    def test_web_analytics_channel_rows_and_organic_click_through(self):
        out = LIBRARY["web_analytics"].impl(INPUTS["web_analytics"])
        self.assertEqual(out["total_sessions"], D(75000))
        self.assertEqual(out["total_conversions"], D(2850))
        self.near(out["blended_conversion_rate"], 0.038, 12)
        self.near(out["revenue_per_session"], 1370000 / 75000, 9)
        self.near(out["session_share_1"], 0.56, 12)
        self.near(out["conversion_rate_2"], 960 / 24000, 12)
        self.near(out["organic_ctr"], 0.04, 12)

    def test_web_analytics_omits_organic_click_through_when_not_declared(self):
        out = LIBRARY["web_analytics"].impl({"channels": INPUTS["web_analytics"]["channels"]})
        self.assertNotIn("organic_ctr", out)

    def test_rfm_scores_are_bands_of_the_rank_in_this_file(self):
        out = LIBRARY["rfm_scoring"].impl(INPUTS["rfm_scoring"])
        rows = out["_appendix"]["customers"]
        self.assertEqual([r["r_score"] for r in rows], [5, 5, 4, 4, 3, 3, 2, 2, 1, 1])
        self.assertEqual([r["f_score"] for r in rows], [5, 5, 4, 4, 3, 3, 2, 2, 1, 1])
        self.assertEqual([r["m_score"] for r in rows], [5, 5, 4, 4, 3, 3, 2, 2, 1, 1])
        self.assertEqual([r["rfm_score"] for r in rows], [15, 15, 12, 12, 9, 9, 6, 6, 3, 3])

    def test_rfm_segments_are_counted_and_sum_to_the_customer_count(self):
        out = LIBRARY["rfm_scoring"].impl(INPUTS["rfm_scoring"])
        self.assertEqual(out["total_customers"], D(10))
        self.assertEqual(out["count_champions"], D(4))
        self.assertEqual(out["count_need_attention"], D(2))
        self.assertEqual(out["count_about_to_sleep"], D(2))
        self.assertEqual(out["count_hibernating"], D(2))
        for key in ("cannot_lose", "loyal", "potential_loyalist", "new", "promising", "at_risk", "lost"):
            self.assertEqual(out["count_" + key], D(0), key)
        self.assertEqual(sum((out["count_" + key] for key in methods.RFM_SEGMENTS), D(0)), D(10))
        self.near(out["mean_r_score"], 3, 12)
        self.near(out["mean_f_score"], 3, 12)
        self.near(out["mean_m_score"], 3, 12)
        self.near(out["mean_rfm_score"], 9, 12)

    def test_every_declared_rfm_segment_rule_can_fire(self):
        cases = {"cannot_lose": (1, 4, 4), "champions": (5, 5, 5), "loyal": (3, 4, 1),
                 "potential_loyalist": (4, 2, 1), "new": (5, 1, 1), "promising": (3, 1, 1),
                 "need_attention": (3, 2, 1), "at_risk": (2, 3, 1), "about_to_sleep": (2, 2, 1),
                 "hibernating": (1, 2, 1), "lost": (1, 1, 5)}
        for segment, (r, f, m) in cases.items():
            self.assertEqual(methods._rfm_segment(r, f, m), segment, (r, f, m))
            self.assertIn(segment, methods.RFM_SEGMENTS)

    def test_media_plan_reach_frequency_and_rating_points(self):
        out = LIBRARY["media_plan"].impl(INPUTS["media_plan"])
        self.near(out["reach_pct_1"], 0.45, 12)
        self.near(out["grp_1"], 360, 9)
        self.near(out["grp_2"], 360, 9)
        self.near(out["grp_3"], 48, 9)
        self.near(out["total_grp"], 768, 9)
        self.assertEqual(out["total_impressions"], D(7680000))
        self.assertEqual(out["total_cost"], D(1830000))
        self.near(out["cpm_1"], 1200000 / 3600000 * 1000, 8)
        self.near(out["cpp_1"], 1200000 / 360, 8)
        self.near(out["blended_cpm"], 1830000 / 7680000 * 1000, 8)
        self.near(out["net_reach"], 1000000 * (1 - 0.55 * 0.70 * 0.88), 6)
        self.near(out["average_frequency"], 7680000 / (1000000 * (1 - 0.55 * 0.70 * 0.88)), 6)


class DigitalRefusals(unittest.TestCase):
    """A student's impossible count must block with a reason, not produce a plausible figure."""

    def refuses(self, method, changes):
        inp = {**INPUTS[method], **changes}
        with self.assertRaises(DataError):
            LIBRARY[method].impl(inp)

    def test_impossible_counts_are_refused(self):
        self.refuses("campaign_efficiency", {"clicks": "300000"})
        self.refuses("campaign_efficiency", {"conversions": "9000"})
        self.refuses("campaign_efficiency", {"contribution_margin_rate": "1.5"})
        self.refuses("ab_test_two_proportion", {"conversions_a": "0"})
        self.refuses("ab_test_two_proportion", {"minimum_effect": "20"})
        self.refuses("attribution_split", {"channels": [{"name": "search", "first_click": "-1", "last_click": "1", "linear": "1"},
                                                        {"name": "social", "first_click": "1", "last_click": "1", "linear": "1"}]})
        self.refuses("channel_economics", {"channels": [{"name": "search", "spend": "1", "new_customers": "1", "contribution_margin": "1", "churn_rate": "0"},
                                                        {"name": "social", "spend": "1", "new_customers": "1", "contribution_margin": "1", "churn_rate": "0.1"}]})
        self.refuses("email_list_health", {"clicks": "99999"})
        self.refuses("social_engagement", {"reach": "200000"})
        self.refuses("web_analytics", {"channels": [{"name": "organic", "sessions": "10", "conversions": "20", "revenue": "1"},
                                                    {"name": "paid", "sessions": "10", "conversions": "1", "revenue": "1"}]})
        self.refuses("rfm_scoring", {"customers": INPUTS["rfm_scoring"]["customers"][:4]})
        self.refuses("rfm_scoring", {"customers": [dict(INPUTS["rfm_scoring"]["customers"][0], name="C2")]
                                     + INPUTS["rfm_scoring"]["customers"][1:]})
        self.refuses("rfm_scoring", {"customers": [dict(INPUTS["rfm_scoring"]["customers"][0], recency_days="-1")]
                                     + INPUTS["rfm_scoring"]["customers"][1:]})
        self.refuses("rfm_scoring", {"customers": [dict(INPUTS["rfm_scoring"]["customers"][0], frequency="0")]
                                     + INPUTS["rfm_scoring"]["customers"][1:]})
        self.refuses("media_plan", {"vehicles": [dict(INPUTS["media_plan"]["vehicles"][0], reach="2000000")]})
        self.refuses("media_plan", {"vehicles": [dict(INPUTS["media_plan"]["vehicles"][0], insertions="0")]})
        self.refuses("media_plan", {"vehicles": [dict(INPUTS["media_plan"]["vehicles"][0], cost="-1")]})
        self.refuses("media_plan", {"population": "0"})

    def test_profile_reports_the_reason_before_execution(self):
        issues = LIBRARY["campaign_efficiency"].profile({**INPUTS["campaign_efficiency"], "clicks": "300000"})
        self.assertTrue(issues)
        self.assertIn("clicks", issues[0])
        issues = LIBRARY["email_list_health"].profile({**INPUTS["email_list_health"], "sends": "0"})
        self.assertTrue(issues)
        self.assertIn("sends", issues[0])


class DigitalContract(unittest.TestCase):
    def test_every_new_method_explains_itself_in_plain_language(self):
        for name in NEW:
            m = LIBRARY[name]
            self.assertEqual(m.tier, "T1", name)
            self.assertTrue(m.intended_use, name)
            self.assertTrue(m.unsupported_use, name)
            self.assertTrue(m.assumptions, name)
            self.assertTrue(m.limitations, name)
            self.assertTrue(m.defaults, name)
            self.assertTrue(m.caveats, name)
            self.assertTrue(m.template, name)
            self.assertEqual(len(m.test_names), 5, name)
            self.assertEqual(m.claim_ceiling,
                             "associational" if name == "ab_test_two_proportion" else "descriptive", name)
            for key, spec in m.input_schema.items():
                self.assertTrue(spec.get("desc"), "%s.%s has no description" % (name, key))

    def test_every_new_method_has_five_passing_checks_on_the_preset(self):
        for name in NEW:
            preset = server.PRESETS[[p for p in PRESETS if server.PRESETS[p]["method"] == name][0]]
            res = LIBRARY[name].tests(preset["inputs"], LIBRARY[name].impl)
            self.assertEqual([n for n, _ in res], list(LIBRARY[name].test_names), name)
            self.assertTrue(all(ok for _, ok in res), name)

    def test_every_new_method_has_a_preset_and_a_marketing_tile(self):
        by_method = {tool["method"] for tool in subjects.detail("marketing")["tools"]}
        for name in NEW:
            self.assertIn(name, LIBRARY)
            self.assertIn(name, by_method)
        for preset in PRESETS:
            self.assertIn(preset, server.PRESETS)
            self.assertIn(server.PRESETS[preset]["method"], LIBRARY)

    def test_every_preset_delivers_a_token_free_report(self):
        for preset in PRESETS:
            body = server.PRESETS[preset]
            delivery = Pipeline().run({"objective": body["objective"], **body}, lambda spec: True)
            self.assertEqual(delivery.status, "delivered", preset)
            self.assertNotIn("{{", delivery.report, preset)
            self.assertNotIn("ref:", delivery.report, preset)

    def test_every_new_method_has_a_study_note(self):
        tools = subjects.detail("marketing")["tools"]
        for tool in tools:
            if tool["method"] in NEW:
                self.assertTrue(tool["formula"], tool["label"])
                self.assertTrue(tool["steps"], tool["label"])
                self.assertTrue(tool["common_mistakes"], tool["label"])


class MarketingShelf(unittest.TestCase):
    def test_the_page_shows_digital_marketing_as_its_own_record_group(self):
        page = subjects.detail("marketing")
        labels = [row["discipline_label"] for row in page["records"]]
        self.assertEqual(labels.count("Digital marketing"), 16)
        self.assertEqual(labels.count("Marketing frameworks"), 11)
        self.assertEqual(labels.count("Customer and market analytics"), 7)

    def test_the_digital_frameworks_and_methods_are_in_the_catalogue(self):
        rows = {row["id"]: row for row in subjects.detail("marketing")["catalogue"]}
        for number in range(13, 22):
            row = rows["MKT-%02d" % number]
            self.assertIn("digital", " ".join(row["disciplines"]))
        from bp import registry
        linked = {i: [m["method_id"] for m in registry.get("QNT-MKT-%02d" % i)["linked_methods"]]
                  for i in range(8, 16)}
        self.assertEqual(linked[8], ["campaign_efficiency"])
        self.assertEqual(linked[9], ["channel_economics", "unit_economics"])
        self.assertEqual(linked[10], ["attribution_split"])
        self.assertEqual(linked[11], ["ab_test_two_proportion", "power_analysis"])
        self.assertEqual(linked[12], ["email_list_health"])
        self.assertEqual(linked[13], ["social_engagement"])
        self.assertEqual(linked[14], ["web_analytics"])
        self.assertEqual(linked[15], ["media_plan"])

    def test_rfm_is_one_record_with_both_ids_and_a_computed_status(self):
        from bp import registry
        record = registry.get("MKT-08")
        self.assertEqual(record["name"], "RFM Segmentation")
        self.assertIn("QNT-MKT-04", record["also_listed_as"])
        self.assertEqual([m["method_id"] for m in record["linked_methods"]], ["rfm_scoring"])
        self.assertEqual(record["form"], "computed")

    def test_media_planning_is_catalogued_and_linked(self):
        from bp import registry
        record = registry.get("QNT-MKT-15")
        self.assertEqual(record["name"], "Media planning")
        self.assertEqual([m["method_id"] for m in record["linked_methods"]], ["media_plan"])
        self.assertEqual(record["form"], "computed")

    def test_the_page_carries_the_digital_vocabulary(self):
        terms = {item["term"] for item in subjects.detail("marketing")["glossary"]}
        for term in ("ROAS", "CPA", "CPC", "CTR", "Attribution", "A/B test", "CAC", "LTV", "UTM",
                     "GRP", "CPP", "Net reach", "Quintile score"):
            self.assertIn(term, terms)

    def test_the_page_grouping_and_period_badges_cover_the_new_tiles(self):
        page = subjects.detail("marketing")
        by_key = {tool["key"]: tool for tool in page["tools"]}
        for key in ("campaign", "attribution", "channelecon", "email", "social", "web"):
            self.assertEqual(by_key[key]["group"], "Campaigns, channels and web analytics", key)
        self.assertEqual(by_key["abtest"]["group"], "Funnel, surveys and testing")
        self.assertEqual(by_key["abtest"]["period"], "per observation")
        self.assertEqual(by_key["web"]["period"], "per period")

    def test_the_glossary_has_no_duplicate_terms(self):
        terms = [item["term"] for item in subjects.detail("marketing")["glossary"]]
        self.assertEqual(len(terms), len(set(terms)))


if __name__ == "__main__":
    unittest.main()
