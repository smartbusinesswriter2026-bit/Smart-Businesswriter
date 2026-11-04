"""One-off: the label and the shape of a completion result, for the per-framework
test modules."""
import copy
import sys
from unittest import mock

sys.path.insert(0, "src")
from bp.product import completion, framework_profiles as fp  # noqa: E402

TEMPLATES = ["template_adkar", "template_lewin", "template_mckinsey_7s",
             "template_burke_litwin", "template_galbraith_star", "template_theory_of_change",
             "template_logic_model", "template_pdsa", "template_dmaic", "template_mintzberg"]

for kind in TEMPLATES:
    profile = fp.get(kind)
    print("%-28s label=%-52r title_prefix=%r" % (
        kind, profile.get("label"), profile.get("title_prefix")))

def academic(query, databases=None, limit=10, year_from=None):
    return {"results": [{
        "title": query[:70],
        "abstract": "Evidence on the conditions named in the query. A second sentence follows it.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal", "doi": "10.1/" + str(abs(hash(query)) % 1000000),
        "url": "https://doi.org/10.1/x", "database": "OpenAlex"}], "errors": [], "skipped": []}

def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}

profile = fp.get("template_adkar")
with mock.patch("bp.product.sources.search_academic", side_effect=academic), \
        mock.patch("bp.product.sources.search_web", side_effect=web):
    result = completion.complete("template_adkar", "The campus meal card is moving to a contactless system and the kitchen staff have to be ready.",
                                  unit_value=profile["unit"]["example"])
print("\nresult keys:", sorted(result))
print("framework:", result.get("framework"))
print("unit:", result.get("unit"))
print("block keys:", [b["key"] for b in result["blocks"]])
print("first block query:", result["blocks"][0].get("query"))
print("first block keys:", sorted(result["blocks"][0]))
print("first item:", result["blocks"][0]["items"][0] if result["blocks"][0]["items"] else None)
print("\nprofile outline keys:", sorted((profile.get("outline") or {})))
