"""
Skill implementations. Each Skill wraps one agent's capability behind
the common run(context) interface used by core.pipeline.Pipeline.

Optimized for high-speed concurrent execution and strictly DOCX report outputs.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from config import EVALUATION_MAX_WORKERS
from core.context import PipelineContext
from core.pipeline import Skill
from core.report_generator import save_report

PLAN_SYSTEM_PROMPT = """You are a strategic research project planner. Given a \
product/business idea, list the concrete research and analysis tasks \
needed to produce an executive business report, as a short numbered list \
(4-6 items). Each item should be a brief task title (e.g., "1. Map competitor landscape", \
"2. Evaluate execution and regulatory risks"). Do not write the full sections — \
only the structured plan."""

PRODUCT_IDEA_SYSTEM_PROMPT = """Restate the following product/business \
idea as a clear, executive-grade 150-250 word section for a formal business report. \
Articulate the core value proposition, target customer segment, and delivery model \
without inventing speculative technical or financial metrics. \
Do not use raw HTML tags (<br>) or informal emojis."""

SUMMARY_SYSTEM_PROMPT = """You are the lead executive synthesizer producing an \
Executive Summary for a business research report. Given the summary points of each \
section, synthesize a punchy, high-impact executive summary (200-300 words) \
structured for senior leadership:
1. The Core Opportunity & Proposition
2. Competitive Standing & Moat
3. Critical Risk Factors
4. Strategic Verdict & Next Steps.
Use clean standard Markdown without HTML tags (<br>) or informal emojis (such as ✅, ❌)."""


def _trim_text(text: str, max_chars: int = 1400) -> str:
    """Trim text to keep summary prompts well within model TPM limits."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "... [full details in section]"


class PlanningSkill(Skill):
    """Asks the model for a task plan specific to this idea, and
    registers each planned item as a real tracked task."""
    name = "planning"

    def __init__(self, supervisor):
        self.supervisor = supervisor

    def run(self, context: PipelineContext) -> None:
        plan_text = self.supervisor.ask(PLAN_SYSTEM_PROMPT, f"Idea:\n{context.idea}")
        self.supervisor.tm.log("plan_created", self.supervisor.name, plan_text.replace("\n", " | "))
        task_ids = []
        for i, line in enumerate(plan_text.strip().split("\n")):
            line = line.strip()
            if line:
                tid = f"plan_item_{i}"
                self.supervisor.tm.add_task(tid, line, self.supervisor.name)
                task_ids.append(tid)
        context.plan = plan_text


class ProductIdeaSkill(Skill):
    """Restates the raw idea as an executive report section."""
    name = "product_idea"

    def __init__(self, supervisor):
        self.supervisor = supervisor

    def run(self, context: PipelineContext) -> None:
        context.product_idea = self.supervisor.ask(
            PRODUCT_IDEA_SYSTEM_PROMPT, f"Idea:\n{context.idea}"
        )


class ResearchSkill(Skill):
    """Delegates to the ResearcherAgent with concurrent web queries."""
    name = "research"

    def __init__(self, researcher_agent):
        self.agent = researcher_agent

    def run(self, context: PipelineContext) -> None:
        context.research = self.agent.run(
            context.idea, focus_competitor=context.focus_competitor, depth=context.depth
        )
        # Progress tracked plan items
        self.agent.tm.complete_task("plan_item_0", result_summary="Market research completed")
        self.agent.tm.complete_task("plan_item_1", result_summary="Competitor analysis completed")


class AnalysisSkill(Skill):
    """Delegates to the ComparatorAgent, building contextually chained
    comparative analysis, risks, and recommendations."""
    name = "analysis"

    def __init__(self, comparator_agent):
        self.agent = comparator_agent

    def run(self, context: PipelineContext) -> None:
        comparator_out = self.agent.run(
            context.idea, context.research, focus_competitor=context.focus_competitor
        )
        context.sections.update(comparator_out)
        self.agent.tm.complete_task("plan_item_2", result_summary="Comparative differentiation analyzed")
        self.agent.tm.complete_task("plan_item_3", result_summary="Risk profile established")


class EvaluationSkill(Skill):
    """Delegates to the EvaluatorAgent for each comparator-produced section.
    Evaluates sections concurrently for maximum performance."""
    name = "evaluation"

    def __init__(self, evaluator_agent):
        self.agent = evaluator_agent

    def run(self, context: PipelineContext) -> None:
        eval_context = (
            f"Product idea:\n{context.idea}\n\n"
            f"Market research:\n{_trim_text(context.research, 2000)}"
        )
        sections_to_eval = [
            k for k in ("comparative_analysis", "risk_factors", "recommendation")
            if k in context.sections
        ]

        # Concurrent section evaluation to dramatically reduce pipeline latency
        with ThreadPoolExecutor(max_workers=min(len(sections_to_eval), EVALUATION_MAX_WORKERS)) as executor:
            futures = {
                executor.submit(
                    self.agent.evaluate_and_revise, key, context.sections[key], eval_context
                ): key
                for key in sections_to_eval
            }
            for future in as_completed(futures):
                key = futures[future]
                try:
                    revised_text = future.result()
                    context.sections[key] = revised_text
                except Exception as exc:
                    self.agent.tm.log("evaluation_error", self.agent.name, f"section={key} error={exc}")


class SummarySkill(Skill):
    """Writes the executive summary once all sections exist, carefully
    budgeting tokens to prevent rate-limit bottlenecks."""
    name = "summary"

    def __init__(self, supervisor):
        self.supervisor = supervisor

    def run(self, context: PipelineContext) -> None:
        sections_for_summary = (
            f"Product Idea:\n{context.product_idea}\n\n"
            f"Market Research Highlights:\n{_trim_text(context.research, 1200)}\n\n"
            f"Comparative Analysis:\n{_trim_text(context.sections.get('comparative_analysis', ''), 1200)}\n\n"
            f"Risks:\n{_trim_text(context.sections.get('risk_factors', ''), 1000)}\n\n"
            f"Recommendation:\n{_trim_text(context.sections.get('recommendation', ''), 1000)}"
        )
        exec_summary = self.supervisor.ask(SUMMARY_SYSTEM_PROMPT, sections_for_summary)

        context.sections["executive_summary"] = exec_summary
        context.sections["product_idea"] = context.product_idea
        context.sections["market_and_competitor_research"] = context.research

        # Complete remaining plan items
        self.supervisor.tm.complete_task("plan_item_4", result_summary="Strategic synthesis complete")
        self.supervisor.tm.complete_task("plan_item_5", result_summary="Final review complete")


class ReportSkill(Skill):
    """Final stage: writes the assembled sections strictly to Word (.docx)
    and records the output path in context."""
    name = "report"

    def run(self, context: PipelineContext) -> None:
        context.report_path = save_report(
            context.idea, context.sections, context.run_id, output_format="docx"
        )
