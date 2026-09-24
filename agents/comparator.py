"""
Comparator / Strategic Analysis agent.

Job: take the researcher's grounded findings plus the product vision and produce:
  - a comparative analysis (strictly anchored to verified competitors)
  - risk factors (grounded in the competitive realities, no invented figures)
  - strategic recommendations (actionable, without speculative third-party claims)
"""

from agents.base import Agent

ANALYSIS_SYSTEM_PROMPT = """You are a senior business intelligence analyst. Given a \
product vision and grounded market/competitor research, produce an executive comparative analysis.

STRICT GROUNDING & FORMATTING CONTRACT:
1. CLOSED-WORLD BENCHMARKING: You may ONLY benchmark against competitors and products \
explicitly identified in the provided market research. You are FORBIDDEN from introducing \
unrelated companies, invented pricing tiers, or speculative features.
2. DIFFERENTIATION & ADVANTAGE: Detail genuine competitive advantages and distinct weaknesses. \
Be candid about defensibility and barriers to entry.
3. DATA GAPS: If competitor pricing, metrics, or market share are not in the research, explicitly \
state '[Requires Primary Diligence / Commercial Confirmation]' rather than guessing.
4. PROFESSIONAL EXECUTIVE FORMATTING: Do NOT use raw HTML tags such as <br> or <b> in tables or text. \
Do NOT use informal emojis or tick marks (such as ✅, ❌, ✔). Use clear, professional corporate terminology \
such as 'Yes', 'No', 'Supported', 'None', 'Not Available'. Use clean standard Markdown tables."""

RISK_SYSTEM_PROMPT = """You are an enterprise risk-assessment specialist. Given a product \
vision, market research, and comparative analysis, identify and deconstruct key risk factors.

STRICT GROUNDING CONTRACT:
1. ANCHORED RISKS: Every risk must logically stem from the competitive weaknesses and market \
realities established in the research and comparative analysis.
2. NO INVENTED NUMBERS: Do not invent precise percentages, exact failure rates, or unsubstantiated \
financial loss figures. State the qualitative driver and risk exposure plainly.
3. STRUCTURE: Analyze across:
   - Market Adoption & Demand Risk
   - Execution & Operational Risk
   - Technical & Integration Risk
   - Regulatory, Compliance & Liability Risk.
4. PROFESSIONAL EXECUTIVE FORMATTING: Do NOT use HTML tags (<br>) or informal emojis."""

RECOMMENDATION_SYSTEM_PROMPT = """You are an executive business strategy advisor. Given a \
product vision, market intelligence, comparative analysis, and risk assessment, provide a \
decisive, strategic recommendation and action roadmap.

STRICT GROUNDING CONTRACT:
1. GROUNDED VERDICT: State clearly whether the concept should be pursued as-is, pursued with \
targeted pivots/adjustments, or tabled. Base this directly on the competitive moat and risk profile.
2. NO SPECULATIVE PARTNERS: Do not invent specific vendor partnerships or corporate alliances \
unless verified in the research findings.
3. ACTIONABLE ROADMAP: Conclude with 3-4 concrete, phased implementation milestones (e.g. Phase 1 \
MVP Pilot, Phase 2 Compliance/Tech Validation, Phase 3 Go-To-Market).
4. PROFESSIONAL EXECUTIVE FORMATTING: Do NOT use HTML tags (<br>) or informal emojis."""


class ComparatorAgent(Agent):
    name = "comparator"

    def run(self, idea: str, research: str, focus_competitor: str = "") -> dict[str, str]:
        analysis = self._analysis(idea, research, focus_competitor)
        risks = self._risks(idea, research, analysis)
        recommendation = self._recommendation(idea, research, analysis, risks)
        return {
            "comparative_analysis": analysis,
            "risk_factors": risks,
            "recommendation": recommendation,
        }

    def _analysis(self, idea: str, research: str, focus_competitor: str = "") -> str:
        task_id = "comparative_analysis"
        self.tm.add_task(task_id, "Produce comparative analysis", self.name)
        self.tm.start_task(task_id)
        focus_note = (
            f"\nTarget Competitor Focus: Compare directly against '{focus_competitor}' as established in the research."
            if focus_competitor else ""
        )
        prompt = (
            f"Product Vision:\n{idea}\n\n"
            f"Verified Market Research:\n{research}\n\n"
            f"Write the comparative analysis section now, strictly adhering to the Grounding Contract.{focus_note}"
        )
        output = self.ask(ANALYSIS_SYSTEM_PROMPT, prompt)
        self.tm.complete_task(task_id)
        return output

    def _risks(self, idea: str, research: str, analysis: str) -> str:
        task_id = "risk_assessment"
        self.tm.add_task(task_id, "Identify risk factors", self.name)
        self.tm.start_task(task_id)
        prompt = (
            f"Product Vision:\n{idea}\n\n"
            f"Verified Market Research:\n{research}\n\n"
            f"Comparative Analysis:\n{analysis}\n\n"
            "Write the risk factors section now, strictly adhering to the Grounding Contract."
        )
        output = self.ask(RISK_SYSTEM_PROMPT, prompt)
        self.tm.complete_task(task_id)
        return output

    def _recommendation(self, idea: str, research: str, analysis: str, risks: str) -> str:
        task_id = "recommendation"
        self.tm.add_task(task_id, "Write final recommendation", self.name)
        self.tm.start_task(task_id)
        prompt = (
            f"Product Vision:\n{idea}\n\n"
            f"Verified Market Research:\n{research}\n\n"
            f"Comparative Analysis:\n{analysis}\n\n"
            f"Risk Assessment:\n{risks}\n\n"
            "Write the strategic recommendation and roadmap now, strictly adhering to the Grounding Contract."
        )
        output = self.ask(RECOMMENDATION_SYSTEM_PROMPT, prompt)
        self.tm.complete_task(task_id)
        return output
