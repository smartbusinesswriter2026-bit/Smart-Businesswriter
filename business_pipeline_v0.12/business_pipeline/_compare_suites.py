"""Compare the baseline suite run with the run after this task: what was fixed,
what is new."""
import io
import re

CURRENT = "D:\\SMART BUSINESSWRITER\\business_pipeline_v0.12\\business_pipeline\\_full_err.txt"
BASELINE = ("D:\\SMART BUSINESSWRITER\\_baseline_wt\\business_pipeline_v0.12\\business_pipeline"
            "\\_base_err.txt")

PATTERN = re.compile(r"^(ERROR|FAIL): (\S+) \(([^)]+)\)", flags=re.M)


def read(path):
    text = io.open(path, encoding="utf-8", errors="replace").read()
    names = set()
    for kind, name, where in PATTERN.findall(text):
        names.add((kind, "%s.%s" % (where, name)))
    summary = re.findall(r"^(FAILED|OK).*$", text, flags=re.M)
    counts = re.findall(r"^Ran (\d+) tests", text, flags=re.M)
    return names, (summary[-1] if summary else "?"), (counts[-1] if counts else "?")


current, current_summary, current_count = read(CURRENT)
baseline, baseline_summary, baseline_count = read(BASELINE)

print("baseline : %s  (%s tests, %d failures+errors)" % (baseline_summary, baseline_count, len(baseline)))
print("current  : %s  (%s tests, %d failures+errors)" % (current_summary, current_count, len(current)))
print()

fixed = sorted(baseline - current)
new = sorted(current - baseline)
print("FIXED by this task (%d):" % len(fixed))
for kind, name in fixed:
    print("  %-5s %s" % (kind, name))

print("\nNEW failures introduced by this task (%d):" % len(new))
for kind, name in new:
    print("  %-5s %s" % (kind, name))

print("\nstill failing in both (%d):" % len(current & baseline))
for kind, name in sorted(current & baseline):
    print("  %-5s %s" % (kind, name))
