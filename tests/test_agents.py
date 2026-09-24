import os
import unittest
from unittest.mock import MagicMock

from agents.base import Agent
from agents.evaluator import EvaluatorAgent
from core.context import PipelineContext
from core.task_manager import TaskManager


class MockLLM:
    def __init__(self, response="Default mock response"):
        self.response = response
        self.calls = []

    def complete(self, system: str, prompt: str, agent_name: str, **kwargs):
        self.calls.append({"system": system, "prompt": prompt, "agent_name": agent_name})
        return self.response


class TestAgents(unittest.TestCase):
    def setUp(self):
        self.tm = TaskManager(run_id="test_agent_run")

    def tearDown(self):
        if os.path.exists(self.tm.log_path):
            os.remove(self.tm.log_path)

    def test_base_agent_ask(self):
        mock_llm = MockLLM("Generated response")
        agent = Agent(mock_llm, self.tm)
        res = agent.ask("System prompt", "User prompt")
        self.assertEqual(res, "Generated response")
        self.assertEqual(len(mock_llm.calls), 1)
        self.assertEqual(mock_llm.calls[0]["agent_name"], "agent")

    def test_evaluator_verdict_pass(self):
        mock_llm = MockLLM("PASS")
        evaluator = EvaluatorAgent(mock_llm, self.tm)
        revised = evaluator.evaluate_and_revise(
            section_key="comparative_analysis",
            section_text="Original section content",
            context="Context details",
        )
        self.assertEqual(revised, "Original section content")

    def test_evaluator_verdict_revise(self):
        # First call returns REVISE critique, second call returns rewritten section
        responses = ["REVISE\nAdd competitor pricing", "Revised section with pricing details"]
        call_count = [0]

        def complete_mock(system, prompt, agent_name, **kwargs):
            resp = responses[min(call_count[0], len(responses) - 1)]
            call_count[0] += 1
            return resp

        mock_llm = MagicMock()
        mock_llm.complete = complete_mock

        evaluator = EvaluatorAgent(mock_llm, self.tm)
        revised = evaluator.evaluate_and_revise(
            section_key="risk_factors",
            section_text="Draft text",
            context="Context details",
        )
        self.assertEqual(revised, "Revised section with pricing details")


if __name__ == "__main__":
    unittest.main()
