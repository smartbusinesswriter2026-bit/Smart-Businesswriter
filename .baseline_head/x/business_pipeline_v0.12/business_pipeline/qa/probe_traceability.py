"""Reconcile the manual's E-rows with the acceptance suite's test names.

Usage:  python qa/probe_traceability.py
"""
import re
import sys

MANUAL = "qa/manual/accounting.md"
SUITE = "tests/test_subject_accounting_acceptance.py"


def main():
    manual = open(MANUAL, encoding="utf-8").read()
    suite = open(SUITE, encoding="utf-8").read()
    rows = set(re.findall(r"E-acc-(\d{3})", manual))
    tests = set(re.findall(r"def test_E_acc_(\d{3})__", suite))
    print("manual rows: %d" % len(rows))
    print("suite tests: %d" % len(tests))
    print("rows with no test:", sorted(rows - tests))
    print("tests with no row:", sorted(tests - rows))
    matrix = manual.split("## 9. Traceability matrix", 1)[1].split("## 10.", 1)[0]
    named = set(re.findall(r"test_E_acc_(\d{3})__", matrix))
    print("matrix rows: %d" % len(re.findall(r"\| E-acc-\d{3} \|", matrix)))
    print("matrix rows with no test:", sorted(named - tests))
    print("tests missing from the matrix:", sorted(tests - named))


if __name__ == "__main__":
    sys.exit(main())
