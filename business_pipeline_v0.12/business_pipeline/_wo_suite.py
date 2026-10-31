"""Run the suite and record the outcome to a file the shell does not have to write.

    python _wo_suite.py baseline     -> _wo_baseline.txt
    python _wo_suite.py after        -> _wo_after.txt
    python _wo_suite.py compare      -> prints new / fixed / unchanged failures
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "src")
ENV = dict(os.environ, PYTHONPATH=ROOT)


def run():
    proc = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "--tb=no"],
                          cwd=HERE, env=ENV, capture_output=True, text=True)
    return proc.stdout + proc.stderr


def failures(text):
    out = []
    for line in text.splitlines():
        if line.startswith("FAILED "):
            out.append(line.split(" - ")[0].strip()[len("FAILED "):])
    return out


def summary(text):
    for line in text.splitlines():
        if " passed" in line and (" failed" in line or " error" in line) and line.strip().endswith("subtests passed in" + ""):
            pass
    tail = [line for line in text.splitlines() if " passed" in line and "==" not in line]
    return tail[-1].strip() if tail else "(no summary line)"


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    text = run()
    failed = failures(text)
    name = {"baseline": "_wo_baseline.txt", "after": "_wo_after.txt"}[mode]
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as stream:
        stream.write(summary(text) + "\n")
        stream.write("\n".join(sorted(failed)))
    print(summary(text))
    print("%d failures -> %s" % (len(failed), name))

    if mode == "compare":
        base = set(open(os.path.join(HERE, "_wo_baseline.txt"), encoding="utf-8").read().splitlines()[1:])
        after = set(failed)
        print("\nNEW failures (%d):" % len(after - base))
        for item in sorted(after - base):
            print("   ", item)
        print("\nFIXED (%d):" % len(base - after))
        for item in sorted(base - after):
            print("   ", item)
        print("\nUNCHANGED: %d" % len(base & after))


if __name__ == "__main__":
    main()
