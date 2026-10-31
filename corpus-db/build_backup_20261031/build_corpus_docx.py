"""Build the Word copies of the corpus documents.

    python corpus-db/build/build_corpus_docx.py             # every document
    python corpus-db/build/build_corpus_docx.py database    # just one

`--target` writes the bytes somewhere else while keeping the same source, so
a document that is open in Word (and therefore locked) can still be built and
checked. The staged copy names its own path in the footer; build the real
target once the lock is gone.

Why this wrapper exists. The house builder
`business_pipeline_v0.12/business_pipeline/scripts/build_manual_docx.py`
does the real work and is the only place the styling lives - fonts, table
shading, heading outline levels, the contents field, the running header. This
wrapper adds two things the builder cannot add for itself:

1. The corpus documents live at the workspace root and in `corpus-db/`, not
   inside the pipeline repo, so the paths, the running header and the cover
   subtitle are recorded here instead of being retyped on the command line.

2. Windows PowerShell 5.1 corrupts a non-ASCII command-line argument - an
   em dash arrives as mojibake - and the house header uses em dashes. The
   strings live in this UTF-8 source file instead, so the rendered document is
   identical on every machine that runs it.

Stdlib only. Deterministic: the same source gives the same document.
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BUILDER = os.path.join(
    ROOT, "business_pipeline_v0.12", "business_pipeline", "scripts", "build_manual_docx.py")

DOCUMENTS = {
    "database": {
        "source": os.path.join(ROOT, "DATABASE.md"),
        "target": os.path.join(ROOT, "DATABASE.docx"),
        "header": "Corpus database manual — how to build the self-enriching corpus",
        "subtitle": "Smart Business Writer — the proprietary evidence corpus, step by step",
    },
    "walkthrough": {
        "source": os.path.join(ROOT, "corpus-db", "WALKTHROUGH.md"),
        "target": os.path.join(ROOT, "corpus-db", "WALKTHROUGH.docx"),
        "header": "Corpus build walkthrough — from an empty folder to a self-filling library",
        "subtitle": "Smart Business Writer — the owner's build guide",
    },
}


def load_builder():
    """Import the house builder as a module, so the styling is not duplicated."""
    spec = importlib.util.spec_from_file_location("build_manual_docx", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    names = []
    target_override = None
    arguments = sys.argv[1:]
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument == "--target" and index + 1 < len(arguments):
            target_override = arguments[index + 1]
            index += 2
            continue
        names.append(argument)
        index += 1

    names = names or list(DOCUMENTS)
    unknown = [name for name in names if name not in DOCUMENTS]
    if unknown:
        print("unknown document(s): %s" % ", ".join(unknown))
        print("known: %s" % ", ".join(sorted(DOCUMENTS)))
        return 2

    builder = load_builder()
    for name in names:
        document = DOCUMENTS[name]
        if not os.path.exists(document["source"]):
            print("skip %s: no source at %s" % (name, document["source"]))
            continue
        target = target_override or document["target"]
        report = builder.build(document["source"], target,
                               header=document["header"],
                               subtitle=document["subtitle"])
        print("%s" % name)
        for key in ("source", "target", "bytes", "sha256", "source_sha256", "blocks",
                    "headings", "tables", "lists", "code_blocks", "paragraphs"):
            print("  %-14s %s" % (key, report[key]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
