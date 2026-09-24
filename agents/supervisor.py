"""
Supervisor agent.

Orchestrates the multi-agent research backend via a middleware Pipeline of
Skills. Manages candidate delegation and plan-execute-evaluate lifecycle.
"""

from agents.base import Agent
from agents.comparator import ComparatorAgent
from agents.evaluator import EvaluatorAgent
from agents.researcher import ResearcherAgent
from agents.skills import (
    AnalysisSkill,
    EvaluationSkill,
    PlanningSkill,
    ProductIdeaSkill,
    ReportSkill,
    ResearchSkill,
    SummarySkill,
)
from core.context import PipelineContext
from core.pipeline import Pipeline


class SupervisorAgent(Agent):
    name = "supervisor"

    def __init__(self, llm, tm):
        super().__init__(llm, tm)
        self.agents = {
            "researcher": ResearcherAgent(llm, tm),
            "comparator": ComparatorAgent(llm, tm),
            "evaluator": EvaluatorAgent(llm, tm),
        }

        # Middleware pipeline chain
        self.pipeline = Pipeline(
            skills=[
                PlanningSkill(self),
                ProductIdeaSkill(self),
                ResearchSkill(self.agents["researcher"]),
                AnalysisSkill(self.agents["comparator"]),
                EvaluationSkill(self.agents["evaluator"]),
                SummarySkill(self),
                ReportSkill(),
            ],
            tm=tm,
        )

        self.last_report_text: str | None = None
        self.last_report_path: str | None = None

    def run_pipeline(self, idea: str, focus_competitor: str = "", depth: str = "quick",
                     output_format: str = "docx") -> str:
        self.tm.log(
            "pipeline_start", self.name,
            f"idea='{idea}' focus_competitor='{focus_competitor}' depth={depth} output_format=docx",
        )

        context = PipelineContext(
            idea=idea,
            focus_competitor=focus_competitor,
            depth=depth,
            output_format="docx",
            run_id=self.tm.run_id,
        )

        context = self.pipeline.run(context)

        self.last_report_text = "\n\n".join(context.sections.values())
        self.last_report_path = context.report_path

        self.tm.log("pipeline_complete", self.name, f"report written to {context.report_path}")
        self.tm.log("task_summary", self.name, "\n" + self.tm.summary())

        return context.report_path
