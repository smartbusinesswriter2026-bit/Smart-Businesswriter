"""Live-lane survival check: did this session's two core edits survive the merge?"""
import inspect
import sys

sys.path.insert(0, "src")

from bp import server
from bp.methods import LIBRARY
from bp.orchestrator import Pipeline

typing_src = inspect.getsource(LIBRARY["logistic_regression"].typing)
import bp.orchestrator as O
module_src = inspect.getsource(O)
lines = [
    "logit declares ratio,4 : %s" % ('("ratio", 4)' in typing_src),
    "logit ratio,6 gone     : %s" % ('("ratio", 6)' not in typing_src),
    "honesty this_method    : %s" % ('honesty["this_method"]' in module_src),
    "own_caveats kept       : %s" % ("own_caveats" in module_src),
    "LIBRARY / PRESETS      : %d / %d" % (len(LIBRARY), len(server.PRESETS)),
]
open("qa/baseline/survived.txt", "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines))
