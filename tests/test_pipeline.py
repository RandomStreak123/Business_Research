import os
import unittest
from core.context import PipelineContext
from core.pipeline import Pipeline, Skill
from core.task_manager import TaskManager


class MockSkillA(Skill):
    name = "skill_a"
    def run(self, context: PipelineContext) -> None:
        context.sections["part_a"] = "Output from Skill A"


class MockSkillB(Skill):
    name = "skill_b"
    def run(self, context: PipelineContext) -> None:
        prior = context.sections.get("part_a", "")
        context.sections["part_b"] = f"{prior} -> Output from Skill B"


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.tm = TaskManager(run_id="test_pipeline_run")

    def tearDown(self):
        if os.path.exists(self.tm.log_path):
            os.remove(self.tm.log_path)

    def test_pipeline_context_defaults(self):
        ctx = PipelineContext(idea="AI Gateway", run_id="run_xyz")
        self.assertEqual(ctx.idea, "AI Gateway")
        self.assertEqual(ctx.run_id, "run_xyz")
        self.assertEqual(ctx.depth, "quick")
        self.assertEqual(ctx.output_format, "docx")
        self.assertEqual(ctx.sections, {})

    def test_pipeline_sequential_execution(self):
        skills = [MockSkillA(), MockSkillB()]
        pipeline = Pipeline(skills=skills, tm=self.tm)

        ctx = PipelineContext(idea="Test Idea", run_id="run_123")
        result_ctx = pipeline.run(ctx)

        self.assertIn("part_a", result_ctx.sections)
        self.assertIn("part_b", result_ctx.sections)
        self.assertEqual(result_ctx.sections["part_b"], "Output from Skill A -> Output from Skill B")


if __name__ == "__main__":
    unittest.main()
