"""
Shared context object passed through the middleware pipeline.

This replaces manual argument-threading between agents. Every Skill
in the pipeline reads what it needs from ONE shared object and writes
its result back into that same object.
"""

from dataclasses import dataclass, field


@dataclass
class PipelineContext:
    # --- inputs, set once at the start of a run ---
    idea: str
    focus_competitor: str = ""
    depth: str = "quick"
    output_format: str = "docx"  # Strictly docx
    run_id: str = ""

    # --- filled in as skills run, in order ---
    plan: str = ""
    product_idea: str = ""
    research: str = ""
    sections: dict = field(default_factory=dict)
    report_path: str = ""