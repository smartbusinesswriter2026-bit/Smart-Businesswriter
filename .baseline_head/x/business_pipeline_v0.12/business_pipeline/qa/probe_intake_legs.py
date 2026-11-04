"""Exercise the three intake legs in-process, with tracebacks, for debugging (read-only).

Usage:  PYTHONPATH=src python qa/probe_intake_legs.py
"""
import base64
import sys
import traceback

sys.path.insert(0, "src")

from bp import ingest  # noqa: E402
from bp.product import intake, sources_file  # noqa: E402

CSV = b"name,score\nAda,10\nBo,12.5\nCy,9\n"
BIB = b"@article{a1, author = {Smith, J.}, title = {Retail expansion}, year = {2019}}\n"


def step(label, fn):
    print("=" * 70)
    print(label)
    try:
        print(fn())
    except Exception:  # noqa: BLE001 - a probe prints the traceback
        traceback.print_exc()


def main():
    step("ingest.decode_request + to_method_inputs", lambda: ingest.to_method_inputs(
        ingest.decode_request({"filename": "scores.csv",
                               "content_base64": base64.b64encode(CSV).decode()}),
        "descriptive_stats", {"values": "score"})["inputs"])
    step("sources_file.parse", lambda: sources_file.summary(sources_file.parse("refs.bib", BIB)))
    step("intake.save + use_as_brief (in a temp store)", lambda: _brief())


def _brief():
    import os
    import tempfile
    root = tempfile.mkdtemp(prefix="bp-probe-intake-")
    os.environ["BP_INTAKE_DIR"] = root
    record = intake.save("instructions.txt", b"Compare the two expansion options.")
    used = intake.use_as_brief(record["id"])
    return {"chars": used["chars"], "unverified": used["unverified"]}


if __name__ == "__main__":
    main()
