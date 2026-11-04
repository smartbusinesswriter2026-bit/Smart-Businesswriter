"""Probe the `typing` hooks: each frozen method must own its own unit/precision hook.

Read-only.  Reports every method whose `typing` callable shares a name or a function
object with another method's — the shadowing class that silently gave `risk_metrics`,
`tax_incidence` and `social_welfare` another method's units (B-179).

Usage:  PYTHONPATH=src python qa/probe_shadowing.py
"""
import inspect
import sys

sys.path.insert(0, "src")

from bp import methods  # noqa: E402
from bp.product import chat  # noqa: E402


def main():
    print("== one typing hook per method ==")
    by_name, by_object = {}, {}
    for method_id, method in sorted(methods.LIBRARY.items()):
        hook = getattr(method, "typing", None)
        if hook is None:
            continue
        name = getattr(hook, "__name__", repr(hook))
        line = inspect.getsourcelines(hook)[1]
        by_name.setdefault(name, []).append(method_id)
        by_object.setdefault(id(hook), []).append(method_id)
        print("%-24s %-28s defined at line %s" % (method_id, name, line))
    shared = {name: ids for name, ids in by_name.items() if len(ids) > 1}
    shared_objects = [ids for ids in by_object.values() if len(ids) > 1]
    print()
    print("shared hook names:", shared or "none")
    print("methods sharing one function object:", shared_objects or "none")

    print()
    print("== the accounting-adjacent hooks, measured ==")
    for method_id, metric in (("tax_declared", "income_tax_rate"),
                              ("tax_declared", "taxable_income"),
                              ("tax_incidence", "producer_share"),
                              ("tax_incidence", "quantity_traded"),
                              ("risk_metrics", "mean_return"),
                              ("social_welfare", "n")):
        hook = getattr(methods.LIBRARY[method_id], "typing", None)
        print("%-16s %-24s -> %s" % (method_id, metric, hook(metric) if hook else None))

    print()
    print("== capability formatters that still resolve through a shared name ==")
    for key, formatter in sorted(chat.CAPABILITY_LINES.items()):
        code = getattr(formatter, "__code__", None)
        if code and "_trend_lines" in set(code.co_names):
            print("%-22s -> _trend_lines" % key)
    print("_trend_lines resolves to line", inspect.getsourcelines(chat._trend_lines)[1])
    print("_capability_lines resolves to line", inspect.getsourcelines(chat._capability_lines)[1])
    print("_declared_inputs_line resolves to line",
          inspect.getsourcelines(chat._declared_inputs_line)[1])


if __name__ == "__main__":
    main()
