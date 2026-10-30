import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

from fra_forecast.agent import execute_tool, run
from fra_forecast.sources import write_json


def tool(name, arguments=None):
    return {"output": [{"type": "function_call", "call_id": "call-test", "name": name,
                        "arguments": json.dumps(arguments or {})}]}


def answer(refs, **extra):
    return {"output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps({
        "explanation": "The saved validation policy retains raw ICON-EU; uncertainty is provisional.",
        "evidence_refs": refs, **extra})}]}]}


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        policy = {"winner": "raw_icon_eu", "weights": {"raw_icon_eu": 1.0}, "reason": "no_candidate_passed_validation_gate"}
        write_json(self.root/"comparison"/"evaluation.json", {"experiment_id": "test", "policy": policy})
        write_json(self.root/"comparison"/"forecast.json", {"experiment_id": "test", "status": "available", "policy": policy,
            "forecast_reference_time": "2026-10-30T12:00:00Z", "forecast": [{"lead_time_hours": 1, "selected": {}, "candidates": {}}]})

    def test_missing_configuration_keeps_deterministic_decision(self):
        with patch.dict("os.environ", {}, clear=True), patch("fra_forecast.agent.request") as call:
            report = run(self.root)
        call.assert_not_called()
        self.assertEqual(report["status"], "unavailable_configuration")
        self.assertEqual(report["decision"]["weights"], {"raw_icon_eu": 1.0})

    def test_two_tool_flow_returns_only_tool_derived_selection(self):
        responses = iter([tool("read_comparison"), tool("inspect_forecast", {"hours": [1]}), answer(["evaluation:test", "hour:2026-10-30T12:00:00Z:1"])])
        def call(payload, timeout):
            self.assertFalse(payload["parallel_tool_calls"])
            self.assertLessEqual(timeout, 30)
            self.assertTrue(all(t["strict"] for t in payload["tools"]))
            return next(responses)
        report = run(self.root, call=call)
        self.assertEqual(report["status"], "completed")
        self.assertEqual(len(report["tool_trace"]), 2)
        self.assertEqual(report["decision"]["winner"], "raw_icon_eu")

    def test_unknown_tool_and_invented_evidence_fall_back(self):
        report = run(self.root, call=lambda *args: tool("set_weights", {"raw_icon_eu": 0.1}))
        self.assertEqual(report["status"], "fallback_template")
        self.assertEqual(report["decision"]["weights"], {"raw_icon_eu": 1.0})
        report = run(self.root, call=lambda *args: answer(["invented"]))
        self.assertEqual(report["status"], "fallback_template")

    def test_model_cannot_add_numeric_weights_to_answer(self):
        responses = iter([tool("read_comparison"), answer(["evaluation:test"], weights={"linear_correction": 1})])
        report = run(self.root, call=lambda *args: next(responses))
        self.assertEqual(report["status"], "fallback_template")
        self.assertEqual(report["decision"]["weights"], {"raw_icon_eu": 1.0})

    def test_invalid_hours_and_repeated_refresh_rejected(self):
        for hours in ([True], [49], [1, 1], []):
            with self.assertRaises(ValueError):
                execute_tool(self.root, "inspect_forecast", {"hours": hours}, {"refreshed": False}, time.monotonic()+90)
        with self.assertRaises(ValueError):
            execute_tool(self.root, "run_forecast_comparison", {}, {"refreshed": True}, time.monotonic()+90)

    def test_repeated_tool_loop_is_bounded(self):
        calls = []
        def call(*args):
            calls.append(1)
            return tool("read_comparison")
        report = run(self.root, call=call)
        self.assertEqual(len(calls), 6)
        self.assertEqual(report["status"], "fallback_template")

    def test_mismatched_reports_do_not_produce_a_recommendation(self):
        write_json(self.root/"comparison"/"evaluation.json", {"experiment_id": "different"})
        with patch.dict("os.environ", {}, clear=True):
            report = run(self.root)
        self.assertEqual(report["decision"]["status"], "report_mismatch")
        self.assertIsNone(report["decision"]["winner"])

    def test_saved_status_is_rechecked_for_staleness(self):
        path = self.root/"comparison"/"forecast.json"
        snapshot = json.loads(path.read_text())
        snapshot["snapshot_generated_at"] = "2000-01-01T00:00:00Z"
        write_json(path, snapshot)
        with patch.dict("os.environ", {}, clear=True):
            report = run(self.root)
        self.assertEqual(report["decision"]["status"], "stale_snapshot")
