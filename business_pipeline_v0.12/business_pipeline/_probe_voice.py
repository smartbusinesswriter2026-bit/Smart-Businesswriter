"""One-off: the voice and unit of every People-shelf profile, and the shape the
completion returns."""
import sys

sys.path.insert(0, "src")
from bp.product import framework_profiles as fp  # noqa: E402

SHELF = ["template_job_characteristics", "template_kirkpatrick", "template_amo",
         "template_tuckman", "template_nine_box", "template_kotter",
         "template_competing_values", "template_org_design", "template_adkar",
         "template_lewin", "template_mckinsey_7s", "template_burke_litwin",
         "template_galbraith_star", "template_theory_of_change", "template_logic_model",
         "template_pdsa", "template_dmaic", "template_mintzberg"]

for kind in SHELF:
    profile = fp.get(kind)
    voice = profile.get("voice") or {}
    unit = profile.get("unit") or {}
    print("%-28s unit=%-28s voice=%s" % (kind, unit, voice))
