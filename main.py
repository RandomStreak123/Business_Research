#!/usr/bin/env python3
"""
Terminal entry point for the enterprise agent research backend.

Tailored for business and strategy teams:
- Researches product vision, competitors, market landscape, and risk profile.
- Outputs strictly professional Microsoft Word (.docx) documents.
- High-speed concurrent execution across web search and section evaluation.
"""

import argparse
import os
import sys

from agents.supervisor import SupervisorAgent
from config import DEFAULT_MAX_DAYS, FALLBACK_MODELS, PRIMARY_MODEL
from core.llm_client import AllModelsFailedError, LLMClient
from core.task_manager import TaskManager


def check_environment() -> bool:
    """Verifies required API keys before starting execution."""
    missing = []
    if not os.environ.get("GROQ_API_KEY"):
        missing.append("GROQ_API_KEY (Get a free key at https://console.groq.com/keys)")
    if not os.environ.get("TAVILY_API_KEY"):
        missing.append("TAVILY_API_KEY (Get a free key at https://tavily.com)")

    if missing:
        print("\n" + "=" * 70, file=sys.stderr)
        print(" PRE-FLIGHT ERROR: Missing Required API Keys", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        for item in missing:
            print(f"  ? {item}", file=sys.stderr)
        print("\nSet them in your environment or in a .env file (see .env.example).\n", file=sys.stderr)
        return False
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Multi-agent backend: turns a product/business idea "
                    "into an executive competitor & market research report (.docx)."
    )
    parser.add_argument("idea", nargs="?", default=None, help="The product or business idea to research")
    parser.add_argument("--model", default=PRIMARY_MODEL, help="Primary model to use")
    parser.add_argument(
        "--fallback-models",
        default=",".join(FALLBACK_MODELS),
        help="Comma-separated fallback models, tried in order if the primary fails",
    )
    parser.add_argument(
        "--max-days", type=int, default=DEFAULT_MAX_DAYS,
        help="Project timeline cap in days (informational, logged only)",
    )
    return parser.parse_args()


def ask_scoping_questions() -> tuple[str, str]:
    """
    Pre-run clarifying questions: competitor focus and research depth.
    Output format is strictly Microsoft Word (.docx).
    """
    print("=" * 70)
    print(" STRATEGIC AGENTIC RESEARCH SYSTEM ? BUSINESS INTELLIGENCE")
    print("=" * 70)
    print("Report Output Format: Microsoft Word (.docx) [Strictly Enabled]\n")

    focus_competitor = input(
        "Target Competitor Focus (optional ? press Enter to auto-discover): "
    ).strip()

    depth = ""
    while depth not in ("quick", "deep"):
        depth = input(
            "Research Depth ? 'quick' overview or 'deep' exhaustive study? [quick/deep] (default: quick): "
        ).strip().lower()
        if depth == "":
            depth = "quick"

    print("-" * 70)
    return focus_competitor, depth


def main() -> int:
    if not check_environment():
        return 1

    args = parse_args()

    if not args.idea:
        args.idea = input("\nEnter your product/business idea to research: ").strip()
        if not args.idea:
            print("No idea provided. Exiting.", file=sys.stderr)
            return 1

    focus_competitor, depth = ask_scoping_questions()
    fallback_models = [m.strip() for m in args.fallback_models.split(",") if m.strip()]

    tm = TaskManager()
    tm.log(
        "run_config", "system",
        f"idea='{args.idea}' model={args.model} "
        f"fallback_models={fallback_models} max_days={args.max_days} "
        f"focus_competitor='{focus_competitor}' depth={depth} output_format=docx",
    )

    try:
        llm = LLMClient(tm, primary_model=args.model, fallback_models=fallback_models)
    except RuntimeError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1

    supervisor = SupervisorAgent(llm, tm)

    print("\n[Executing Multi-Agent Pipeline: Plan -> Research -> Analysis -> Evaluation -> Synthesis -> DOCX]")
    try:
        report_path = supervisor.run_pipeline(
            args.idea, focus_competitor=focus_competitor, depth=depth, output_format="docx"
        )
    except AllModelsFailedError as exc:
        print(f"\nERROR: Pipeline execution failed ? all configured models exhausted.\n{exc}",
              file=sys.stderr)
        return 1

    print("\n" + "=" * 70)
    print(" EXECUTIVE REPORT GENERATION COMPLETE")
    print("=" * 70)
    print(f"Word Report Saved To : {report_path}")
    print(f"Audit Activity Log   : {tm.log_path}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
