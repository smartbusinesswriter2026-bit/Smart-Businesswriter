"""Report worksheet shapes and the diff size of the key product files."""

import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.getcwd(), "src"))

import bp.product.subjects as subjects  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    for path in ["src/bp/product/subjects.py", "src/bp/product/framework_profiles.py",
                 "src/bp/product/drafting.py", "src/bp/product/completion.py",
                 "src/bp/templates.py", "src/bp/registry.py"]:
        full = os.path.join(ROOT, path)
        print("%-42s size=%-8d mtime=%s" % (
            path, os.path.getsize(full),
            time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(full)))))

    print("")
    for key in ["STR-06", "PPL-03", "PPL-01", "CHG-01", "OPS-01"]:
        ws = subjects.WORKSHEETS.get(key)
        if ws is None:
            print("%-8s MISSING" % key)
            continue
        print("%-8s keys=%s" % (key, list(ws.keys())))

    print("")
    out = subprocess.run(["git", "diff", "--stat", "src/bp/"], capture_output=True, text=True,
                         cwd=ROOT).stdout
    print(out)


if __name__ == "__main__":
    main()
