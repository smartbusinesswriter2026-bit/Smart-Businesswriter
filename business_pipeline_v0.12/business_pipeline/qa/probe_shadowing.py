"""Probe the methods and capabilities whose formatter/typing was defined twice.

Read-only: reports which function object each frozen method actually captured,
and which formatter each capability formatter resolves to at call time.

Usage:  PYTHONPATH=src python qa/probe_shadowing.py
"""
import inspect
import sys

sys.path.insert(0, "src")

from bp import methods  # noqa: E402
from bp.product import chat  # noqa: E402


def main():
    print("== method typing hooks ==")
    for method_id, method in sorted(methods.LIBRARY.items()):
        hook = getattr(method, "typing", None)
        if hook is None:
            continue
        name = getattr(hook, "__name__", "")
        if name not in ("_tax_typing", "_risk_typing", "_social_typing"):
            continue
        line = inspect.getsourcelines(hook)[1]
        print("%-24s %-14s defined at line %s" % (method_id, name, line))
        for metric in ("equilibrium_quantity_no_tax", "quantity_traded", "consumer_share",
                       "producer_share", "income_tax_rate", "taxable_income", "deferred_tax_rate"):
            try:
                print("      %-30s -> %s" % (metric, hook(metric)))
            except Exception as error:                      # pragma: no cover - probe only
                print("      %-30s -> error %s" % (metric, error))

    print()
    print("== capability formatters that reference a duplicated helper ==")
    for key, formatter in sorted(chat.CAPABILITY_LINES.items()):
        code = getattr(formatter, "__code__", None)
        if code is None:
            continue
        names = set(code.co_names)
        if names & {"_trend_lines", "_capability_lines", "_declared_inputs_line"}:
            print("%-22s -> %s" % (key, sorted(names & {"_trend_lines"})))
    print()
    print("_trend_lines resolves to line", inspect.getsourcelines(chat._trend_lines)[1])
    print("_capability_lines resolves to line", inspect.getsourcelines(chat._capability_lines)[1])
    print("_declared_inputs_line resolves to line", inspect.getsourcelines(chat._declared_inputs_line)[1])


if __name__ == "__main__":
    main()
