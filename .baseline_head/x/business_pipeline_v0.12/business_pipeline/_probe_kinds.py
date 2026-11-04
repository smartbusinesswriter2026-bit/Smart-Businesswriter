"""One-off diagnostic: how a worksheet button reaches the engine, and whether
a template with no drafting schema can still be offered."""
import sys

sys.path.insert(0, "src")
from bp import templates as T  # noqa: E402
from bp.product import drafting  # noqa: E402

for kind in ("template_stp", "template_generic_strategies", "template_adkar",
             "template_kotter", "template_raci", "template_five_forces"):
    template = T.TEMPLATES.get(kind, {})
    described = T.describe(kind) if kind in T.TEMPLATES else {}
    print("%-30s tier=%-4s form_kind=%-9s draft_supported=%s" % (
        kind, template.get("tier"), described.get("form_kind"), drafting.supported(kind)))

print()
print("drafting module surface:")
print("  SCHEMAS keys:", len(drafting.SCHEMAS))
print("  supported() source:")
import inspect  # noqa: E402
print(inspect.getsource(drafting.supported))
