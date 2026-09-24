import json
import os
import unittest
from core.task_manager import TaskManager


class TestTaskManager(unittest.TestCase):
    def setUp(self):
        self.tm = TaskManager(run_id="test_run_123")

    def tearDown(self):
        if os.path.exists(self.tm.log_path):
            os.remove(self.tm.log_path)

    def test_task_lifecycle(self):
        self.tm.add_task("task_1", "Test description", "agent_a")
        self.assertIn("task_1", self.tm.tasks)
        self.assertEqual(self.tm.tasks["task_1"]["status"], "pending")

        self.tm.start_task("task_1")
        self.assertEqual(self.tm.tasks["task_1"]["status"], "in_progress")

        self.tm.complete_task("task_1", result_summary="Success")
        self.assertEqual(self.tm.tasks["task_1"]["status"], "done")
        self.assertEqual(self.tm.tasks["task_1"]["result_summary"], "Success")

    def test_task_failure(self):
        self.tm.add_task("task_fail", "Failing task", "agent_b")
        self.tm.fail_task("task_fail", reason="Timeout error")
        self.assertEqual(self.tm.tasks["task_fail"]["status"], "failed")
        self.assertEqual(self.tm.tasks["task_fail"]["failure_reason"], "Timeout error")

    def test_activity_logging_persistence(self):
        self.tm.log("custom_event", "test_agent", "Custom details")
        self.assertTrue(os.path.exists(self.tm.log_path))

        with open(self.tm.log_path, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        event_names = [e["event"] for e in lines]
        self.assertIn("custom_event", event_names)

    def test_summary_generation(self):
        self.tm.add_task("t1", "First task", "owner_a")
        self.tm.complete_task("t1", "Finished")
        summary = self.tm.summary()
        self.assertIn("DONE", summary)
        self.assertIn("First task", summary)


if __name__ == "__main__":
    unittest.main()
