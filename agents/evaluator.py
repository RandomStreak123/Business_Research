"""
Evaluator agent.

Job: review each generated report section against a quality rubric
BEFORE the report is finalized. This is the piece that answers "how is
evaluation taken care of" — without it, nothing ever checks whether the
researcher/comparator's output is actually good, specific, and
grounded, versus generic filler.

Design: for each section, ask the model to verdict PASS or REVISE with
feedback. On REVISE, one rewrite attempt is made using that feedback
(bounded by config.MAX_SECTION_REVISIONS so this can never loop
forever on a stubborn section). Every verdict and revision is logged
via the shared TaskManager so the evaluation step is fully auditable,
not a silent black box.
"""

from agents.base import Agent
from config import MAX_SECTION_REVISIONS

EVAL_SYSTEM_PROMPT = """You are a quality evaluator for a business \
research report section. You will be shown the original product idea, \
supporting context, and one section of the report. Judge it against \
this rubric:
1. Specificity — does it reference concrete details (real or clearly \
flagged as placeholder search data), not generic filler that could \
apply to any business idea?
2. Grounding — are claims consistent with the supplied context, without \
inventing facts, statistics, or company names not present in it?
3. Completeness — does it actually fulfill what the section is supposed \
to cover, without trailing off or leaving obvious gaps?
4. Internal consistency — does it avoid contradicting the supplied \
context?

Respond in exactly this format:
Line 1: either the single word PASS, or the single word REVISE
If REVISE, Line 2 onward: specific, actionable feedback on what to fix \
(2-4 sentences). Do not rewrite the section yourself — only critique it."""

REVISE_SYSTEM_PROMPT = """You are revising one section of a business \
research report based on an evaluator's critique.

Rewrite the section to address every point in the feedback, while \
strictly maintaining grounded facts from the context. Do not invent \
unsupported claims. Return ONLY the revised section content without meta-commentary."""


class EvaluatorAgent(Agent):
    name = "evaluator"

    def evaluate_and_revise(self, section_key: str, section_text: str, context: str) -> str:
        task_id = f"evaluate_{section_key}"
        self.tm.add_task(task_id, f"Evaluate section: {section_key}", self.name)
        self.tm.start_task(task_id)

        current_text = section_text
        for revision_round in range(MAX_SECTION_REVISIONS + 1):
            verdict_text = self.ask(
                EVAL_SYSTEM_PROMPT,
                f"Context:\n{context}\n\nSection ({section_key}):\n{current_text}",
                max_tokens=300,
            )
            lines = verdict_text.strip().split("\n", 1)
            verdict = lines[0].strip().upper()
            feedback = lines[1].strip() if len(lines) > 1 else ""

            self.tm.log(
                "evaluation_verdict", self.name,
                f"section={section_key} round={revision_round} verdict={verdict}"
                + (f" feedback={feedback[:150]}" if feedback else ""),
            )

            if verdict == "PASS":
                self.tm.complete_task(task_id, result_summary=f"passed after {revision_round} revision(s)")
                return current_text

            if revision_round >= MAX_SECTION_REVISIONS:
                # Out of revision budget — accept current text as final,
                # but log clearly that this section did not pass clean.
                self.tm.log(
                    "evaluation_exhausted", self.name,
                    f"section={section_key} accepted without a clean PASS after "
                    f"{MAX_SECTION_REVISIONS} revision(s)",
                )
                self.tm.complete_task(task_id, result_summary="revision budget exhausted, accepted as-is")
                return current_text

            # REVISE: rewrite once using the evaluator's feedback, then loop
            # back to re-evaluate the new version.
            current_text = self.ask(
                REVISE_SYSTEM_PROMPT,
                f"Context:\n{context}\n\nOriginal section ({section_key}):\n{current_text}\n\n"
                f"Evaluator feedback:\n{feedback}\n\nRewrite the section now.",
                max_tokens=2200,
            )
            self.tm.log("section_revised", self.name, f"section={section_key} round={revision_round}")

        # Unreachable given the loop bounds above, but keeps type-checkers happy.
        return current_text
