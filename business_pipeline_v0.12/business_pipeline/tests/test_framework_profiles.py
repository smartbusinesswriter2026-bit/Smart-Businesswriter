"""One framework description, two surfaces: the profiles cannot drift."""

import copy
import unittest
import unittest.mock

import sys
sys.path.insert(0, "src")

from bp import templates  # noqa: E402
from bp.product import chat, framework_profiles  # noqa: E402


class ProfileTest(unittest.TestCase):
    def test_the_pestel_blocks_are_the_templates_own_blocks(self):
        described = {block["key"]: block["label"]
                     for block in templates.describe("template_pestel")["blocks"]}
        profile = {block["key"]: block["label"]
                   for block in framework_profiles.get("template_pestel")["blocks"]}
        self.assertEqual(profile, described)

    def test_the_pestel_words_are_the_conductors_own_words(self):
        """One copy of the cues: the worksheet and the chat cannot disagree."""
        conductor = {key: (label, cues) for key, label, cues, _category in chat.DIMENSIONS}
        profile = {block["key"]: (block["label"], block["cues"])
                   for block in framework_profiles.get("template_pestel")["blocks"]}
        self.assertEqual(profile, conductor)

    def test_the_two_profiles_declare_their_own_gate(self):
        """The gate is data, and each framework states its own.

        Five Forces keeps the rule the pilot was tuned on: the industry and a
        force word in the title, which is what kept a paper that merely mentions
        competition out of an industry block. PESTEL's unit is a country, so the
        binding rule there is the country; its cue may appear anywhere, which is
        also what the chat has always used for it.
        """
        five = framework_profiles.get("template_five_forces")["gate"]
        pestel = framework_profiles.get("template_pestel")["gate"]
        self.assertTrue(five["title_cue"])
        self.assertFalse(pestel["title_cue"])
        self.assertTrue(five["title_context"])
        self.assertFalse(pestel["title_context"])
        self.assertFalse(five["require_geography"])
        self.assertTrue(pestel["require_geography"])

    def test_every_conductor_dimension_builds_its_query_from_one_phrase(self):
        """The chat reads the phrase from the profile where a profile exists."""
        state = chat.start("A firm is weighing a market entry decision in Saudi Arabia for its grocery business.")
        state["answers"].update({"industry": "grocery retail", "geography": "Middle East"})
        for name, config in chat.FRAMEWORKS.items():
            for key, _label, cues, _category in config.get("dimensions") or []:
                query = chat._query(state, key, cues)
                phrase = framework_profiles.phrase(key) or chat.SEARCH_TERMS.get(key)
                self.assertTrue(query, "%s/%s built no query" % (name, key))
                if phrase:
                    self.assertIn(phrase, query, "%s/%s ignored its phrase" % (name, key))

    def test_a_phrase_never_hard_codes_one_case(self):
        """The chat used to search 'grocery retail' for any Five Forces brief."""
        banned = ("grocery", "retail", "smartphone", "cold chain", "bakery")
        for profile in framework_profiles.PROFILES.values():
            for block in profile["blocks"]:
                # A block that is quoted from the student or left as a gap is
                # never searched, so it carries no phrase to check.
                for phrase in block.get("queries") or []:
                    self.assertFalse([word for word in banned if word in phrase.lower()],
                                     "%s/%s hard-codes %r" % (profile["label"], block["key"], phrase))

    def test_an_incomplete_profile_is_refused(self):
        profile = copy.deepcopy(framework_profiles.get("template_pestel"))
        profile["notes"]["political"].pop("qualify")
        with unittest.mock.patch.dict(framework_profiles.PROFILES,
                                      {"template_pestel": profile}):
            with self.assertRaises(ValueError) as refused:
                framework_profiles.profile_for("template_pestel")
        self.assertIn("political", str(refused.exception))

    def test_a_framework_without_a_profile_has_no_extension(self):
        # A template with no profile yet: the customer journey is catalogued but
        # not built, so it must fall back to its plain worksheet.
        self.assertIsNone(framework_profiles.describe_extra("template_customer_journey"))
        self.assertFalse(framework_profiles.has("template_customer_journey"))

    def test_the_served_extension_names_the_unit_and_the_blocks(self):
        extra = framework_profiles.describe_extra("template_pestel")
        self.assertEqual(extra["unit"]["field"], "country")
        self.assertFalse(extra["ratings"])
        self.assertEqual(extra["assumption"], "probe")
        self.assertEqual(len(extra["blocks"]), 6)
        five = framework_profiles.describe_extra("template_five_forces")
        self.assertEqual(five["unit"]["field"], "industry")
        self.assertTrue(five["ratings"])
        self.assertEqual(five["assumption"], "case")

    def test_the_label_is_the_profiles_not_a_literal(self):
        self.assertEqual(framework_profiles.label_for("template_pestel"), "PESTEL")
        self.assertEqual(framework_profiles.label_for("template_five_forces"), "Porter's Five Forces")
        # A template with no profile of its own falls back to the default
        # profile's label; it never borrows another framework's name.
        self.assertEqual(framework_profiles.label_for("template_customer_journey"),
                         "Porter's Five Forces")


if __name__ == "__main__":
    unittest.main()
