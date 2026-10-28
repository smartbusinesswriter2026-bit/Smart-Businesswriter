"""Replay: a saved case can prove its plan, its figures and its claims still hold.

The command is the audit path a reviewer uses, so the test drives the command,
not a helper: a case is written to a file, replayed, and the exit code and
message are what a person would see.
"""

import contextlib
import io
import json
import pathlib
import tempfile
import unittest

from bp import methods
from bp.product import api, chat, replay

BRIEF = ("The grocery chain is assessing the Saudi market for a second branch; will it pay for itself? "
         "fixed cost 40000, price 25, variable 12.")


def _run(method_id, values):
    method = methods.LIBRARY[method_id]
    errors = methods.validate_inputs(method, values)
    if errors:
        raise ValueError("; ".join(errors))
    return method.impl(values)


def setUpModule():
    api.attach_compute(lambda values: methods.breakeven(values))
    api.attach_methods(_run, methods.describe)


def answer_all(state):
    for _ in range(60):
        question = chat.current_question(state)
        if not question:
            break
        if question["type"] == "choice":
            first = question["choices"][0]
            value = first[0] if isinstance(first, (list, tuple)) else first
        elif question["type"] == "number":
            value = "5"
        elif question["type"] == "items":
            value = "one; two"
        else:
            value = "the board decision"
        state = chat.answer(state, question["id"], value)
    return state


def build_state(implications="The branch must reach its volume."):
    state = answer_all(chat.start(BRIEF, "management", "pestel"))
    state = chat.confirm_plan(state)
    state = chat.attach_computation(state, "breakeven",
                                    {"fixed": "40000", "price": "25", "variable": "12"})
    state["stage"] = "evidence"
    state["evidence"] = []
    state["gaps"] = []
    return chat.draft(state, accepted_ids=[], implications=implications)


class ReplayTest(unittest.TestCase):
    def _replay(self, state):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "case.json"
            path.write_text(json.dumps(state, default=str), encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = replay.main([str(path)])
        return code, out.getvalue(), err.getvalue()

    def test_a_sound_case_replays_clean(self):
        code, out, err = self._replay(build_state())
        self.assertEqual(code, 0, err)
        result = json.loads(out)
        self.assertTrue(result["ok"])
        self.assertTrue(result["plan"]["match"])
        self.assertTrue(result["brief"]["match"])
        self.assertEqual(result["recompute"], [])
        self.assertEqual(result["claims"], [])
        self.assertEqual(result["catalogue_version"], "1")

    def test_a_tampered_figure_fails_replay_and_is_named(self):
        state = build_state()
        state["computations"]["breakeven"]["result"]["breakeven_units"] = "1"
        code, _out, err = self._replay(state)
        self.assertEqual(code, 1)
        self.assertIn("figure drift", err)
        self.assertIn("no longer reproduces", err)

    def test_a_changed_brief_fails_replay(self):
        state = build_state()
        state["brief"] = state["brief"] + " The rent is 9000."
        code, _out, err = self._replay(state)
        self.assertEqual(code, 1)
        self.assertIn("not the one the plan was frozen against", err)

    def test_an_overclaim_in_the_draft_fails_replay(self):
        state = build_state(implications="This analysis guarantees that the branch will pay for itself.")
        code, _out, err = self._replay(state)
        self.assertEqual(code, 1)
        self.assertIn("claim:", err)
        self.assertIn("guarantees", err)

    def test_a_missing_or_broken_file_is_a_usage_error_not_a_pass(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(replay.main([]), 2)
            self.assertEqual(replay.main(["C:/no/such/case.json"]), 2)
        self.assertIn("usage", err.getvalue())


if __name__ == "__main__":
    unittest.main()
