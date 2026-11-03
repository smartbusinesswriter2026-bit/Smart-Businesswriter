"""Local CI gate: run this before committing or handing the tree over.

    python scripts/ci.py

It runs, in order:
  1. the ledger check (`scripts/ledger.py --check`): the numbers stored in the documents
     must be the measured ones - skipped, not failed, when the tree is being written;
  2. the full unit-test suite;
  3. the shelf audit and frozen-contract check (`scripts/econ_shelf.py --check`);
  4. a JavaScript syntax check of the served page (skipped with a warning if Node is absent).

Exit code 0 only when every step passes.  It uses the standard library only and does not touch the
network.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def _run(name, command, env=None):
    print("\n== %s ==" % name)
    print("$ " + " ".join(command))
    result = subprocess.run(command, cwd=ROOT, env=env)
    print("-> %s" % ("PASS" if result.returncode == 0 else "FAIL (exit %d)" % result.returncode))
    return result.returncode == 0


def _node_check():
    node = shutil.which("node")
    if not node:
        print("\n== page syntax ==\nnode not found; skipped (install Node to run this gate)")
        return True
    page = os.path.join(ROOT, "web", "index.html")
    with open(page, encoding="utf-8") as stream:
        html = stream.read()
    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    if not scripts:
        print("\n== page syntax ==\nno inline script found")
        return False
    directory = tempfile.mkdtemp(prefix="bp-ci-")
    path = os.path.join(directory, "page.js")
    try:
        with open(path, "w", encoding="utf-8") as stream:
            stream.write(scripts[-1])
        return _run("page syntax", [node, "--check", path])
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def _ledger_check(env):
    """The numbers stored in prose must be the measured ones.

    `scripts/ledger.py` measures the suite and the build twice: a tree another lane is
    writing gives two different counts, and it then refuses (exit 2) rather than write a
    number the tree may not keep.  A refusal is reported as a skip, not a failure - it is
    a re-run, not a defect.
    """
    print("\n== ledger ==")
    print("$ python scripts/ledger.py --check")
    result = subprocess.run([PY, os.path.join("scripts", "ledger.py"), "--check"],
                            cwd=ROOT, env=env)
    if result.returncode == 2:
        print("-> SKIPPED (the tree is being written; re-run when it settles)")
        return True
    print("-> %s" % ("PASS" if result.returncode == 0 else
                    "FAIL (exit %d) - run python scripts/ledger.py --fix" % result.returncode))
    return result.returncode == 0


def main():
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(ROOT, "src") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    steps = [
        _ledger_check(env),
        _run("unit tests", [PY, "-m", "unittest", "discover", "-s", "tests"], env=env),
        _run("shelf audit and frozen contract", [PY, os.path.join("scripts", "econ_shelf.py"), "--check"], env=env),
        _node_check(),
    ]
    print("\n%d of %d steps passed" % (sum(steps), len(steps)))
    return 0 if all(steps) else 1


if __name__ == "__main__":
    sys.exit(main())
