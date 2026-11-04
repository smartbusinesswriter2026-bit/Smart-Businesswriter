"""Prove that a tree is byte-exact to a commit, by comparing git tree hashes.

    python qa/manual/suite_treehash.py <tree-dir> <commit>

The tree is staged into a throwaway index (so the working repository is never
touched) and written as a tree object; the result is compared with the commit's
own tree hash.  Equal tree hashes mean equal file names, equal modes and equal
blob contents - the definition of "byte-exact".

Why this and not a file count: the earlier baseline for the 1.99 increment was
described as "every one of 5775 tracked files hash-compared against the HEAD
blob", and in fact the tree it produced matches **no commit in this history**.
A tree hash settles the question in one comparison, and says which commit the
tree really is.

A scratch index is used deliberately: `git add` into the real index would stage
the tree into the working repository, which is exactly what must not happen.

Two differences are expected and are named in the output, because `git archive`
cannot produce them and the suite produces one of them:

  * `_baseline_wt` - a submodule pointer (a commit, not a file); `git archive`
    cannot materialise it, so the entry is absent from the copy;
  * `documents/index.json` - a generated file; the suite rewrites it while it
    runs, so a tree measured after a run differs from the commit in exactly
    this one file.

Anything else in the diff is a real difference and fails the check.
"""

import collections
import os
import subprocess
import sys
import tempfile

# expected, nameable differences between a commit and its archived copy
EXPECTED = {
    "_baseline_wt": "submodule pointer: git archive cannot materialise it",
    "business_pipeline_v0.12/business_pipeline/documents/index.json":
        "generated file: the suite rewrites it while it runs",
}

# paths excluded from the archive on purpose
EXCLUDED_PREFIXES = {
    ".baseline_head/": "committed archive of an older commit, excluded from the copy on purpose",
}


def expected_reason(path):
    if path in EXPECTED:
        return EXPECTED[path]
    for prefix, reason in EXCLUDED_PREFIXES.items():
        if path.startswith(prefix):
            return reason
    return None


def run(cwd, git_dir, work_tree, *args, index=None):
    env = dict(os.environ)
    if index:
        env["GIT_INDEX_FILE"] = index
    cmd = ["git", "--git-dir", git_dir, "--work-tree", work_tree] + list(args)
    return subprocess.run(
        cmd, cwd=cwd, check=True, capture_output=True, text=True, env=env,
    ).stdout.strip()


def main():
    repo = os.path.abspath(sys.argv[1])
    tree = os.path.abspath(sys.argv[2])
    rev = sys.argv[3]
    git_dir = os.path.join(repo, ".git")

    with tempfile.TemporaryDirectory() as tmp:
        index = os.path.join(tmp, "index")
        run(tree, git_dir, tree, "read-tree", rev, index=index)
        run(tree, git_dir, tree, "add", "-A", "--", ".", index=index)
        computed = run(tree, git_dir, tree, "write-tree", index=index)
    expected = run(repo, git_dir, repo, "rev-parse", rev + "^{tree}")

    print("tree     : %s" % tree)
    print("commit   : %s (%s)" % (rev, run(repo, git_dir, repo, "rev-parse", rev)))
    print("computed : %s" % computed)
    print("expected : %s" % expected)

    if computed == expected:
        print("RESULT: byte-exact")
        return 0

    diff = run(repo, git_dir, repo, "diff-tree", "-r", "--name-status", expected, computed)
    named = collections.Counter()
    unexpected = []
    for line in diff.splitlines():
        status, path = line.split("\t", 1)
        reason = expected_reason(path)
        if reason:
            named[reason] += 1
        else:
            unexpected.append("%s %s" % (status, path))
    print("expected differences:")
    for reason, count in named.items():
        print("   %3d  %s" % (count, reason))
    if unexpected:
        print("UNEXPECTED differences: %d" % len(unexpected))
        for line in unexpected[:20]:
            print("   " + line)
        print("RESULT: NOT byte-exact")
        return 1
    print("RESULT: byte-exact, apart from the differences named above")
    return 0


if __name__ == "__main__":
    sys.exit(main())
