"""One lane's git and suite discipline, in commands instead of memory.

Three lanes share this checkout, and the failure that costs the most is not a red test
- it is a commit that carries another lane's work, or a suite claim nobody can
re-check.  Both have happened here: `OPEN_ISSUES.md` records the 09:50 incident, where
a concurrent write reverted two files, took eight tests with it, and swept a lane's doc
edits into someone else's commit.

    python scripts/lane.py guard
        Before a long run: is there uncommitted work in this tree?  A twenty-minute run
        is twenty minutes in which a concurrent write can lose it.

    python scripts/lane.py commit -F msg.txt -- <path> [<path> ...]
        Commit exactly these paths.  It prints them first, refuses when a path holds no
        change, and **verifies after the fact** that the commit contains nothing else -
        so a sweep is caught at the moment it happens, not next session.

    python scripts/lane.py suite
        Run the whole suite and print a claim that cannot rot: "green at <sha> at <time>,
        N tests".  The record is appended to qa/baseline/lane-runs.txt.

It never runs `git add -A`, never deletes a file, never force-pushes, never edits the
tree.  Standard library only.
"""

import datetime
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git(*args):
    return subprocess.run(["git"] + list(args), cwd=ROOT, text=True, capture_output=True)


def guard():
    """Advisory: uncommitted work is work a concurrent write can take away."""
    status = git("status", "--short", "--untracked-files=no").stdout.strip()
    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    sha = git("rev-parse", "--short", "HEAD").stdout.strip()
    print("lane guard: branch %s at %s" % (branch, sha))
    if not status:
        print("  nothing uncommitted - safe to start a long run")
        return 0
    print("  %d file(s) hold uncommitted work:" % len(status.splitlines()))
    for line in status.splitlines():
        print("    " + line)
    print("  commit before a long run: python scripts/lane.py commit -F msg.txt -- <paths>")
    return 0


def commit(arguments):
    """Commit exactly the named paths, and prove the commit contains nothing else.

    It does **not** run `git add` for tracked files: a path-scoped commit already
    commits the named paths, and staging a tracked file in a shared tree is how another
    lane's edits get swept in.  `--new` adds the named *untracked* files, because a new
    file cannot be committed by pathspec alone.
    """
    if "-F" not in arguments or "--" not in arguments:
        print("lane commit: use -F msg.txt [--new] -- <paths>; this wrapper never assumes the paths")
        return 2
    split = arguments.index("--")
    flags, paths = arguments[:split], arguments[split + 1:]
    add_new = "--new" in flags
    flags = [flag for flag in flags if flag != "--new"]
    if not paths:
        print("lane commit: no paths given after --")
        return 2
    changed = git("status", "--short", "--untracked-files=no", "--", *paths).stdout.strip()
    untracked = [path for path in paths
                 if git("ls-files", "--error-unmatch", "--", path).returncode != 0]
    if not changed and not untracked:
        print("lane commit: none of those paths holds a change; nothing to commit")
        return 2
    print("lane commit: about to commit %d path(s):" % len(paths))
    for path in paths:
        numbers = git("diff", "--numstat", "--", path).stdout.strip().split("\t")
        if len(numbers) >= 2:
            print("  %-70s +%s -%s" % (path, numbers[0], numbers[1]))
        elif path in untracked:
            print("  %-70s (new file)" % path)
        else:
            print("  %-70s (no change)" % path)
    if untracked and not add_new:
        print("lane commit: %d path(s) are new; add --new to commit them" % len(untracked))
        return 2
    if add_new and untracked:
        added = subprocess.run(["git", "add", "--"] + untracked, cwd=ROOT, text=True,
                               capture_output=True)
        if added.returncode != 0:
            print("lane commit: git add refused:\n" + added.stderr.strip())
            return 2
    result = subprocess.run(["git", "commit"] + flags + ["--"] + paths, cwd=ROOT,
                            text=True, capture_output=True)
    print(result.stdout.strip() or result.stderr.strip())
    if result.returncode != 0:
        return result.returncode
    landed = git("show", "--name-only", "--relative", "--format=", "HEAD").stdout.split()
    extra = [name for name in landed if name not in paths]
    if extra:
        print("lane commit: WARNING - the commit carries %d path(s) you did not name:"
              % len(extra))
        for name in extra:
            print("  " + name)
        print("  `git reset --soft HEAD~1`, then commit again with a narrowed path set.")
        return 1
    print("lane commit: verified - the commit contains exactly the %d named path(s)"
          % len(paths))
    return 0


def suite():
    """Run the suite and print a claim that names the tree it was measured on."""
    sha = git("rev-parse", "--short", "HEAD").stdout.strip()
    dirty = bool(git("status", "--short", "--untracked-files=no").stdout.strip())
    started = datetime.datetime.now()
    print("lane suite: running at %s%s (about twenty minutes)"
          % (sha, " with uncommitted changes" if dirty else ""))
    result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                            cwd=ROOT, text=True, capture_output=True,
                            env=dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src")))
    finished = datetime.datetime.now()
    summary = [line for line in result.stderr.splitlines()
               if re.match(r"^(Ran \d+ tests|OK|FAILED)", line)]
    ran = next((line for line in summary if line.startswith("Ran ")), "Ran ? tests")
    verdict = "green" if result.returncode == 0 else "FAILED"
    claim = ("%s at %s on %s, %s, %.0f s%s"
             % (verdict, sha, started.strftime("%Y-%m-%d %H:%M"),
                ran.split(" in ")[0].replace("Ran ", ""),
                (finished - started).total_seconds(),
                " (tree had uncommitted changes)" if dirty else ""))
    print("lane suite: " + claim)
    for line in summary[1:]:
        print("  " + line)
    record = os.path.join(ROOT, "qa", "baseline", "lane-runs.txt")
    try:
        with open(record, "a", encoding="utf-8") as stream:
            stream.write(claim + "\n")
    except OSError as problem:
        print("lane suite: could not append the record (%s)" % problem)
    if result.returncode != 0:
        for line in result.stderr.splitlines():
            if line.startswith(("FAIL: ", "ERROR: ")):
                print("  " + line)
    return result.returncode


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    command = argv[0].lower()
    if command == "guard":
        return guard()
    if command == "commit":
        return commit(argv[1:])
    if command == "suite":
        return suite()
    print("lane: unknown command %r (guard, commit, suite)" % command)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

