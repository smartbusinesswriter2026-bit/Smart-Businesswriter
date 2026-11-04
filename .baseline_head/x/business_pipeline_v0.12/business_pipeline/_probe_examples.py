"""One-off: every People-shelf example runs and passes its own checks."""
import copy
import io
import sys

sys.path.insert(0, "src")
from bp import templates as T  # noqa: E402

SHELF = ["template_job_characteristics", "template_kirkpatrick", "template_amo",
         "template_tuckman", "template_nine_box", "template_kotter",
         "template_competing_values", "template_org_design", "template_adkar",
         "template_lewin", "template_mckinsey_7s", "template_burke_litwin",
         "template_galbraith_star", "template_theory_of_change", "template_logic_model",
         "template_pdsa", "template_dmaic", "template_mintzberg"]

failed = 0
for kind in SHELF:
    example = T.EXAMPLES.get(kind)
    if example is None:
        print("NO EXAMPLE:", kind)
        failed += 1
        continue
    out = T.run_template(kind, copy.deepcopy(example["inputs"]))
    checks = {name: ok for name, ok in out["results"]}
    bad = [name for name, ok in checks.items() if not ok]
    print("%-28s checks=%s empty=%s %s" % (
        kind, "OK" if not bad else bad, out["analysis"]["audit"]["empty_blocks"],
        "" if not bad else "<<< FAIL"))
    failed += len(bad)

raw = io.open("src/bp/templates.py", "rb").read()
print("\ntemplates.py LF %d CRLF %d" % (raw.count(b"\n"), raw.count(b"\r\n")))
print("failed checks:", failed)
